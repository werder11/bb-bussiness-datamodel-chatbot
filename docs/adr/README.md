# Architecture Decision Records — CDM RAG Chatbot

Structural/shape-level architecture decisions for the reeeliance Business Data Model Chatbot case study, plus the vendor-level tech-adapter decisions (ADR-0023) that were deliberately deferred until the shape was settled — see [`FINDINGS.md §7`](../../FINDINGS.md#7-open-architecture-decisions) for that resolution history. See [`docs/README.md`](../README.md) for the full documentation map this ADR set is one layer of.

## Index

| ADR | Title | Status | Date |
|---|---|---|---|
| [0001](0001-hexagonal-architecture-ports-and-adapters.md) | Hexagonal Architecture (Ports & Adapters) | Accepted | 2026-08-11 |
| [0002](0002-separate-offline-ingestion-from-online-query-path.md) | Separate Offline Ingestion from the Online Query Path | Accepted | 2026-08-11 |
| [0003](0003-dual-projection-retrieval-not-cqrs.md) | Dual-Projection Retrieval — "Polyglot Read Models," Not CQRS | Accepted | 2026-08-11 |
| [0004](0004-embedded-structured-index-not-a-database-server.md) | Embedded/In-Process Structured Index, Not a Database Server | Accepted | 2026-08-11 |
| [0005](0005-explicit-grounding-guard-before-generation.md) | Explicit Grounding Guard Before Any Generation Call | Accepted | 2026-08-11 |
| [0006](0006-intent-classification-swappable-strategy.md) | Intent Classification Is a Swappable Strategy | Accepted | 2026-08-11 |
| [0007](0007-resolver-scope-bounded-anti-corruption-layer.md) | Resolver Scope Is Explicitly Bounded (Anti-Corruption Layer) | Accepted | 2026-08-11 |
| [0008](0008-cdm-source-version-pinned-at-ingestion.md) | CDM Source Is Version-Pinned at Ingestion Time | Accepted | 2026-08-11 |
| [0009](0009-relationship-traversal-bounded-to-depth-2.md) | Relationship Traversal Is Graph-Shaped, Bounded to Depth 2 | Accepted | 2026-08-11 |
| [0010](0010-post-generation-grounding-verification.md) | Post-Generation Grounding Verification (Citation Check) | Accepted | 2026-08-11 |
| [0011](0011-entity-name-matching-closed-vocabulary.md) | Entity Name Matching Is Closed-Vocabulary Exact + Fuzzy Matching | Accepted | 2026-08-11 |
| [0012](0012-ingestion-fails-per-entity-skip-and-log.md) | Ingestion Fails Per-Entity (Skip-and-Log), Not the Whole Run | Accepted | 2026-08-11 |
| [0013](0013-deterministic-hits-through-llm-for-phrasing.md) | Deterministic Structured Hits Still Go Through the LLM for Phrasing | **Superseded** by 0016 | 2026-08-11 |
| [0014](0014-explicit-validation-pass.md) | Explicit Validation Pass Between Resolver and Canonical Model | Accepted | 2026-08-11 |
| [0015](0015-canonical-model-provenance.md) | Canonical Model Carries Lightweight Provenance | Accepted | 2026-08-11 |
| [0016](0016-deterministic-hits-template-rendered.md) | Deterministic Hits Are Template-Rendered; LLM Reserved for Synthesis | Accepted (supersedes 0013) | 2026-08-11 |
| [0017](0017-evaluation-as-first-class-layer.md) | Evaluation Is a First-Class Architectural Layer | Accepted | 2026-08-11 |
| [0018](0018-testing-strategy-istqb-aligned.md) | Testing Strategy — ISTQB-Aligned Levels, Data-Driven by Default | Accepted | 2026-08-11 |
| [0019](0019-cicd-pipeline-layered-by-cost-and-speed.md) | CI/CD Pipeline Layered by Cost and Speed | Accepted | 2026-08-11 |
| [0020](0020-task-automation-modular-taskfiles.md) | Task Automation via Modular Taskfiles | Accepted | 2026-08-11 |
| [0021](0021-schema-based-design-at-port-boundaries.md) | Schema-Based Design at Every Port Boundary | Accepted | 2026-08-11 |
| [0022](0022-ui-layer-deferred-future-scope.md) | UI Layer Deferred to Future Scope | **Superseded** by 0025 | 2026-08-11 |
| [0023](0023-tech-layer-adapters.md) | Tech-Layer Adapters — ChromaDB, Anthropic Claude, sentence-transformers, per-entity chunking | Accepted | 2026-08-11 |
| [0024](0024-second-llm-provider-gemini.md) | Add Google Gemini as a Second, Swappable LLM Provider | Accepted | 2026-08-11 |
| [0025](0025-ui-typescript-chat-and-entity-browser.md) | UI — TypeScript Chat + Entity Browser, Statically Served by FastAPI | Accepted (supersedes 0022) | 2026-08-11 |
| [0026](0026-eval-kpi-snapshot-in-ui.md) | Evaluation KPI Snapshot in the UI — Build-Time, Not Live | Accepted | 2026-08-12 |
| [0027](0027-pipeline-view-derived-client-side.md) | Pipeline View — Reconstructed Client-Side, Not a New API Field | Accepted | 2026-08-12 |
| [0028](0028-pipeline-zoom-view-server-side-debug-payload.md) | Pipeline Zoom View — a Real `debug` Payload, Not More Client-Side Guessing | Accepted | 2026-08-12 |
| [0029](0029-playwright-e2e-tests.md) | Playwright E2E Tests — Real Browser, No LLM Credentials Required | Accepted | 2026-08-12 |
| [0030](0030-interactive-answer-scoring-utility.md) | Interactive "Score an Answer" Utility — Real Pipeline, Lexical Comparison, No External Eval Framework | Accepted | 2026-08-12 |

## Decision Graph (Reading Order)

The ADRs build on each other roughly in this dependency order, not strictly numeric order:

1. **Domain shape**: 0001 (ports) → 0007 (canonical model + resolver scope) → 0014 (validation) → 0015 (provenance) → 0021 (schema contracts for all of the above)
2. **Ingestion mechanics**: 0002 (offline/online split) → 0008 (version pinning) → 0012 (per-entity failure policy)
3. **Retrieval shape**: 0003 (dual projection) → 0004 (structured index sizing) → 0009 (bounded traversal)
4. **Query path**: 0011 (entity resolution) → 0006 (intent classification)
5. **Grounding**: 0005 (pre-generation guard) → 0010 (post-generation validator)
6. **Answer construction**: 0013 (superseded) → 0016 (template vs. LLM split)
7. **Quality assurance**: 0018 (testing) and 0017 (evaluation) — deliberately distinct disciplines, see 0017's Context for why
8. **Delivery mechanics**: 0020 (task runner) → 0019 (CI/CD gates built on it)
9. ~~**Future scope**: 0022 (UI) — accepted as a deferral, not built~~ — superseded by 0025, same day
10. **Tech adapters**: 0023 (vendor picks behind 0001's ports) — the last decision before implementation could start
11. **Provider swap**: 0024 (Gemini as a second LLM adapter) — a post-implementation decision, exercising 0001's port boundary rather than changing it
12. **UI**: 0025 (TypeScript chat + entity browser, statically served) — a post-implementation decision, the thin client 0022 had pre-scoped, actually built
13. **UI + evaluation**: 0026 (KPI snapshot in the UI) — connects 0025's UI to 0017's evaluation layer, deliberately build-time rather than live to stay within both 0025's "thin client" constraint and 0024's free-tier quota limits
14. **UI + pipeline visibility**: 0027 (pipeline view) — same "stay within the thin-client constraint" instinct as 0026, applied to per-query stage tracing instead of aggregate KPIs
15. **UI + pipeline zoom**: 0028 (per-stage debug payload) — the one place this project deliberately crosses the thin-client line 0025/0027 hold everywhere else, because the alternative is data that cannot be recovered any other way
16. **E2E verification**: 0029 (Playwright) — the first automated check of everything 0025-0028 built, closing the "not verified in an actual browser" caveat every one of those ADRs left open
17. **UI + interactive evaluation**: 0030 (score-an-answer utility) — completes the early-session evaluation discussion 0026 partially answered (static KPI snapshot); reuses 0028's zoom-view and 0025's pipeline wiring rather than introducing a new evaluation code path

## Creating a New ADR

1. Copy [`template.md`](template.md) to `NNNN-title-with-dashes.md` (next sequential number).
2. Fill in the template — Context, Decision, Consequences (positive/negative), Alternatives Considered, Related Decisions.
3. Add a row to the Index table above.
4. If this ADR reverses a prior one, mark the old ADR's Status as `Superseded by ADR-NNNN` rather than editing its Decision — see 0013 for the pattern.

## Status Definitions

- **Proposed** — under discussion, not yet committed to.
- **Accepted** — decision made, this is the base to build from.
- **Superseded by ADR-NNNN** — replaced by a later decision; kept for historical record, not maintained further.
- **Deprecated** — no longer relevant (not currently used in this project).
- **Rejected** — considered but not adopted (not currently used in this project — rejected *options* are instead captured inline under "Alternatives Considered" on the ADR that considered them).
