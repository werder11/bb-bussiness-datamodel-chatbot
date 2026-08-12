# ADR-0029: Playwright E2E Tests — Real Browser, Real Server, No LLM Credentials Required

**Status:** Accepted
**Date:** 2026-08-12
**Deciders:** Emre Gözütok

## Context

Every UI feature built this session (ADR-0025 through ADR-0028) had the same verification gap: confirmed correct via `curl` against the real API and via `tsc`/`vite build` succeeding, but never actually exercised in a real browser by the agent building it — no browser automation tool was available. Each ADR up to this one says some version of "not verified: actual browser rendering/click-through." The user tested manually in a real browser throughout, but nothing automated ever did.

This is also the same gap `docs/quality/testing-strategy.md`'s four ISTQB-aligned levels (Component/Unit, Component Integration, System, Acceptance — ADR-0018) don't cover: all four exercise the FastAPI app directly (`TestClient`) or Python objects directly, never a real DOM, never real click/type/navigate behavior.

## Decision

Add a fifth test level: Playwright E2E, living in `ui/tests/e2e/` (a UI-scoped concern, not a Python one — `ui/` already has its own `package.json`/toolchain). Five spec files, 32 tests total: `chat.spec.ts` (page load, all four deterministic sample-query routes, free-text submission, matched-entity links), `entity-panel.spec.ts` (list, filter, detail panel), `pipeline-view.spec.ts` (toggle behavior, stage derivation, click-to-zoom drawer), `pipeline-view-semantic.spec.ts` (see below), `info-and-eval-panels.spec.ts`.

**Needs zero LLM credentials, by design** — same "fast, free, deterministic" discipline ADR-0018/0019 apply to the Python test levels, extended to the browser:
- Every `chat.spec.ts`/`entity-panel.spec.ts`/`pipeline-view.spec.ts` assertion exercises a route that never touches the model (structured, traversal, ambiguous, out-of-scope refusal) — real backend, real corpus, zero cost.
- The semantic/LLM-route UI cases (`pipeline-view-semantic.spec.ts`) — the ones this project has repeatedly found real bugs in live (ADR-0010, ADR-0027's amendment) — are tested by intercepting `POST /query` at the network layer (`page.route()`) and fulfilling with response shapes copied verbatim from real captured API responses earlier in this project. The UI code under test has no idea the network layer is mocked; this exercises the exact same rendering path a real Gemini response would, without spending the free tier's 20-requests/day budget or being flaky against a rate limit mid-test-run.

`playwright.config.ts`'s `webServer` boots the real `uvicorn app.api.main:app` from the repo root (paths inside `main.py` resolve relative to cwd, not the config file's location) and waits on `/health` — the same real corpus (`cdm.db`, `chroma_data/`) every other test level and the live demo use, not a fixture subset.

**Not wired into `task ci:fast` by default.** Installing a browser binary (~150-300MB, `task ui:e2e:setup`) is real one-time weight the existing fast gate doesn't carry, and this project's CI runs on GitHub-hosted runners without a persistent cache for it yet. `task ui:e2e` exists as an explicitly-invoked task — run it yourself (locally, or before the interview) rather than on every push. Revisit if this project ever gets a `browsers` cache step in `.github/workflows/ci.yml`.

## Consequences

### Positive
- First real, automated confirmation — not agent-narrated, not manually eyeballed — that the UI actually works: all 32 tests passed against the real running app on the first corrected run (two initial failures were test bugs — a race against an unrealistically-fast deterministic response, and a miscounted assertion — not app bugs; both fixed and reconfirmed).
- The mocking pattern for the semantic route means the UI's most bug-prone path (this project's history: two real live-found bugs there) now has fast, free, repeatable coverage instead of none.
- Closes every "not verified in an actual browser" caveat left open by ADR-0025 through ADR-0028.

### Negative
- Mocked semantic-route tests can drift from the real API shape if `QueryResponse`/`PipelineDebug` change without the fixtures in `pipeline-view-semantic.spec.ts` being updated — the TypeScript import of `QueryResponse` (`import type { QueryResponse } from "../../src/types"`) catches a *shape* drift (a missing/renamed field fails to compile) but not a *semantic* drift (e.g. the real pipeline starting to also populate a field the fixture leaves empty). Real API-contract testing (the deterministic specs) doesn't have this risk.
- Not part of the fast gate — a UI regression the deterministic specs would have caught can still merge if nobody runs `task ui:e2e` locally first. Accepted for now given the setup weight; not a permanent stance.
- Single browser (Chromium) only, no cross-browser matrix — proportionate to this project's scope, not a claim of full compatibility coverage.

## Alternatives Considered

Cypress — comparable capability, but Playwright's built-in `webServer` orchestration and native TypeScript support fit this project's existing Vite/TS toolchain with less configuration. Wiring E2E into `ci:fast` immediately — rejected for now per the "Not wired into ci:fast" reasoning above; the task exists and works, adoption into CI is a follow-up, not a blocker. Testing the semantic route against the real live API instead of mocking — rejected: this project's own history shows that path hits Gemini's daily quota reliably within a normal working session, which would make the suite flaky by design.

## Related Decisions

- [ADR-0018](0018-testing-strategy-istqb-aligned.md) — the four Python-side levels this adds a fifth, UI-side level alongside
- [ADR-0019](0019-cicd-pipeline-layered-by-cost-and-speed.md) — the "no live calls in the fast/free tier" discipline this extends to the browser
- [ADR-0025](0025-ui-typescript-chat-and-entity-browser.md), [ADR-0027](0027-pipeline-view-derived-client-side.md), [ADR-0028](0028-pipeline-zoom-view-server-side-debug-payload.md) — the UI features this suite is the first automated verification of
