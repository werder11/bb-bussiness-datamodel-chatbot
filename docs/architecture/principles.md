# Principles

The judgment calls that shape every decision in this system — what's deliberately excluded, and the risk register that keeps those calls honest.

## What's Deliberately Not Built (and why)

| Not building | Why not |
|---|---|
| Microservices split | Single small domain, solo developer — a modular monolith fits per the [pattern comparison](../../.claude/skills/architecture-designer/references/architecture-patterns.md); splitting services would only add network hops and deploy complexity |
| Message queue / event-driven pipeline | No async/high-throughput requirement; ingestion is a one-shot batch step |
| Full observability stack (Prometheus/Grafana/tracing) | Disproportionate to a single-container demo; structured log lines + the ingestion validation summary suffice — see [Operations: Monitoring](../operations/monitoring.md) |
| Auth/authz | No stated requirement, no sensitive data in CDM schema content |
| Multi-region / HA | No availability target beyond "the demo works when shown" |
| Official CDM ObjectModel SDK, as the default | Heavier dependency tied to a decommissioned schema store; scoped custom resolver is sufficient by default — kept swappable as a future adapter ([ADR-0007](../adr/0007-resolver-scope-bounded-anti-corruption-layer.md)) |
| ML/NER-based entity extraction | Closed, fixed vocabulary of 43 known entity names — exact + fuzzy string matching is sufficient, deterministic, testable ([ADR-0011](../adr/0011-entity-name-matching-closed-vocabulary.md)) |
| Unbounded/arbitrary-depth graph traversal | Depth ≤ 2 is a scoped query decision validated by the eval set ([ADR-0009](../adr/0009-relationship-traversal-bounded-to-depth-2.md)), not a general graph-diameter claim |
| Per-field version tracking in provenance | `source_path` + one `source_commit` per ingestion run ([ADR-0015](../adr/0015-canonical-model-provenance.md)) is enough for a static, one-shot ingestion |
| A UI | Not requested by the brief; documented future scope only — see [Vision: Roadmap](../vision/roadmap.md#future-scope-not-built-deliberately) / [ADR-0022](../adr/0022-ui-layer-deferred-future-scope.md) |
| Full evaluation run on every commit | LLM-judged metrics cost money/time per run; gated separately — see [Operations: CI/CD](../operations/ci-cd.md) / [ADR-0019](../adr/0019-cicd-pipeline-layered-by-cost-and-speed.md) |

## Guiding Principles

- **Schema-based design at every boundary** — every port and external contract is a typed schema (Pydantic), not a loose dict. See [ADR-0021](../adr/0021-schema-based-design-at-port-boundaries.md); project layout in [Design: Subsystem Design](../design/subsystem-design.md).
- **Hexagonal architecture** — domain core (Canonical Model) surrounded by ports; adapters are the only layer that knows about specific vendors. See [ADR-0001](../adr/0001-hexagonal-architecture-ports-and-adapters.md).
- **AI where semantic interpretation adds value, not for deterministic operations** — the LLM is never called when a database lookup already has the complete answer. See [ADR-0016](../adr/0016-deterministic-hits-template-rendered.md).
- **Non-hallucination is empirically checked, not prompted** — see [Quality: Evaluation Strategy](../quality/evaluation-strategy.md).

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Resolver misses a relationship pattern not yet seen (only 3 patterns sampled so far) | Medium — incomplete attribute/relationship answers | Prototype resolver against Account, Contact, Relationship first; fixture-based golden tests ([ADR-0007](../adr/0007-resolver-scope-bounded-anti-corruption-layer.md)) catch regressions |
| Validation Pass surfaces more unresolved references than expected | Low-Medium — informational, not a demo blocker | Non-blocking by design ([ADR-0014](../adr/0014-explicit-validation-pass.md)): reported in the summary, referenced-but-unresolved entities treated as out-of-scope |
| Entity Matcher mis-resolves a paraphrased or ambiguous name (e.g. "customer" → Account or Contact?) | Medium | Closed vocabulary keeps matching simple ([ADR-0011](../adr/0011-entity-name-matching-closed-vocabulary.md)); eval set includes ambiguous/paraphrased cases; on genuine ambiguity, surface both candidates |
| Depth-2 traversal cap misses a legitimate longer relationship chain | Low — no 3+-hop pattern found so far, but not exhaustively sampled | Documented as a query-scope decision ([ADR-0009](../adr/0009-relationship-traversal-bounded-to-depth-2.md)), not silent; revisit only if the eval set surfaces a real 3-hop question |
| Grounding Validator is too strict or too lenient | Medium | Start with simple string containment; tune against the eval set ([Quality](../quality/evaluation-strategy.md)); documented as best-effort |
| Grounding Guard vector-similarity cutoff tuned wrong | Medium | Start conservative (favor refusal over guessing); tune against the eval set |
| Structured/semantic projections drift out of sync | Low (both derived from one ingestion run, rebuilt together) | Single idempotent ingestion entrypoint writes both ([ADR-0002](../adr/0002-separate-offline-ingestion-from-online-query-path.md)) |
| A single malformed entity file aborts the whole ingestion run | Low-Medium | Skip-and-log per entity, not abort-all ([ADR-0012](../adr/0012-ingestion-fails-per-entity-skip-and-log.md)) |
| Slow CI/CD gate (full evaluation) drifts out of sync with code between manual runs | Low-Medium | Required as an explicit pre-release step ([Operations: CI/CD](../operations/ci-cd.md)), not left to memory alone |

## Open Items Before Implementation

See [Vision: Roadmap](../vision/roadmap.md#before-implementation-can-start) for the current punch list — kept in one place rather than duplicated here.
