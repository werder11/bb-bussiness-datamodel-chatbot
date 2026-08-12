# Multi-stage build — see docs/architecture/containers.md: ingestion and the
# API service ship in one image, but ingestion's own toolchain (the CDM
# source clone) doesn't belong in the runtime layer that actually serves
# requests (ADR-0002 keeps the two paths separate even within one image).
# The UI (ADR-0025) is a third, independent stage — Node never touches the
# runtime image at all, only its build output does.

FROM node:22-slim AS frontend-builder

WORKDIR /ui

COPY ui/package.json ui/package-lock.json ./
RUN npm ci

COPY ui/tsconfig.json ui/vite.config.ts ui/index.html ./
COPY ui/src ./src

RUN npm run build


FROM python:3.14-slim AS builder

# Official distroless uv image — just the binary, nothing else (ADR-0031).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
# --no-dev: this stage only ever runs `app.ingestion.run`, never pytest/ruff/
# mypy. CPU-only torch on Linux comes from pyproject.toml's
# [tool.uv.sources]/[[tool.uv.index]], not a per-install-site flag.
RUN uv sync --locked --no-dev
ENV PATH="/app/.venv/bin:$PATH"

COPY app ./app
# Sparse-cloned once, locally, before `docker build` — not fetched by the
# build itself (docs/architecture/system-context.md: "offline, read-only,
# sparse-cloned once"; ADR-0008: ingestion pins whatever's present at
# ingestion time, no re-fetch mechanism).
COPY cdm-source ./cdm-source

RUN python -m app.ingestion.run


FROM python:3.14-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# The embedding model is already baked in below — no reason for the
# huggingface_hub client to ever make a network call to check for updates.
ENV HF_HUB_OFFLINE=1

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=builder /app/app ./app
COPY --from=builder /app/cdm.db ./cdm.db
COPY --from=builder /app/chroma_data ./chroma_data
# The embedding model was already downloaded once, at build time, by the
# ingestion run above — without this, the runtime stage would re-download it
# from the Hugging Face Hub on every container start (a live network
# dependency at query-serving startup that the architecture is meant to
# avoid; only actual LLM generation calls should touch the network).
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface
COPY --from=frontend-builder /ui/dist ./ui/dist

EXPOSE 8000
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
