# Roadmap

## Current phase: architecture accepted, implementation not started

All structural/shape decisions are locked in as [Accepted ADRs](../adr/README.md). No application code exists yet — this phase was deliberately spent on getting the design right before writing anything, given the source data (CDM) turned out to have real structural complexity worth understanding first (see [`FINDINGS.md`](../../FINDINGS.md)).

## Before implementation can start

From [`docs/architecture/principles.md`](../architecture/principles.md#open-items-before-implementation), in rough dependency order:

1. Resolve [`FINDINGS.md §7`](../../FINDINGS.md#7-open-architecture-decisions) — concrete adapters for `StructuredIndex`, `VectorIndex`, `Embedder`, `LLM` (vector DB flavor, LLM provider, embedding model, chunking granularity).
2. Define the Pydantic schemas for the Canonical Model and port contracts ([ADR-0021](../adr/0021-schema-based-design-at-port-boundaries.md)).
3. Prototype the Resolver against Account, Contact, and Relationship (highest-complexity entities found) before scaling to all 43.
4. Build the evaluation dataset ([`docs/quality/evaluation-strategy.md`](../quality/evaluation-strategy.md#evaluation-dataset)) — needed before the Grounding Guard cutoff or Grounding Validator can be sensibly tuned.
5. Wire the fast CI/CD gate ([`docs/operations/ci-cd.md`](../operations/ci-cd.md)) early, alongside the first Component/Unit tests, so it's exercising real coverage from day one.
6. Confirm the depth-2 traversal cap ([ADR-0009](../adr/0009-relationship-traversal-bounded-to-depth-2.md)) against at least one real Contact ↔ Organization-style question from the eval set.
7. Design the Validation Pass's exact check list ([ADR-0014](../adr/0014-explicit-validation-pass.md)) alongside the Resolver prototype (item 3).
8. Decide the Grounding Validator's matching strategy in more detail ([ADR-0010](../adr/0010-post-generation-grounding-verification.md)) — start simple, revisit only if the eval set shows it's too strict or too lenient.
9. Decide the template format for deterministic answers ([ADR-0016](../adr/0016-deterministic-hits-template-rendered.md)).

## Deliverables checklist

From the task brief:
- [ ] GitHub repository link with source code.
- [ ] Live demo of the API.
- [ ] Technical walkthrough, max 4 slides — embedding strategy + how relationships were handled.
- [ ] Self-intro slide — "How do I see myself as a Senior Data & AI Architect at reeeliance?"

## Future scope (not built, deliberately)

- **UI layer** — a thin client over the existing API, no new backend logic. See [ADR-0022](../adr/0022-ui-layer-deferred-future-scope.md).
- **Full CDM coverage beyond Banking + common objects** — the current scope (43 entities) is a deliberate cut per the brief; expanding it should mean re-running ingestion, not re-architecting, per the Scalability NFR in [`docs/architecture/README.md`](../architecture/README.md#requirements).
- **Deeper Resolver fidelity via the official Microsoft ObjectModel SDK**, if the scoped custom resolver's known limitations ([ADR-0007](../adr/0007-resolver-scope-bounded-anti-corruption-layer.md)) prove costly in practice.
- **Re-ingestion on upstream CDM changes** — currently version-pinned at ingestion time with no drift detection ([ADR-0008](../adr/0008-cdm-source-version-pinned-at-ingestion.md)).
