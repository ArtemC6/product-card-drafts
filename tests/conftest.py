import json

import pytest

from cardgen.models import ProductInput


@pytest.fixture
def product_data() -> dict:
    return {
        "name": "Манометр показывающий DM 02",
        "manufacturer": "Манотомь",
        "specs": {
            "диапазон измерений": "0–1,6 МПа",
            "класс точности": "1,5",
            "присоединение": "G1/2",
            "диаметр корпуса": "100 мм",
        },
        "description": "Прибор предназначен для измерения избыточного давления.",
    }


@pytest.fixture
def product(product_data: dict) -> ProductInput:
    return ProductInput.model_validate(product_data)


@pytest.fixture
def make_draft():
    def _make(**overrides) -> str:
        draft = {
            "seo_title": "Манометр DM 02 Манотомь 0–1,6 МПа",
            "seo_description": "Манометр для контроля давления. " * 30,
            "search_queries": ["манометр dm 02", "манометр 1,6 мпа", "манометр 100 мм"],
            "commercial": {"audience": ["Службы КИПиА"], "tasks": ["Контроль давления"]},
            "missing_characteristics": ["Температура измеряемой среды", "Диапазон измерения"],
        }
        draft.update(overrides)
        return json.dumps(draft, ensure_ascii=False)

    return _make
