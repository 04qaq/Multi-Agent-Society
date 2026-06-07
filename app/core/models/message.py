from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


class Message(BaseModel):
    id: str
    group_id: str
    sender_id: str
    sender_type: Literal["agent", "user"] = "user"
    content: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
