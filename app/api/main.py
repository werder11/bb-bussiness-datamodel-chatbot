"""FastAPI app — `docs/api/README.md`.

Adapters are constructed once at startup (`lifespan`) from the SQLite file
and Chroma persistence dir that `task ingest:run` already wrote — the API
never re-runs ingestion itself (ADR-0002 keeps the two paths separate).

Each adapter is exposed to handlers through a `Depends()` provider reading
`request.app.state`, rather than read inline, specifically so tests can
swap in fakes via `app.dependency_overrides` without lifespan ever running
a real Chroma/LLM construction (ADR-0018's fast-gate requirement).

The LLM provider (Anthropic or Gemini, ADR-0024) is chosen at startup via
`build_llm()` / the `LLM_PROVIDER` env var, not hardcoded here.

The static mount at the bottom serves the built UI (ADR-0025) — a thin
client with no server-side involvement beyond serving files. `check_dir`
is off because `ui/dist` only exists after `task ui:build`/the Docker
frontend stage; test/CI environments that never build the UI still import
this module fine, they just get 404s for anything under the mount.
"""

import logging
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

from app.adapters.llm_factory import build_llm
from app.adapters.structured_index_sqlite import SQLiteStructuredIndex
from app.adapters.vector_index_chroma import ChromaVectorIndex
from app.api.schemas import (
    AttributeSchema,
    EntityDetailResponse,
    EntityListResponse,
    EvaluateRequest,
    EvaluateResponseSchema,
    HealthResponse,
    QueryRequest,
    QueryResponseSchema,
    RelationshipSchema,
)
from app.domain.comparison import compare_answer
from app.domain.pipeline import answer_query
from app.domain.ports import LLM, StructuredIndex, VectorIndex

# Without this, the Retrieval Tracer's logger.info() calls below go nowhere
# — uvicorn configures its own "uvicorn"/"uvicorn.access" loggers but never
# touches the root logger, and Python's root logger has no handler by
# default. Found live: a forced LLM failure produced the right graceful
# refusal in the response, but nothing showed up in `docker logs` at all —
# the trace line docs/operations/monitoring.md calls "concrete, inspectable
# evidence" had silently never been emitted. format="%(message)s" keeps the
# line as bare JSON (trace.model_dump_json()), not a logging preamble.
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("app.api")

_DB_PATH = os.environ.get("CDM_DB_PATH", "cdm.db")
_CHROMA_PATH = os.environ.get("CDM_CHROMA_PATH", "chroma_data")
_UI_DIST_PATH = os.environ.get("CDM_UI_DIST_PATH", "ui/dist")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    structured = SQLiteStructuredIndex(db_path=_DB_PATH)
    app.state.structured = structured
    app.state.vector = ChromaVectorIndex(persist_path=_CHROMA_PATH)
    app.state.llm = build_llm()
    app.state.known_entities = frozenset(structured.list_entities())
    yield


app = FastAPI(title="CDM RAG Chatbot", lifespan=lifespan)


@app.middleware("http")
async def _cache_control(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # Found live: the UI's index.html was served with no Cache-Control
    # header at all, so a browser could keep showing a stale page — old
    # hashed JS/CSS filenames included — after a real rebuild, with no
    # error and no visible sign anything was wrong; only a hard-refresh
    # would show the new build. Vite content-hashes filenames under
    # /assets/, so those are safe to cache forever; everything else
    # (notably index.html, plus the JSON API responses) must always
    # revalidate so a new build/response is never silently stale.
    response = await call_next(request)
    if request.url.path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    else:
        response.headers["Cache-Control"] = "no-cache"
    return response


def get_structured_index(request: Request) -> StructuredIndex:
    return request.app.state.structured  # type: ignore[no-any-return]


def get_vector_index(request: Request) -> VectorIndex:
    return request.app.state.vector  # type: ignore[no-any-return]


def get_llm(request: Request) -> LLM:
    return request.app.state.llm  # type: ignore[no-any-return]


def get_known_entities(request: Request) -> frozenset[str]:
    return request.app.state.known_entities  # type: ignore[no-any-return]


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/entities", response_model=EntityListResponse)
def list_entities(
    structured: StructuredIndex = Depends(get_structured_index),
) -> EntityListResponse:
    return EntityListResponse(entities=structured.list_entities())


@app.get("/entities/{name}", response_model=EntityDetailResponse)
def get_entity(
    name: str, structured: StructuredIndex = Depends(get_structured_index)
) -> EntityDetailResponse:
    attrs = structured.get_attributes(name)
    if not attrs.found:
        raise HTTPException(status_code=404, detail=f"Entity '{name}' not found")
    rels = structured.get_relationships(name)
    return EntityDetailResponse(
        entity=name,
        attributes=tuple(AttributeSchema(**a.model_dump()) for a in attrs.attributes),
        relationships=tuple(RelationshipSchema(**r.model_dump()) for r in rels.relationships),
    )


@app.post("/query", response_model=QueryResponseSchema)
def query(
    payload: QueryRequest,
    structured: StructuredIndex = Depends(get_structured_index),
    vector: VectorIndex = Depends(get_vector_index),
    llm: LLM = Depends(get_llm),
    known_entities: frozenset[str] = Depends(get_known_entities),
) -> QueryResponseSchema:
    response = answer_query(
        payload.question,
        structured,
        vector,
        llm,
        known_entities,
        trace_sink=lambda trace: logger.info(trace.model_dump_json()),
    )
    return QueryResponseSchema.from_domain(response)


@app.post("/evaluate", response_model=EvaluateResponseSchema)
def evaluate(
    payload: EvaluateRequest,
    structured: StructuredIndex = Depends(get_structured_index),
    vector: VectorIndex = Depends(get_vector_index),
    llm: LLM = Depends(get_llm),
    known_entities: frozenset[str] = Depends(get_known_entities),
) -> EvaluateResponseSchema:
    # Runs the real pipeline (same code path as /query — grounded/verified,
    # error, and the full debug payload are all real, not simulated) and
    # compares the real answer to a user-supplied desired answer. See
    # app/domain/comparison.py for why this is a plain lexical comparison
    # rather than an external eval-framework call.
    response = answer_query(
        payload.question,
        structured,
        vector,
        llm,
        known_entities,
        trace_sink=lambda trace: logger.info(trace.model_dump_json()),
    )
    comparison = compare_answer(response.answer, payload.expected_answer)
    return EvaluateResponseSchema.from_domain(response, comparison)


if Path(_UI_DIST_PATH).is_dir():
    # Mounted last, after every API route above — Starlette matches routes in
    # registration order, so /health, /entities*, /query are always tried
    # first and this mount only ever catches the UI's own static assets.
    app.mount("/", StaticFiles(directory=_UI_DIST_PATH, html=True), name="ui")
