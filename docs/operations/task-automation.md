# Task Automation

[Task](https://taskfile.dev) (`go-task`), one root `Taskfile.yml` including namespaced files under `tasks/` — see [ADR-0020](../adr/0020-task-automation-modular-taskfiles.md).

```
Taskfile.yml
tasks/
  dev.yml        # setup, lint, format, run API locally
  ingest.yml     # run the ingestion pipeline
  test.yml       # test:unit, test:integration, test:system, test:acceptance, test:all
  eval.yml       # eval:run — the slow-gate evaluation dataset run
  docker.yml     # docker:build, docker:run
  ci.yml         # ci:fast, ci:slow — the CI/CD gates, composed from the tasks above
```

CI/CD invokes `task ci:fast` / `task ci:slow` directly ([Operations: CI/CD](ci-cd.md)) — the same commands a developer runs locally, composed from `test:*`, `dev:lint`, `docker:build`, `ingest:run`, and `eval:run`. No separate CI-only scripts, no drift between "what CI does" and "what you can run on your laptop." `task --list-all` is the single discoverable entry point.

This file tree already exists and is verified working (`task --list-all` parses cleanly) — see [Design: Subsystem Design](../design/subsystem-design.md) for the surrounding `app/`/`tests/` layout it was written against.
