# ADR-0010: Post-Generation Grounding Verification (Citation Check)

**Status:** Accepted
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

The Grounding Guard ([ADR-0005](0005-explicit-grounding-guard-before-generation.md)) only catches the *zero-context* failure mode. The more common RAG failure in practice is the model embellishing a real, retrieved answer with a plausible but unsupported detail — a fabricated attribute, an inverted relationship direction. Nothing upstream of generation catches this.

## Decision

Add a `Grounding Validator` step after generation: the entity and attribute names cited in the generated answer must appear in the retrieved context; if the check fails, fall back to the fixed refusal. Start with simple string containment as the check — no new dependency, fully testable.

Since [ADR-0016](0016-deterministic-hits-template-rendered.md) routes fully-deterministic hits to a template instead of the LLM, this validator's meaningful work is on the LLM-generation path only — for templated answers it trivially passes (the answer is definitionally built from the retrieved facts) and mostly serves as a regression check on the template logic itself, not a runtime gate.

## Consequences

### Positive
- Closes the more common hallucination mode (embellishment on real context) on the path that actually needs it.
- Keeps "non-hallucinated" a checked property rather than a prompting hope.

### Negative
- String containment is a blunt instrument — can false-positive on legitimate paraphrasing (e.g. "identifier" vs. "ID") and won't catch a fabricated *relationship direction* stated using real entity names. Documented as best-effort, tuned against the evaluation set, not a hard guarantee. Tracked as a risk in [`docs/architecture/principles.md`](../architecture/principles.md#risks--mitigations) ("Grounding Validator is too strict / too lenient").

## Alternatives Considered

No verification, relying on prompting alone — rejected, leaves the most likely hallucination mode entirely unchecked given it's an explicitly graded requirement. A second LLM call to self-critique the first — rejected for now as added cost/latency/complexity disproportionate to a demo; worth reconsidering if the simple containment check proves too blunt against the eval set.

## Related Decisions

- [ADR-0005](0005-explicit-grounding-guard-before-generation.md) — the complementary guard for the zero-context failure mode
- [ADR-0016](0016-deterministic-hits-template-rendered.md) — narrows this validator's meaningful scope to the LLM-generation path
