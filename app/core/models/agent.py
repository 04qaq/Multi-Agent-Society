from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


class ModelConfig(BaseModel):
    provider: Literal["openai", "anthropic"] = "openai"
    base_url: Optional[str] = None
    api_key: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int = 2048


class AgentStatus(str):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"


class Agent(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    id: str
    name: str
    avatar: str = ""
    persona: str = ""
    status: str = AgentStatus.OFFLINE
    llm_config: ModelConfig = ModelConfig()
    psychology_profile: str = ""
    groups: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
