from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str: ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ): ...

    @abstractmethod
    async def chat_structured(
        self,
        messages: list[dict],
        response_model: type | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any: ...
