import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o-mini"):
        self._model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        kwargs = {"model": self._model, "messages": messages}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        response = await self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    async def stream_chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        kwargs = {"model": self._model, "messages": messages, "stream": True}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        stream = await self._client.chat.completions.create(**kwargs)
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    async def chat_structured(
        self,
        messages: list[dict],
        response_model: type | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        if response_model is not None:
            kwargs = {
                "model": self._model,
                "messages": messages,
                "response_format": {"type": "json_object"},
            }
            if temperature is not None:
                kwargs["temperature"] = temperature
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            response = await self._client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        else:
            text = await self.chat(messages, temperature=temperature, max_tokens=max_tokens)
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw": text}
