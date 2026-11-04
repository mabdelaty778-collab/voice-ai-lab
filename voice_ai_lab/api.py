"""Application factory makes each test environment independent."""

import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from voice_ai_lab.config import Settings
from voice_ai_lab.knowledge import KNOWLEDGE, answer
from voice_ai_lab.models import LeadInput, Question
from voice_ai_lab.store import PersistenceUnavailable, RequestConflict, Store

STATIC = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = Store(settings.db_path, settings.fail_writes)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store.initialize()
        yield

    app = FastAPI(title="Voice AI Lab", version="0.1.0", lifespan=lifespan)
    app.state.store = store
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"]
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.update(
            {
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; "
                "style-src 'self'; "
                "connect-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; "
                "object-src 'none'; form-action 'self'",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Cache-Control": "no-store",
            }
        )
        return response

    def authorize(x_lab_key: Annotated[str | None, Header()] = None):
        if not x_lab_key or not secrets.compare_digest(
            x_lab_key.encode(), settings.api_key.encode()
        ):
            raise HTTPException(401, "Missing or invalid X-Lab-Key")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return JSONResponse({"error": {"message": exc.detail}}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Do not echo submitted contact data in errors.
        return JSONResponse(
            {
                "error": {
                    "message": "Invalid input",
                    "fields": [".".join(map(str, e["loc"])) for e in exc.errors()],
                }
            },
            status_code=422,
        )

    @app.exception_handler(sqlite3.Error)
    async def database_error(request: Request, exc: sqlite3.Error):
        return JSONResponse(
            {"error": {"message": "Local database unavailable. No success is confirmed."}},
            status_code=503,
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": "simulation", "external_services": False}

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    protected = [Depends(authorize)]

    @app.get("/api/v1/catalog", dependencies=protected)
    def catalog():
        return {"data": KNOWLEDGE["courses"], "academy": KNOWLEDGE["academy"]}

    @app.post("/api/v1/questions", dependencies=protected)
    def question(body: Question):
        started = time.perf_counter()
        result = answer(body.text)
        elapsed = round((time.perf_counter() - started) * 1000, 3)
        store.record_retrieval(elapsed)
        return {"data": {"mode": "simulation", **result, "retrieval_ms": elapsed}}

    @app.post("/api/v1/leads", dependencies=protected, status_code=201)
    def capture(body: LeadInput, response: Response):
        try:
            row, created = store.capture(body)
        except RequestConflict as exc:
            raise HTTPException(409, "Request ID was already used with different data") from exc
        except PersistenceUnavailable as exc:
            raise HTTPException(503, "Lead was not saved. Retry with the same request_id.") from exc
        response.status_code = 201 if created else 200
        return {"data": row, "persisted": True, "replayed": not created}

    @app.get("/api/v1/leads", dependencies=protected)
    def leads(
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ):
        rows, total = store.leads(limit, offset)
        return {"data": rows, "meta": {"total": total, "limit": limit, "offset": offset}}

    @app.get("/api/v1/metrics", dependencies=protected)
    def metrics():
        return {
            "data": store.metrics(),
            "note": "Local simulation counts, not voice latency or cost",
        }

    return app
