import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


class SpeechToTextService:
    def __init__(self):
        self._models = {}

    def _load_model(self, model_size: str = "small"):
        if model_size in self._models:
            return self._models[model_size]
        try:
            import whisper  # type: ignore
        except Exception as e:
            raise RuntimeError(f"openai-whisper not installed: {e}")
        model = whisper.load_model(model_size)
        self._models[model_size] = model
        return model

    def transcribe_file(self, file_path: str, model_size: str = "small", language: Optional[str] = None) -> Dict[str, Any]:
        p = Path(file_path)
        if not p.exists():
            return {"ok": False, "error": f"Audio file not found: {file_path}"}
        try:
            model = self._load_model(model_size)
            result = model.transcribe(str(p), language=language)
            return {
                "ok": True,
                "text": result.get("text", "").strip(),
                "language": result.get("language"),
                "segments": result.get("segments", []),
                "model_size": model_size,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def transcribe_bytes(self, audio_bytes: bytes, suffix: str = ".wav", model_size: str = "small", language: Optional[str] = None) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
            tf.write(audio_bytes)
            tmp_path = tf.name
        return self.transcribe_file(tmp_path, model_size=model_size, language=language)
