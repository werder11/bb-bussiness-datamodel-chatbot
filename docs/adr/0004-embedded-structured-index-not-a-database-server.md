# ADR-0004: Embedded/In-Process Structured Index, Not a Database Server

**Status:** Accepted
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

The relational projection ([ADR-0003](0003-dual-projection-retrieval-not-cqrs.md)) holds facts for ~43 entities and a few hundred attributes/relationships — dataset size is fixed and small. This ADR is about *operational footprint*, not about whether a relational projection is architecturally justified — it is, per ADR-0003.

## Decision

Implement the `StructuredIndex` port with an in-process adapter (SQLite file), not a database server.

## Consequences

### Positive
- Zero operational surface, trivial to run in a single Docker container.
- Trivial to unit-test (construct and query in-process, no fixtures/containers needed).

### Negative
- Doesn't demonstrate DB-server operational patterns — acceptable, since that's not what's being evaluated here.

## Alternatives Considered

PostgreSQL — not rejected on principle, just disproportionate operationally at this scale; would be reconsidered if scope grew to multi-tenant CDM sources or concurrent writers, neither of which applies here.

## Related Decisions

- [ADR-0003](0003-dual-projection-retrieval-not-cqrs.md) — architectural justification for a relational projection at all
