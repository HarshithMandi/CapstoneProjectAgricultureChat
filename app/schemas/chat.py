from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class MessageBase(BaseModel):
    role: str = Field(..., description="Role of the message sender (user/assistant)")
    content: str = Field(..., description="Message content")


class MessageCreate(MessageBase):
    pass


class Message(MessageBase):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="_id")
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionBase(BaseModel):
    title: str | None = None


class SessionCreate(SessionBase):
    pass


class Session(SessionBase):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="_id")
    user_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    memory: dict[str, Any] = Field(default_factory=dict)
    messages: list[Message] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")


class ChatResponse(BaseModel):
    message: str = Field(..., description="Assistant response")
    sources: list[dict[str, Any]] = Field(default_factory=list)
    session_id: str
