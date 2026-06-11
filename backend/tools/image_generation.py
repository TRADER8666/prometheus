import os
import time
from pathlib import Path
from typing import Any, Dict

IMAGE_DIR = Path(os.getenv("IMAGE_DIR", "/tmp/prometheus-images")).resolve()
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

_PIPELINE = None


def _device_dtype():
    try:
        import torch  # type: ignore
    except Exception as e:
        raise RuntimeError(f"torch is not installed: {e}")

    if torch.cuda.is_available():
        return "cuda", torch.float16
    return "cpu", torch.float32


def _get_pipeline():
    global _PIPELINE
    if _PIPELINE is not None:
        return _PIPELINE

    try:
        import torch  # type: ignore
        from diffusers import StableDiffusionPipeline  # type: ignore
    except Exception as e:
        raise RuntimeError(f"diffusers/torch not installed: {e}")

    device, dtype = _device_dtype()
    model_id = os.getenv("SD_MODEL_ID", "runwayml/stable-diffusion-v1-5")

    pipe = StableDiffusionPipeline.from_pretrained(model_id, torch_dtype=dtype)
    pipe = pipe.to(device)
    if device == "cuda":
        pipe.enable_attention_slicing()
    _PIPELINE = pipe
    return _PIPELINE


def generate(
    prompt: str,
    negative_prompt: str = "",
    steps: int = 25,
    guidance_scale: float = 7.5,
    width: int = 512,
    height: int = 512,
) -> Dict[str, Any]:
    if not prompt.strip():
        return {"ok": False, "error": "prompt is required"}

    try:
        pipe = _get_pipeline()
        out = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt if negative_prompt else None,
            num_inference_steps=max(1, int(steps)),
            guidance_scale=float(guidance_scale),
            width=int(width),
            height=int(height),
        )
        image = out.images[0]
        filename = f"generated_{int(time.time() * 1000)}.png"
        save_path = IMAGE_DIR / filename
        image.save(save_path)
        return {"ok": True, "image_path": str(save_path), "filename": filename}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    return generate(
        prompt=payload.get("prompt", ""),
        negative_prompt=payload.get("negative_prompt", ""),
        steps=int(payload.get("steps", 25)),
        guidance_scale=float(payload.get("guidance_scale", 7.5)),
        width=int(payload.get("width", 512)),
        height=int(payload.get("height", 512)),
    )
