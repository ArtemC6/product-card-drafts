"""Карточка в Markdown — чтобы контент-менеджер копировал её целиком или по блокам."""
from cardgen.models import ProductCard


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def render_markdown(card: ProductCard) -> str:
    lines = [
        f"# {card.product_name}",
        "",
        f"**SEO-заголовок** ({len(card.seo_title)} симв.): {card.seo_title}",
        "",
        f"## SEO-описание ({len(card.seo_description)} симв.)",
        "",
        card.seo_description,
        "",
        "## Ключевые характеристики",
        "",
        "| Характеристика | Значение |",
        "|---|---|",
        *(f"| {_cell(item.name)} | {_cell(item.value)} |" for item in card.characteristics),
        "",
        "## Поисковые запросы",
        "",
        *_bullets(card.search_queries),
        "",
        "## Для менеджера",
        "",
        "**Кому подходит:**",
        "",
        *_bullets(card.commercial.audience),
        "",
        "**Какие задачи решает:**",
        "",
        *_bullets(card.commercial.tasks),
    ]
    if card.missing_data:
        lines += ["", "## Требует уточнения", "", *_bullets(card.missing_data)]
    if card.warnings:
        lines += ["", "## Предупреждения автопроверки", "", *_bullets(card.warnings)]
    return "\n".join(lines) + "\n"
