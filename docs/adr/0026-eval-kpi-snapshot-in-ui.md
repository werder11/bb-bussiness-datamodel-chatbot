# ADR-0026: Evaluation KPI Snapshot in the UI — Build-Time, Not Live

**Status:** Accepted
**Date:** 2026-08-12
**Deciders:** Emre Gözütok

## Context

The UI ([ADR-0025](0025-ui-typescript-chat-and-entity-browser.md)) demos live retrieval and generation, but says nothing about the aggregate evidence behind it — the whole reason [ADR-0017](0017-evaluation-as-first-class-layer.md) treats evaluation as a first-class layer with named, RAGAS-aligned metrics. Discussed and explicitly scoped down from two adjacent, larger ideas:

1. **Actually running `ragas`/`deepeval`** as dependencies instead of the existing hand-rolled metric implementations — rejected. Both compute their scores via LLM-as-judge, typically several calls per question, which would multiply LLM usage on a free tier that had already hit its daily cap twice in one day during this project's live testing (see [ADR-0024](0024-second-llm-provider-gemini.md)). The existing implementation already claims RAGAS's metric *definitions* by name (`docs/quality/evaluation-strategy.md`) without that cost; running the real libraries live would trade a defensible, understood design for a framework dependency, for no metric-quality gain proportionate to the risk.
2. **A live "run evaluation" button in the UI**, calling a new backend endpoint that triggers `tests/eval/run.py` on demand — rejected. This is real generation-path LLM traffic, hard to size in advance (27 questions, several with retries), and doing it from a UI click in front of a live audience risks hitting the same rate limit mid-demo. It would also be the first UI feature to need genuinely new backend logic, crossing the "thin client only" line ADR-0022/0025 both hold deliberately.

## Decision

Show the *last real* evaluation run's KPIs as a static snapshot, baked into the UI's JS bundle at build time — not fetched, not triggered, not live.

- `tests/eval/run.py`'s `main()` now writes a second file alongside `docs/eval-report.md`: `ui/src/eval-snapshot.json`, a compact dict of the same numbers already computed for the markdown report (no duplicated computation, no extra LLM calls — `_render_report` now returns `tuple[str, dict]` instead of just the markdown string).
- The UI imports it directly — `import evalSnapshotData from "./eval-snapshot.json"` — so Vite inlines the numbers into the built JS at compile time (confirmed: the built bundle contains the literal values, not a fetch call). Viewing the panel costs nothing and needs no network request beyond the page load already happening.
- A "📊 Evaluation" button in the chat header opens it in the same slide-over panel already used for entity details and "How this works" — the third use of that one interaction pattern, not a third UI paradigm.
- `eval-snapshot.json` is committed (unlike `docs/eval-report.md`, which stays gitignored as a full diagnostic dump) — the UI build has a hard dependency on it existing, so it can't be treated as a purely regenerable, ignorable artifact the way the markdown report is.

## Consequences

### Positive
- Zero marginal cost to view, zero new backend surface, zero risk of a live rate-limit failure during a demo.
- Single source of truth: the snapshot numbers come from the exact same computation as the markdown report, in the same run — no risk of the two drifting by being computed twice.
- Directly demos ADR-0017's thesis ("quality is measurable, not just asserted") without asking the audience to go read a markdown file.

### Negative
- **Goes stale.** The snapshot reflects whichever `task eval:run` last committed it, not the code currently running. Mitigated by an explicit `generated_at` date shown in the panel and by the underlying claim being narrow ("here's evidence from a real run," not "here's what's true right now") — but a reviewer who reads the code between eval runs could see a mismatch.
- Two files now carry KPI numbers (`docs/eval-report.md`, `ui/src/eval-snapshot.json`) that must be regenerated together; `task eval:run` does write both from one run, but nothing currently enforces they're committed together if someone hand-edits one.

## Alternatives Considered

Real `ragas`/`deepeval` integration and a live "run eval" UI button — both covered under Context above. Fetching `docs/eval-report.md` at runtime and parsing the markdown client-side — rejected as more fragile than a small, purpose-built JSON snapshot (markdown structure could change without a compile-time signal; the JSON schema is a TypeScript type that fails the build if it drifts).

## Related Decisions

- [ADR-0017](0017-evaluation-as-first-class-layer.md) — the evaluation design this makes visible in the UI
- [ADR-0025](0025-ui-typescript-chat-and-entity-browser.md) — the "thin client only" constraint this stays within
- [ADR-0024](0024-second-llm-provider-gemini.md) — the free-tier quota constraints that ruled out the two live-LLM alternatives
