import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from cookbook import detect_hardware


@dataclass
class TaskClassifier:
    coding_patterns: List[str] = field(default_factory=lambda: [r"\bcode\b", r"\bbug\b", r"\bpython\b", r"\bfunction\b"])
    vision_patterns: List[str] = field(default_factory=lambda: [r"\bimage\b", r"\bvision\b", r"\bocr\b", r"\bphoto\b"])
    heavy_reasoning_patterns: List[str] = field(default_factory=lambda: [r"\bprove\b", r"\bderive\b", r"\boptimize\b", r"\bstrategy\b"])

    def classify(self, text: str) -> str:
        t = text.lower()
        if any(re.search(p, t) for p in self.vision_patterns):
            return "vision"
        if any(re.search(p, t) for p in self.coding_patterns):
            return "coding"
        if any(re.search(p, t) for p in self.heavy_reasoning_patterns):
            return "reasoning"
        return "general"


class ModelRouter:
    def __init__(self):
        self.classifier = TaskClassifier()
        self.performance: Dict[str, Dict[str, Any]] = {}

    def _has_vram(self, hw: Dict[str, Any], min_vram_gb: float) -> bool:
        return float(hw.get("vram_gb", 0.0) or 0.0) >= min_vram_gb

    def route_task(self, task: str, available_models: List[str] | None = None) -> str:
        available_models = available_models or []
        task_type = self.classifier.classify(task)
        hw = detect_hardware()

        if task_type == "coding":
            candidate = "qwen2.5-coder:1.5b"
        elif task_type == "vision":
            candidate = "llava"
        elif task_type == "reasoning":
            if self._has_vram(hw, 40) and "llama3.1:70b" in available_models:
                candidate = "llama3.1:70b"
            elif "llama3.2:8b" in available_models:
                candidate = "llama3.2:8b"
            else:
                candidate = "llama3.2:3b"
        else:
            candidate = "llama3.2:3b"

        if available_models and candidate not in available_models:
            # fallback chain
            for c in ["llama3.2:3b", "qwen2.5-coder:1.5b", "llava", "nomic-embed-text"]:
                if c in available_models:
                    candidate = c
                    break

        return candidate

    def recommend(self, task: str, available_models: List[str] | None = None) -> Dict[str, Any]:
        available_models = available_models or []
        task_type = self.classifier.classify(task)
        selected = self.route_task(task, available_models)
        return {
            "task": task,
            "task_type": task_type,
            "selected_model": selected,
            "available_models": available_models,
            "hardware": detect_hardware(),
        }

    def record_performance(self, model: str, latency_ms: float, success: bool):
        stats = self.performance.setdefault(model, {"count": 0, "success": 0, "latency_ms_total": 0.0})
        stats["count"] += 1
        stats["success"] += int(bool(success))
        stats["latency_ms_total"] += float(latency_ms)

    def get_performance(self) -> Dict[str, Any]:
        out = {}
        for model, stats in self.performance.items():
            cnt = max(1, stats["count"])
            out[model] = {
                **stats,
                "success_rate": stats["success"] / cnt,
                "avg_latency_ms": stats["latency_ms_total"] / cnt,
            }
        return out
