# Architecture Documentation — CDM RAG Chatbot

Entry point for developers, reviewers, and AI coding agents. Read this first.

## System Purpose

A Python/FastAPI RAG service that answers natural-language questions about the Microsoft Common Data Model's Banking Model — which entities exist, their attributes, their relationships — grounded in the actual ingested schema, never hallucinated. Built as a take-home case study for a Senior Data & AI Architect role at reeeliance. Full context: [Vision: Goals](vision/goals.md).

## Architecture Overview

Microsoft CDM is resolved into a vendor-independent Canonical Model, then projected two ways — a relational projection for deterministic data access, a semantic projection for retrieval over free-text. The AI layer sits above this data architecture, invoked only where semantic interpretation adds value. See [Architecture: Components](architecture/components.md) for the full diagram, or [Vision: Goals](vision/goals.md#positioning-for-the-technical-walkthrough) for the one-paragraph version.

## Documentation Map

The navigation model this documentation follows:

```
Vision → Architecture → Domain → Design → Quality → ADRs → API → Operations
```

| Layer | Purpose | Location |
|---|---|---|
| [Vision](vision/README.md) | Why does the system exist? What's the roadmap? | `docs/vision/` |
| [Architecture](architecture/README.md) | What is the system's structure? (requirements, context, containers, components, principles) | `docs/architecture/` |
| [Domain](domain/README.md) | What business concepts exist? (the CDM itself) | `docs/domain/` |
| [Design](design/README.md) | How do components work, dynamically? | `docs/design/` |
| [Quality](quality/README.md) | How is "good" checked? (testing + evaluation, kept distinct) | `docs/quality/` |
| [Decisions](adr/README.md) | Why were specific choices made? | `docs/adr/` |
| [API](api/README.md) | How do clients communicate with the system? | `docs/api/` |
| [Operations](operations/README.md) | How is the system built, deployed, gated, observed? | `docs/operations/` |

`Quality` is an addition beyond the base seven-layer template — this project treats testing and evaluation as two distinct first-class disciplines ([ADR-0017](adr/0017-evaluation-as-first-class-layer.md), [ADR-0018](adr/0018-testing-strategy-istqb-aligned.md)), not a subsection of Architecture.

Outside this knowledge graph: [`FINDINGS.md`](../FINDINGS.md) (project root) is the raw research log — the working notes from investigating the task brief and the CDM source repo, kept separate from the cleaned-up reference pages above.

## Active Decisions

31 ADRs, all **Accepted** (two superseded by later ones) — full index with status, date, and a suggested reading order: [`docs/adr/README.md`](adr/README.md). Headline decisions:

| ADR | Topic | Status |
|---|---|---|
| [0001](adr/0001-hexagonal-architecture-ports-and-adapters.md) | Hexagonal Architecture (Ports & Adapters) | Accepted |
| [0007](adr/0007-resolver-scope-bounded-anti-corruption-layer.md) | Resolver scope explicitly bounded | Accepted |
| [0009](adr/0009-relationship-traversal-bounded-to-depth-2.md) | Bounded graph traversal for relationships | Accepted |
| [0013](adr/0013-deterministic-hits-through-llm-for-phrasing.md) | Always route through the LLM | **Superseded** by 0016 |
| [0016](adr/0016-deterministic-hits-template-rendered.md) | Template deterministic hits, LLM only for synthesis | Accepted |
| [0017](adr/0017-evaluation-as-first-class-layer.md) | Evaluation as a first-class layer | Accepted |
| [0021](adr/0021-schema-based-design-at-port-boundaries.md) | Schema-based design at every boundary | Accepted |
| [0023](adr/0023-tech-layer-adapters.md) | Tech-layer adapters — ChromaDB, sentence-transformers, per-entity chunking | Accepted |
| [0024](adr/0024-second-llm-provider-gemini.md) | Second LLM provider (Gemini), swappable via `LLM_PROVIDER` | Accepted |
| [0025](adr/0025-ui-typescript-chat-and-entity-browser.md) | UI — TypeScript chat + entity browser, served by FastAPI | Accepted |
| [0026](adr/0026-eval-kpi-snapshot-in-ui.md) | Evaluation KPI snapshot in the UI, build-time not live | Accepted |
| [0027](adr/0027-pipeline-view-derived-client-side.md) | Pipeline view, reconstructed client-side, no new API field | Accepted |
| [0028](adr/0028-pipeline-zoom-view-server-side-debug-payload.md) | Pipeline zoom view — real per-query debug payload | Accepted |
| [0029](adr/0029-playwright-e2e-tests.md) | Playwright E2E tests — real browser, no LLM credentials required | Accepted |
| [0030](adr/0030-interactive-answer-scoring-utility.md) | Interactive "score an answer" utility — real pipeline, lexical comparison | Accepted |
| [0031](adr/0031-migrate-to-uv.md) | Migrate Python dependency management to uv | Accepted |

All vendor/tech picks (vector DB, LLM provider(s), embedding model, chunking granularity) are decided — see [`FINDINGS.md §7`](../FINDINGS.md#7-open-architecture-decisions) for the resolution history.

## Current Project Phase

Implementation complete — all 9 build phases done, tested (122 automated tests across unit/integration/system/acceptance), and verified against the real 44-entity ingested corpus and a real running Docker container. Remaining work is non-code: committing/pushing the repo, and the self-intro + technical-walkthrough slides. See [Vision: Roadmap](vision/roadmap.md) and `.docs/adhoc/cdm-rag-chatbot/cdm-rag-chatbot-tasks.md` for the detailed checklist.

## AI Agent Navigation Rule

Before making implementation changes: read this file → identify the affected layer(s) above → read the relevant Architecture/Domain/Design pages → check related ADRs → check Quality (does this change need a test level, an eval-set case, or both?) → make the change → update the affected layer's docs if the change is architectural, not just implementation detail.
