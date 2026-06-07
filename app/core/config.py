from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class LLMProviderConfig(BaseSettings):
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"


class LLMConfig(BaseSettings):
    default_provider: str = "openai"
    providers: dict[str, LLMProviderConfig] = {
        "openai": LLMProviderConfig(),
        "anthropic": LLMProviderConfig(),
    }


class EmbeddingConfig(BaseSettings):
    provider: str = "openai"
    model: str = "text-embedding-3-small"
    dimensions: int = 1536


class DatabaseConfig(BaseSettings):
    host: str = "localhost"
    port: int = 5432
    name: str = "multi_agent_society"
    user: str = "postgres"
    password: str = ""


class RedisConfig(BaseSettings):
    host: str = "localhost"
    port: int = 6379


class MemoryConfig(BaseSettings):
    working_memory_limit: int = 50
    long_memory_search_top_k: int = 5
    long_memory_search_threshold: float = 0.3
    mood_judge_enabled: bool = True
    mood_judge_max_messages: int = 10
    mood_judge_timeout_s: float = 15.0
    memory_gating_mode: Literal["preset", "ocean", "hybrid"] = "ocean"


class SchedulerConfig(BaseSettings):
    auto_chat_interval: int = 30
    reply_timeout: int = 20


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        yaml_file="configs/global.yaml",
    )

    app_name: str = "Multi-Agent Society"
    debug: bool = True
    llm: LLMConfig = LLMConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    memory: MemoryConfig = MemoryConfig()
    scheduler: SchedulerConfig = SchedulerConfig()


config = AppConfig()
