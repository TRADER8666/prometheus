import json
import re
from typing import Dict, Any, List, Tuple, Optional

from tools import (
    code_executor,
    file_ops,
    web_search,
    rag,
    object_detection,
    image_generation,
    image_editing,
    vision_analysis,
    ocr,
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
}


def parse_tool_calls(text: str) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Inline tool syntax:
    [[tool:search {"query":"latest fastapi"}]]
    [[tool:detect_objects {"image_path":"/tmp/image.png"}]]
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


def _inject_image_context(payload: Dict[str, Any], image_paths: List[str]):
    # If user provided image context and tool payload omitted an image_path,
    # default to the first attached image.
    if image_paths and "image_path" not in payload:
        payload["image_path"] = image_paths[0]


def execute_tools(input_text: str, image_paths: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    image_paths = image_paths or []
    results = []
    calls = parse_tool_calls(input_text)
    for tool, payload in calls:
        _inject_image_context(payload, image_paths)
        fn = TOOL_MAP.get(tool)
        if not fn:
            results.append({"tool": tool, "ok": False, "error": "unknown tool"})
            continue
        out = fn(payload)
        results.append({"tool": tool, "input": payload, "output": out})
    return results
