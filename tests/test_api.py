import pytest
from fastapi.testclient import TestClient

from cardgen.api import app, get_generator
from cardgen.errors import LLMError
from cardgen.generator import CardGenerator
from tests.fakes import FakeLLM


class FailingLLM:
    def complete(self, messages):
        raise LLMError("LLM API вернул ошибку 401: invalid api key")


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_card_is_returned_with_markdown(client, product_data, make_draft):
    app.dependency_overrides[get_generator] = lambda: CardGenerator(FakeLLM(make_draft()))
    response = client.post("/api/cards", json=product_data)
    assert response.status_code == 200
    body = response.json()
    assert body["seo_title"] == "Манометр DM 02 Манотомь 0–1,6 МПа"
    assert body["markdown"].startswith("# Манометр показывающий DM 02")


def test_malformed_json(client):
    app.dependency_overrides[get_generator] = lambda: CardGenerator(FakeLLM())
    response = client.post("/api/cards", content="{не json", headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "Некорректный входной JSON"


def test_insufficient_data(client):
    app.dependency_overrides[get_generator] = lambda: CardGenerator(FakeLLM())
    response = client.post("/api/cards", json={"name": "Манометр"})
    assert response.status_code == 422
    assert response.json()["detail"]["missing"]


def test_llm_error_is_502(client, product_data):
    app.dependency_overrides[get_generator] = lambda: CardGenerator(FailingLLM())
    response = client.post("/api/cards", json=product_data)
    assert response.status_code == 502
    assert "401" in response.json()["detail"]["message"]
