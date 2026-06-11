import json
import os
import subprocess
import tempfile
from typing import Dict, Any


def run_python(code: str, timeout: int = 8) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as td:
        script = os.path.join(td, "script.py")
        with open(script, "w", encoding="utf-8") as f:
            f.write(code)

        try:
            proc = subprocess.run(
                ["python3", script],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=td,
            )
            return {
                "ok": proc.returncode == 0,
                "stdout": proc.stdout[-6000:],
                "stderr": proc.stderr[-6000:],
                "returncode": proc.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "", "stderr": "Execution timed out", "returncode": -1}
        except Exception as e:
            return {"ok": False, "stdout": "", "stderr": str(e), "returncode": -1}


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    code = payload.get("code", "")
    return run_python(code)
