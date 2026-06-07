from app.core.models.agent import ModelConfig as AgentModelConfig
from app.core.config import config
from app.llm.base import LLMProvider
from app.llm.providers.openai import OpenAIProvider
from app.llm.providers.anthropic import AnthropicProvider


class LLMRouter:
    _providers: dict[str, LLMProvider] = {}
    _mood_provider: LLMProvider | None = None

    def _build_provider(self, provider_name: str, base_url: str | None = None, api_key: str = "", model: str = "") -> LLMProvider:
        provider_config = config.llm.providers.get(provider_name)
        if provider_name == "openai":
            return OpenAIProvider(
                api_key=api_key or (provider_config.api_key if provider_config else ""),
                base_url=base_url or (provider_config.base_url if provider_config else "https://api.openai.com/v1"),
                model=model or "gpt-4o-mini",
            )
        elif provider_name == "anthropic":
            return AnthropicProvider(
                api_key=api_key or (provider_config.api_key if provider_config else ""),
                base_url=base_url or (provider_config.base_url if provider_config else None),
                model=model or "claude-sonnet-4-20250514",
            )
        raise ValueError(f"Unsupported provider: {provider_name}")

    def get_provider(self, model_cfg: AgentModelConfig) -> LLMProvider:
        key = f"{model_cfg.provider}:{model_cfg.model}"
        if key not in self._providers:
            self._providers[key] = self._build_provider(
                provider_name=model_cfg.provider,
                base_url=model_cfg.base_url,
                api_key=model_cfg.api_key,
                model=model_cfg.model,
            )
        return self._providers[key]

    def get_for_mood_judge(self) -> LLMProvider:
        if self._mood_provider is None:
            default = config.llm.default_provider
            provider_config = config.llm.providers.get(default)
            if default == "openai":
                self._mood_provider = OpenAIProvider(
                    api_key=provider_config.api_key if provider_config else "",
                    base_url=provider_config.base_url if provider_config else "https://api.openai.com/v1",
                    model="gpt-4o-mini",
                )
            else:
                self._mood_provider = self._build_provider(default)
        return self._mood_provider


llm_router = LLMRouter()
