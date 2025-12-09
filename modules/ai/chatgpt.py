"""OpenAI ChatGPT 클라이언트 구현체."""
from typing import Optional
import openai
from modules.core.config import get_openai_api_key, get_openai_model
from .base import LLMClient


class ChatGPTClient(LLMClient):
    """ChatGPT API 클라이언트."""

    def __init__(self):
        self.client = openai.OpenAI(api_key=get_openai_api_key())
        self.model = get_openai_model()

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 4096) -> str:
        """ChatGPT를 사용하여 텍스트 생성.

        Usage:
            공격 시나리오 생성, 명령어 수정 등 LLM의 추론 능력이 필요한 모든 곳에서 사용됩니다.

        Args:
            prompt: 사용자 프롬프트.
            system_prompt: 시스템 프롬프트.
            max_tokens: 최대 생성 토큰 수.

        Returns:
            str: 생성된 응답 텍스트.
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7
        )

        return response.choices[0].message.content
