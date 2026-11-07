"""Настройки из переменных окружения (или файла .env, который не попадает в git)."""
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from dotenv import load_dotenv

from cardgen.errors import ConfigError

DEFAULT_MODEL = "gpt-4.1-mini"

T = TypeVar("T")


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str | None
    model: str
    temperature: float
    max_attempts: int
    timeout: float


def _number(name: str, default: T, cast: Callable[[str], T]) -> T:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return cast(raw)
    except ValueError as exc:
        raise ConfigError(f"{name}: ожидалось число, получено «{raw}»") from exc


def load_settings() -> Settings:
    load_dotenv()
    base_url = os.getenv("LLM_BASE_URL", "").strip() or None
    api_key = (os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        if base_url is None:
            raise ConfigError(
                "Не задан LLM_API_KEY. Скопируйте .env.example в .env и укажите ключ "
                "или адрес локальной модели в LLM_BASE_URL."
            )
        # Локальные OpenAI-совместимые серверы (Ollama, vLLM) ключ не проверяют.
        api_key = "local"
    return Settings(
        api_key=api_key,
        base_url=base_url,
        model=os.getenv("LLM_MODEL", "").strip() or DEFAULT_MODEL,
        temperature=_number("LLM_TEMPERATURE", 0.3, float),
        max_attempts=_number("LLM_MAX_ATTEMPTS", 3, int),
        timeout=_number("LLM_TIMEOUT", 60.0, float),
    )
