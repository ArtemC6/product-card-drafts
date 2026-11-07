"""Импорт товаров из YML-выгрузки сайта (feed.xml, формат Яндекс.Маркета).

offer → входной JSON сервиса: name, vendor → manufacturer, param → specs, description.
"""
import io
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path

import httpx

USER_AGENT = "Mozilla/5.0 (compatible; product-card-drafts/1.0)"


def load_feed(source: str) -> bytes:
    """Читает выгрузку по URL или из локального файла."""
    if source.startswith(("http://", "https://")):
        response = httpx.get(source, timeout=120, follow_redirects=True, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        return response.content
    return Path(source).read_bytes()


def _child_text(element: ET.Element, tag: str) -> str:
    child = element.find(tag)
    return (child.text or "").strip() if child is not None else ""


def offer_to_product(offer: ET.Element) -> dict:
    name = _child_text(offer, "name")
    if not name:
        # Тип vendor.model: название собирается из typePrefix + vendor + model.
        parts = [_child_text(offer, tag) for tag in ("typePrefix", "vendor", "model")]
        name = " ".join(part for part in parts if part)

    specs: dict[str, str] = {}
    for param in offer.findall("param"):
        key = (param.get("name") or "").strip()
        if not key:
            continue
        value = (param.text or "").strip()
        unit = (param.get("unit") or "").strip()
        specs[key] = f"{value} {unit}" if value and unit else value

    return {
        "id": offer.get("id", ""),
        "name": name,
        "manufacturer": _child_text(offer, "vendor"),
        "specs": specs,
        "description": _child_text(offer, "description"),
    }


def iter_offers(data: bytes) -> Iterator[dict]:
    """Потоковый разбор: выгрузка всех товаров сайта может быть большой."""
    for _, element in ET.iterparse(io.BytesIO(data)):
        if element.tag == "offer":
            yield offer_to_product(element)
            element.clear()


def search_offers(data: bytes, query: str, limit: int) -> list[dict]:
    needle = query.casefold()
    found = []
    for offer in iter_offers(data):
        if needle in offer["name"].casefold():
            found.append(offer)
            if len(found) >= limit:
                break
    return found


def find_offer(data: bytes, offer_id: str) -> dict | None:
    return next((offer for offer in iter_offers(data) if offer["id"] == offer_id), None)
