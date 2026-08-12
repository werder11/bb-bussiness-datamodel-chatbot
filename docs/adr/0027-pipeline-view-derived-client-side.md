# ADR-0027: Pipeline View — Reconstructed Client-Side, Not a New API Field

**Status:** Accepted
**Date:** 2026-08-12
**Deciders:** Emre Gözütok

## Context

The chat UI shows the final answer plus `route`/`grounded`/`verified` badges (ADR-0025), and "How this works" explains the pipeline shape in the abstract (ADR-0025's info panel). Neither shows, for *this specific question just asked*, which stages actually ran — Entity Matcher, Router, structured/traversal lookup vs. vector search, the Grounding Guard, the LLM call, the Grounding Validator. Requested as an optional, toggleable "pipeline view."

The obvious implementation — add a `stages: Stage[]` field to `QueryResponse`/`RetrievalTrace` populated by `answer_query()` as it runs — was not needed. Every branch in `app/domain/pipeline.py` produces a response shape distinguishable from every other branch using fields the API already returns:

| Branch | `route` | `grounded` | `verified` | `answer` |
|---|---|---|---|---|
| Ambiguous match | `none` | `false` | `false` | starts `"That name is ambiguous..."` |
| Structured attributes/relationship | `structured` | `true` | `true` | template-rendered |
| Traversal | `traversal` | `true` | `true` | template-rendered |
| Semantic, validator passed | `semantic` | `true` | `true` | generated text |
| Semantic, validator failed | `semantic` | `true` | `false` | fixed refusal |
| Semantic, LLM call itself failed | `semantic` | `true` | `false` | fixed refusal |
| Fell through to vector search, nothing cleared the Grounding Guard | `none` | `false` | `false` | fixed refusal (not the ambiguous prefix) |

Almost a complete, injective mapping from (route, grounded, verified, answer-prefix) back to which pipeline branch ran — enough to reconstruct an accurate stage list without touching the backend, with one real exception found the first time this was actually used live (see "Amendment" below).

## Decision

`deriveStages(response)` in `ui/src/main.ts` maps a `QueryResponse` to an ordered `PipelineStage[]` (`{name, status: done|failed|skipped, detail}`) purely from fields already in the response. A header toggle ("🔬 Pipeline view") turns on a compact stage tracker rendered under each *new* answer's badges (existing messages aren't retroactively annotated). No API change, no new `RetrievalTrace` field, stays inside ADR-0025's "thin client" constraint the same way the eval snapshot (ADR-0026) did.

One stage is intentionally labeled **"Embed query (local)"**, not "Embedding API" — the embedding model (`sentence-transformers`, ADR-0023) runs in-process with no network call; naming it an "API" would misstate the architecture on the one screen meant to explain it accurately.

Verified against four real live responses (structured, ambiguous, semantic-verified, semantic-guard-refused) — each matched its predicted derivation exactly before this was considered done.

## Consequences

### Positive
- Zero backend risk (no new endpoint, no new live cost) for a feature that reads as "live" — same value proposition as ADR-0026's snapshot panel, applied to a different demo need.
- Directly shows the "deterministic paths never touch the model" claim in action, per-question, which is the single strongest architectural point this project makes.

### Negative
- **Honest, stated limitation**: on the semantic/refused routes, the *original* Entity Matcher output (exact vs. fuzzy match, or no match) isn't recoverable — by the time `matched_entities` reaches the response on that path, it's been overwritten with the vector search hits (see `answer_query`'s semantic branch). The Entity Match stage is generic ("checked — no deterministic reroute") there rather than fabricated. If this granularity is ever needed, it requires an actual `RetrievalTrace`/response field, not more client-side inference.
- The derivation is a second place that encodes `answer_query()`'s branch logic (the first being `answer_query()` itself) — if the pipeline's branches change shape, `deriveStages()` needs a matching update or it silently mislabels stages. No automated check currently guards this pairing (unlike the schema types, which fail the TS build on drift).

## Amendment: One Case Wasn't Actually Distinguishable (2026-08-12)

The table above has a real gap the first version of this ADR missed: "Semantic, validator failed" and "Semantic, LLM call itself failed" produce the *exact same* `(route, grounded, verified, answer)` tuple — `("semantic", true, false, _REFUSAL)` — because both are handled by `respond()` with identical arguments (see ADR-0010's "Provider-Call Failures" section). `deriveStages()` originally couldn't tell them apart and always rendered "Generate (LLM): done, Validator: failed" — actively wrong whenever the real cause was a provider error, since the model was never even successfully called.

Found live, not by re-reading the derivation table: asked a real question through the deployed UI, saw "Validator: failed," and separately reproduced Gemini's daily quota (20 req/day) being exhausted at that same moment while investigating. The two facts together made the mislabeling obvious.

Fixed by widening the one field this whole ADR's premise says wasn't needed: `QueryResponse.error` (previously only on `RetrievalTrace`, log-only) is now also returned to the client, `null` except on the LLM-call-failure path. `deriveStages()` checks it first for `route === "semantic"` and renders "Generate (LLM): failed" / "Validator: skipped" with the real error text, instead of guessing from `verified` alone. This is a narrow, honest exception to the ADR's "no API change" premise — not a reversal of it: every *other* stage is still purely derived, and this one field only disambiguates a case that was otherwise genuinely unrecoverable, not a general retreat to server-side stage computation.

Regression coverage: `tests/unit/test_pipeline.py::test_llm_call_failure_degrades_to_refusal_not_a_crash` now also asserts `response.error` (not just the trace log's `error`) is populated; `test_grounding_validator_catches_an_unsupported_claim_and_refuses` asserts `response.error is None` to lock in the distinction going forward.

## Alternatives Considered

A new `stages` field computed server-side in `answer_query()` and threaded through `RetrievalTrace`/`QueryResponse` — more accurate (would recover the real Entity Matcher output on every route) but real new backend logic for a visualization, not the retrieval/generation behavior itself; deferred unless the derived version's one known gap turns out to matter in practice.

## Related Decisions

- [ADR-0025](0025-ui-typescript-chat-and-entity-browser.md) — the "thin client only" constraint this stays within
- [ADR-0026](0026-eval-kpi-snapshot-in-ui.md) — the same "derive/precompute instead of add backend surface" instinct, applied to evaluation KPIs instead of per-query tracing
- [ADR-0011](0011-entity-name-matching-closed-vocabulary.md) / [ADR-0006](0006-intent-classification-swappable-strategy.md) / [ADR-0005](0005-explicit-grounding-guard-before-generation.md) / [ADR-0010](0010-post-generation-grounding-verification.md) — the real stages this view visualizes
