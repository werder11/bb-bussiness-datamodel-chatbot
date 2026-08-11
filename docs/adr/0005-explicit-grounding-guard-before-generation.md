# ADR-0005: Explicit Grounding Guard Before Any Generation Call

**Status:** Accepted
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

The case study brief explicitly grades non-hallucination. The most likely *zero-context* failure mode is an out-of-ingested-scope question silently reaching the LLM without grounding context. (A second failure mode — the LLM embellishing on top of real context — is addressed separately by [ADR-0010](0010-post-generation-grounding-verification.md).)

## Decision

Introduce a `GroundingGuard` step between retrieval and generation, with mechanics that differ by retrieval type since the two signal types aren't comparable:

- Structured lookup / graph traversal: **boolean** — a hit was found or it wasn't. Any hit ⇒ grounded.
- Vector search: **continuous similarity score** — grounded only above a tuned cutoff (see [`docs/quality/evaluation-strategy.md`](../quality/evaluation-strategy.md)).

If neither path produces a grounded result, short-circuit to a fixed "not found in the ingested CDM scope" response. The LLM is never called ungrounded.

## Consequences

### Positive
- Closes the zero-context hallucination path.
- Cheaper — skips generation entirely for out-of-scope questions.

### Negative
- The vector-search cutoff is a tunable that needs real examples to set sensibly — not guessable in the abstract.

## Alternatives Considered

No guard, rely entirely on prompting the LLM to refuse — rejected, prompting alone is not a checkable guarantee for a requirement that is explicitly graded.

## Related Decisions

- [ADR-0010](0010-post-generation-grounding-verification.md) — the complementary guard for the *embellishment* failure mode
- [ADR-0009](0009-relationship-traversal-bounded-to-depth-2.md) — one of the retrieval paths this guard evaluates
