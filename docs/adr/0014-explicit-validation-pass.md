# ADR-0014: Explicit Validation Pass Between Resolver and Canonical Model

**Status:** Accepted
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

[ADR-0012](0012-ingestion-fails-per-entity-skip-and-log.md) handles resolution failure *within* a single entity, but nothing checks *cross-entity* integrity once all entities are individually resolved — e.g. an `entityAttribute`'s `entityReference` pointing to a name that was never actually resolved, or a name collision outside the already-known Account/Contact case. Silent gaps here would surface later only as confusing retrieval failures, instead of a clear ingestion-time signal.

## Decision

Add an explicit Validation stage after the Resolver, before entities are considered part of the Canonical Model: check for duplicate canonical entity names, unresolved relationship references, relationships pointing to non-existent attributes, and missing required identifiers. Produce a plain-text ingestion summary, e.g.:

```
43 entities discovered, 41 resolved, 2 skipped
67 relationships discovered, 3 unresolved references
```

## Consequences

### Positive
- Turns "why did this question return nothing" into a debuggable ingestion-time report instead of a silent gap discovered only at query time.
- The summary itself is good demoable evidence for the technical-walkthrough slide.

### Negative
- Another ingestion stage to write and test — kept small and read-only (checks, doesn't repair).

## Alternatives Considered

Skip validation, rely on the Grounding Guard to mask any gaps at query time — rejected, that hides data-quality issues behind a generic "not found" response instead of surfacing them where they can actually be fixed.

## Implementation Notes

Concrete checks, each a simple pass over the resolved entity set (no external validation library needed at this scale):

| Check | Rule |
|---|---|
| Duplicate entity names | Two resolved entities share a canonical name outside the known Account/Contact collision |
| Unresolved relationship reference | An `entityAttribute`'s `entityReference` points to a name not present in the resolved set |
| Dangling attribute reference | A relationship references an attribute that doesn't exist on its target entity |
| Missing required identifier | An entity has no `identifiedBy`-purpose attribute (e.g. no `accountId`-equivalent) |

Output feeds directly into the Data Quality pillar of [Evaluation](0017-evaluation-as-first-class-layer.md).

## Related Decisions

- [ADR-0007](0007-resolver-scope-bounded-anti-corruption-layer.md) — the Resolver whose output this validates
- [ADR-0012](0012-ingestion-fails-per-entity-skip-and-log.md) — the complementary per-entity failure policy
