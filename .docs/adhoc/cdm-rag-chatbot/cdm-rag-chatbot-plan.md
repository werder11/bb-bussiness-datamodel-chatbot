# CDM RAG Chatbot — Implementation Plan

**Created**: 2026-08-11
**Last Updated**: 2026-08-11

## Overview

Build a Python/FastAPI RAG service answering natural-language questions about the Microsoft CDM Banking Model, grounded in ingested schema data, non-hallucinated. This is the code deliverable for a reeeliance Senior Data & AI Architect take-home. Architecture is fully decided (22 ADRs, `docs/adr/`); this plan sequences the build from zero code to a running, tested, containerized service.

## Current State Analysis

Greenfield: no `app/`, no `tests/`, no `Dockerfile`, no git repo. What exists: complete architecture docs (`docs/`), a sparse-cloned CDM source repo (`cdm-source/schemaDocuments/`), and a working `Taskfile.yml` + `tasks/*.yml` whose commands reference paths this plan creates.

### Key locations already in place:
- `cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/RetailBankingCoreDataModel.manifest.cdm.json` — 20 Banking entities
- `cdm-source/schemaDocuments/manifests/bankingAccelerator.manifest.cdm.json` — 23 common entities
- `cdm-source/schemaDocuments/core/wellKnownCDSAttributeGroups.cdm.json` (~line 4129) — polymorphic `Customer` group
- `cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/Relationship.cdm.json` — party-to-party relationships
- `Taskfile.yml` + `tasks/{dev,ingest,test,eval,docker,ci}.yml` — verified working, commands await the code below

## Desired End State

A containerized FastAPI service that ingests the 43-entity CDM scope into a Canonical Model → SQLite structured index + ChromaDB vector index, answers `POST /query` grounded (template for deterministic hits, Claude for semantic/mixed evidence), passes `task ci:fast` with zero live calls, and has a working `task ci:slow` producing a KPI evaluation report.

**Verification**: `task ci:fast` exits 0; `task docker:run` + the brief's two example questions via curl return correct grounded answers; `task eval:run` produces a populated `docs/eval-report.md`.

## What We're NOT Doing

Per `docs/architecture/principles.md`: no microservices, message queue, auth, multi-region/HA, official CDM ObjectModel SDK, ML/NER entity extraction, unbounded traversal, UI (ADR-0022), full eval on every commit. Slides (self-intro + technical walkthrough) are tracked in `cdm-rag-chatbot-tasks.md` as a final non-code item, not planned here.

## Implementation Approach

Bottom-up through the Hexagonal layers (ADR-0001): domain core/ports (no tech dependency) → Resolver/ingestion (testable against fixtures alone) → adapters (now unblocked, tech decided this session) → query pipeline wiring → API/Docker/CI shell → evaluation. Each phase carries its own ADR-0018 test level.

---

## Phase 0: Scaffold, Tech ADR, Environment

### Overview
Record the four tech decisions made this session, then create the skeleton everything else fills in.

### Changes Required

**New**: `docs/adr/0023-tech-layer-adapters.md` — records ChromaDB (embedded), Anthropic Claude, local `sentence-transformers` (`all-MiniLM-L6-v2`), one-chunk-per-entity, with alternatives considered (matches the four `AskUserQuestion` option sets already presented and answered).

**Edit**: `FINDINGS.md §7` — mark all four previously-open rows Decided, linking to ADR-0023.

**New tree**:
```
app/{domain,adapters,ingestion,api}/__init__.py
tests/{unit,integration,system,acceptance,eval}/__init__.py
tests/integration/fixtures/
requirements.txt        # fastapi, uvicorn, pydantic>=2, chromadb, sentence-transformers, anthropic
requirements-dev.txt    # pytest, ruff, mypy, httpx
```

**Reasoning**: `tasks/dev.yml`'s `dev:setup` already runs `pip install -r requirements.txt -r requirements-dev.txt` — this phase just makes that command (and every other Taskfile command) resolve to something real.

### Testing for This Phase
No code to test yet — verification is that tooling runs at all.

### Success Criteria

#### Automated Verification:
- [ ] `git init && git add -A && git commit` succeeds (first commit)
- [ ] `task dev:setup` completes without error
- [ ] `task dev:lint` runs (passes trivially against an empty-but-valid tree)

#### Manual Verification:
- [ ] `docs/adr/README.md` index includes ADR-0023
- [ ] `FINDINGS.md §7` shows no "Still open" rows

---

## Phase 1: Domain Core (ADR-0021 schema-based design)

### Overview
The vendor-independent Canonical Model and the three port `Protocol`s everything else is tested against.

### Changes Required

**New**: `app/domain/models.py` — frozen Pydantic v2 `Trait`, `Attribute`, `Relationship`, `Entity` (with `source_path` provenance per ADR-0015).

**New**: `app/domain/provenance.py` — `IngestionRun(source_commit, entities)`.

**New**: `app/domain/ports.py` — closes a gap the docs left implicit (only example method names existed, e.g. `get_attributes(entity: str) -> AttributesResult` in ADR-0021's Implementation Notes): full `StructuredIndex`, `VectorIndex`, `LLM` `Protocol`s plus their typed result models (`AttributesResult`, `RelationshipsResult`, `TraversalResult`, `SemanticSearchResult`). Full signatures are in the approved plan at `/Users/emre/.claude/plans/wild-finding-wind.md` Phase 1 — copy verbatim.

**Reasoning**: Hexagonal architecture (ADR-0001) requires these exist before anything else can be written against them, fake or real.

### Testing for This Phase
`tests/unit/test_domain_models.py` — schema validation (bad `data_type`, missing required field → `ValidationError`); frozen-instance mutation raises.

### Success Criteria

#### Automated Verification:
- [ ] `task test:unit` passes for this module
- [ ] `mypy app/domain` passes

#### Manual Verification:
- [ ] N/A — pure data layer, fully covered by automated tests

---

## Phase 2: Resolver + Validation Pass (ADR-0007, ADR-0012, ADR-0014)

### Overview
Turns raw CDM JSON into the Canonical Model. Highest-risk component — this is where FINDINGS §5's three structural quirks (inheritance-splits-attributes, polymorphic Customer group, Account/Contact collision) get handled.

### Changes Required

**New**: `app/ingestion/resolver.py` — `discover_entities()`, `resolve_entity()` (single-hop `extendsEntity`/`attributeGroupReference` only, namespaces by source path — `banking:Account` vs `crmCommon:Account`), `resolve_all()` (skip-and-log, never aborts on one bad entity).

**New**: `app/ingestion/validate.py` — `validate(entities) -> ValidationReport` implementing the exact 4-check table from ADR-0014 (duplicate names, unresolved relationship refs, dangling attribute refs, missing identifier), rendering the exact summary format ADR-0014 specifies.

**New fixtures**: `tests/integration/fixtures/` — 5 frozen `.cdm.json` inputs + expected Canonical Model outputs, one per pattern in FINDINGS §5 (single-hop extends, attributeGroupReference, polymorphic Customer, explicit Relationship entity, Account/Contact collision pair).

**Reasoning**: ADR-0007 mandates fixture-based golden tests as the correctness mechanism, not exhaustive resolution guarantees — this phase builds exactly that oracle.

### Testing for This Phase
`tests/integration/test_resolver.py` — golden tests, one per fixture. `tests/unit/test_validate.py` — data-driven table of `entity-list → expected ValidationReport`.

### Success Criteria

#### Automated Verification:
- [ ] `task test:integration` passes all 5 golden-fixture tests
- [ ] `task test:unit` passes validation-table tests

#### Manual Verification:
- [ ] Run resolver against the real `cdm-source/` manifests, inspect the printed summary — expect most/all of 43 entities resolved

---

## Phase 3: Adapters (ChromaDB, SQLite, Anthropic — ADR-0023)

### Overview
Concrete implementations behind the three ports, now unblocked.

### Changes Required

**New**: `app/adapters/structured_index_sqlite.py` — `SQLiteStructuredIndex`: `entities`/`attributes`/`relationships` tables, `load()` idempotent clear-then-write (ADR-0002), `get_attributes`/`get_relationships` via SQL, `traverse` via BFS over an adjacency dict built once in `load()` (ADR-0009 — no graph DB).

**New**: `app/adapters/vector_index_chroma.py` — `ChromaVectorIndex`: one document per entity (chosen chunking), embedded via `sentence-transformers` `all-MiniLM-L6-v2`, persisted to a local Chroma path (no server).

**New**: `app/adapters/llm_anthropic.py` — `AnthropicLLM.generate(question, context)`: system prompt constrains to provided context only (defense in depth alongside the Grounding Guard/Validator, which are the real enforcement).

**Reasoning**: All three tech picks were resolved this session (ADR-0023) specifically to unblock this phase.

### Testing for This Phase
`tests/unit/test_adapters_*.py` — each adapter against a tiny fixture, no real network calls (Chroma persisted to a temp dir is fine; Anthropic client is not called in unit tests, only constructed/mocked).

### Success Criteria

#### Automated Verification:
- [ ] `task test:unit` passes, zero network calls made during the run

#### Manual Verification:
- [ ] N/A until Phase 6/7 (API + Docker) — that's where live adapter behavior gets exercised

---

## Phase 4: Entity Matcher + Intent Classification (ADR-0011, ADR-0006)

### Overview
Free text → known entity name(s) → retrieval intent.

### Changes Required

**New**: `app/domain/entity_matcher.py` — `match(query, known_entities)`: exact case-insensitive match first, `difflib.get_close_matches` fallback, ambiguity surfaces both candidates.

**New**: `app/domain/router.py` — `classify(query, matched_entity)`: rule-based keyword classification into `attributes(entity) | relationship(entity, target?) | semantic`.

### Testing for This Phase
`tests/unit/test_entity_matcher.py`, `tests/unit/test_router.py` — data-driven parametrized tables (ADR-0018's default technique).

### Success Criteria

#### Automated Verification:
- [ ] `task test:unit` passes, including at least one ambiguous-name case (Account/Contact collision) and one paraphrase case

#### Manual Verification:
- [ ] N/A — fully covered by data-driven unit tests

---

## Phase 5: Query Pipeline Wiring (ADR-0005, ADR-0010, ADR-0016)

### Overview
The core "retrieval logic" the brief explicitly grades. Orchestrates Phases 1–4 against port `Protocol`s (fakeable).

### Changes Required

**New**: `app/domain/pipeline.py` — `answer_query(question, structured, vector, llm, known_entities) -> QueryResponse`, steps matching `docs/design/workflows.md#query-workflow`: Entity Matcher → Router → retrieve → Evidence Assembly → Grounding Guard (boolean structured/traversal, similarity-cutoff vector) → branch (template vs `llm.generate`) → Grounding Validator (string containment) → refusal-on-failure → `RetrievalTrace` log.

**New**: `app/domain/templates.py` — three f-string templates (attribute list, single-hop relationship, depth-2 path) per ADR-0016, no Jinja2.

**New**: `app/domain/tracing.py` — `RetrievalTrace{query, matched_entities, route, grounded, verified}`.

### Testing for This Phase
`tests/unit/test_pipeline.py` — fakes for all three ports: deterministic-hit → template, semantic-hit → fake-LLM, no-hit → refusal, Validator-catches-unsupported-claim → refusal.

### Success Criteria

#### Automated Verification:
- [ ] `task test:unit` passes all four pipeline scenarios above
- [ ] Zero LLM/network calls in this test file (fakes only)

#### Manual Verification:
- [ ] N/A — this is the phase automated tests exist specifically to cover

---

## Phase 6: FastAPI App (ADR-0021, `docs/api/README.md`)

### Overview
The HTTP surface.

### Changes Required

**New**: `app/api/main.py`, `app/api/schemas.py` — `POST /query`, `GET /entities`, `GET /entities/{name}`, `GET /health`; adapters constructed at startup (`lifespan`), reading the SQLite file + Chroma dir ingestion wrote.

### Testing for This Phase
`tests/system/test_api.py` — `TestClient` against a real small test corpus, deterministic paths only. `tests/acceptance/test_requirements.py` — one test per FR1–FR7.

### Success Criteria

#### Automated Verification:
- [ ] `task test:system` and `task test:acceptance` pass

#### Manual Verification:
- [ ] `task dev:api`, then `curl localhost:8000/health` and the two brief example questions

---

## Phase 7: Dockerfile + Deployment

### Overview
Containerize, bake ingestion into the image build (static corpus, ADR-0008).

### Changes Required

**New**: `Dockerfile` — Python slim, install deps, copy `app/`, run `python -m app.ingestion.run` at build time, `CMD uvicorn app.api.main:app --host 0.0.0.0 --port 8000`.

### Success Criteria

#### Automated Verification:
- [ ] `task docker:build` succeeds

#### Manual Verification:
- [ ] `task docker:run`, then the same curl checks as Phase 6 against the container

---

## Phase 8: Evaluation Dataset + KPI Runner (ADR-0017)

### Overview
Turns "non-hallucinated" into a measured property.

### Changes Required

**New**: `tests/eval/dataset.py` — 20-30 schema-validated `EvalQuestion` records across the 8 named categories from `docs/quality/evaluation-strategy.md`.

**New**: `tests/eval/run.py` — matches `tasks/eval.yml`'s existing command exactly (`python -m tests.eval.run --report docs/eval-report.md`); runs the real pipeline (real Chroma + real Claude), computes the full KPI table, writes the report. Also where the Grounding Guard's similarity cutoff moves from a placeholder to a tuned value.

### Success Criteria

#### Automated Verification:
- [ ] `task eval:run` completes, produces `docs/eval-report.md` with every KPI row populated

#### Manual Verification:
- [ ] Spot-check 3-5 eval answers by hand against the CDM source

---

## Phase 9: CI Wiring (ADR-0019)

### Changes Required

**New**: `.github/workflows/ci.yml` — `task ci:fast` on every push, `task ci:slow` as `workflow_dispatch`. No new logic beyond what `tasks/ci.yml` already composes.

### Success Criteria

#### Automated Verification:
- [ ] A pushed commit triggers the fast-gate workflow and it passes

---

## Testing Strategy

Maps 1:1 to `docs/quality/testing-strategy.md`'s four ISTQB levels; each phase above states its level(s). Phases 2 and 5 are the highest-value targets — the brief's explicit "unit tests for retrieval logic" ask.

## Performance Considerations

No SLA; ~43-entity corpus keeps everything (SQLite queries, BFS traversal, Chroma similarity search) trivially fast. LLM call latency (Phase 3/5) is the only user-visible latency, only on the semantic/mixed path.

## Migration Notes

None — greenfield, no existing data to migrate.

## References

- Approved plan (source of truth for this file): `/Users/emre/.claude/plans/wild-finding-wind.md`
- Full architecture: `docs/README.md` and all 22 ADRs it links to
- Research notes: `cdm-rag-chatbot-research.md`
- Quick reference: `cdm-rag-chatbot-context.md`
- Task checklist: `cdm-rag-chatbot-tasks.md`
