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


class PlanRequest(BaseModel):
    request: str


class ExecuteDAGRequest(BaseModel):
    request: Optional[str] = None
    plan: Optional[List[Dict[str, Any]]] = None
    max_parallel: int = 4


class MCPExecuteRequest(BaseModel):
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ModelRecommendRequest(BaseModel):
    task: str
    available_models: List[str] = Field(default_factory=list)


# Productivity
class NoteCreateRequest(BaseModel):
    title: str
    content: str = ""
    tags: List[str] = Field(default_factory=list)


class NoteUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


class KanbanBoardCreateRequest(BaseModel):
    name: str
    description: str = ""


class KanbanBoardUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    position: Optional[int] = None


class KanbanColumnCreateRequest(BaseModel):
    board_id: int
    name: str


class KanbanColumnUpdateRequest(BaseModel):
    name: Optional[str] = None
    position: Optional[int] = None


class KanbanCardCreateRequest(BaseModel):
    column_id: int
    title: str
    description: str = ""
    assignee: str = ""
    due_date: str = ""
    labels: List[str] = Field(default_factory=list)
    checklist: List[Dict[str, Any]] = Field(default_factory=list)


class KanbanCardUpdateRequest(BaseModel):
    column_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    labels: Optional[List[str]] = None
    checklist: Optional[List[Dict[str, Any]]] = None
    position: Optional[int] = None


class MoveCardRequest(BaseModel):
    target_column_id: int
    position: int


class BookmarkCreateRequest(BaseModel):
    url: str
    title: str = ""
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    folder: str = ""
    favicon: str = ""


class BookmarkUpdateRequest(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    folder: Optional[str] = None
    favicon: Optional[str] = None


# Scheduler
class SchedulerJobCreateRequest(BaseModel):
    name: str
    schedule: str
    action: str
    action_payload: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class SchedulerJobUpdateRequest(BaseModel):
    name: Optional[str] = None
    schedule: Optional[str] = None
    action: Optional[str] = None
    action_payload: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


# Voice
class VoiceSpeakRequest(BaseModel):
    text: str
    voice_model: Optional[str] = None

