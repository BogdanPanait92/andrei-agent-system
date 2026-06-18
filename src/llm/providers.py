"""LLM provider with Grok primary and fallback chain."""

import os
from enum import Enum
from typing import Any

from crewai import LLM as CrewAILLM
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class LLMProvider(str, Enum):
    GROK = "grok"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


def _create_grok() -> BaseChatModel:
    if not settings.xai_api_key:
        raise ValueError("XAI_API_KEY not configured")
    return ChatOpenAI(
        model=settings.grok_model,
        api_key=settings.xai_api_key,
        base_url="https://api.x.ai/v1",
        temperature=0.7,
        max_tokens=4096,
    )


def _create_anthropic() -> BaseChatModel:
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")
    return ChatAnthropic(
        model=settings.anthropic_model,
        api_key=settings.anthropic_api_key,
        temperature=0.7,
        max_tokens=4096,
    )


def _create_openai() -> BaseChatModel:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY not configured")
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.7,
        max_tokens=4096,
    )


_PROVIDERS: dict[LLMProvider, Any] = {
    LLMProvider.GROK: _create_grok,
    LLMProvider.ANTHROPIC: _create_anthropic,
    LLMProvider.OPENAI: _create_openai,
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def get_llm(provider: LLMProvider | None = None) -> BaseChatModel:
    """Get LLM instance with automatic fallback chain."""
    order = settings.llm_providers if provider is None else [provider.value]

    last_error: Exception | None = None
    for name in order:
        try:
            prov = LLMProvider(name)
            llm = _PROVIDERS[prov]()
            logger.info("llm_initialized", provider=name)
            return llm
        except (ValueError, Exception) as e:
            last_error = e
            logger.warning("llm_provider_failed", provider=name, error=str(e))

    raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")


def get_llm_with_fallback() -> BaseChatModel:
    """Alias for get_llm with full fallback chain."""
    return get_llm()


def _litellm_model_name(provider: str, model: str) -> str:
    """Map config model to LiteLLM provider/model format for CrewAI."""
    if "/" in model:
        return model
    prefixes = {"grok": "xai", "anthropic": "anthropic", "openai": "openai"}
    prefix = prefixes.get(provider, provider)
    return f"{prefix}/{model}"


def configure_llm_environment() -> None:
    """Expose API keys to LiteLLM/CrewAI via environment variables."""
    if settings.xai_api_key:
        os.environ["XAI_API_KEY"] = settings.xai_api_key
    if settings.openai_api_key and "your_" not in settings.openai_api_key:
        os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    if settings.anthropic_api_key and "your_" not in settings.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key


def get_crewai_llm() -> CrewAILLM:
    """CrewAI-compatible LLM with Grok primary and LiteLLM provider prefix."""
    configure_llm_environment()
    order = settings.llm_providers
    last_error: Exception | None = None

    creators = {
        "grok": lambda: CrewAILLM(
            model=_litellm_model_name("grok", settings.grok_model),
            api_key=settings.xai_api_key,
            temperature=0.7,
            max_tokens=4096,
        ),
        "anthropic": lambda: CrewAILLM(
            model=_litellm_model_name("anthropic", settings.anthropic_model),
            api_key=settings.anthropic_api_key,
            temperature=0.7,
            max_tokens=4096,
        ),
        "openai": lambda: CrewAILLM(
            model=_litellm_model_name("openai", settings.openai_model),
            api_key=settings.openai_api_key,
            temperature=0.7,
            max_tokens=4096,
        ),
    }

    for name in order:
        try:
            if name not in creators:
                continue
            key_attr = {"grok": "xai_api_key", "anthropic": "anthropic_api_key", "openai": "openai_api_key"}[name]
            if not getattr(settings, key_attr) or "your_" in getattr(settings, key_attr, ""):
                raise ValueError(f"{key_attr} not configured")
            llm = creators[name]()
            logger.info("crewai_llm_initialized", provider=name, model=llm.model)
            return llm
        except (ValueError, Exception) as e:
            last_error = e
            logger.warning("crewai_llm_provider_failed", provider=name, error=str(e))

    raise RuntimeError(f"All CrewAI LLM providers failed. Last error: {last_error}")