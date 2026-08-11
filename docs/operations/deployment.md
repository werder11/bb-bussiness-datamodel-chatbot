# Deployment

Single Docker image, single container — see [Architecture: Containers](../architecture/containers.md) for why ingestion and the API service ship together rather than as separate always-on processes.

## Build & Run

```
task docker:build   # docker build -t cdm-rag-chatbot:local .
task docker:run      # docker run --rm -p 8000:8000 --env-file .env cdm-rag-chatbot:local (depends on docker:build)
```

`docker:run` depends on `docker:build`, so a stale or missing image can't silently be run — see [Operations: Task Automation](task-automation.md).

## Configuration

Vendor credentials (LLM provider API key, vector DB connection if not embedded) are injected via a `.env` file / environment variables at container run time — never committed. This is the only real security requirement given the CDM schema data itself has no PII/secrets — see [Architecture: Requirements](../architecture/README.md#requirements).

## Deployment Scope

Best-effort, single container, no HA/multi-region — matches the Availability NFR in [Architecture: Requirements](../architecture/README.md#requirements) and the demo-only nature of this deliverable. See [Architecture: Principles](../architecture/principles.md#whats-deliberately-not-built-and-why) for what's explicitly not built here (auth, multi-region, message queues).
