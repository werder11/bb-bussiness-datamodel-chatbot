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
| [0022](0022-ui-layer-deferred-future-scope.md) | UI Layer Deferred to Future Scope | Accepted | 2026-08-11 |
| [0023](0023-tech-layer-adapters.md) | Tech-Layer Adapters — ChromaDB, Anthropic Claude, sentence-transformers, per-entity chunking | Accepted | 2026-08-11 |

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
9. **Future scope**: 0022 (UI) — accepted as a deferral, not built
10. **Tech adapters**: 0023 (vendor picks behind 0001's ports) — the last decision before implementation could start

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
