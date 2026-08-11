# Architecture

What the system is structured like, and why. Individual decisions live as [ADRs](../adr/README.md); this layer is the narrative and the diagrams that tie them together, following a C4-style zoom: [System Context](system-context.md) → [Containers](containers.md) → [Components](components.md), plus [Principles](principles.md) (NFRs, what's deliberately not built, risks).

Domain concepts (what the CDM actually contains) live separately in [Domain](../domain/README.md) — this layer is about system *structure*, not the business concepts it operates on.

## Requirements

### Functional
- FR1: Answer natural-language questions about which CDM entities exist and their core attributes.
- FR2: Answer natural-language questions about relationships between entities (e.g. Contact ↔ Organization) — including relationships that aren't a direct single-hop reference (see [ADR-0009](../adr/0009-relationship-traversal-bounded-to-depth-2.md)).
- FR3: Every answer must be grounded in ingested CDM data; if the question falls outside ingested scope, say so explicitly rather than guessing.
- FR4: Scope = Banking Model (20 entities) + common/supporting objects (23 entities) — see [Domain: CDM Model](../domain/domain-model.md#scope).
- FR5: Exposed as an HTTP API (FastAPI), containerized (Dockerfile).
- FR6: Ingestion parses CDM `.cdm.json` definitions and populates the retrieval index/indexes.
- FR7: The system's own quality (groundedness, retrieval accuracy, refusal correctness) must be measurable, not just asserted — see [Quality](../quality/README.md).

### Non-functional (calibrated to a graded take-home, not a production system)
| Category | Target | Rationale |
|---|---|---|
| Performance | Interactive demo latency (LLM call dominates only on the semantic-synthesis path; no sub-100ms requirement) | No stated SLA; correctness matters more than speed here |
| Scalability | Fixed corpus (~43 entities, low hundreds of attributes/relationships), single instance | Growing to full CDM later should mean re-ingestion, not re-architecture — noted, not built |
| Availability | Best-effort, single container | No HA/multi-region requirement for a demo |
| Security | No PII/secrets in CDM schema data itself; API keys via env vars only, never committed | Lowest-sensitivity data; only real requirement is credential hygiene |
| Reliability | Graceful degradation to "not found in ingested scope" over silent failure or fabrication | Directly protects the graded non-hallucination requirement |
| Maintainability | Ports swappable without touching domain logic; ADRs recorded; schemas typed ([ADR-0021](../adr/0021-schema-based-design-at-port-boundaries.md)) | Take-home is judged partly on architectural judgment, not just working code |
| Testability | Every component testable without live external services ([ADR-0018](../adr/0018-testing-strategy-istqb-aligned.md)) | Explicit grading criterion in the brief |
| Observability | Structured retrieval trace logs + ingestion validation summary — no metrics/alerting stack | See [Operations: Monitoring](../operations/monitoring.md) |
| Cost | Minimal — one container, pay-per-call embedding/LLM (only on the synthesis path and the slow evaluation gate) | No infra budget stated |

### Constraints
- Solo developer, take-home timeline (days, not weeks) — assumption, not stated in brief.
- Must use Python + FastAPI; must include unit tests for retrieval logic; must include a Dockerfile.
- Data source is fixed (official Microsoft CDM repo), scope is fixed (Banking + common objects).
- Deliverables beyond code: live demo, 4-slide technical walkthrough, separate self-intro slide — see [Vision: Roadmap](../vision/roadmap.md#deliverables-checklist).

## Layer Contents

- [System Context](system-context.md) — the system as a black box: who uses it, what it depends on
- [Containers](containers.md) — the deployable units and how data flows between them
- [Components](components.md) — what's inside each container, with a component catalog
- [Principles](principles.md) — what's deliberately not built, and the risk register
