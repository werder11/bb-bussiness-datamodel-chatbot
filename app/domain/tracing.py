"""Retrieval Tracer shape — `docs/operations/monitoring.md`.

`RetrievalTrace` deliberately excludes the answer text itself (unlike
`QueryResponse` in `app/domain/pipeline.py`) — it's the log-line shape,
not the API response. Domain code never performs the actual logging I/O
(ADR-0001, hexagonal core); `answer_query`'s `trace_sink` parameter is
where a caller in `app/api/` wires up real logging.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class RetrievalTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    matched_entities: tuple[str, ...]
    route: Literal["structured", "traversal", "semantic", "none"]
    grounded: bool
    verified: bool
    # Set only when the LLM call itself failed (rate limit, timeout, ...) and
    # the pipeline fell back to a refusal rather than propagating a 500 — see
    # ADR-0010's "Provider-Call Failures" addendum. None on every other path.
    error: str | None = None


def build_trace(
    *,
    query: str,
    matched_entities: tuple[str, ...],
    route: Literal["structured", "traversal", "semantic", "none"],
    grounded: bool,
    verified: bool,
    error: str | None = None,
) -> RetrievalTrace:
    return RetrievalTrace(
        query=query,
        matched_entities=matched_entities,
        route=route,
        grounded=grounded,
        verified=verified,
        error=error,
    )
