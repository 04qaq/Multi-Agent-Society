from pydantic import BaseModel, Field
from datetime import datetime


class Relationship(BaseModel):
    agent_id: str
    target_id: str
    trust: float = 0.5
    respect: float = 0.5
    love: float = 0.0
    hate: float = 0.0
    intimacy: float = 0.0
    cooperation: float = 0.5
    updated_at: datetime = Field(default_factory=datetime.now)
