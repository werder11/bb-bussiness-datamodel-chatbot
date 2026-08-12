# ADR-0024: Add Google Gemini as a Second, Swappable LLM Provider

**Status:** Accepted
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

[ADR-0023](0023-tech-layer-adapters.md) chose Anthropic Claude as the LLM provider. In practice, the deliverable's owner didn't have an Anthropic API key available to exercise the semantic-search/generation path or run a complete `task eval:run` (Faithfulness/Answer Relevancy require a live LLM call). Google's Gemini API offers a genuinely free tier via Google AI Studio (no credit card required) for Flash-class models — a practical way to unblock live testing and the interview demo without cost.

This is also a concrete opportunity to demonstrate that [ADR-0001](0001-hexagonal-architecture-ports-and-adapters.md)'s `LLM` port/adapter boundary actually delivers what it promises: swapping providers should be "write a new adapter," not "touch the domain."

## Decision

Add `GeminiLLM` (`app/adapters/llm_gemini.py`) implementing the same `LLM` Protocol as `AnthropicLLM`, using the `google-genai` SDK. Structured identically to `AnthropicLLM` for consistency: the underlying client is constructor-injectable, real construction is deferred into a `_build_client` static method never reached by unit tests using a fake client, and `generate()` itself imports nothing from the SDK — the request config is passed as a plain dict (the SDK accepts either a dict or its typed `GenerateContentConfig`), keeping unit tests fully offline (ADR-0018).

Provider selection is a single small factory, `app/adapters/llm_factory.py`'s `build_llm()`, driven by an `LLM_PROVIDER` environment variable (`anthropic` | `gemini`, default `anthropic` — preserves ADR-0023's original choice as the default). Both `app/api/main.py`'s `lifespan` and `tests/eval/run.py` call this factory instead of hardcoding a provider, so switching providers is a `.env` change, not a code change.

## Consequences

### Positive
- Unblocks live testing and the interview demo without an Anthropic key or any cost.
- Concretely demonstrates the port/adapter architecture's swappability, not just its theoretical existence — a stronger interview talking point than the ADRs alone.
- No domain or pipeline code changed at all; only a new adapter, a new small factory, and one line each in the two composition roots (`app/api/main.py`, `tests/eval/run.py`).

### Negative
- Two providers to keep the system prompt/grounding behavior consistent across, going forward, if either adapter's prompt needs tuning based on the evaluation set.
- A real behavioral difference between the two SDKs, discovered while writing the factory's tests: `anthropic.Anthropic(api_key=None)` constructs successfully and only fails on the first real API call, but `google.genai.Client()` raises immediately if no key is present anywhere (env var or explicit) — it doesn't validate the key is *correct* at construction time, just that *something* was provided. Practical effect: `LLM_PROVIDER=gemini` with no `GEMINI_API_KEY` set fails at API startup (`lifespan`), not on the first `/query` call, unlike the Anthropic default. Documented here rather than papered over with a try/except, since a fail-fast startup is arguably the more correct behavior anyway.
- Free-tier usage note (Google AI Studio, not Vertex AI): Google may use free-tier inputs/outputs to improve its models. Irrelevant for this project's public CDM schema data, but worth knowing if this pattern is reused for anything sensitive later.
- Pinned model names go stale fast on this API: the original choice, `gemini-2.0-flash-001`, returned a hard 404 ("no longer available") the first time this was exercised against the live API (2026-08-11) — and its replacement, `gemini-2.5-flash`, 404'd the same way for new API keys minutes later. Switched to `gemini-flash-latest`, an alias Google maintains to always point at the current recommended Flash model, trading version pinning for staying live without code changes. The free tier behind that alias also carries a **daily** request cap (observed: 20/day for the model it resolved to at test time, separate from the smaller per-minute cap) — enough for interactive demo use but not for repeated full `task eval:run` cycles in one day; budget live-key testing accordingly.

## Alternatives Considered

Wait for an Anthropic key instead of adding a second provider — rejected, blocks live testing and the demo for no architectural benefit, and the port/adapter boundary already existed specifically to make this kind of swap cheap.

A generic multi-provider LLM library (e.g. LiteLLM) instead of a hand-rolled second adapter — rejected as disproportionate: the `LLM` Protocol is one method wide, and this project already has an established, working adapter pattern (`AnthropicLLM`) to mirror; a routing library would add a dependency and its own abstraction on top of one that already exists here.

## Related Decisions

- [ADR-0001](0001-hexagonal-architecture-ports-and-adapters.md) — the port/adapter boundary this decision exercises
- [ADR-0023](0023-tech-layer-adapters.md) — the original (still-default) LLM provider choice
- [ADR-0018](0018-testing-strategy-istqb-aligned.md) — the fast-gate requirement both adapters' dependency-injection pattern satisfies
