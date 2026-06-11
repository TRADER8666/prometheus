import base64
from typing import Any, Dict

from .speech_to_text import SpeechToTextService
from .text_to_speech import TextToSpeechService


class VoiceIntegrationService:
    def __init__(self):
        self.stt = SpeechToTextService()
        self.tts = TextToSpeechService()

    def handle_voice_command(self, audio_bytes: bytes, model_size: str = "small", language: str | None = None) -> Dict[str, Any]:
        stt_result = self.stt.transcribe_bytes(audio_bytes, model_size=model_size, language=language)
        if not stt_result.get("ok"):
            return stt_result
        return {
            "ok": True,
            "command_text": stt_result.get("text", ""),
            "stt": stt_result,
        }

    def speak_response(self, text: str, voice_model: str | None = None) -> Dict[str, Any]:
        return self.tts.speak(text=text, voice_model=voice_model)

    def process_webrtc_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Minimal protocol helper for real-time flows.
        # Expected payload: {"type":"audio_chunk","data":"<base64 wav bytes>","language":"en"}
        ptype = payload.get("type")
        if ptype == "audio_chunk":
            raw = base64.b64decode(payload.get("data", ""))
            return self.handle_voice_command(raw, model_size=payload.get("model_size", "small"), language=payload.get("language"))
        if ptype == "speak":
            return self.speak_response(payload.get("text", ""), voice_model=payload.get("voice_model"))
        return {"ok": False, "error": "Unsupported voice payload type"}
