"""Клиент LLM через OpenAI-совместимый Chat Completions API.

Один и тот же код работает с OpenAI и с локальными моделями (Ollama, vLLM, llama.cpp server):
меняются только LLM_BASE_URL и LLM_MODEL.
"""
from typing import Protocol

import openai

from cardgen.config import Settings
from cardgen.errors import LLMError


class ChatModel(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str:
        """Возвращает текст ответа модели (ожидается JSON)."""
        ...


class OpenAICompatibleLLM:
    def __init__(self, settings: Settings) -> None:
        # max_retries: SDK сам повторяет запрос при 429, 5xx и обрывах соединения с паузой.
        self._client = openai.OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout,
            max_retries=2,
        )
        self._model = settings.model
        self._temperature = settings.temperature

    def complete(self, messages: list[dict[str, str]]) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._temperature,
                response_format={"type": "json_object"},
            )
        except openai.APIStatusError as exc:
            raise LLMError(f"LLM API вернул ошибку {exc.status_code}: {exc.message}") from exc
        except openai.APIConnectionError as exc:
            raise LLMError(f"Не удалось связаться с LLM API: {exc}") from exc
        except openai.OpenAIError as exc:
            raise LLMError(f"Ошибка LLM API: {exc}") from exc

        if not response.choices or not response.choices[0].message.content:
            raise LLMError("LLM вернула пустой ответ")
        return response.choices[0].message.content
