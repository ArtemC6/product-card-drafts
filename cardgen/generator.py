"""Сборка карточки: вызов модели, автопроверка, повтор с обратной связью."""
from difflib import get_close_matches

from pydantic import ValidationError

from cardgen.checks import find_issues
from cardgen.errors import InsufficientDataError, LLMError
from cardgen.llm import ChatModel
from cardgen.models import NO_DATA, CardDraft, Characteristic, ProductCard, ProductInput
from cardgen.prompts import build_fix_message, build_messages

MANUFACTURER = "Производитель"


def extract_json(raw: str) -> str:
    """Вырезает JSON-объект, если модель обернула его в ```json ... ``` или текст."""
    start, end = raw.find("{"), raw.rfind("}")
    return raw[start : end + 1] if start != -1 and end > start else raw


def describe_validation_error(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors()[:5]:
        location = ".".join(str(part) for part in error["loc"]) or "ответ"
        parts.append(f"{location}: {error['msg']}")
    return "; ".join(parts)


def build_card(product: ProductInput, draft: CardDraft, warnings: list[str]) -> ProductCard:
    """Характеристики берутся из входных данных кодом, а не моделью, — выдумать значение негде."""
    characteristics = []
    if MANUFACTURER.casefold() not in (key.casefold() for key in product.specs):
        characteristics.append(Characteristic(name=MANUFACTURER, value=product.manufacturer or NO_DATA))
    characteristics += [Characteristic(name=key, value=value or NO_DATA) for key, value in product.specs.items()]

    missing_data = product.gaps()
    known = [item.name.casefold() for item in characteristics]
    for name in draft.missing_characteristics:
        key = name.casefold()
        # Модель могла назвать уже известную характеристику иначе («диапазон измерения»).
        if get_close_matches(key, known, n=1, cutoff=0.8):
            continue
        known.append(key)
        characteristics.append(Characteristic(name=name, value=NO_DATA))
        missing_data.append(f"{name} — нет во входных данных")

    return ProductCard(
        product_name=product.name,
        seo_title=draft.seo_title,
        seo_description=draft.seo_description,
        characteristics=characteristics,
        search_queries=draft.search_queries,
        commercial=draft.commercial,
        missing_data=missing_data,
        warnings=warnings,
    )


class CardGenerator:
    def __init__(self, llm: ChatModel, max_attempts: int = 3) -> None:
        self._llm = llm
        self._max_attempts = max(1, max_attempts)

    def generate(self, product: ProductInput) -> ProductCard:
        missing = product.insufficient_fields()
        if missing:
            raise InsufficientDataError(missing)

        messages = build_messages(product)
        best: tuple[CardDraft, list[str]] | None = None
        last_error = ""

        for _ in range(self._max_attempts):
            raw = self._llm.complete(messages)
            try:
                draft = CardDraft.model_validate_json(extract_json(raw))
            except ValidationError as exc:
                last_error = f"ответ не соответствует формату: {describe_validation_error(exc)}"
                issues = [last_error]
            else:
                issues = find_issues(draft, product)
                if best is None or len(issues) <= len(best[1]):
                    best = (draft, issues)
                if not issues:
                    break
            messages = [
                *messages,
                {"role": "assistant", "content": raw},
                {"role": "user", "content": build_fix_message(issues)},
            ]

        if best is None:
            raise LLMError(f"Модель не вернула корректный JSON за {self._max_attempts} попытки: {last_error}")
        draft, warnings = best
        return build_card(product, draft, warnings)
