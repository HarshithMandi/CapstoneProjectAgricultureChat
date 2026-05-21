from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Role = Literal["admin", "user"]


class UserCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    full_name: str | None = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserPublic(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., alias="_id")
    email: str
    full_name: str | None = None
    role: Role
    is_active: bool = True
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class AdminSetupStatus(BaseModel):
    has_admin: bool


class UserUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None
    full_name: str | None = None
