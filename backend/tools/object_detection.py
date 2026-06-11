import json
import os
from pathlib import Path
from typing import Any, Dict

_MODEL = None
MODEL_NAME = os.getenv("YOLO_MODEL", "yolov8n.pt")
WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "/tmp/prometheus-workspace")).resolve()
WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)


def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    try:
        from ultralytics import YOLO  # type: ignore
    except Exception as e:
        raise RuntimeError(f"ultralytics is not installed: {e}")
    _MODEL = YOLO(MODEL_NAME)
    return _MODEL


def detect(image_path: str, conf: float = 0.25) -> Dict[str, Any]:
    p = Path(image_path)
    if not p.exists():
        return {"ok": False, "error": f"Image not found: {image_path}"}

    try:
        model = _load_model()
        results = model.predict(source=str(p), conf=conf, verbose=False)
        detections = []
        for result in results:
            names = result.names
            if result.boxes is None:
                continue
            for b in result.boxes:
                cls_id = int(b.cls[0].item())
                conf_score = float(b.conf[0].item())
                xyxy = [float(x) for x in b.xyxy[0].tolist()]
                detections.append(
                    {
                        "label": names.get(cls_id, str(cls_id)),
                        "confidence": conf_score,
                        "bbox_xyxy": xyxy,
                    }
                )
        return {"ok": True, "image_path": str(p), "count": len(detections), "detections": detections}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    image_path = payload.get("image_path", "")
    conf = float(payload.get("conf", 0.25))
    return detect(image_path, conf)
