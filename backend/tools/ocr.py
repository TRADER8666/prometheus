from pathlib import Path
from typing import Any, Dict

_READER = None


def _get_reader(langs=None):
    global _READER
    if _READER is not None:
        return _READER
    langs = langs or ["en"]
    try:
        import easyocr  # type: ignore
    except Exception as e:
        raise RuntimeError(f"easyocr not installed: {e}")
    _READER = easyocr.Reader(langs, gpu=False)
    return _READER


def extract(image_path: str, langs=None) -> Dict[str, Any]:
    p = Path(image_path)
    if not p.exists():
        return {"ok": False, "error": f"Image not found: {image_path}"}

    try:
        reader = _get_reader(langs)
        result = reader.readtext(str(p))
        items = []
        full_text_parts = []
        for box, text, conf in result:
            items.append({"bbox": box, "text": text, "confidence": float(conf)})
            full_text_parts.append(text)
        return {
            "ok": True,
            "image_path": str(p),
            "full_text": "\n".join(full_text_parts),
            "items": items,
            "count": len(items),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    return extract(payload.get("image_path", ""), payload.get("langs", ["en"]))
