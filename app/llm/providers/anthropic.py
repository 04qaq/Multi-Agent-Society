import json
import logging
from typing import Any

from anthropic import AsyncAnthropic

from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str | None = None, model: str = "claude-sonnet-4-20250514"):
        self._model = model
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncAnthropic(**kwargs)

    async def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        system = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs = {
            "model": self._model,
            "messages": chat_messages,
            "max_tokens": max_tokens or 2048,
        }
        if system:
            kwargs["system"] = system
        if temperature is not None:
            kwargs["temperature"] = temperature

        response = await self._client.messages.create(**kwargs)
        return response.content[0].text if response.content else ""

    async def stream_chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        system = None
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs = {
            "model": self._model,
            "messages": chat_messages,
            "max_tokens": max_tokens or 2048,
            "stream": True,
        }
        if system:
            kwargs["system"] = system
        if temperature is not None:
            kwargs["temperature"] = temperature

        async with self._client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    async def chat_structured(
        self,
        messages: list[dict],
        response_model: type | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        text = await self.chat(messages, temperature=temperature, max_tokens=max_tokens)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}
