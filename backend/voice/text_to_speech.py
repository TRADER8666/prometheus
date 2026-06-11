import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict


class TextToSpeechService:
    def __init__(self, output_dir: str = "/tmp/prometheus-audio"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.default_voice = os.getenv("PIPER_VOICE", "/opt/prometheus/voices/en_US-lessac-medium.onnx")

    def speak(self, text: str, voice_model: str | None = None) -> Dict[str, Any]:
        if not text.strip():
            return {"ok": False, "error": "Text is required"}

        voice_model = voice_model or self.default_voice
        out_file = self.output_dir / f"tts_{int(time.time() * 1000)}.wav"

        # piper CLI mode: echo "text" | piper --model voice.onnx --output_file out.wav
        cmd = ["piper", "--model", voice_model, "--output_file", str(out_file)]
        try:
            proc = subprocess.run(
                cmd,
                input=text,
                text=True,
                capture_output=True,
                timeout=120,
            )
            if proc.returncode != 0:
                return {
                    "ok": False,
                    "error": f"piper failed: {proc.stderr.strip() or proc.stdout.strip()}",
                    "command": " ".join(cmd),
                }
            return {"ok": True, "audio_path": str(out_file), "voice_model": voice_model}
        except FileNotFoundError:
            return {"ok": False, "error": "piper binary not found. Please install piper-tts."}
        except Exception as e:
            return {"ok": False, "error": str(e)}
