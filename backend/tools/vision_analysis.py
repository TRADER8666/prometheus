import base64
from pathlib import Path
from typing import Any, Dict

import httpx
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
DEFAULT_VISION_MODEL = os.getenv("VISION_MODEL", "llava")


def _encode_image(image_path: str) -> str:
    p = Path(image_path)
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    return base64.b64encode(p.read_bytes()).decode("utf-8")


def analyze(image_path: str, prompt: str, model: str = DEFAULT_VISION_MODEL) -> Dict[str, Any]:
    if not prompt.strip():
        prompt = "Describe this image in detail."

    try:
        image_b64 = _encode_image(image_path)
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "images": [image_b64],
        }
        with httpx.Client(timeout=180) as client:
            r = client.post(f"{OLLAMA_URL}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
        return {
            "ok": True,
            "model": model,
            "image_path": image_path,
            "response": data.get("response", ""),
            "raw": data,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    return analyze(
        image_path=payload.get("image_path", ""),
        prompt=payload.get("prompt", "Describe the image."),
        model=payload.get("model", DEFAULT_VISION_MODEL),
    )
