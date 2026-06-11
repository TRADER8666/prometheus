import json
import re
from typing import Dict, Any, List, Tuple

from tools import code_executor, file_ops, web_search, rag

TOOL_MAP = {
    "code": code_executor.execute,
    "file": file_ops.execute,
    "search": web_search.execute,
    "rag": rag.execute,
}


def parse_tool_calls(text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Simple parser for inline tool syntax:
    [[tool:search {"query":"latest fastapi"}]]
    """
    calls = []
    pattern = r"\[\[tool:(\w+)\s+(\{.*?\})\]\]"
    for m in re.finditer(pattern, text):
        tool = m.group(1)
        payload = {}
        try:
            payload = json.loads(m.group(2))
        except Exception:
            payload = {"raw": m.group(2)}
        calls.append((tool, payload))
    return calls


def execute_tools(input_text: str) -> List[Dict[str, Any]]:
    results = []
    calls = parse_tool_calls(input_text)
    for tool, payload in calls:
        fn = TOOL_MAP.get(tool)
        if not fn:
            results.append({"tool": tool, "ok": False, "error": "unknown tool"})
            continue
        out = fn(payload)
        results.append({"tool": tool, "input": payload, "output": out})
    return results
