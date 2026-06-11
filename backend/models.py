from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    conversation_id: Optional[int] = None
    message: str
    model: str = "llama3.2:3b"
    profile: Optional[str] = "balanced"
    use_tools: bool = True
    use_rag: bool = True


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
