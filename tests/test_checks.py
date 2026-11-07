from cardgen.checks import find_issues, unknown_numbers
from cardgen.models import CardDraft


def test_unknown_numbers_respects_formats():
    source = "Диапазон 0–1,0 МПа, модель DM 02, резьба G1/2"
    assert unknown_numbers("до 1 МПа, DM 2, G1/2, 1.0", source) == []
    assert unknown_numbers("температура до 150 °C, IP65", source) == ["150", "65"]


def test_valid_draft_has_no_issues(product, make_draft):
    draft = CardDraft.model_validate_json(make_draft())
    assert find_issues(draft, product) == []


def test_issues_are_reported(product, make_draft):
    draft = CardDraft.model_validate_json(
        make_draft(
            seo_title="Манометр " * 10,
            seo_description="Короткий текст, рабочая температура до 120 °C.",
            search_queries=["манометр"],
            commercial={"audience": [], "tasks": ["Контроль давления"]},
        )
    )
    issues = find_issues(draft, product)
    assert any(issue.startswith("seo_title") for issue in issues)
    assert any(issue.startswith("seo_description") for issue in issues)
    assert any(issue.startswith("search_queries") for issue in issues)
    assert "commercial.audience: пустой список" in issues
    assert issues[-1] == "в тексте есть числа, которых нет во входных данных: 120"
