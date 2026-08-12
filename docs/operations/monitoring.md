# Monitoring

Deliberately minimal — a full observability stack (Prometheus/Grafana/tracing) would be disproportionate to a single-container demo; see [Architecture: Principles](../architecture/principles.md#whats-deliberately-not-built-and-why).

## What's observable

- **Retrieval Tracer** — one structured log line per query: `{query, matched_entities, route, grounded, verified, error}` (`error` is `null` unless the LLM call itself failed — [ADR-0010](../adr/0010-post-generation-grounding-verification.md#provider-call-failures-treated-the-same-as-unverified-2026-08-11)) ([Architecture: Components](../architecture/components.md)). Cheap, and gives concrete, inspectable evidence if asked live "how do you know it's not hallucinating." Requires `logging.basicConfig()` to actually be called (`app/api/main.py`) — found live that this line silently produced nothing until that was added, since uvicorn never configures the root logger itself.
- **Ingestion validation summary** — printed at the end of every ingestion run: entities discovered/resolved/skipped, relationships discovered/unresolved ([ADR-0014](../adr/0014-explicit-validation-pass.md)).
- **Evaluation report** — produced by the CI/CD slow gate ([Operations: CI/CD](ci-cd.md)), the KPI evidence for [Quality: Evaluation Strategy](../quality/evaluation-strategy.md).

## What's not built, and why

| Not building | Why not |
|---|---|
| Metrics/alerting (Prometheus, Grafana) | No on-call, no SLA to alert against — a demo-only single container |
| Distributed tracing | Single process, single container — nothing distributed to trace |
| Centralized log aggregation | Container logs are sufficient for a local/demo deployment |

If this ever became a real production service, the Retrieval Tracer's structured log lines are already shaped to feed a log aggregator with minimal change — that's a deliberate, cheap hook for the future, not a promise this project builds it.
