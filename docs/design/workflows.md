# Workflows

Step-by-step views of the two flows in [Architecture: Containers](../architecture/containers.md) / [Components](../architecture/components.md). Static structure is documented there; this page is the dynamic "what happens in what order."

## Ingestion Workflow

1. **Discover** — walk the Banking + common-objects manifests, listing `{entityName, entityPath}` pairs ([Domain](../domain/domain-model.md#scope)).
2. **Resolve** — for each entity, follow single-hop `extendsEntity` / `attributeGroupReference` composition, namespace by source path to handle the Account/Contact collision, attach provenance. On failure, log and skip that entity, continue with the rest ([ADR-0007](../adr/0007-resolver-scope-bounded-anti-corruption-layer.md), [ADR-0012](../adr/0012-ingestion-fails-per-entity-skip-and-log.md)).
3. **Validate** — cross-entity integrity pass over everything successfully resolved: duplicate names, unresolved relationship references, missing identifiers. Produces a summary report, non-blocking ([ADR-0014](../adr/0014-explicit-validation-pass.md)).
4. **Project** — write the validated Canonical Model into both the relational and semantic projections, clearing each first (idempotent — safe to re-run) ([ADR-0002](../adr/0002-separate-offline-ingestion-from-online-query-path.md), [ADR-0003](../adr/0003-dual-projection-retrieval-not-cqrs.md)).

Invoked via `task ingest:run` — see [Operations: Task Automation](../operations/task-automation.md).

## Query Workflow

1. **Receive** — `POST /query {question}` hits the FastAPI handler.
2. **Resolve entity** — Entity Matcher: exact match against the 43-name vocabulary, fuzzy fallback if no exact match; on genuine ambiguity, both candidates are carried forward ([ADR-0011](../adr/0011-entity-name-matching-closed-vocabulary.md)).
3. **Classify intent** — attributes-of-X / relationship-X-to-Y / open-ended, routed to the matching retrieval path ([ADR-0006](../adr/0006-intent-classification-swappable-strategy.md)).
4. **Retrieve** — structured lookup (single-hop), bounded traversal (depth ≤ 2, [ADR-0009](../adr/0009-relationship-traversal-bounded-to-depth-2.md)), or semantic search, depending on the classified intent.
5. **Assemble evidence** — combine whatever was retrieved into one evidence set.
6. **Check grounding (pre-generation)** — Grounding Guard: any structured/traversal hit is grounded; a vector hit needs to clear a similarity cutoff. No grounded evidence → skip straight to the fixed refusal, no generation call ([ADR-0005](../adr/0005-explicit-grounding-guard-before-generation.md)).
7. **Answer** — deterministic (structured/traversal-only) evidence is template-rendered, no LLM call; semantic/mixed evidence goes through LLM generation, context-only ([ADR-0016](../adr/0016-deterministic-hits-template-rendered.md)).
8. **Check grounding (post-generation)** — Grounding Validator: cited entity/attribute names must appear in the retrieved context; templated answers trivially pass, generated answers are actually checked ([ADR-0010](../adr/0010-post-generation-grounding-verification.md)).
9. **Trace and respond** — log `{query, matched_entities, route, grounded, verified}`, return the response ([Operations: Monitoring](../operations/monitoring.md)).

`GET /entities`, `GET /entities/{name}`, `GET /health` skip steps 3–8 entirely, reading the Structured Index directly — see [API](../api/README.md).
