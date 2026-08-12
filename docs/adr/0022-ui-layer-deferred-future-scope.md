# ADR-0022: UI Layer Deferred to Future Scope

**Status:** Superseded by [ADR-0025](0025-ui-typescript-chat-and-entity-browser.md)
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

> **2026-08-11 update:** the UI was built later the same day. [ADR-0025](0025-ui-typescript-chat-and-entity-browser.md) implements exactly the shape this ADR pre-decided — thin client, no new backend logic — with the two remaining choices (tech stack, scope) made there. This document is kept for the reasoning behind *why* a UI wasn't in the original deliverable scope.

## Context

The case study brief asks for an API and a live demo of the API — not a UI. A UI is nonetheless a natural, low-risk extension once the API exists, and worth sketching so it's clear it was considered rather than overlooked.

## Decision

No UI is built for this deliverable. If added later, it is a **thin client only**: a chat-style front end that calls the existing `POST /query` (and `GET /entities*`) endpoints exactly as documented by the FastAPI OpenAPI schema (see [ADR-0021](0021-schema-based-design-at-port-boundaries.md)) — no new backend logic, no bypass of the Grounding Guard/Validator. A minimal Streamlit app or a static HTML+JS page are both sufficient candidates; neither changes any decision in this document.

```
[Optional, future] Chat UI ──POST /query──▶ FastAPI (unchanged)
```

## Consequences

### Positive
- Zero cost now; clearly scoped so it can't quietly expand into "let's also build a frontend" during the take-home window.
- Because the API is schema-driven (ADR-0021), a future UI has a stable, typed contract to build against without needing backend involvement.

### Negative
- The live demo (a required deliverable) will be shown via API calls (e.g. a REST client, curl, or the FastAPI `/docs` Swagger UI) rather than a polished chat window — acceptable, the brief asks for a live demo of the API, not a product UI.

## Alternatives Considered

Build a minimal Streamlit UI now — rejected for this deliverable: not requested, and the time is better spent on the graded requirements (ingestion, retrieval, grounding, tests, Dockerfile). FastAPI's auto-generated `/docs` Swagger UI already provides an interactive, zero-effort way to demo the API live.

## Related Decisions

- [ADR-0021](0021-schema-based-design-at-port-boundaries.md) — the typed API contract a future UI would build against
