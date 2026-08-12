# ADR-0031: Migrate Python Dependency Management to uv

**Status:** Accepted
**Date:** 2026-08-12
**Deciders:** Emre Gözütok

## Context

Since Phase 0, Python dependencies were managed the plain way: `python3 -m venv .venv`, then `pip install -r requirements.txt -r requirements-dev.txt`, with a hand-maintained `--extra-index-url https://download.pytorch.org/whl/cpu` flag repeated at three separate install sites (`tasks/dev.yml`, and both Dockerfile stages) to avoid pulling PyPI's default CUDA-bundled `torch` wheel for a CPU-only embedding workload (a real bug found and fixed live in Phase 7 — see `docs/adr/0023-tech-layer-adapters.md`'s history). Neither `requirements.txt` nor `requirements-dev.txt` pinned versions, so every fresh install silently picked up whatever was newest — re-running `uv sync` for this migration surfaced two new `ruff` lint findings (`UP037`, quoted-annotation) purely from `ruff` having drifted forward since the original install, invisible until something re-resolved dependencies.

`uv` (Astral) addresses both gaps directly: a committed lockfile (`uv.lock`) pins the exact resolved version of every dependency, transitive included, so "fresh install" and "the install this was tested against" are the same thing; and per-package index routing (`[tool.uv.sources]`) expresses the CPU-torch requirement once, in project config, instead of as a flag every install site has to remember to pass.

## Decision

Replace `requirements.txt`/`requirements-dev.txt` + `pip`/`venv` with `uv`:

- **`pyproject.toml`** gains a real `[project]` table (base runtime dependencies) and a `[dependency-groups] dev` group (pytest/ruff/mypy/httpx) — PEP 735 dependency groups, uv's native mechanism, installed by default on a plain `uv sync` the same way `pip install -r requirements.txt -r requirements-dev.txt` did.
- **`[tool.uv] package = false`** — this is a plain app run via `python -m app.*`/`uvicorn app.api.main:app`, not something meant to be built into a distributable wheel; without this, `uv sync` tries to install `app/` itself as a package.
- **`[tool.uv.sources]`/`[[tool.uv.index]]`** pin `torch` to PyTorch's CPU-only index on Linux only (`marker = "sys_platform == 'linux'"`, `explicit = true` so the index is scoped to torch/torchvision alone) — the same effective behavior as the old `--extra-index-url` flag, expressed once instead of at three separate call sites. `torch` is listed as an explicit direct dependency (not left purely transitive via `sentence-transformers`) — see "Real-World Verification" below for why that turned out to matter.
- **`uv.lock`** is committed — every dependency, direct and transitive, pinned to an exact resolved version.
- **`tasks/dev.yml`**'s `setup` task becomes `uv sync` — `.venv` still lands in the same place, so every other task's `.venv/bin/pytest`/`.venv/bin/ruff`/`.venv/bin/mypy`/`.venv/bin/uvicorn` invocation is untouched.
- **`Dockerfile`** (both `builder` and `runtime` stages) copies the official distroless `uv` binary (`COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/`), runs `uv sync --locked --no-dev` (`--locked` fails the build if `uv.lock` and `pyproject.toml` have drifted apart rather than silently re-resolving; `--no-dev` matches the old behavior of never installing pytest/ruff/mypy into either stage), then puts `.venv/bin` on `PATH` so `CMD ["uvicorn", ...]` and `RUN python -m app.ingestion.run` resolve exactly as before, unchanged.
- **CI** (`.github/workflows/ci.yml`) adds `astral-sh/setup-uv@v9` (`enable-cache: true`) to both the fast and slow gate jobs, ahead of the existing `task dev:setup` step — everything downstream of that step is unchanged, since the Taskfile abstraction absorbed the actual mechanism change.

## Rationale

- **Reproducibility gap, closed.** A committed lockfile means "it passed CI" and "it works on a fresh machine" are backed by the same exact dependency graph — not the case before, where an unpinned `ruff`/`mypy`/anything-else could silently drift between a developer's machine, CI, and the Docker image, three separate `pip install` invocations each resolving independently at whatever moment they happened to run.
- **One CPU-torch fix, not three.** The `--extra-index-url` flag was a real bug once (found and fixed live in Phase 7) precisely because it was easy to add in one place and forget in another. Project-level config can't be forgotten at a call site — there's no flag left to omit.
- **No workflow change for anyone using the Taskfile.** Every existing `task dev:*`/`task ci:*`/`task docker:*` entry point behaves identically; the mechanism swap is contained entirely inside `tasks/dev.yml`'s `setup` task and the Dockerfile's install steps.
- **Speed**, while real (uv's resolver and installer are substantially faster than pip's), was not the deciding factor here — reproducibility and eliminating the repeated-flag footgun were.

## Consequences

### Positive
- `uv.lock` makes dependency drift visible and diffable in code review, instead of invisible until something breaks.
- The CPU-torch behavior is expressed once, correctly scoped by platform marker, impossible to forget at a new install site.
- Docker layer caching improves slightly: `COPY pyproject.toml uv.lock ./` + `RUN uv sync` is cached independently of `COPY app ./app`, same layering discipline the old `COPY requirements.txt .` + `RUN pip install` already had — no regression, marginal gain from `uv`'s faster resolution when the cache does miss.

### Negative
- One more tool in the prerequisite list (`uv`, alongside Python/Node/go-task/Docker) — a real, if small, addition to setup friction for anyone cloning the repo fresh.
- `uv.lock` is a new file to keep in sync; forgetting to re-run `uv lock` after hand-editing `pyproject.toml` would be caught by CI's `--locked` flag failing loudly, not silently drifting — an acceptable trade given the alternative is the invisible-drift problem this migration fixes.

## Real-World Verification (2026-08-12)

The first `task docker:build` after this migration landed reintroduced the exact bug this ADR set out to fix: `uv.lock` showed `torch` resolving from plain PyPI (`source = { registry = "https://pypi.org/simple" }`) even under the Linux build, pulling in the full CUDA dependency chain (`cuda-toolkit[cublas, cudart, cufft, curand, cusolver, ...]`, several hundred MB of `nvidia-*` packages) — `[tool.uv.sources]`'s marker-based override on `torch` had no effect at all, despite matching Astral's own documented pattern for exactly this scenario (a transitive-only dependency, source-pinned without being listed directly).

Root cause, confirmed by reading `uv.lock` directly: the override applied reliably only once `torch` was added as an **explicit direct dependency** in `[project.dependencies]`, not left purely transitive via `sentence-transformers`. After that one-line change, `uv lock` produced two separate resolution-marker branches for `torch` — `2.13.0` from PyPI for non-Linux platforms, `2.13.0+cpu` from the pinned index for Linux, the `+cpu` suffix and empty `nvidia-*` dependency list confirming the correct wheel — and a real `task docker:build` against the actual Linux/aarch64 container completed without touching a single CUDA package, then served correct, grounded answers on both brief example questions.

This is the same lesson this project has run into repeatedly (ADR-0007, ADR-0010, ADR-0023, ADR-0028's SQLite concurrency fix, and now this): a fix that looks correct by reading documentation and code is not confirmed until it's run against the real target environment. Local `uv sync` on macOS never exercised the Linux marker branch at all, since the marker simply doesn't match there — only an actual Linux Docker build could have caught this.

## Alternatives Considered

**Keep pip + requirements.txt, just pin versions by hand** — would close the reproducibility gap but not the repeated-flag problem, and hand-maintaining transitive-dependency pins without a resolver is exactly the kind of manual bookkeeping a lockfile tool exists to avoid.

**Poetry** — comparable lockfile guarantees, but heavier tooling and a distinct `[tool.poetry]` dependency syntax instead of the now-standard `[project]` table (PEP 621) uv reads directly; uv's `[tool.uv.sources]` per-package index routing is also a more direct fit for the CPU-torch case than Poetry's source configuration.

**pip-tools (`pip-compile`)** — would produce a lockfile-equivalent but keeps `pip`/`venv` as the actual installer, and has no equivalent to `[tool.uv.sources]`'s per-package, marker-scoped index routing — the CPU-torch flag would still need to live somewhere as a manually-repeated `--extra-index-url`.

## Related Decisions

- [ADR-0020](0020-task-automation-modular-taskfiles.md) — the Taskfile abstraction layer that absorbed this change with zero surface-level impact on any `task <name>` entry point
- [ADR-0023](0023-tech-layer-adapters.md) — where the CPU-only-torch requirement was first found and fixed, the bug this migration structurally prevents from recurring
