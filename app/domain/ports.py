"""Port contracts — ADR-0001 (Hexagonal Architecture) + ADR-0021 (schema-based design).

`StructuredIndex`, `VectorIndex`, and `LLM` are the three swappable
capabilities the domain core depends on. Concrete adapters live in
`app/adapters/`; fakes used in unit tests (ADR-0018) implement the same
`Protocol`s so they're structurally guaranteed to match real adapters.

The docs (ADR-0021's Implementation Notes) only ever gave one example
signature (`get_attributes(entity: str) -> AttributesResult`) — the full
set below is this plan's design, not a re-statement of something already
specified elsewhere.
"""

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.domain.models import Attribute, Relationship


class AttributesResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity: str
    found: bool
    attributes: tuple[Attribute, ...] = ()


class RelationshipsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity: str
    found: bool
    relationships: tuple[Relationship, ...] = ()


class TraversalResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_entity: str
    found: bool
    path: tuple[str, ...] = ()  # entity names along the path, len <= 3 (depth <= 2 hops)
    relationships: tuple[Relationship, ...] = ()  # the edges actually traversed


class SemanticHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity: str
    score: float
    snippet: str


class SemanticSearchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    hits: tuple[SemanticHit, ...] = ()


class StructuredIndex(Protocol):
    def list_entities(self) -> tuple[str, ...]:
        """All namespaced entity names currently loaded — the vocabulary the
        Entity Matcher (ADR-0011) and `GET /entities` both need."""
        ...

    def get_attributes(self, entity: str) -> AttributesResult: ...

    def get_relationships(self, entity: str) -> RelationshipsResult:
        """Single-hop only — ADR-0009."""
        ...

    def traverse(
        self, entity: str, target: str | None = None, max_depth: int = 2
    ) -> TraversalResult:
        """Bounded BFS, depth <= 2 — ADR-0009. `target=None` returns everything reachable
        within `max_depth`; a `target` narrows to paths toward that entity specifically."""
        ...


class VectorIndex(Protocol):
    def semantic_search(self, query: str, k: int = 5) -> SemanticSearchResult: ...


class LLM(Protocol):
    def generate(self, question: str, context: tuple[str, ...]) -> str:
        """Context-only generation — ADR-0016. Never called for fully-deterministic hits."""
        ...
