import json
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from orchestration.dag_engine import DAGExecutor, DAGNode
from orchestration.planner import TaskPlanner
from orchestration.swarm_coordinator import MasterAgent
from routing.model_router import ModelRouter
from tools import (
    calendar_tool,
    code_executor,
    file_ops,
    rag,
    web_search,
    object_detection,
    image_generation,
    image_editing,
    vision_analysis,
    ocr,
    git_tool,
    browser_tool,
    email_tool,
    utility_tools,
)


TOOL_MAP = {
    "code": code_executor.execute,
    "file": file_ops.execute,
    "search": web_search.execute,
    "rag": rag.execute,
    "detect_objects": object_detection.execute,
    "generate_image": image_generation.execute,
    "edit_image": image_editing.execute,
    "analyze_image": vision_analysis.execute,
    "extract_text": ocr.execute,
    "git": git_tool.execute,
    "browser": browser_tool.execute,
    "email": email_tool.execute,
    "calendar": calendar_tool.execute,
    "utility": utility_tools.execute,
}


class PrometheusAgent:
    def __init__(self, ollama_url: str):
        self.ollama_url = ollama_url
        self.router = ModelRouter()
        self.planner = TaskPlanner(ollama_url=ollama_url)

    def parse_tool_calls(self, text: str) -> List[Tuple[str, Dict[str, Any]]]:
        calls: List[Tuple[str, Dict[str, Any]]] = []
        pattern = r"\[\[tool:(\w+)\s+(\{.*?\})\]\]"
        for m in re.finditer(pattern, text):
            tool = m.group(1)
            payload: Dict[str, Any] = {}
            try:
                payload = json.loads(m.group(2))
            except Exception:
                payload = {"raw": m.group(2)}
            calls.append((tool, payload))
        return calls

    def _inject_image_context(self, payload: Dict[str, Any], image_paths: List[str]):
        if image_paths and "image_path" not in payload:
            payload["image_path"] = image_paths[0]

    def execute_tool(self, tool: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        fn = TOOL_MAP.get(tool)
        if not fn:
            return {"ok": False, "error": f"unknown tool: {tool}"}
        return fn(payload)

    def execute_tools(self, input_text: str, image_paths: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        image_paths = image_paths or []
        results: List[Dict[str, Any]] = []
        for tool, payload in self.parse_tool_calls(input_text):
            self._inject_image_context(payload, image_paths)
            out = self.execute_tool(tool, payload)
            results.append({"tool": tool, "input": payload, "output": out})
        return results

    async def _llm_text(self, prompt: str, model: str) -> str:
        payload = {"model": model, "prompt": prompt, "stream": False}
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(f"{self.ollama_url}/api/generate", json=payload)
            r.raise_for_status()
            return r.json().get("response", "")

    async def execute_node(self, node: DAGNode, original_request: str = "") -> Dict[str, Any]:
        action = node.task.get("action", "noop")
        inp = node.task.get("input", {})

        if action == "analyze_request":
            model = self.router.route_task(f"analyze {original_request}")
            try:
                text = await self._llm_text(f"Analyze this request and identify core objectives:\n{original_request}", model)
            except Exception:
                text = f"Fallback analysis: request received and parsed for execution. ({original_request[:200]})"
            return {"analysis": text, "model": model}

        if action == "execute_tools":
            req = inp.get("request", original_request)
            return {"tool_results": self.execute_tools(req)}

        if action == "summarize":
            model = self.router.route_task(f"summarize {original_request}")
            try:
                text = await self._llm_text(f"Summarize the execution status for request:\n{original_request}", model)
            except Exception:
                text = "Fallback summary: DAG execution completed with local fallback mode."
            return {"summary": text, "model": model}

        if action == "tool_call":
            tool = inp.get("tool", "")
            payload = inp.get("payload", {})
            return self.execute_tool(tool, payload)

        if action == "llm":
            model = inp.get("model") or self.router.route_task(inp.get("prompt", original_request))
            text = await self._llm_text(inp.get("prompt", original_request), model)
            return {"response": text, "model": model}

        return {"noop": True, "action": action, "input": inp}

    async def create_plan(self, request: str) -> List[Dict[str, Any]]:
        plan = await self.planner.create_plan(request)
        return plan

    async def create_dag(self, request: str) -> List[DAGNode]:
        return await self.planner.generate_dag(request)

    async def execute_dag(
        self,
        request: str,
        nodes: List[DAGNode],
        max_parallel: int = 4,
        on_state_change=None,
    ) -> Dict[str, Any]:
        async def run_node(node: DAGNode):
            return await self.execute_node(node, request)

        # swarm is used for parallel capability and observability
        swarm = MasterAgent(execute_fn=run_node, worker_count=max_parallel)

        executor = DAGExecutor(
            nodes=nodes,
            execution_fn=run_node,
            max_parallel=max_parallel,
            on_state_change=on_state_change,
        )

        dag_state = await executor.execute()
        return {
            "dag": dag_state,
            "swarm_health": swarm.health_check(),
            "swarm_messages": swarm.messages,
            "model_performance": self.router.get_performance(),
        }


# Backward-compatible helper expected by existing chat flow.
_default_agent: Optional[PrometheusAgent] = None


def get_default_agent(ollama_url: str) -> PrometheusAgent:
    global _default_agent
    if _default_agent is None:
        _default_agent = PrometheusAgent(ollama_url=ollama_url)
    return _default_agent


def execute_tools(input_text: str, image_paths: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    if _default_agent is None:
        raise RuntimeError("Default agent is not initialized. Call get_default_agent first.")
    return _default_agent.execute_tools(input_text, image_paths)
