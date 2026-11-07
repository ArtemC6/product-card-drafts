"""Автопроверка ответа модели: длины полей и числа, которых нет во входных данных."""
import re

from cardgen.models import CardDraft, ProductInput

TITLE_MAX = 70
DESCRIPTION_MIN = 800
DESCRIPTION_MAX = 1200
QUERIES_MIN = 3
QUERIES_MAX = 5

_NUMBER_RE = re.compile(r"[0-9]+(?:[.,][0-9]+)?")


def _value(token: str) -> float:
    # «1,0», «1.0» и «1» — одно и то же число; «02» и «2» тоже.
    return float(token.replace(",", "."))


def unknown_numbers(text: str, source: str) -> list[str]:
    """Числа из text, которых нет в source. Любое такое число — кандидат в выдумку."""
    allowed = {_value(token) for token in _NUMBER_RE.findall(source)}
    unknown: list[str] = []
    for token in _NUMBER_RE.findall(text):
        if _value(token) not in allowed and token not in unknown:
            unknown.append(token)
    return unknown


def generated_text(draft: CardDraft) -> str:
    return "\n".join(
        [
            draft.seo_title,
            draft.seo_description,
            *draft.search_queries,
            *draft.commercial.audience,
            *draft.commercial.tasks,
        ]
    )


def find_issues(draft: CardDraft, product: ProductInput) -> list[str]:
    """Список нарушений. Пустой список — ответ годится."""
    issues = []

    title_length = len(draft.seo_title)
    if title_length > TITLE_MAX:
        issues.append(f"seo_title: {title_length} симв., допустимо не больше {TITLE_MAX}")

    description_length = len(draft.seo_description)
    if not DESCRIPTION_MIN <= description_length <= DESCRIPTION_MAX:
        issues.append(
            f"seo_description: {description_length} симв., нужно от {DESCRIPTION_MIN} до {DESCRIPTION_MAX}"
        )

    queries = len(draft.search_queries)
    if not QUERIES_MIN <= queries <= QUERIES_MAX:
        issues.append(f"search_queries: {queries} шт., нужно от {QUERIES_MIN} до {QUERIES_MAX}")

    if not draft.commercial.audience:
        issues.append("commercial.audience: пустой список")
    if not draft.commercial.tasks:
        issues.append("commercial.tasks: пустой список")

    unknown = unknown_numbers(generated_text(draft), product.source_text())
    if unknown:
        issues.append("в тексте есть числа, которых нет во входных данных: " + ", ".join(unknown))

    return issues
