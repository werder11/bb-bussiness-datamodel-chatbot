# ADR-0028: Pipeline Zoom View — a Real `debug` Payload, Not More Client-Side Guessing

**Status:** Accepted
**Date:** 2026-08-12
**Deciders:** Emre Gözütok

## Context

ADR-0027 built the pipeline view by deriving stage status purely from fields the API already returned, explicitly deferring "a new `stages` field computed server-side" as its Alternative Considered — "more accurate... but real new backend logic for a visualization, not the retrieval/generation behavior itself; deferred unless the derived version's one known gap turns out to matter in practice." That same day's amendment (surfacing `error` on `QueryResponse`) already crossed that line once, narrowly, to fix one real ambiguity.

Requested next: make each pipeline stage clickable, with a "zoom view" showing that stage's actual data — what context was passed to the LLM, individual vector hit scores, which cited terms the Grounding Validator found or didn't. None of this exists anywhere derivable from the response as it stood. The deferred alternative's condition — "unless the derived version's gap turns out to matter" — is now squarely met: client-side inference has hit its ceiling.

## Decision

Add `PipelineDebug` (`app/domain/pipeline.py`) and mirror it as `PipelineDebugSchema` (`app/api/schemas.py`, ADR-0021's "API contracts are their own category" pattern). `QueryResponse.debug: PipelineDebug` is now always populated — every branch in `answer_query()` builds it from values it already computes, via one small typed helper (`debug_for(...)`), not duplicated logic:

| Field | Populated by | Empty/None when |
|---|---|---|
| `entity_match_kind`, `entity_match_candidates` | Entity Matcher's real `MatchResult` | never — every query reaches the matcher |
| `intent` | Router's real `Intent.kind` | the ambiguous-match short-circuit (Router never runs) |
| `vector_hits` (entity, score, snippet, `passed_cutoff`) | the real `VectorIndex.semantic_search()` result | any deterministic (structured/traversal) hit |
| `similarity_cutoff` | the real cutoff value used | same as above |
| `llm_raw_answer` | the model's actual output, **captured before** the Grounding Validator can replace it with the fixed refusal | deterministic hits, or the LLM call itself failing |
| `validator_cited_tokens`, `validator_missing_tokens` | the same token-extraction logic `_verify_grounding` already ran, exposed instead of discarded | anything that never reached generation |

The UI (`ui/src/main.ts`) turns each pipeline node into a `<button>`; clicking it opens an inline detail drawer directly under that message's own track — not the side slide-over, since the point is staying next to the exact node clicked in a scrollback that can hold many past traces. One drawer open at a time per message. `deriveStages()` (ADR-0027) also got richer for free: stage *detail* text now cites real match-kind/intent/hit-counts instead of the generic placeholders that field's absence used to force.

One deliberate visual choice: a rejected raw answer renders with a struck-through, dimmed treatment and the label "this is what got blocked, not what you saw" — the one moment in the whole UI that makes the Grounding Validator's existence viscerally concrete rather than a badge to take on faith.

## Consequences

### Positive
- Closes ADR-0027's stated gap for real, not with another derivation trick — `llm_raw_answer` in particular literally cannot exist any other way, since the pipeline discards the model's real output the moment the Validator rejects it.
- `deriveStages()`'s labels are now accurate on every route, not just the ones this ADR was about.
- Verified live end-to-end before any frontend work started: real vector hit scores, real entity-match kind, real captured provider-error text, all confirmed correct in the raw JSON response first.

### Negative
- **This is the "new backend logic" ADR-0025/0027 both drew a line against**, crossed deliberately here because the alternative (guessing scores, snippets, and raw model text from nothing) isn't possible, not because the line stopped mattering. Future UI features should still default to derivation; this is the exception, not a new pattern.
- `llm_raw_answer` puts the model's rejected output on the wire even when the user only sees a refusal. Fine for this project's public CDM schema content; would need a second look before reusing this pattern anywhere the underlying data is sensitive.
- Response payload size grows on the semantic route (five snippet-bearing vector hits, potentially a full raw answer) — a non-issue at this project's scale (44 entities, single-digit KB responses), worth remembering if the corpus ever grew by orders of magnitude.

## Alternatives Considered

Keep deriving everything client-side and simply not build the zoom view — rejected; the request was specifically for real per-query data the derived approach cannot produce. A separate `/query/{id}/debug` endpoint fetched on demand — rejected as more machinery (an id to mint and correlate) for no benefit over just including it in the one response that already exists; nothing here is expensive to compute since it's values the pipeline produces anyway, not new work done only when asked.

## Related Decisions

- [ADR-0027](0027-pipeline-view-derived-client-side.md) — the "derive, don't add backend surface" default this ADR's Amendment section already dented once, and this ADR crosses further, on purpose
- [ADR-0021](0021-schema-based-design-at-port-boundaries.md) — the API-contracts-are-their-own-category pattern `PipelineDebugSchema` follows
- [ADR-0010](0010-post-generation-grounding-verification.md) — the Grounding Validator whose actual mechanics (cited vs. missing tokens) this makes inspectable
