# Roadmap

## Current phase: implementation complete

All 9 build phases of the approved implementation plan (`.docs/adhoc/cdm-rag-chatbot/cdm-rag-chatbot-{plan,tasks}.md`) are done, tested (122 automated tests across unit/integration/system/acceptance), and verified against the real 44-entity ingested corpus and a real running Docker container — not just written. See [`docs/README.md#current-project-phase`](../README.md#current-project-phase).

## What's left

Everything below is packaging/demo prep, not missing capability:

1. **Commit and push to GitHub.** As of this writing, only the original architecture/docs scaffold is committed — every implementation phase's code (`app/`, `tests/`, `Dockerfile`, `.github/workflows/ci.yml`, ADR-0024, and the live-testing bug fixes below) is sitting uncommitted in the working tree, and no GitHub remote exists yet. **This is now the single largest remaining gap** — everything else below is done.
2. ~~Run a real `task eval:run` with a live LLM key~~ — **done.** Ran end-to-end against a live Gemini key (real Docker container, real ingestion, real Gemini calls). Found and fixed two real bugs invisible to unit tests: a Gemini model name Google had removed server-side (now `gemini-flash-latest`, an alias that won't go stale the same way — [ADR-0024](../adr/0024-second-llm-provider-gemini.md)), and a Grounding Validator that was refusing genuinely correct answers over an incomplete word-exclusion list ([ADR-0010](../adr/0010-post-generation-grounding-verification.md)). `docs/eval-report.md` now has real numbers: Faithfulness 75%, Answer Relevancy 95%, all retrieval metrics 100% except vector Recall@5 at 89%. Note for the demo: Gemini's free tier has a daily cap (20 requests/day observed), separate from its per-minute cap — budget live calls accordingly.
3. **Confirm the CI workflow actually runs on GitHub** — `.github/workflows/ci.yml` mirrors `task ci:fast`/`task ci:slow` exactly and that composition is verified locally, but the workflow itself has never executed against real GitHub Actions infrastructure (depends on item 1).
4. ~~Build the two non-code deliverables~~ — **both done.** The 4-slide technical walkthrough (`presentation/technical-walkthrough.html`, built from the content basis in [`docs/vision/goals.md#positioning-for-the-technical-walkthrough`](goals.md#positioning-for-the-technical-walkthrough) plus real numbers from `docs/eval-report.md`) and the self-intro slide (`presentation/self-intro.html`, strengths/experience/role-evolution, grounded in the real resume and reference letter, tailored against the actual reeeliance job posting). Same visual system, self-contained, no build step.

## Deliverables checklist

From the task brief:
- [ ] GitHub repository link with source code — code complete, not yet committed/pushed (see item 1 above).
- [x] Live demo of the API — verified live end-to-end against the real corpus and a real Gemini key, all routes (structured, traversal, semantic, refusals); ready to repeat live. Beyond the brief's ask: a clickable UI (chat + entity browser) is also available at the API's root, not just curl/Swagger — see [ADR-0025](../adr/0025-ui-typescript-chat-and-entity-browser.md).
- [x] Technical walkthrough, max 4 slides — embedding strategy + how relationships were handled — `presentation/technical-walkthrough.html`, self-contained HTML deck, every number pulled from the real running system.
- [x] Self-intro slide — "How do I see myself as a Senior Data & AI Architect at reeeliance?" — `presentation/self-intro.html`, strengths/experience/role-evolution mapped against the real reeeliance job posting.

## Future scope (not built, deliberately)

- ~~**UI layer** — a thin client over the existing API, no new backend logic.~~ **Built 2026-08-11** — TypeScript chat box + entity browser, served by FastAPI itself. See [ADR-0025](../adr/0025-ui-typescript-chat-and-entity-browser.md) (supersedes [ADR-0022](../adr/0022-ui-layer-deferred-future-scope.md)).
- **Full CDM coverage beyond Banking + common objects** — the current scope (44 entities) is a deliberate cut per the brief; expanding it should mean re-running ingestion, not re-architecting, per the Scalability NFR in [`docs/architecture/README.md`](../architecture/README.md#requirements).
- **Deeper Resolver fidelity via the official Microsoft ObjectModel SDK**, if the scoped custom resolver's known limitations ([ADR-0007](../adr/0007-resolver-scope-bounded-anti-corruption-layer.md)) prove costly in practice.
- **Re-ingestion on upstream CDM changes** — currently version-pinned at ingestion time with no drift detection ([ADR-0008](../adr/0008-cdm-source-version-pinned-at-ingestion.md)).
