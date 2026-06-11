import shutil
import subprocess
from typing import Any, Dict, List

import psutil


def detect_hardware() -> Dict[str, Any]:
    ram_gb = round(psutil.virtual_memory().total / (1024**3), 2)
    cpu_cores = psutil.cpu_count(logical=True)
    gpu_type = "none"
    vram_gb = 0.0

    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=memory.total,name", "--format=csv,noheader,nounits"],
                text=True,
                timeout=3,
            ).strip().splitlines()
            if out:
                gpu_type = "nvidia"
                # first GPU for quick recommendation
                mem, name = [x.strip() for x in out[0].split(",", 1)]
                vram_gb = round(float(mem) / 1024.0, 2)
                gpu_name = name
            else:
                gpu_name = "unknown"
        except Exception:
            gpu_name = "unknown"
    else:
        gpu_name = "none"

    return {
        "ram_gb": ram_gb,
        "cpu_cores": cpu_cores,
        "gpu_type": gpu_type,
        "gpu_name": gpu_name,
        "vram_gb": vram_gb,
    }


def recommend_models(hw: Dict[str, Any]) -> Dict[str, List[str]]:
    quality = ["llama3.2:3b", "qwen2.5-coder:1.5b"]
    balanced = ["llama3.2:3b"]
    speed = ["qwen2.5-coder:1.5b"]

    if hw["gpu_type"] == "nvidia" and hw["vram_gb"] >= 10:
        quality = ["llama3.2:3b", "qwen2.5-coder:1.5b"]
    elif hw["ram_gb"] < 8:
        quality = ["qwen2.5-coder:1.5b"]
        balanced = ["qwen2.5-coder:1.5b"]

    return {
        "quality": quality,
        "balanced": balanced,
        "speed": speed,
        "embeddings": ["nomic-embed-text"],
    }
