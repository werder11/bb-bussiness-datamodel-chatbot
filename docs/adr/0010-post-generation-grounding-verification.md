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

## Real-World Tuning (against live Gemini output, 2026-08-11)

The "too strict" risk predicted above materialized immediately the first time this ran against a real LLM (Gemini, [ADR-0024](0024-second-llm-provider-gemini.md)) instead of a fake: every semantic-route answer was refused, `verified=False`, even fully-grounded ones. Root cause: the excluded-common-words list only covered pronouns/articles, not the discourse markers Gemini reliably opens sentences and bullet points with — "**Based** on the provided context, ..." and "banking:X: **Defined** as ...". Both got treated as unsupported "cited entities" since they're capitalized and absent from the retrieved context text verbatim.

Fixed by expanding the exclusion list with these observed words (`app/domain/pipeline.py::_COMMON_CAPITALIZED_WORDS`), verified with a regression test (`tests/unit/test_pipeline.py::test_grounded_answer_with_hedging_discourse_marker_is_not_refused`) and a live eval re-run: Faithfulness went from 0% to 75% (3/4 scored) on the semantic-route questions that reached generation. This is evidence-driven tuning, not exhaustive — the list only contains words actually observed in real output, per this ADR's "tuned against the evaluation set" framing above. One eval question (disc-03) remained unverified after the fix and wasn't re-diagnosed because Gemini's free tier hit its **daily** quota (20 requests/day for the model behind `gemini-flash-latest` at time of testing) mid-session — a real operational constraint worth knowing before a live demo, not a code defect.

## Provider-Call Failures Treated the Same as Unverified (2026-08-11)

A second, distinct gap surfaced in the same live-testing session, once the free tier's rate limit actually tripped mid-demo: `llm.generate()` raising (timeout, rate limit, transient API error) was never caught anywhere — it propagated out of `answer_query()` as an unhandled exception, through FastAPI's default handler, into a raw 500 with no useful body. A real evidence-retrieval had already happened at that point; only the generation call itself failed.

Fixed in `app/domain/pipeline.py::answer_query()`: the `llm.generate()` call is now wrapped in a `try`/`except Exception`, degrading to exactly the same shape as an unsupported-claim refusal — `grounded=True` (real evidence was retrieved), `verified=False`, answer replaced with the fixed refusal. The underlying exception string is captured on `RetrievalTrace.error` (a new, optional field, `app/domain/tracing.py`) rather than swallowed, so operators can still see the real cause in logs without it ever reaching the API response. Verified live with a deliberately invalid API key: `HTTP 200`, a graceful refusal, and the real `429`/`400` provider error visible in the trace log.

Regression test: `tests/unit/test_pipeline.py::test_llm_call_failure_degrades_to_refusal_not_a_crash`.

## A Third Gap, Found Diagnosing the Second: the Trace Log Was Never Actually Emitted

Confirming the fix above required checking `docker logs`/the server console for the trace line — and it wasn't there. `app/api/main.py`'s `logger.info(trace.model_dump_json())` had been silently going nowhere since it was written: nothing in the app ever called `logging.basicConfig()` (or configured the root logger any other way), and uvicorn only configures its own `"uvicorn"`/`"uvicorn.access"` loggers, not the root logger or `"app.api"`. Python's logging module silently drops `INFO`-level records with no handler in the chain — no error, no warning, just nothing. This meant the Retrieval Tracer — [`docs/operations/monitoring.md`](../operations/monitoring.md)'s "concrete, inspectable evidence if asked live 'how do you know it's not hallucinating'" — had never actually produced a single log line, in any environment, since it was implemented.

Fixed with one line in `app/api/main.py`: `logging.basicConfig(level=logging.INFO, format="%(message)s")` before the logger is constructed. The bare-message format keeps the log line as pure JSON (`trace.model_dump_json()`), matching the "structured log line" the docs describe. Verified live: the trace line now appears in the console/`docker logs` on every request, including the new `error` field from the fix above.

## Alternatives Considered

No verification, relying on prompting alone — rejected, leaves the most likely hallucination mode entirely unchecked given it's an explicitly graded requirement. A second LLM call to self-critique the first — rejected for now as added cost/latency/complexity disproportionate to a demo; worth reconsidering if the simple containment check proves too blunt against the eval set.

## Related Decisions

- [ADR-0005](0005-explicit-grounding-guard-before-generation.md) — the complementary guard for the zero-context failure mode
- [ADR-0016](0016-deterministic-hits-template-rendered.md) — narrows this validator's meaningful scope to the LLM-generation path
