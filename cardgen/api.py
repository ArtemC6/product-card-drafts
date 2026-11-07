"""HTTP API и веб-форма: uvicorn cardgen.api:app --reload"""
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from cardgen.config import load_settings
from cardgen.errors import ConfigError, InsufficientDataError, LLMError
from cardgen.generator import CardGenerator
from cardgen.llm import OpenAICompatibleLLM
from cardgen.models import CardResponse, ProductInput
from cardgen.render import render_markdown

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Черновики карточек товаров", version="1.0.0")


@lru_cache
def get_generator() -> CardGenerator:
    settings = load_settings()
    return CardGenerator(OpenAICompatibleLLM(settings), settings.max_attempts)


@app.exception_handler(RequestValidationError)
async def invalid_input(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"] if part != "body")
        errors.append(f"{location}: {error['msg']}" if location else error["msg"])
    return JSONResponse(status_code=422, content={"detail": {"message": "Некорректный входной JSON", "errors": errors}})


@app.exception_handler(ConfigError)
async def config_error(_: Request, exc: ConfigError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": {"message": str(exc)}})


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/cards", response_model=CardResponse)
def create_card(product: ProductInput, generator: CardGenerator = Depends(get_generator)) -> CardResponse:
    try:
        card = generator.generate(product)
    except InsufficientDataError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "missing": exc.missing}) from exc
    except LLMError as exc:
        raise HTTPException(status_code=502, detail={"message": str(exc)}) from exc
    return CardResponse(**card.model_dump(), markdown=render_markdown(card))
