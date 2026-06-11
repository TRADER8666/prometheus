import os
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(os.getenv("WORKSPACE_ROOT", "/tmp/prometheus-workspace")).resolve()
ROOT.mkdir(parents=True, exist_ok=True)


def _safe(path: str) -> Path:
    p = (ROOT / path).resolve()
    if not str(p).startswith(str(ROOT)):
        raise ValueError("Path escapes workspace")
    return p


def read_file(path: str) -> Dict[str, Any]:
    p = _safe(path)
    if not p.exists():
        return {"ok": False, "error": "File not found"}
    return {"ok": True, "content": p.read_text(encoding="utf-8")}


def write_file(path: str, content: str) -> Dict[str, Any]:
    p = _safe(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(p.relative_to(ROOT))}


def list_files(path: str = ".") -> Dict[str, Any]:
    p = _safe(path)
    if not p.exists():
        return {"ok": False, "error": "Path not found"}
    entries: List[str] = []
    for e in sorted(p.iterdir()):
        rel = e.relative_to(ROOT)
        entries.append(f"{rel}/" if e.is_dir() else str(rel))
    return {"ok": True, "entries": entries}


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    action = payload.get("action")
    if action == "read":
        return read_file(payload.get("path", ""))
    if action == "write":
        return write_file(payload.get("path", ""), payload.get("content", ""))
    if action == "list":
        return list_files(payload.get("path", "."))
    return {"ok": False, "error": "Unknown file action"}
