# API

How components communicate — specifically, how a client talks to this system. No code exists yet, so this is the contract specification; once the FastAPI app exists, its auto-generated OpenAPI schema becomes the source of truth and this page should link to it rather than restate it (see [ADR-0021](../adr/0021-schema-based-design-at-port-boundaries.md) — request/response models are Pydantic, so OpenAPI generation is automatic, not hand-maintained).

## Endpoints

| Endpoint | Purpose | Grounding |
|---|---|---|
| `POST /query` | Natural-language question in, grounded answer out | Full pipeline — see [Design: Workflows](../design/workflows.md#query-workflow) |
| `GET /entities` | List all ingested entity names | Reads the Structured Index directly, bypasses the LLM entirely |
| `GET /entities/{name}` | Full attribute/relationship detail for one entity | Reads the Structured Index directly, bypasses the LLM entirely |
| `GET /health` | Liveness check | No dependencies |

The two `GET /entities*` endpoints exist deliberately as an LLM-independent way to demo that ingestion is correct — useful for the live demo and as a source of deterministic test fixtures ([Quality: Testing Strategy](../quality/testing-strategy.md)).

## Request/Response Shape

`POST /query` request: `{"question": "<free text>"}`. Response includes the answer text, whether it was grounded, which entities were matched, and which route was taken (structured / traversal / semantic) — the same fields the Retrieval Tracer logs ([Operations: Monitoring](../operations/monitoring.md)), so a client can introspect *why* an answer looks the way it does.

Exact field-level schemas are defined once the Pydantic request/response models exist ([ADR-0021](../adr/0021-schema-based-design-at-port-boundaries.md)) — this page intentionally doesn't duplicate them ahead of time to avoid drift.

## Consumers

- The live demo, directly, or via FastAPI's auto-generated `/docs` Swagger UI.
- A future, optional UI — same contract, no special access ([ADR-0022](../adr/0022-ui-layer-deferred-future-scope.md)).
