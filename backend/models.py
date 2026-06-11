from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    message: str
    model: str = "llama3.2:3b"
    profile: Optional[str] = "balanced"
    use_tools: bool = True
    use_rag: bool = True
    image_paths: List[str] = Field(default_factory=list)
    vision_model: Optional[str] = "llava"


class ChatResponse(BaseModel):
    conversation_id: int
    assistant_message: str


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    model: Optional[str]
    created_at: str


class ToolCallRequest(BaseModel):
    tool: str
    input: Dict[str, Any]


class ModelPullRequest(BaseModel):
    model: str


class RecommendationOut(BaseModel):
    hardware: Dict[str, Any]
    recommendations: Dict[str, List[str]]


class ImageUploadResponse(BaseModel):
    ok: bool
    filename: str
    image_path: str
    image_url: str


class ObjectDetectRequest(BaseModel):
    image_path: str
    conf: float = 0.25


class ImageGenerateRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    steps: int = 25
    guidance_scale: float = 7.5
    width: int = 512
    height: int = 512


class ImageEditRequest(BaseModel):
    image_path: str
    mask_path: str
    prompt: str
    negative_prompt: str = ""
    steps: int = 25
    guidance_scale: float = 7.5


class VisionAnalyzeRequest(BaseModel):
    image_path: str
    prompt: str = "Describe this image in detail."
    model: str = "llava"


class OCRRequest(BaseModel):
    image_path: str
    langs: List[str] = Field(default_factory=lambda: ["en"])
