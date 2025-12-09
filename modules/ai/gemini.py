"""Google Gemini 클라이언트 구현체."""
from typing import Optional
import google.generativeai as genai
from modules.core.config import get_google_api_key, get_gemini_model
from .base import LLMClient


class GeminiClient(LLMClient):
    """Gemini API 클라이언트."""

    def __init__(self):
        genai.configure(api_key=get_google_api_key())
        self.model = genai.GenerativeModel(get_gemini_model())

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 4096) -> str:
        """Gemini를 사용하여 텍스트 생성.

        Usage:
            공격 시나리오 생성, 명령어 수정 등 LLM의 추론 능력이 필요한 모든 곳에서 사용됩니다.

        Args:
            prompt: 사용자 프롬프트.
            system_prompt: 시스템 프롬프트.
            max_tokens: 최대 생성 토큰 수.

        Returns:
            str: 생성된 응답 텍스트.
        """
        # Gemini의 경우 system instruction을 생성 시 설정
        generation_config = genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=0.7
        )

        # System prompt가 있으면 user prompt 앞에 추가
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        response = self.model.generate_content(
            full_prompt,
            generation_config=generation_config
        )

        return response.text
