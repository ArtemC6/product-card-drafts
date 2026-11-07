"""Ошибки сервиса: каждая превращается в понятное сообщение в API и CLI."""


class CardGenError(Exception):
    """Базовая ошибка сервиса."""


class ConfigError(CardGenError):
    """Не хватает настроек (например, не задан API-ключ)."""


class LLMError(CardGenError):
    """LLM API недоступен, вернул ошибку или неразборчивый ответ."""


class InsufficientDataError(CardGenError):
    """Входных данных слишком мало, чтобы писать карточку без выдумок."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__("Недостаточно данных для карточки: " + "; ".join(missing))
