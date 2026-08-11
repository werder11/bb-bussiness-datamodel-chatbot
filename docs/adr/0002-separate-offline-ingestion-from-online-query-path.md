# ADR-0002: Separate Offline Ingestion from the Online Query Path

**Status:** Accepted
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

CDM definitions are static for the duration of the demo; there's no requirement to re-parse GitHub on every query.

## Decision

Ingestion is a standalone batch step (CLI script / startup task) that populates both indexes once, rebuilding them idempotently (clear-then-write) on every run so re-running never accumulates duplicates. The FastAPI request path only ever reads from the indexes, never touches raw CDM JSON.

## Consequences

### Positive
- Query latency isn't coupled to parsing cost.
- Ingestion can be re-run independently and tested in isolation from the API.
- Safe to re-run repeatedly during development (idempotent).

### Negative
- Index staleness if the CDM source changes without re-running ingestion — acceptable, see [ADR-0008](0008-cdm-source-version-pinned-at-ingestion.md).

## Alternatives Considered

Parsing CDM JSON on the request path (no pre-built index) — rejected, couples query latency to parse cost for no benefit given the source is static.

## Related Decisions

- [ADR-0008](0008-cdm-source-version-pinned-at-ingestion.md) — accepts the staleness trade-off this ADR creates
- [ADR-0012](0012-ingestion-fails-per-entity-skip-and-log.md) — failure policy within this ingestion step
- [ADR-0014](0014-explicit-validation-pass.md) — an additional stage within this same ingestion step
