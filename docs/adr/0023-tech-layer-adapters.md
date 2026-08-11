# ADR-0023: Tech-Layer Adapters — ChromaDB, Anthropic Claude, Local Sentence-Transformers, Per-Entity Chunking

**Status:** Accepted
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

Every structural/shape decision (ADR-0001–0022) deliberately deferred the concrete vendor behind each port, tracked as open rows in [`FINDINGS.md §7`](../../FINDINGS.md#7-open-architecture-decisions): vector DB, LLM provider, embedding model, chunking granularity. These were the only remaining blockers before Phase 3 (Adapters) of the implementation plan could start — the ports themselves ([ADR-0001](0001-hexagonal-architecture-ports-and-adapters.md)) don't need this decision to exist, but nothing can implement them without it.

## Decision

- **Vector DB**: ChromaDB, embedded/in-process. Consistent with [ADR-0004](0004-embedded-structured-index-not-a-database-server.md)'s "no DB server" reasoning for the structured side — one container, not two, for a take-home demo.
- **LLM provider**: Anthropic Claude, for the `LLM` port's `generate()` (semantic/mixed-evidence path only, per [ADR-0016](0016-deterministic-hits-template-rendered.md)).
- **Embedding model**: local `sentence-transformers` (`all-MiniLM-L6-v2`). Free, offline, no API key — runs inside the container regardless of LLM vendor. (Anthropic has no first-party embeddings endpoint, so this isn't a compromise against "matching the LLM vendor" — that option doesn't really exist.)
- **Chunking granularity**: one chunk per entity — name + description + full attribute list + relationship list as one text blob per entity. Matches the [Entity Matcher](0011-entity-name-matching-closed-vocabulary.md)'s per-entity granularity; relationship-level chunking would be redundant with the [Bounded Graph Traversal](0009-relationship-traversal-bounded-to-depth-2.md), which already handles relationships deterministically.

## Consequences

### Positive
- Every adapter now has a concrete implementation path; Phase 3 of the implementation plan is unblocked.
- Single-container deployment preserved — no additional services beyond the FastAPI process itself.
- Zero external dependency for embeddings specifically, keeping the fast CI gate's "no live calls" property ([ADR-0019](0019-cicd-pipeline-layered-by-cost-and-speed.md)) easy to hold to in adapter unit tests.

### Negative
- Anthropic API key becomes a required runtime secret for the generation path and for `task eval:run` — never required for `task ci:fast` or for questions the deterministic/template path can answer.
- Local embedding quality (`all-MiniLM-L6-v2`) is lower than a large hosted embedding model — acceptable given the corpus is small (43 entities) and precision is tunable via the evaluation set ([`docs/quality/evaluation-strategy.md`](../quality/evaluation-strategy.md)).

## Alternatives Considered

Presented to and decided by the user via structured options; recommended defaults were chosen in all four cases. Rejected alternatives: Qdrant/FAISS/pgvector (vector DB — more infra or less filtering than Chroma offers for this scale), OpenAI/local Ollama (LLM — worse demo-reliability tradeoff than a hosted Anthropic API), OpenAI embeddings (adds an API dependency purely for embeddings when Anthropic doesn't offer first-party embeddings anyway), one-chunk-per-attribute/relationship (fragments context or duplicates the structured path's job).

## Related Decisions

- [ADR-0001](0001-hexagonal-architecture-ports-and-adapters.md) — the ports these are adapters for
- [ADR-0004](0004-embedded-structured-index-not-a-database-server.md) — the parallel "no server" reasoning on the structured side
- [ADR-0016](0016-deterministic-hits-template-rendered.md) — scopes exactly when the LLM adapter is actually invoked
- Supersedes the "Still open" status of all four rows in [`FINDINGS.md §7`](../../FINDINGS.md#7-open-architecture-decisions)
