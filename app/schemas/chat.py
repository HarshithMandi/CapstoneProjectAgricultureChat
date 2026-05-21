from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class MessageBase(BaseModel):
    role: str = Field(..., description="Role of the message sender (user/assistant)")
    content: str = Field(..., description="Message content")


class MessageCreate(MessageBase):
    pass


class Message(MessageBase):
    id: str = Field(..., alias="_id")
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class SessionBase(BaseModel):
    title: str | None = None


class SessionCreate(SessionBase):
    pass


class Session(SessionBase):
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    memory: dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")


class ChatResponse(BaseModel):
    message: str = Field(..., description="Assistant response")
    sources: list[dict[str, Any]] = Field(default_factory=list)
    session_id: str