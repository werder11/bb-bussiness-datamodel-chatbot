# ADR-0030: Interactive "Score an Answer" Utility — Real Pipeline, Lexical Comparison, No External Eval Framework

**Status:** Accepted
**Date:** 2026-08-12
**Deciders:** Emre Gözütok

## Context

Early in this session's UI work, before the eval-snapshot panel (ADR-0026) was built, the question came up of whether to extend evaluation with real RAGAS/DeepEval integration via an API, and separately whether an interactive "evaluate this answer against a desired answer" utility made sense. The KPI-snapshot direction was pursued and shipped (ADR-0026); the interactive utility was left as a stated recommendation, never built, tracked in the task checklist as outstanding.

`tests/eval/run.py` already establishes this project's answer-quality philosophy: Faithfulness, Answer Relevancy, and Completeness are all "simplified operational proxies" (the module's own docstrings say so directly) rather than calls to RAGAS, DeepEval, or an LLM-as-judge — deliberate, per `docs/quality/evaluation-strategy.md`'s "not a complicated evaluation framework" stance. Any interactive utility built now should extend that same philosophy to a single, ad-hoc, user-supplied question rather than introduce a second, inconsistent evaluation approach.

## Decision

Add `POST /evaluate`: given `{question, expected_answer}`, it runs the real pipeline (`answer_query` — same code path `/query` uses, real entity match, real retrieval, a real LLM call on the semantic route) and compares the real answer to the user-supplied `expected_answer` with a plain lexical comparison — `app/domain/comparison.py::compare_answer()`:
- **Similarity**: `difflib.SequenceMatcher` ratio over the raw text, 0-1.
- **Shared / missing / extra terms**: word-level set comparison (lowercased, stopwords removed, 3+ letter tokens) — shared (in both), missing (in the desired answer, not the real one — a coverage gap), extra (in the real answer, not the desired one).

No embedding model, no LLM-as-judge call, nothing beyond what the pipeline already computes plus one `difflib` call — zero new runtime cost beyond what a normal `/query` call already costs.

UI: a new "🧪 Score an answer" panel (reusing the existing slide-over, the fourth thing to reuse it after entity detail / info / eval snapshot) with a question input and a desired-answer textarea. Submitting shows the real rendered answer with badges and matched-entity links (reusing `renderAnswer`), the pipeline zoom-view (ADR-0028) always expanded — not gated behind the chat box's opt-in toggle, since the entire point of this panel is inspecting one answer closely — and a comparison card: a similarity bar (reusing the KPI panel's bar-fill styling) plus three chip rows (reusing the Validator drawer's `chip-found`/`chip-missing` classes, with a new neutral `chip-extra` for terms the real answer introduced beyond the desired one).

## Rationale

- **Consistent, not competing, evaluation philosophy.** `tests/eval/run.py` already rejected RAGAS/DeepEval integration in favor of simple, transparent, zero-cost proxies for the batch eval dataset. Building a second, framework-backed comparison method for the interactive case would leave two different definitions of "how good is this answer" in the same codebase, disagreeing with each other for no good reason.
- **Real pipeline, not a simulation.** Running the actual `answer_query()` — not a separate scoring-only code path — means every debug field, badge, and pipeline-view stage the user sees is exactly what a real chat query would have produced; the utility is a lens on the real system, not an approximation of it.
- **Zero-cost by construction.** No new embedding calls, no new LLM calls beyond what the question's own route already requires. A user probing many candidate desired-answers costs nothing extra per probe beyond the one real pipeline run.
- **Explainable over precise.** Shared/missing/extra term chips tell a user *why* the similarity score is what it is — the same "diagnosability over opacity" instinct `tests/eval/run.py`'s `_diagnostics_section()` and ADR-0017 already establish for the batch report, applied here to a single ad-hoc question.

## Consequences

### Positive
- Closes the one recommendation from this session's UI work that was discussed but never built.
- No new runtime dependency, no new external API, no new cost surface — `app/domain/comparison.py` is ~40 lines of pure stdlib.
- Reuses four already-built UI primitives (slide-over panel, badges, pipeline zoom-view, chip rows) rather than introducing new visual language.
- Found and fixed a real, unrelated concurrency bug while verifying this feature (see "Related discovery" below) — a materially more valuable outcome than the feature itself.

### Negative
- Lexical/word-overlap comparison is a much cruder signal than an embedding-similarity or LLM-as-judge score would give — two answers that are semantically identical but phrased very differently score low. Acceptable for the same reason `_answer_relevancy`'s proxy is acceptable in the batch runner: transparency and zero cost matter more than precision for a ~44-entity demo corpus, and the chip breakdown lets a user see *why* a low score happened rather than trust an opaque number.
- `expected_answer` is free text with no structure (unlike `tests/eval/dataset.py`'s `expected_entities`/`expected_attributes`), so this utility can't feed into the batch KPI report — it's a standalone inspection tool, not a way to grow the eval dataset.

## Alternatives Considered

**Wire in a real RAGAS/DeepEval call via API**, scored explicitly in the early-session discussion — rejected: introduces an external dependency and live-call cost for a single-question ad-hoc tool, inconsistent with the batch runner's own stated avoidance of the same frameworks.

**Embedding-similarity comparison** (reuse the existing `sentence-transformers` model already loaded for retrieval) instead of `difflib` — considered, not chosen for this pass: adds a second use of the embedding model outside its retrieval role, and a cosine-similarity float is less immediately explainable to a user than a set of shared/missing words. Worth revisiting if lexical comparison proves too coarse in practice.

**A second, separate results view instead of reusing `renderAnswer`/the pipeline drawer** — rejected: the whole value of this utility is inspecting a real answer the same way the chat box shows one; a bespoke rendering would drift from what `/query` responses actually look like.

## Related discovery: a real SQLite concurrency bug

Verifying this feature's Playwright coverage (`ui/tests/e2e/evaluate.spec.ts`, run with `fullyParallel: true`) surfaced a genuine, pre-existing bug unrelated to this feature's own logic: `SQLiteStructuredIndex` (`app/adapters/structured_index_sqlite.py`) shares one `sqlite3.Connection` across every request (`check_same_thread=False`, required since FastAPI runs sync handlers on threadpool worker threads), but had no lock serializing access to it. Two concurrent requests (a `/query` and an `/evaluate` call, both hitting `get_attributes` at once) interleaved their `execute()`/`fetchall()` calls on the shared connection and produced a corrupted row — `Attribute(name=None, data_type=None)`, a real Pydantic `ValidationError` surfaced as a 500.

Fixed with a `threading.RLock()` (`RLock`, not `Lock`, since `get_attributes`/`get_relationships`/`traverse` each call the internal `_entity_exists()` helper, which also acquires it) wrapping every method that touches `self._conn` or `self._adjacency`. Regression test: `tests/unit/test_adapters_sqlite.py::TestConcurrentAccess` — 200 reads across 16 threads, asserting no corrupted rows. This bug existed before this session's Playwright work (ADR-0029) but was never triggered until a test genuinely fired concurrent requests at the same live process; the single-request curl-style verification this project relied on throughout could never have found it.

## Related Decisions

- [ADR-0017](0017-evaluation-as-first-class-layer.md) — the "evaluation as its own discipline, with diagnosability over opacity" stance this utility extends to a single ad-hoc question
- [ADR-0026](0026-eval-kpi-snapshot-in-ui.md) — the static batch-KPI counterpart this utility complements (snapshot of many questions vs. live inspection of one)
- [ADR-0028](0028-pipeline-zoom-view-server-side-debug-payload.md) — the zoom-view this panel always shows, unconditionally
- [ADR-0029](0029-playwright-e2e-tests.md) — the E2E suite whose concurrent test execution surfaced the SQLite bug fixed alongside this feature
