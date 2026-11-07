"""Входные данные о товаре, ответ модели и итоговая карточка."""
import html
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

NO_DATA = "данных нет"

_LINE_BREAK_TAGS_RE = re.compile(r"<br\s*/?>|</p>|</li>|</div>|</h\d>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_SPACES_RE = re.compile(r"[ \t\r\f\v\xa0]+")
_BLANK_LINES_RE = re.compile(r"\n{2,}")


def html_to_text(value: str) -> str:
    """Убирает HTML из описания: в выгрузках с сайта оно обычно в разметке."""
    text = _LINE_BREAK_TAGS_RE.sub("\n", value)
    text = html.unescape(_TAG_RE.sub("", text))
    text = _SPACES_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return _BLANK_LINES_RE.sub("\n", text).strip()


def _to_text(value: object) -> str:
    """Приводит значение из JSON к строке: числа — к строке, null — к пустой строке."""
    if value is None:
        return ""
    if isinstance(value, dict):
        raise ValueError("ожидалась строка, а не объект")
    if isinstance(value, (list, tuple)):
        return ", ".join(_to_text(item) for item in value if item is not None)
    return str(value).strip()


def _clean_list(items: list[str]) -> list[str]:
    """Обрезает пробелы, убирает пустые строки и повторы, сохраняя порядок."""
    result: list[str] = []
    for item in items:
        text = item.strip()
        if text and text not in result:
            result.append(text)
    return result


class ProductInput(BaseModel):
    """Данные о приборе, по которым готовится карточка."""

    model_config = ConfigDict(extra="ignore")

    name: str = ""
    manufacturer: str = ""
    specs: dict[str, str] = Field(default_factory=dict)
    description: str = ""

    @field_validator("name", "manufacturer", mode="before")
    @classmethod
    def _plain_text(cls, value: object) -> str:
        return _to_text(value)

    @field_validator("description", mode="before")
    @classmethod
    def _description(cls, value: object) -> str:
        return html_to_text(_to_text(value))

    @field_validator("specs", mode="before")
    @classmethod
    def _specs(cls, value: object) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError('specs должен быть объектом вида {"характеристика": "значение"}')
        specs: dict[str, str] = {}
        for key, raw in value.items():
            name = str(key).strip()
            if name:
                specs[name] = _to_text(raw)
        return specs

    def filled_specs(self) -> dict[str, str]:
        return {key: value for key, value in self.specs.items() if value}

    def insufficient_fields(self) -> list[str]:
        """Без чего карточку не написать вовсе — тогда модель не вызываем."""
        missing = []
        if not self.name:
            missing.append("name — не указано название товара")
        if not self.filled_specs() and not self.description:
            missing.append("specs / description — нет ни характеристик, ни описания")
        return missing

    def gaps(self) -> list[str]:
        """Что пусто во входных данных: карточку сделать можно, но это нужно уточнить."""
        gaps = []
        if not self.manufacturer:
            gaps.append("производитель — не указан")
        if not self.filled_specs():
            gaps.append("характеристики — не заполнены")
        gaps += [f"{key} — пустое значение во входных данных" for key, value in self.specs.items() if not value]
        if not self.description:
            gaps.append("описание — не заполнено")
        return gaps

    def source_text(self) -> str:
        """Весь входной текст — с ним сверяются числа в ответе модели."""
        parts = [self.name, self.manufacturer, self.description]
        parts += [f"{key}: {value}" for key, value in self.specs.items()]
        return "\n".join(parts)


class Commercial(BaseModel):
    """Блок для менеджера по продажам."""

    audience: list[str] = Field(description="Кому подходит прибор")
    tasks: list[str] = Field(description="Какие задачи решает")

    @field_validator("audience", "tasks")
    @classmethod
    def _clean(cls, items: list[str]) -> list[str]:
        return _clean_list(items)


class CardDraft(BaseModel):
    """То, что пишет модель. Характеристики она не пишет — их собирает код."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    seo_title: str = Field(min_length=1)
    seo_description: str = Field(min_length=1)
    search_queries: list[str]
    commercial: Commercial
    missing_characteristics: list[str] = Field(default_factory=list)

    @field_validator("search_queries", "missing_characteristics")
    @classmethod
    def _clean(cls, items: list[str]) -> list[str]:
        return _clean_list(items)


class Characteristic(BaseModel):
    name: str
    value: str


class ProductCard(BaseModel):
    """Черновик карточки товара для контент-менеджера."""

    product_name: str
    seo_title: str
    seo_description: str
    characteristics: list[Characteristic]
    search_queries: list[str]
    commercial: Commercial
    missing_data: list[str] = Field(description="Что отсутствует во входных данных и требует уточнения")
    warnings: list[str] = Field(description="Что не прошло автопроверку после всех попыток")


class CardResponse(ProductCard):
    """Ответ API: карточка плюс готовый Markdown для копирования."""

    markdown: str
