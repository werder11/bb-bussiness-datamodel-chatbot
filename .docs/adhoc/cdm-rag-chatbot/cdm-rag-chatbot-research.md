# CDM RAG Chatbot — Research & Working Notes

**Research Date**: 2026-08-11
**Researchers**: Claude + Emre Gözütok

## Initial Understanding

Take-home case study: build a RAG API over the Microsoft CDM Banking Model. Initial work (earlier sessions) covered PDF brief analysis, cloning the CDM source repo, deep architecture design (22 ADRs), and a full documentation restructure into a layered knowledge base (`docs/`). This research pass was specifically about closing the gap between "architecture is decided" and "here's an implementation plan" — i.e., verifying every decision was actually captured correctly in the docs before sequencing a build.

## Research Process

Two Explore agents launched in parallel, both read-only, both covering the entire `docs/` tree plus the existing `Taskfile.yml`/`tasks/*.yml` files directly (not just docs *about* them):

### Agent 1 — Domain/Architecture/Design
Read: `docs/README.md`, `docs/domain/*`, `docs/architecture/*`, `docs/design/*`, ADRs 0001-0012/0014-0016/0021, `FINDINGS.md §3-§7`.

Key discovery: **the exact Python port method signatures are not fully specified anywhere in the docs** — only example names (`get_attributes(entity: str) -> AttributesResult`) and diagram labels. This was flagged explicitly as a planning gap to close, not something to re-derive from documentation that doesn't exist. Closed in Phase 1 of the plan.

Confirmed both CDM manifest files exist on disk at the paths FINDINGS.md claims:
- `cdm-source/schemaDocuments/FinancialServices/RetailBankingCoreDataModel/RetailBankingCoreDataModel.manifest.cdm.json`
- `cdm-source/schemaDocuments/manifests/bankingAccelerator.manifest.cdm.json`

### Agent 2 — Quality/Operations/API + literal Taskfile contents
Read: `docs/quality/*`, `docs/operations/*`, `docs/api/README.md`, and **every task file verbatim** (not summarized): `Taskfile.yml`, `tasks/{dev,ingest,test,eval,docker,ci}.yml`.

Key discovery: confirmed **no** `Dockerfile`, `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `app/`, or `tests/` exist — every Taskfile command currently points at a path that doesn't exist yet. This directly shaped Phase 0 (scaffold first, so the already-built automation has something to run against).

Extracted the full KPI table and the 8-category evaluation dataset spec verbatim from `docs/quality/evaluation-strategy.md` — used directly in plan Phase 8, no re-derivation.

## Questions Asked & Answers

1. **Q**: Should we plan the implementation? (user, plain yes/no)
   **A**: Yes.

2. **Q** (via `AskUserQuestion`, 4 questions, since the implementation-planner skill forbids unresolved questions in a final plan and Phase 3 was blocked on exactly these): Vector DB? LLM provider? Embedding model? Chunking granularity?
   **A**: ChromaDB (embedded) / Anthropic Claude / local `sentence-transformers` (`all-MiniLM-L6-v2`) / one chunk per entity — all the recommended defaults, matching the reasoning already laid out in `FINDINGS.md §7` months earlier in the process (Chroma = lowest friction for a take-home Docker demo; Anthropic = natural fit given the build environment; local embeddings = no API key, good "embedding strategy" slide story; per-entity chunking = matches Entity Matcher's per-entity granularity, avoids fragmenting relationship context that's already handled deterministically by the Bounded Graph Traversal).

No follow-up research needed — these were vendor picks with the shape already fully specified by the ports (ADR-0001), not open design questions.

## Key Discoveries

### Technical Discoveries
- Grounding Guard (ADR-0005, pre-generation) and Grounding Validator (ADR-0010, post-generation) are frequently conflated at a glance but target different failure modes — zero-context vs. embellishment-on-real-context. Both needed distinct handling in the pipeline design (Phase 5).
- `docs/adr/0009` and `docs/adr/0016` cross-reference each other in a way that determines the Grounding Validator's actual runtime relevance: since ADR-0016 routes deterministic hits to templates (not the LLM), the Validator's *meaningful* work only happens on the LLM path — for templated answers it's a no-op regression check, not a runtime gate. This shaped the pipeline's branch structure in Phase 5.
- `tasks/eval.yml`'s existing command (`python -m tests.eval.run --report docs/eval-report.md`) was written *before* any Python code existed — Phase 8 must match that exact invocation, not invent a new one, to keep the already-verified Taskfile working without edits.

### Patterns to Follow
- Every ADR that names a concrete implementation detail (ADR-0011's `difflib`, ADR-0016's f-strings, ADR-0009's plain adjacency dict, ADR-0021's frozen Pydantic v2 models) was written specifically to avoid a heavier dependency at this project's scale — the plan preserves every one of these choices rather than "improving" them during implementation.

### Constraints Identified
- No git repo exists — needed before `task ci:*` means anything and before the brief's "GitHub Repository link" deliverable is even possible. Added to Phase 0.
- Anthropic has no first-party embeddings endpoint (surfaced during the `AskUserQuestion` options) — confirms local `sentence-transformers` is the cleaner pick given Claude was chosen for generation, not a forced compromise.

## Design Decisions

### Decision 1: Vector DB
**Options considered**: ChromaDB (embedded) / Qdrant (own container) / FAISS (no metadata filter) / pgvector (no existing Postgres story).
**Chosen**: ChromaDB, embedded.
**Rationale**: Matches ADR-0004's existing "no DB server" reasoning for the structured side — one container, not two, for a take-home demo.

### Decision 2: LLM provider
**Options considered**: Anthropic Claude / OpenAI / local Ollama.
**Chosen**: Anthropic Claude.
**Rationale**: Natural fit given the build environment; hosted API is more reliable for a live demo than local Ollama.

### Decision 3: Embedding model
**Options considered**: local `sentence-transformers` / OpenAI `text-embedding-3-small` / match-LLM-vendor.
**Chosen**: local `sentence-transformers` (`all-MiniLM-L6-v2`).
**Rationale**: Free, offline, no API key; concrete story for the embedding-strategy walkthrough slide; Anthropic doesn't offer first-party embeddings anyway.

### Decision 4: Chunking granularity
**Options considered**: one chunk per entity / one per attribute / one per relationship.
**Chosen**: one chunk per entity.
**Rationale**: Matches Entity Matcher's per-entity granularity; relationships are already handled deterministically by the Bounded Graph Traversal (ADR-0009), so per-relationship chunking would be redundant with the structured path, not complementary.

## Open Questions (During Research)

- [x] Vector DB — Resolved: ChromaDB
- [x] LLM provider — Resolved: Anthropic Claude
- [x] Embedding model — Resolved: local sentence-transformers
- [x] Chunking granularity — Resolved: one chunk per entity
- [x] Exact port method signatures — Resolved: designed in plan Phase 1, since docs only implied them

**All questions resolved before the plan was finalized** — no open questions remain in `cdm-rag-chatbot-plan.md` or the approved plan file.

## Code Snippets Reference

### Existing Taskfile commands the implementation must satisfy (verbatim, from `tasks/*.yml`)

```yaml
# tasks/ingest.yml
run:
  cmds:
    - .venv/bin/python -m app.ingestion.run

# tasks/eval.yml
run:
  cmds:
    - .venv/bin/python -m tests.eval.run --report docs/eval-report.md

# tasks/dev.yml
api:
  cmds:
    - .venv/bin/uvicorn app.api.main:app --reload --port 8000
```

### Port signature pattern from ADR-0021 (the one literal example in the docs)

```python
# ADR-0021's Implementation Notes example — extrapolated to the full port set in Phase 1
get_attributes(entity: str) -> AttributesResult
```
