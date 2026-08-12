# ADR-0025: UI — TypeScript Chat + Entity Browser, Statically Served by FastAPI

**Status:** Accepted (supersedes [ADR-0022](0022-ui-layer-deferred-future-scope.md))
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

[ADR-0022](0022-ui-layer-deferred-future-scope.md) deferred the UI, pre-deciding its shape if it were ever built: a thin client only, calling the existing `POST /query` / `GET /entities*` endpoints, no new backend logic, no bypass of the Grounding Guard/Validator. That decision is revisited here, not overturned — the request now is to actually build it, and ADR-0022's shape constraint is exactly what's implemented.

Two concrete choices remained: what to build it *with*, and what it should *cover*. Decided directly with the user: TypeScript (not the plain JS or Streamlit ADR-0022 had listed as candidates), and chat box + entity browser (not chat-only).

## Decision

- **Stack**: Vite + TypeScript, no UI framework (no React/Vue). One page, ~350 lines of hand-written DOM code across `src/main.ts`/`api.ts`/`types.ts`. `tsconfig.json` runs in `strict` mode with `noUncheckedIndexedAccess` — same rigor as `mypy` on the Python side.
- **Contract**: `src/types.ts` hand-mirrors `app/api/schemas.py`'s four response shapes exactly. No codegen — four small shapes don't justify an OpenAPI-client-generator dependency, and hand-mirroring means a backend schema change that breaks the UI shows up as a TypeScript compile error, not a silent runtime mismatch.
- **Scope**: a chat panel (`POST /query`, rendering the answer plus `route`/`grounded`/`verified` badges and clickable matched-entity chips) and an entity browser sidebar (`GET /entities` on load, `GET /entities/{name}` on click) — both directly against existing endpoints, zero new backend code, per ADR-0022's constraint.
- **Serving**: built to static files (`ui/dist`) and served by FastAPI itself via `StaticFiles`, mounted at `/` *after* every API route so `/health`/`/entities*`/`/query` always match first (`app/api/main.py`). One container, one port, no CORS configuration anywhere, no separate frontend server/process to run or deploy — same "single container" reasoning as ADR-0004/0023's embedded-database choices.
- **Build**: a third Docker stage (`frontend-builder`, `node:22-slim`) — Node never touches the runtime image, only its `dist/` output does (mirrors the existing `builder`/`runtime` stage separation, ADR-0002). `task ui:build`/`task ui:dev` (`tasks/ui.yml`) for local dev; `task ci:fast` now runs `ui:build` (type-check via `tsc --noEmit`, then the Vite build) before `docker:build`, so a UI type error fails the fast gate — the Docker build would have caught it anyway (the frontend stage runs the same `npm run build`), this just fails faster.
- **`app/api/main.py`'s mount guards on `Path(_UI_DIST_PATH).is_dir()`** — `ui/dist` only exists after a build, so importing the app in test/CI environments that never build the UI still works; they simply get 404s under the mount, and every existing test is unaffected.

## Consequences

### Positive
- Zero new Python dependencies; zero new runtime processes; the "one container" architecture story stays intact.
- A live, clickable demo of both the generation path and the structured index, not just curl/Swagger — meaningfully better for an in-person walkthrough than ADR-0022's fallback (`/docs`).
- TypeScript's structural typing against hand-mirrored schemas gives a real (if partial) contract check between the two layers without a shared-codegen pipeline.

### Negative
- A second toolchain (Node/npm) enters the build, alongside Python — more to install locally (`task ui:setup`) and a longer Docker build (an extra stage, `node:22-slim` pull).
- The hand-mirrored TypeScript types can drift from `app/api/schemas.py` silently if a field is renamed on one side and not the other — no automated contract test catches this today (would need something like a schema snapshot test or OpenAPI-generated types to fully close). Acceptable for this deliverable's scope; worth revisiting if the UI grows.
- No frontend automated tests (no Vitest/Playwright) — verified instead by `tsc --noEmit` (type safety), a real `npm run build`, and live HTTP-level smoke tests against a running container (status codes, asset MIME types, JSON responses). Interactive/visual behavior (does clicking actually work, does it look right) was **not** verified by an automated browser tool — no such tool was available in the agent environment that built this. Manual verification in an actual browser is still needed before relying on this for a live demo.

## Alternatives Considered

Plain JavaScript or Streamlit, as ADR-0022 originally floated — superseded by the user's explicit choice of TypeScript. A UI framework (React/Vue) — rejected as disproportionate for one page with two panels; vanilla DOM code with TypeScript's type safety gets the same correctness benefit without the framework/bundler-config surface area. Generating the TS types from the OpenAPI schema instead of hand-mirroring — rejected for now given only four small shapes exist; noted above as the fix if the contract-drift risk becomes real.

## Related Decisions

- [ADR-0022](0022-ui-layer-deferred-future-scope.md) — superseded; pre-decided the "thin client only" shape this ADR implements
- [ADR-0021](0021-schema-based-design-at-port-boundaries.md) — the typed API contract the UI builds against
- [ADR-0002](0002-separate-offline-ingestion-from-online-query-path.md) — the builder/runtime stage-separation pattern the new `frontend-builder` stage follows
- [ADR-0004](0004-embedded-structured-index-not-a-database-server.md) / [ADR-0023](0023-tech-layer-adapters.md) — the "one container" reasoning this decision preserves
