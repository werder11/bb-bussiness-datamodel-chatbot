# ADR-0011: Entity Name Matching Is Closed-Vocabulary Exact + Fuzzy String Matching, Not NER/ML

**Status:** Accepted
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

The Intent Classification stage and structured lookups need to know which of the 43 known entity names (see [FINDINGS §3](../../FINDINGS.md#3-source-repository-map--scope)) a free-text question refers to, including paraphrases and the Account/Contact name collision. This is treated as a distinct **Entity Resolution** stage, separate from and upstream of Intent Classification ([ADR-0006](0006-intent-classification-swappable-strategy.md)) — "which entity is this about" and "what does the user want to know about it" are different questions.

## Decision

Add an `Entity Matcher` step right after the API boundary: exact, case-insensitive match against the known entity name list first; fall back to simple fuzzy string matching (e.g. edit distance / substring) over the same closed, 43-name vocabulary. No NER model or ML classifier — the vocabulary is small and fixed, and a deterministic matcher is fully unit-testable with a static list of inputs/expected matches. On genuine ambiguity (e.g. the name collision, or a paraphrase that plausibly matches two entities), surface both candidates rather than silently guessing one.

## Consequences

### Positive
- Simple, deterministic, fully unit-testable, no added model dependency.

### Negative
- Won't handle deep semantic paraphrases a real NER/embedding-based matcher might catch (e.g. "the org an account belongs to") — acceptable given vocabulary size; the vector search path remains available as a fallback for genuinely fuzzy phrasing the matcher can't resolve.

## Alternatives Considered

Embedding-based entity linking — rejected as disproportionate to a 43-name closed vocabulary; would only be worth it if the entity set were large or unbounded.

## Implementation Notes

Python stdlib `difflib.get_close_matches` is the default fuzzy-match implementation — no new dependency for a 43-item vocabulary. Swappable for a small library like `rapidfuzz` later if the evaluation set ([ADR-0017](0017-evaluation-as-first-class-layer.md)) shows precision issues against paraphrased/ambiguous test cases.

## Related Decisions

- [ADR-0006](0006-intent-classification-swappable-strategy.md) — the downstream stage this matcher feeds
