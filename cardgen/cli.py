"""Командная строка.

python -m cardgen generate examples/input/*.json --out examples/output
python -m cardgen feed <URL или путь к feed.xml> --search манометр
python -m cardgen feed <URL или путь к feed.xml> --id 12345 --out examples/input/item.json
"""
import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
from pydantic import ValidationError

from cardgen.config import load_settings
from cardgen.errors import CardGenError, ConfigError
from cardgen.feed import find_offer, load_feed, search_offers
from cardgen.generator import CardGenerator, describe_validation_error
from cardgen.llm import OpenAICompatibleLLM
from cardgen.models import ProductInput
from cardgen.render import render_markdown


class InputFileError(Exception):
    pass


def load_products(path: Path) -> list[ProductInput]:
    """Файл с одним товаром (объект) или с несколькими (массив объектов)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InputFileError(f"не удалось прочитать файл: {exc.strerror}") from exc
    except json.JSONDecodeError as exc:
        raise InputFileError(f"некорректный JSON (строка {exc.lineno}, столбец {exc.colno}): {exc.msg}") from exc

    items = data if isinstance(data, list) else [data]
    products = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise InputFileError(f"товар №{index}: ожидался JSON-объект")
        try:
            products.append(ProductInput.model_validate(item))
        except ValidationError as exc:
            raise InputFileError(f"товар №{index}: {describe_validation_error(exc)}") from exc
    return products


def _generate(args: argparse.Namespace) -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return 2
    generator = CardGenerator(OpenAICompatibleLLM(settings), settings.max_attempts)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)

    failed = 0
    for path in args.files:
        try:
            products = load_products(path)
        except InputFileError as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            failed += 1
            continue

        for index, product in enumerate(products, start=1):
            stem = path.stem if len(products) == 1 else f"{path.stem}-{index}"
            try:
                card = generator.generate(product)
            except CardGenError as exc:
                print(f"{path} ({product.name or f'товар №{index}'}): {exc}", file=sys.stderr)
                failed += 1
                continue

            markdown = render_markdown(card)
            if args.out:
                (args.out / f"{stem}.json").write_text(card.model_dump_json(indent=2) + "\n", encoding="utf-8")
                (args.out / f"{stem}.md").write_text(markdown, encoding="utf-8")
                print(f"Готово: {path} → {args.out / stem}.json, .md", file=sys.stderr)
            else:
                print(markdown)
            for warning in card.warnings:
                print(f"  предупреждение: {warning}", file=sys.stderr)

    return 1 if failed else 0


def _feed(args: argparse.Namespace) -> int:
    try:
        data = load_feed(args.source)
        if args.offer_id:
            offer = find_offer(data, args.offer_id)
            if offer is None:
                print(f"Товар с id={args.offer_id} не найден в выгрузке", file=sys.stderr)
                return 1
            text = json.dumps(offer, ensure_ascii=False, indent=2) + "\n"
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_text(text, encoding="utf-8")
                print(f"Сохранено: {args.out}", file=sys.stderr)
            else:
                print(text, end="")
            return 0

        offers = search_offers(data, args.search, args.limit)
    except httpx.HTTPError as exc:
        print(f"Не удалось скачать выгрузку: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Не удалось прочитать файл: {exc}", file=sys.stderr)
        return 1
    except ET.ParseError as exc:
        print(f"Выгрузка не является корректным XML: {exc}", file=sys.stderr)
        return 1

    if not offers:
        print("Ничего не найдено", file=sys.stderr)
        return 1
    for offer in offers:
        print(f"{offer['id']}\t{offer['name']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m cardgen", description="Черновики карточек товаров КИП с помощью LLM")
    commands = parser.add_subparsers(dest="command", required=True)

    generate = commands.add_parser("generate", help="сгенерировать карточки по JSON-файлам")
    generate.add_argument("files", nargs="+", type=Path, help="JSON-файлы с товарами")
    generate.add_argument("--out", type=Path, help="папка для .json и .md; без неё Markdown печатается в консоль")
    generate.set_defaults(handler=_generate)

    feed = commands.add_parser("feed", help="найти товар в YML-выгрузке и сохранить его как входной JSON")
    feed.add_argument("source", help="URL или путь к feed.xml")
    feed.add_argument("--search", default="", help="подстрока в названии товара")
    feed.add_argument("--id", dest="offer_id", help="id товара (offer id) для сохранения")
    feed.add_argument("--out", type=Path, help="куда сохранить JSON товара")
    feed.add_argument("--limit", type=int, default=30, help="сколько найденных товаров показать")
    feed.set_defaults(handler=_feed)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)
