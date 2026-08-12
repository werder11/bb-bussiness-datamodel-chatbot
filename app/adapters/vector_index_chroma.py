"""ChromaDB adapter for the `VectorIndex` port — ADR-0023 (ChromaDB embedded,
local sentence-transformers, one chunk per entity).

The embedder is dependency-injected (defaults to a lazily-constructed real
`sentence-transformers` model) so unit tests never trigger a model download
or any network call — ADR-0018's fast-gate requirement. Only integration/
system/eval runs actually load the real model.
"""

from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

import chromadb
from chromadb.config import Settings

from app.domain.models import Entity
from app.domain.ports import SemanticHit, SemanticSearchResult

Embedder = Callable[[Sequence[str]], list[list[float]]]

_COLLECTION_NAME = "cdm_entities"
_MODEL_NAME = "all-MiniLM-L6-v2"


def _default_embedder() -> Embedder:
    # Deferred import: no cost/network hit in unit tests, which always inject a fake embedder.
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(_MODEL_NAME)

    def embed(texts: Sequence[str]) -> list[list[float]]:
        return model.encode(list(texts)).tolist()

    return embed


def entity_to_chunk(entity: Entity) -> str:
    """One chunk per entity (ADR-0023): name, description, full attribute
    list, full relationship list, as one text blob."""
    attrs = ", ".join(a.name for a in entity.attributes) or "none"
    rels = ", ".join(f"{r.name} -> {'/'.join(r.targets)}" for r in entity.relationships) or "none"
    return f"{entity.name}: {entity.description or ''}\nAttributes: {attrs}\nRelationships: {rels}"


class ChromaVectorIndex:
    """Implements the `VectorIndex` Protocol (app/domain/ports.py)."""

    def __init__(self, persist_path: str | Path, embedder: Embedder | None = None) -> None:
        self._client = chromadb.PersistentClient(
            path=str(persist_path), settings=Settings(anonymized_telemetry=False)
        )
        self._embed = embedder or _default_embedder()
        self._collection = self._client.get_or_create_collection(
            _COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )

    def load(self, entities: Iterable[Entity]) -> None:
        """Idempotent clear-then-write (ADR-0002)."""
        existing = {c.name for c in self._client.list_collections()}
        if _COLLECTION_NAME in existing:
            self._client.delete_collection(_COLLECTION_NAME)
        self._collection = self._client.create_collection(
            _COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )

        entities = list(entities)
        if not entities:
            return
        documents = [entity_to_chunk(e) for e in entities]
        embeddings = self._embed(documents)
        # chromadb's stubs are stricter than its actual accepted input shapes
        # (plain list[list[float]] works fine at runtime).
        self._collection.add(
            ids=[e.name for e in entities],
            documents=documents,
            embeddings=embeddings,  # type: ignore[arg-type]
        )

    def semantic_search(self, query: str, k: int = 5) -> SemanticSearchResult:
        count = self._collection.count()
        if count == 0:
            return SemanticSearchResult(query=query, hits=())
        query_embedding = self._embed([query])
        results = self._collection.query(
            query_embeddings=query_embedding,  # type: ignore[arg-type]
            n_results=min(k, count),
        )
        ids, documents, distances = results["ids"], results["documents"], results["distances"]
        assert ids is not None and documents is not None and distances is not None
        hits = tuple(
            SemanticHit(entity=entity_id, score=1.0 - distance, snippet=document[:200])
            for entity_id, document, distance in zip(ids[0], documents[0], distances[0], strict=True)
        )
        return SemanticSearchResult(query=query, hits=hits)
