"""LLM provider with Grok primary and fallback chain."""

from enum import Enum
from typing import Any

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