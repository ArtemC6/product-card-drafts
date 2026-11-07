from cardgen.feed import find_offer, iter_offers, search_offers
from cardgen.models import ProductInput

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<yml_catalog date="2026-11-01 10:00">
  <shop>
    <offers>
      <offer id="101" available="true">
        <name>Манометр ДМ 02</name>
        <vendor>Манотомь</vendor>
        <description><![CDATA[<p>Для измерения давления.</p>]]></description>
        <param name="Класс точности">1,5</param>
        <param name="Диаметр корпуса" unit="мм">100</param>
      </offer>
      <offer id="102" type="vendor.model">
        <typePrefix>Датчик давления</typePrefix>
        <vendor>ОВЕН</vendor>
        <model>ПД100И</model>
      </offer>
    </offers>
  </shop>
</yml_catalog>
""".encode("utf-8")


def test_offers_are_converted_to_input_json():
    offers = list(iter_offers(FEED))
    assert len(offers) == 2
    assert offers[0]["specs"] == {"Класс точности": "1,5", "Диаметр корпуса": "100 мм"}
    assert offers[1]["name"] == "Датчик давления ОВЕН ПД100И"

    product = ProductInput.model_validate(offers[0])
    assert product.manufacturer == "Манотомь"
    assert product.description == "Для измерения давления."


def test_search_and_find():
    assert [offer["id"] for offer in search_offers(FEED, "датчик", limit=10)] == ["102"]
    assert find_offer(FEED, "101")["name"] == "Манометр ДМ 02"
    assert find_offer(FEED, "999") is None
