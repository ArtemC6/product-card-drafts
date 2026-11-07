import pytest

from cardgen.errors import InsufficientDataError, LLMError
from cardgen.generator import CardGenerator, extract_json
from cardgen.models import NO_DATA, ProductInput
from tests.fakes import FakeLLM


def test_card_is_built_from_input_specs(product, make_draft):
    llm = FakeLLM(make_draft())
    card = CardGenerator(llm).generate(product)

    assert len(llm.calls) == 1
    assert card.warnings == []
    values = {item.name: item.value for item in card.characteristics}
    assert values["Производитель"] == "Манотомь"
    assert values["диапазон измерений"] == "0–1,6 МПа"
    assert values["Температура измеряемой среды"] == NO_DATA
    # «Диапазон измерения» от модели — то же, что «диапазон измерений» из входных данных.
    assert "Диапазон измерения" not in values
    assert card.missing_data == ["Температура измеряемой среды — нет во входных данных"]


def test_invented_number_triggers_retry_with_feedback(product, make_draft):
    bad = make_draft(seo_title="Манометр DM 02, до 150 °C")
    llm = FakeLLM(bad, make_draft())
    card = CardGenerator(llm).generate(product)

    assert len(llm.calls) == 2
    feedback = llm.calls[1][-1]["content"]
    assert "150" in feedback
    assert card.warnings == []


def test_broken_json_is_retried(product, make_draft):
    llm = FakeLLM("Вот карточка: {не json", "```json\n" + make_draft() + "\n```")
    card = CardGenerator(llm).generate(product)
    assert len(llm.calls) == 2
    assert card.seo_title == "Манометр DM 02 Манотомь 0–1,6 МПа"


def test_remaining_issues_become_warnings(product, make_draft):
    short = make_draft(seo_description="Слишком коротко.")
    card = CardGenerator(FakeLLM(short, short), max_attempts=2).generate(product)
    assert card.warnings and card.warnings[0].startswith("seo_description")


def test_no_valid_json_raises(product):
    with pytest.raises(LLMError):
        CardGenerator(FakeLLM("нет", "нет"), max_attempts=2).generate(product)


def test_insufficient_data_skips_llm():
    llm = FakeLLM()
    with pytest.raises(InsufficientDataError) as exc_info:
        CardGenerator(llm).generate(ProductInput.model_validate({"name": "Манометр", "specs": {"класс": ""}}))
    assert llm.calls == []
    assert exc_info.value.missing


def test_extract_json():
    assert extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert extract_json("без json") == "без json"
