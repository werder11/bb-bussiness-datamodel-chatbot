# ADR-0020: Task Automation via Modular Taskfiles

**Status:** Accepted
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

The project now has several distinct command groups — dev/lint, ingestion, three-plus test levels ([ADR-0018](0018-testing-strategy-istqb-aligned.md)), evaluation ([ADR-0017](0017-evaluation-as-first-class-layer.md)), Docker/build — that both a local developer and CI/CD ([ADR-0019](0019-cicd-pipeline-layered-by-cost-and-speed.md)) need to invoke consistently. A single flat script or ad hoc shell commands scattered across a README would drift out of sync with what CI actually runs.

## Decision

Use [Task](https://taskfile.dev) (`go-task`) as the single command-runner entry point, with one root `Taskfile.yml` that `includes:` namespaced sub-files under `tasks/` — one file per concern:

```
Taskfile.yml          # root: includes below, `task --list-all` is the discoverable entry point
tasks/
  dev.yml              # setup, lint, format, run API locally
  ingest.yml           # run ingestion pipeline (Resolver → Validate → Canonical → Projections)
  test.yml              # test:unit, test:integration, test:system, test:acceptance, test:all
  eval.yml               # eval:run (the slow-gate evaluation dataset run)
  docker.yml              # docker:build, docker:run
  ci.yml                   # ci:fast, ci:slow — composes the two gates from ADR-0019 out of the tasks above
```

CI/CD invokes `task ci:fast` / `task ci:slow` directly ([ADR-0019](0019-cicd-pipeline-layered-by-cost-and-speed.md)) — the same commands a developer runs locally, composed from `test:*`, `dev:lint`, `docker:build`, `ingest:run`, and `eval:run`. No separate CI-only scripts, no drift between "what CI does" and "what you can run on your laptop."

## Consequences

### Positive
- One discoverable entry point (`task --list-all`); namespacing (`test:unit`, `docker:build`) keeps the command surface organized as it grows.
- CI/CD config becomes a thin wrapper that calls the same tasks a developer already knows — the pipeline is never a source of undocumented behavior.
- Cross-platform (Go binary, no shell-dialect issues) unlike a Makefile.

### Negative
- One more tool a reviewer needs installed to run things locally (mitigated: Task has a single-binary install, and the Dockerfile itself doesn't depend on it — only local dev/CI convenience does).

## Alternatives Considered

Makefile — rejected, no native namespaced includes, shell-dialect portability issues (GNU Make vs. BSD Make), phony-target boilerplate for a project this size doesn't pay for itself.

Bare shell scripts under `scripts/` — rejected, no built-in discoverability (`--list-all`), no dependency-between-tasks support, more boilerplate for the same namespacing Task gives for free.

## Related Decisions

- [ADR-0019](0019-cicd-pipeline-layered-by-cost-and-speed.md) — the two gates this task runner implements
- [ADR-0018](0018-testing-strategy-istqb-aligned.md) — the test levels each `test:*` task corresponds to
