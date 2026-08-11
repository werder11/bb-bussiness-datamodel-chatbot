# CDM RAG Chatbot — Context & Dependencies

**Last Updated**: 2026-08-11

## Quick Summary

Python/FastAPI RAG service over the Microsoft CDM Banking Model — Canonical Model ingestion, dual (SQL + vector) retrieval, grounded generation, all shape decisions already made across 22 ADRs; this plan builds it from zero code.

## Key Files & Locations

### Files to Create (none exist yet)
- `app/domain/{models,ports,entity_matcher,router,pipeline,templates,tracing}.py` — domain core, no adapter dependencies
- `app/adapters/{structured_index_sqlite,vector_index_chroma,llm_anthropic}.py` — concrete port implementations
- `app/ingestion/{resolver,validate,run}.py` — offline pipeline
- `app/api/{main,schemas}.py` — FastAPI
- `tests/{unit,integration,system,acceptance,eval}/` — one dir per ADR-0018 test level
- `Dockerfile`, `requirements.txt`, `requirements-dev.txt`

### Files to Reference (already exist, define the contract)
- `docs/architecture/components.md` — the full pipeline diagram, source of truth for `app/domain/pipeline.py`'s step order
- `docs/design/workflows.md#query-workflow` — the same pipeline as an ordered list, easier to check off against
- `docs/adr/0014-explicit-validation-pass.md` — the exact 4-check table `app/ingestion/validate.py` must implement
- `docs/quality/evaluation-strategy.md` — the exact KPI table and 8-category dataset spec `tests/eval/` must implement
- `Taskfile.yml` + `tasks/*.yml` — every command this implementation must make resolve to something real, unmodified

### Test Files
- `tests/integration/fixtures/` — 5 golden `.cdm.json` fixtures + expected outputs, created in Phase 2, referenced by `tests/integration/test_resolver.py`

## Dependencies

### Code Dependencies (Python packages)
- `fastapi`, `uvicorn` — API
- `pydantic>=2` — schema-based design (ADR-0021), used everywhere
- `chromadb` — vector index (ADR-0023)
- `sentence-transformers` — local embeddings (ADR-0023)
- `anthropic` — LLM generation (ADR-0023)
- Dev-only: `pytest`, `ruff`, `mypy`, `httpx`

### External Dependencies
- Anthropic API key (env var, e.g. `ANTHROPIC_API_KEY`) — only used on the semantic/mixed-evidence generation path and by `task eval:run`; never required for the fast CI gate or deterministic-only demo questions
- No database server, no message queue, no other external service

## Key Technical Decisions

1. **Port signatures** (Phase 1): designed fresh since the docs only implied them — `StructuredIndex.{get_attributes, get_relationships, traverse}`, `VectorIndex.semantic_search`, `LLM.generate`, all typed Pydantic request/response models per ADR-0021.
2. **Name-collision namespacing** (Phase 2): `f"{namespace}:{entity_name}"` — e.g. `banking:Account` vs `crmCommon:Account` — concrete implementation of ADR-0007's "source-path namespacing."
3. **Adjacency dict for traversal** (Phase 3): built once in `SQLiteStructuredIndex.load()`, not recomputed per query — matches ADR-0009's "no graph database" note and keeps `traverse()` O(1) lookup + bounded BFS.
4. **Vector DB / LLM / embeddings / chunking** (ADR-0023, this session): ChromaDB embedded, Anthropic Claude, local `sentence-transformers` `all-MiniLM-L6-v2`, one chunk per entity.

## Integration Points

- **CDM source** (`cdm-source/schemaDocuments/`): read-only, offline, only touched by `app/ingestion/resolver.py` — never on the query path (ADR-0002).
- **ChromaDB**: embedded, persisted to a local directory inside the container — no network call.
- **Anthropic API**: network call, only on `LLM.generate()`, only reached when Grounding Guard passes and evidence needs synthesis (ADR-0016).
- **SQLite**: embedded file, written once by ingestion, read-only on the query path.

## Environment Requirements

- Python 3.11+ (modern typing: `X | None`, `tuple[...]`, used throughout Phase 1's models)
- Env vars: `ANTHROPIC_API_KEY` (required for `LLM.generate` and `task eval:run`; not required for `task ci:fast`)
- No database migrations — SQLite schema is created fresh by `SQLiteStructuredIndex.load()` every ingestion run (idempotent, ADR-0002)

## Related Documentation

- Original approved plan: `/Users/emre/.claude/plans/wild-finding-wind.md`
- Research notes: `cdm-rag-chatbot-research.md`
- Implementation plan: `cdm-rag-chatbot-plan.md`
- Task checklist: `cdm-rag-chatbot-tasks.md`
- Full architecture: `docs/README.md`
