# ADR-0015: Canonical Model Carries Lightweight Provenance

**Status:** Accepted
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

[ADR-0008](0008-cdm-source-version-pinned-at-ingestion.md) pins ingestion to "the latest un-suffixed files at ingestion time," but nothing in the data itself records *which* files/version that was — so a query answer can't currently be traced back to its exact source.

## Decision

Every entity/relationship in the Canonical Model carries `source_path`; the ingestion run as a whole records `source_commit` (the CDM repo commit ingested against). No per-field version tracking — that would over-build for a static, one-shot ingestion.

## Consequences

### Positive
- Cheap; enables tracing any answer back to its exact source file for debugging or a live-demo "show your work" moment.
- Makes ADR-0008's version-pinning decision auditable rather than just asserted.

### Negative
- Small additional metadata to carry through Resolver → Validation → both projections — negligible given the scale.

## Alternatives Considered

Per-field version tracking (tracking versions at the attribute level, not just the entity/run level) — rejected as speculative over-engineering for a static, one-shot ingestion.

## Related Decisions

- [ADR-0008](0008-cdm-source-version-pinned-at-ingestion.md) — the decision this provenance makes auditable
- [ADR-0007](0007-resolver-scope-bounded-anti-corruption-layer.md) — the Resolver that attaches this provenance
