"""LLM 클라이언트 팩토리."""
from typing import Optional
from .base import LLMClient
from .claude import ClaudeClient
from .chatgpt import ChatGPTClient
from .gemini import GeminiClient
from modules.core.config import get_llm_provider


def get_llm_client(provider: Optional[str] = None) -> LLMClient:
    """설정된 공급자에 맞는 LLM 클라이언트 반환.

    Args:
        provider: AI 공급자 이름. None일 경우 환경변수에서 읽음.
                 지원되는 공급자: 'claude', 'chatgpt', 'openai', 'gemini', 'google'

    Returns:
        LLMClient: 생성된 클라이언트 인스턴스.

    Raises:
        ValueError: 지원하지 않는 공급자인 경우.
    """
    if provider is None:
        provider = get_llm_provider()

    provider_lower = provider.lower()

    if provider_lower == "claude":
        return ClaudeClient()
    elif provider_lower in ("chatgpt", "openai", "gpt"):
        return ChatGPTClient()
    elif provider_lower in ("gemini", "google"):
        return GeminiClient()
    else:
        raise ValueError(f"지원하지 않는 AI 공급자: {provider}. 지원되는 공급자: claude, chatgpt, gemini")
