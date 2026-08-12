# CDM RAG Chatbot

A FastAPI service that answers natural-language questions about the [Microsoft Common Data Model](https://github.com/microsoft/CDM) Banking Model — which entities exist, their attributes, and their relationships — grounded in the actual ingested schema, never hallucinated.

Built as a take-home case study for a Senior Data & AI Architect role at reeeliance.

## Presentation

Live, rendered — no download needed: **https://werder11.github.io/bb-bussiness-datamodel-chatbot/** (`.github/workflows/pages.yml` publishes `presentation/` on every push that touches it; requires the one-time repo Settings → Pages → Source → "GitHub Actions" toggle).

- [`presentation/technical-walkthrough.html`](presentation/technical-walkthrough.html) — the brief's required 4-slide technical walkthrough (embedding strategy + how relationships were handled), self-contained and arrow-key navigable; open it directly in a browser, no build step. Every number and quote on it comes from actually running the code against the real corpus — the KPI slide mirrors `docs/eval-report.md` (gitignored by default; run `task eval:run` to regenerate it, or un-gitignore it if you want the committed repo to include the exact numbers shown).
- [`presentation/self-intro.html`](presentation/self-intro.html) — the brief's required self-intro slide ("How do I see myself as a Senior Data & AI Architect at reeeliance?"), same visual system as the technical walkthrough. Strengths, experience, and role evolution, each grounded in real resume/reference-letter facts rather than generic claims.

## What it does

- Ingests the CDM Banking Model + common/supporting objects (44 entities) into a Canonical Model, then two retrieval indexes: a relational one (SQLite) for deterministic attribute/relationship lookups and a semantic one (ChromaDB) for open-ended questions.
- Answers via `POST /query`: fully-structured hits (attributes, single-hop relationships, bounded 2-hop traversal) are template-rendered with zero LLM involvement — zero hallucination surface. Open-ended questions go through an LLM (Anthropic Claude or Google Gemini, swappable), constrained to the retrieved context and checked by a post-generation Grounding Validator.
- Refuses explicitly, rather than guessing, when nothing relevant was retrieved or a question is ambiguous (e.g. the real `Account`/`Contact` name collision between the Banking and common-object namespaces).
- Ships a small TypeScript UI (chat box + entity browser) served by the API itself — open `http://localhost:8000` after `task docker:run`/`task dev:api`, no separate frontend process.
- Includes an interactive "Score an answer" panel: type any question plus the answer you'd expect, and it runs the real pipeline and compares the two — real per-query pipeline inspection, not just the build-time eval snapshot (ADR-0030).

## Architecture

Full documentation lives in [`docs/`](docs/README.md) — a layered knowledge base (Vision → Architecture → Domain → Design → Quality → ADRs → API → Operations) with 30 Architecture Decision Records covering every structural and technology choice. Start there for the "why," not just the "what."

Quick orientation:
- [`docs/architecture/components.md`](docs/architecture/components.md) — the full request/ingestion-time component diagram.
- [`docs/adr/README.md`](docs/adr/README.md) — every decision, indexed with a suggested reading order.
- [`FINDINGS.md`](FINDINGS.md) — the raw research log from investigating the CDM source repo.

## Quickstart

Requires Python 3.14, [uv](https://docs.astral.sh/uv/), Node 22+, [go-task](https://taskfile.dev), and Docker. `task --list-all` lists every available command.

```bash
task dev:setup   # create .venv, install Python dependencies
task ui:setup    # install UI dependencies (only needed to build/run the UI locally)
task test:all    # unit + integration + system + acceptance tests
task dev:lint    # ruff + mypy
```

### Run it locally

```bash
git clone --filter=blob:none --no-checkout https://github.com/microsoft/CDM.git cdm-source
cd cdm-source && git sparse-checkout set schemaDocuments && git checkout master && cd ..

task ingest:run          # parses the CDM source into cdm.db + chroma_data/
cp .env.example .env     # set LLM_PROVIDER + an API key for the semantic/generation path
task ui:build             # optional — builds ui/dist so the API serves the UI too
task dev:api               # runs the FastAPI app on :8000 with autoreload
```

```bash
curl localhost:8000/health
curl -X POST localhost:8000/query -H "Content-Type: application/json" \
  -d '{"question": "What are the attributes of banking:Account?"}'
```

Or open `http://localhost:8000` in a browser for the UI (if `task ui:build` was run) — chat box on the right, entity browser on the left.

### Run it in Docker

```bash
task docker:build       # bakes ingestion + the UI into the image at build time
task docker:run         # requires .env (see above); UI at http://localhost:8000
```

### Evaluate

```bash
task eval:run            # runs the eval dataset (tests/eval/dataset.py) against the real
                          # pipeline, writes docs/eval-report.md with the full KPI table
                          # (entity-matching accuracy, retrieval P/R, faithfulness, refusal
                          # accuracy, ...) — needs a live LLM key for the generation-path metrics
```

## LLM provider

Set via `LLM_PROVIDER` in `.env` — `anthropic` (default) or `gemini` (free tier via [Google AI Studio](https://aistudio.google.com), no card required). See [ADR-0024](docs/adr/0024-second-llm-provider-gemini.md).

## UI

A thin TypeScript client (no framework) — a chat box against `POST /query` and an entity browser against `GET /entities*` — built with Vite and served by FastAPI itself from the same origin, no separate process or CORS setup. `task ui:dev` for a live-reloading dev server (proxies to `task dev:api` on :8000), `task ui:build` to produce the `ui/dist` that both `task dev:api` and the Docker image serve. See [ADR-0025](docs/adr/0025-ui-typescript-chat-and-entity-browser.md).

## Testing

Four ISTQB-aligned levels (`docs/quality/testing-strategy.md`): Component/Unit (fakes, no live services), Component Integration (fixture `.cdm.json` files), System (real small corpus via `TestClient`), Acceptance (one test per functional requirement). Evaluation (`tests/eval/`) is a deliberately separate, fifth discipline — empirical answer-quality measurement, not pass/fail correctness (ADR-0017).

A sixth, UI-side level lives in `ui/tests/e2e/` — Playwright against a real browser and a real running server, needing zero LLM credentials (the semantic/LLM-route UI is tested by mocking `POST /query` with real captured response shapes, not by spending Gemini's free-tier quota). `task ui:e2e:setup` once (installs the browser, ~150-300MB), then `task ui:e2e`. See [ADR-0029](docs/adr/0029-playwright-e2e-tests.md).

## CI/CD

`.github/workflows/ci.yml` — fast gate (`task ci:fast`: lint, all test levels, UI type-check + build, Docker build) on every push; slow gate (`task ci:slow`: live ingestion + full evaluation dataset) on manual `workflow_dispatch` only, since it costs real LLM calls. See [`docs/operations/ci-cd.md`](docs/operations/ci-cd.md).
