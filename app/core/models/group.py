from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class Member(BaseModel):
    member_id: str
    member_type: Literal["agent", "user"]


class Group(BaseModel):
    id: str
    name: str
    members: list[Member] = Field(default_factory=list)
    auto_chat: bool = False
    auto_chat_enabled: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
