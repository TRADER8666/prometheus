import os
import platform
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict

import psutil


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    action = payload.get("action")
    try:
        if action == "clipboard_set":
            import pyperclip  # type: ignore
            pyperclip.copy(payload.get("text", ""))
            return {"ok": True}

        if action == "clipboard_get":
            import pyperclip  # type: ignore
            return {"ok": True, "text": pyperclip.paste()}

        if action == "compress":
            src = Path(payload["src"])
            dst = Path(payload.get("dst", f"{src}.zip"))
            with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zf:
                if src.is_dir():
                    for p in src.rglob("*"):
                        if p.is_file():
                            zf.write(p, p.relative_to(src.parent))
                else:
                    zf.write(src, src.name)
            return {"ok": True, "archive": str(dst)}

        if action == "extract":
            src = Path(payload["src"])
            dst = Path(payload.get("dst", "/tmp/extracted"))
            dst.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(src, "r") as zf:
                zf.extractall(dst)
            return {"ok": True, "dst": str(dst)}

        if action == "system_info":
            disk = shutil.disk_usage("/")
            return {
                "ok": True,
                "platform": platform.platform(),
                "cpu_count": psutil.cpu_count(logical=True),
                "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "cwd": os.getcwd(),
            }

        if action == "screenshot":
            # lightweight fallback using playwright if available
            from .browser_tool import execute as browser_exec
            path = payload.get("path", "/tmp/screenshot.png")
            return browser_exec({"action": "screenshot", "url": payload.get("url", "about:blank"), "path": path})

        return {"ok": False, "error": "Unknown action"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
