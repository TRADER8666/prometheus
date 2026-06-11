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
        from diffusers import StableDiffusionInpaintPipeline  # type: ignore
    except Exception as e:
        raise RuntimeError(f"diffusers is not installed: {e}")

    device, dtype = _device_dtype()
    model_id = os.getenv("SD_INPAINT_MODEL_ID", "runwayml/stable-diffusion-inpainting")
    pipe = StableDiffusionInpaintPipeline.from_pretrained(model_id, torch_dtype=dtype)
    pipe = pipe.to(device)
    if device == "cuda":
        pipe.enable_attention_slicing()
    _PIPELINE = pipe
    return _PIPELINE


def inpaint(
    image_path: str,
    mask_path: str,
    prompt: str,
    negative_prompt: str = "",
    steps: int = 25,
    guidance_scale: float = 7.5,
) -> Dict[str, Any]:
    img = Path(image_path)
    mask = Path(mask_path)
    if not img.exists():
        return {"ok": False, "error": f"Image not found: {image_path}"}
    if not mask.exists():
        return {"ok": False, "error": f"Mask not found: {mask_path}"}
    if not prompt.strip():
        return {"ok": False, "error": "prompt is required"}

    try:
        from PIL import Image

        pipe = _get_pipeline()
        source = Image.open(img).convert("RGB")
        mask_img = Image.open(mask).convert("RGB")

        out = pipe(
            prompt=prompt,
            image=source,
            mask_image=mask_img,
            negative_prompt=negative_prompt if negative_prompt else None,
            num_inference_steps=max(1, int(steps)),
            guidance_scale=float(guidance_scale),
        )
        result = out.images[0]
        filename = f"edited_{int(time.time() * 1000)}.png"
        save_path = IMAGE_DIR / filename
        result.save(save_path)
        return {"ok": True, "image_path": str(save_path), "filename": filename}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    return inpaint(
        image_path=payload.get("image_path", ""),
        mask_path=payload.get("mask_path", ""),
        prompt=payload.get("prompt", ""),
        negative_prompt=payload.get("negative_prompt", ""),
        steps=int(payload.get("steps", 25)),
        guidance_scale=float(payload.get("guidance_scale", 7.5)),
    )
