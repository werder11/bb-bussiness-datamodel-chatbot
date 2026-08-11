# ADR-0008: CDM Source Is Version-Pinned at Ingestion Time; Re-Ingestion Is Out of Scope

**Status:** Accepted
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

CDM ships numbered file variants (e.g. `Account.1.0.cdm.json` alongside `Account.cdm.json`) and the upstream project's own policy is additive-only versioning.

## Decision

Ingestion always reads the latest un-suffixed manifest/entity files at the time of ingestion; historical numbered variants are ignored. No mechanism is built to detect or react to upstream CDM changes. This decision is made auditable, not just asserted, by [ADR-0015](0015-canonical-model-provenance.md)'s provenance recording.

## Consequences

### Positive
- Simple, predictable ingestion; no speculative machinery built for a one-off demo.

### Negative
- Index silently goes stale if CDM is updated upstream — acceptable, noted as a known follow-up rather than built now.

## Alternatives Considered

Build a mechanism to detect upstream CDM changes and trigger re-ingestion — rejected as speculative machinery disproportionate to a one-off take-home deliverable.

## Related Decisions

- [ADR-0015](0015-canonical-model-provenance.md) — records what was actually ingested, making this pin auditable
- [ADR-0002](0002-separate-offline-ingestion-from-online-query-path.md) — the ingestion step this pin applies to
