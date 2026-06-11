import json
import re
from typing import Any, Dict, List

import httpx

from .dag_engine import DAGNode


class TaskPlanner:
    def __init__(self, ollama_url: str, planner_model: str = "llama3.2:3b"):
        self.ollama_url = ollama_url
        self.planner_model = planner_model

    async def _llm_plan(self, request: str) -> List[Dict[str, Any]]:
        prompt = f"""
You are a task planner. Break the user request into executable subtasks.
Return strict JSON array only, each item with:
- id (string)
- action (string)
- input (object)
- dependencies (array of ids)

User request: {request}
"""
        payload = {"model": self.planner_model, "prompt": prompt, "stream": False}
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{self.ollama_url}/api/generate", json=payload)
            r.raise_for_status()
            txt = r.json().get("response", "[]")

        # best-effort JSON extraction
        m = re.search(r"\[.*\]", txt, re.S)
        raw = m.group(0) if m else "[]"
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return []

    def _fallback_plan(self, request: str) -> List[Dict[str, Any]]:
        # deterministic fallback for robustness
        return [
            {
                "id": "n1",
                "action": "analyze_request",
                "input": {"request": request},
                "dependencies": [],
            },
            {
                "id": "n2",
                "action": "execute_tools",
                "input": {"request": request},
                "dependencies": ["n1"],
            },
            {
                "id": "n3",
                "action": "summarize",
                "input": {"request": request},
                "dependencies": ["n2"],
            },
        ]

    async def create_plan(self, request: str) -> List[Dict[str, Any]]:
        try:
            plan = await self._llm_plan(request)
        except Exception:
            plan = []
        if not plan:
            plan = self._fallback_plan(request)
        return self.optimize_ordering(plan)

    def optimize_ordering(self, plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # simple optimization: ensure dependencies refer to previous ids where possible
        ids = {p.get("id") for p in plan}
        for p in plan:
            deps = [d for d in p.get("dependencies", []) if d in ids and d != p.get("id")]
            p["dependencies"] = deps
        return plan

    async def generate_dag(self, request: str) -> List[DAGNode]:
        plan = await self.create_plan(request)
        nodes: List[DAGNode] = []
        for step in plan:
            nodes.append(
                DAGNode(
                    id=step.get("id", f"node_{len(nodes)+1}"),
                    task={"action": step.get("action", "noop"), "input": step.get("input", {})},
                    dependencies=step.get("dependencies", []),
                    condition=step.get("condition"),
                )
            )
        return nodes
