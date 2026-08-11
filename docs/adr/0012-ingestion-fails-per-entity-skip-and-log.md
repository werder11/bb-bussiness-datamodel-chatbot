# ADR-0012: Ingestion Fails Per-Entity (Skip-and-Log), Not the Whole Run

**Status:** Accepted
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

[FINDINGS §5](../../FINDINGS.md#5-the-core-challenge-multi-hop-attribute--relationship-resolution) already found structural surprises across just 3 sampled entities out of 43; more are likely among the rest. Ingestion needs a stated policy for when the Resolver can't handle a given entity's shape.

Note this is distinct from [ADR-0014](0014-explicit-validation-pass.md)'s Validation Pass: this ADR covers a single entity failing to resolve at all; ADR-0014 covers cross-entity integrity once individual entities have already resolved successfully.

## Decision

If the Resolver fails on a given entity, log a clear warning identifying the entity and reason, exclude that entity from both projections, and continue ingesting the rest. Ingestion prints a final summary (N/43 entities resolved, list of skipped entities with reasons) rather than failing silently or aborting the whole run on one bad file.

## Consequences

### Positive
- One unexpected entity shape doesn't block the entire demo; failures are visible, not silent.

### Negative
- A skipped entity is simply absent from answers (correctly triggering the Grounding Guard's refusal for questions about it) rather than partially answered — acceptable, and consistent with never guessing.

## Alternatives Considered

Abort the whole ingestion run on any single entity failure — rejected, one bad file shouldn't block the entire demo given real structural surprises are expected across 43 entities.

## Related Decisions

- [ADR-0007](0007-resolver-scope-bounded-anti-corruption-layer.md) — the Resolver whose failures this policy governs
- [ADR-0014](0014-explicit-validation-pass.md) — the complementary cross-entity integrity check
