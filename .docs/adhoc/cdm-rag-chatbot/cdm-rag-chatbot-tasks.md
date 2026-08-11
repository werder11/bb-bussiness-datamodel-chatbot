# CDM RAG Chatbot — Task Checklist

**Last Updated**: 2026-08-11
**Status**: In Progress

## Phase 0: Scaffold, Tech ADR, Environment

- [ ] **Task 0.1**: Write ADR-0023 (tech-layer adapters: ChromaDB, Anthropic, sentence-transformers, per-entity chunking)
  - File: `docs/adr/0023-tech-layer-adapters.md`
  - Effort: S
  - Dependencies: None
  - Acceptance: Follows the existing ADR template; linked from `docs/adr/README.md` index

- [ ] **Task 0.2**: Update `FINDINGS.md §7` — mark all four rows Decided
  - File: `FINDINGS.md`
  - Effort: S
  - Dependencies: Task 0.1
  - Acceptance: No "Still open" rows remain

- [ ] **Task 0.3**: Scaffold `app/`/`tests/` package tree + `requirements.txt`/`requirements-dev.txt`
  - Files: `app/**/__init__.py`, `tests/**/__init__.py`, `requirements.txt`, `requirements-dev.txt`
  - Effort: S
  - Dependencies: None
  - Acceptance: `task dev:setup` completes

- [ ] **Task 0.4**: `git init` + first commit
  - Effort: S
  - Dependencies: Task 0.3
  - Acceptance: `git log` shows one commit containing docs + scaffold

### Phase 0 Verification
- [ ] Run: `task dev:setup && task dev:lint`
- [ ] Verify: `docs/adr/README.md` and `FINDINGS.md` both reflect the ADR-0023 decision

---

## Phase 1: Domain Core

- [ ] **Task 1.1**: Write failing tests for Canonical Model schema validation + frozen-instance mutation
  - File: `tests/unit/test_domain_models.py`
  - Effort: S
  - Dependencies: Task 0.3
  - Acceptance: Tests written, fail with `ModuleNotFoundError` initially

- [ ] **Task 1.2**: Implement `Trait`/`Attribute`/`Relationship`/`Entity` (frozen Pydantic v2, provenance fields)
  - File: `app/domain/models.py`
  - Effort: M
  - Dependencies: Task 1.1
  - Acceptance: Task 1.1's tests pass

- [ ] **Task 1.3**: Implement port `Protocol`s + result models
  - File: `app/domain/ports.py`
  - Effort: M
  - Dependencies: Task 1.2
  - Acceptance: `mypy app/domain/ports.py` passes; matches the signatures in the approved plan Phase 1

### Phase 1 Verification
- [ ] Run: `task test:unit`
- [ ] Verify: `mypy app/domain` clean

---

## Phase 2: Resolver + Validation Pass

- [ ] **Task 2.1**: Create 5 golden fixtures (one per structural pattern) + expected outputs
  - Files: `tests/integration/fixtures/*.cdm.json` + expected JSON
  - Effort: M
  - Dependencies: Task 1.2
  - Acceptance: Fixtures cover extendsEntity, attributeGroupReference, polymorphic Customer, Relationship entity, Account/Contact collision

- [ ] **Task 2.2**: Write failing golden tests against the fixtures
  - File: `tests/integration/test_resolver.py`
  - Effort: S
  - Dependencies: Task 2.1
  - Acceptance: Tests fail (Resolver doesn't exist yet)

- [ ] **Task 2.3**: Implement Resolver (`discover_entities`, `resolve_entity`, `resolve_all`, skip-and-log, source-path namespacing)
  - File: `app/ingestion/resolver.py`
  - Effort: L
  - Dependencies: Task 2.2
  - Acceptance: All 5 golden tests pass

- [ ] **Task 2.4**: Implement Validation Pass (4-check table + summary format)
  - File: `app/ingestion/validate.py`
  - Effort: M
  - Dependencies: Task 2.3
  - Acceptance: `tests/unit/test_validate.py` data-driven table passes

### Phase 2 Verification
- [ ] Run: `task test:integration && task test:unit`
- [ ] Verify: manually run resolver against real `cdm-source/` manifests, inspect printed summary

---

## Phase 3: Adapters

- [ ] **Task 3.1**: Implement `SQLiteStructuredIndex` (load, get_attributes, get_relationships, traverse/BFS)
  - File: `app/adapters/structured_index_sqlite.py`
  - Effort: L
  - Dependencies: Task 1.3, Task 2.4
  - Acceptance: `tests/unit/test_adapters_sqlite.py` passes, including a depth-2 traversal case

- [ ] **Task 3.2**: Implement `ChromaVectorIndex` (per-entity chunking, sentence-transformers embedding, semantic_search)
  - File: `app/adapters/vector_index_chroma.py`
  - Effort: M
  - Dependencies: Task 1.3
  - Acceptance: `tests/unit/test_adapters_chroma.py` passes against a temp-dir Chroma instance

- [ ] **Task 3.3**: Implement `AnthropicLLM.generate`
  - File: `app/adapters/llm_anthropic.py`
  - Effort: S
  - Dependencies: Task 1.3
  - Acceptance: Constructs correctly; generate() mocked in unit tests, no live call

### Phase 3 Verification
- [ ] Run: `task test:unit`
- [ ] Verify: zero network calls during `task test:unit` (check via a network-blocking test fixture or manual inspection)

---

## Phase 4: Entity Matcher + Intent Classification

- [ ] **Task 4.1**: Implement Entity Matcher (exact + difflib fuzzy, ambiguity surfacing)
  - File: `app/domain/entity_matcher.py`
  - Effort: M
  - Dependencies: Task 1.2 (needs the 43-name vocabulary, derivable from ingested entities)
  - Acceptance: `tests/unit/test_entity_matcher.py` data-driven table passes, incl. Account/Contact ambiguity case

- [ ] **Task 4.2**: Implement rule-based Router
  - File: `app/domain/router.py`
  - Effort: M
  - Dependencies: Task 4.1
  - Acceptance: `tests/unit/test_router.py` data-driven table passes, all 3 routes covered

### Phase 4 Verification
- [ ] Run: `task test:unit`

---

## Phase 5: Query Pipeline Wiring

- [ ] **Task 5.1**: Implement f-string templates (attribute list, single-hop relationship, depth-2 path)
  - File: `app/domain/templates.py`
  - Effort: S
  - Dependencies: Task 1.2

- [ ] **Task 5.2**: Implement `RetrievalTrace` logging
  - File: `app/domain/tracing.py`
  - Effort: S
  - Dependencies: Task 1.2

- [ ] **Task 5.3**: Write failing pipeline tests (4 scenarios: deterministic hit, semantic hit, no hit, Validator-catches-unsupported)
  - File: `tests/unit/test_pipeline.py`
  - Effort: M
  - Dependencies: Tasks 4.2, 5.1, 5.2

- [ ] **Task 5.4**: Implement `answer_query` orchestration (Grounding Guard, branch, Grounding Validator)
  - File: `app/domain/pipeline.py`
  - Effort: L
  - Dependencies: Task 5.3
  - Acceptance: All 4 scenarios in Task 5.3 pass

### Phase 5 Verification
- [ ] Run: `task test:unit`
- [ ] Verify: this is the brief's explicit "unit tests for retrieval logic" — confirm coverage is genuinely meaningful, not just line coverage

---

## Phase 6: FastAPI App

- [ ] **Task 6.1**: Implement request/response Pydantic schemas
  - File: `app/api/schemas.py`
  - Effort: S
  - Dependencies: Task 5.4

- [ ] **Task 6.2**: Implement `POST /query`, `GET /entities`, `GET /entities/{name}`, `GET /health`, startup adapter wiring
  - File: `app/api/main.py`
  - Effort: M
  - Dependencies: Task 6.1, Phase 3 complete

- [ ] **Task 6.3**: System tests (TestClient, real small corpus, deterministic paths)
  - File: `tests/system/test_api.py`
  - Effort: M
  - Dependencies: Task 6.2

- [ ] **Task 6.4**: Acceptance tests, one per FR1-FR7
  - File: `tests/acceptance/test_requirements.py`
  - Effort: M
  - Dependencies: Task 6.2

### Phase 6 Verification
- [ ] Run: `task test:system && task test:acceptance`
- [ ] Verify: `task dev:api`, curl the two brief example questions manually

---

## Phase 7: Dockerfile + Deployment

- [ ] **Task 7.1**: Write `Dockerfile` (build-time ingestion, uvicorn entrypoint)
  - File: `Dockerfile`
  - Effort: M
  - Dependencies: Phase 6 complete

### Phase 7 Verification
- [ ] Run: `task docker:build && task docker:run`
- [ ] Verify: curl checks against the running container

---

## Phase 8: Evaluation Dataset + KPI Runner

- [ ] **Task 8.1**: Write the 20-30 question eval dataset across 8 categories
  - File: `tests/eval/dataset.py`
  - Effort: L
  - Dependencies: Phase 6 complete (needs a working pipeline to write realistic expected answers against)

- [ ] **Task 8.2**: Implement the KPI runner
  - File: `tests/eval/run.py`
  - Effort: L
  - Dependencies: Task 8.1
  - Acceptance: matches `tasks/eval.yml`'s existing command exactly

- [ ] **Task 8.3**: Tune Grounding Guard similarity cutoff + Grounding Validator strategy against real eval results
  - File: `app/domain/pipeline.py` (constants)
  - Effort: M
  - Dependencies: Task 8.2

### Phase 8 Verification
- [ ] Run: `task eval:run`
- [ ] Verify: `docs/eval-report.md` populated, spot-check 3-5 answers by hand

---

## Phase 9: CI Wiring

- [ ] **Task 9.1**: Write `.github/workflows/ci.yml` (fast gate on push, slow gate on `workflow_dispatch`)
  - File: `.github/workflows/ci.yml`
  - Effort: S
  - Dependencies: Phase 0 (git repo), Phase 8 (eval runner exists for the slow-gate job)

### Phase 9 Verification
- [ ] Push a commit, confirm the fast-gate workflow runs and passes

---

## Final Verification

### Automated Checks
- [ ] `task ci:fast` exits 0
- [ ] `task eval:run` produces a populated `docs/eval-report.md`

### Manual Checks
- [ ] Live demo: `task docker:run`, ask both brief example questions, confirm grounded correct answers
- [ ] Ask one deliberately out-of-scope question, confirm refusal not fabrication

## Non-Code Deliverable (tracked here, not a build phase)

- [ ] Self-intro slide — "How do I see myself as a Senior Data & AI Architect at reeeliance?"
- [ ] 4-slide technical walkthrough (embedding strategy + relationship handling) — content basis already drafted in `docs/vision/goals.md#positioning-for-the-technical-walkthrough`

## Notes Section

Plan approved via harness plan-mode on 2026-08-11; source plan at `/Users/emre/.claude/plans/wild-finding-wind.md`. All four previously-open tech decisions (vector DB, LLM, embeddings, chunking) resolved via `AskUserQuestion` before this checklist was written — see `cdm-rag-chatbot-research.md` for the Q&A record.
