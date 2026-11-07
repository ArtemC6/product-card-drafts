import pytest
from pydantic import ValidationError

from cardgen.models import ProductInput, html_to_text


def test_numbers_and_nulls_are_normalized():
    product = ProductInput.model_validate(
        {"name": "  Манометр ", "manufacturer": None, "specs": {"класс точности": 1.5, "питание": None}}
    )
    assert product.name == "Манометр"
    assert product.manufacturer == ""
    assert product.specs == {"класс точности": "1.5", "питание": ""}
    assert product.filled_specs() == {"класс точности": "1.5"}


def test_gaps_list_empty_fields():
    product = ProductInput.model_validate({"name": "Датчик", "specs": {"диапазон": "0–1 МПа", "питание": ""}})
    assert product.gaps() == [
        "производитель — не указан",
        "питание — пустое значение во входных данных",
        "описание — не заполнено",
    ]


def test_insufficient_fields():
    assert ProductInput.model_validate({"name": "Манометр"}).insufficient_fields() == [
        "specs / description — нет ни характеристик, ни описания"
    ]
    assert len(ProductInput.model_validate({}).insufficient_fields()) == 2


def test_specs_must_be_object():
    with pytest.raises(ValidationError):
        ProductInput.model_validate({"name": "Манометр", "specs": ["0–1 МПа"]})


def test_html_is_removed_from_description():
    assert html_to_text("<p>Для&nbsp;измерения <b>давления</b>.</p><p>Вторая строка</p>") == (
        "Для измерения давления.\nВторая строка"
    )
