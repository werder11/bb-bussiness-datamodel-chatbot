# ADR-0018: Testing Strategy — ISTQB-Aligned Levels, Data-Driven by Default

**Status:** Accepted
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

The brief explicitly grades "unit tests for retrieval logic." The architecture already implies natural test boundaries via its ports ([ADR-0001](0001-hexagonal-architecture-ports-and-adapters.md)) and its many small, pure decision points (Entity Matcher, Router, Grounding Guard, Grounding Validator, Resolver). Without a stated strategy, testing risks either being too shallow (only happy-path asserts) or drifting into duplicating what [Evaluation](0017-evaluation-as-first-class-layer.md) is for. ISTQB's classic test-level model (component/unit → integration → system → acceptance) maps cleanly onto this architecture's layers, and ISTQB's data-driven testing technique — separating test *procedure* from test *data* so one procedure runs many parametrized cases — fits this system unusually well, since nearly every component here is a pure function over a small, enumerable input space (43 entity names, a handful of query shapes, a handful of CDM structural patterns).

## Decision

Adopt four ISTQB-style test levels, each with a stated data-driven default:

| Level | Scope | Data-driven fixture | Example |
|---|---|---|---|
| **Component/Unit** | Single function/class, in isolation, fake ports | Parametrized table of (input → expected output) | `get_attributes("Account")` against a fixed fake `StructuredIndex`; Entity Matcher against a table of (query text, expected entity or "ambiguous"); Router against a table of (query text, expected route) |
| **Component Integration** | Two or more real components wired together, still no live external services | Fixture `.cdm.json` files checked into the repo | Resolver → Validation → Canonical Model against the fixture files covering each pattern in [FINDINGS §5](../../FINDINGS.md#5-the-core-challenge-multi-hop-attribute--relationship-resolution) — the golden tests already named in [ADR-0007](0007-resolver-scope-bounded-anti-corruption-layer.md) |
| **System** | Full FastAPI app, real ingested (small) corpus, black-box via `TestClient` | A curated subset of the evaluation dataset ([ADR-0017](0017-evaluation-as-first-class-layer.md)) restricted to deterministic (template-rendered) cases, so assertions can be exact | `POST /query "what are Account's attributes"` → assert exact attribute list in response |
| **Acceptance** | Traces back to FR1–FR7 ([`docs/architecture/README.md`](../architecture/README.md#requirements)) | One test per functional requirement | "system answers an in-scope attribute question," "system refuses an out-of-scope question" |

**Data-driven testing is the default technique at every level above Acceptance**: test logic is written once per behavior; cases are added as rows in a fixture table/file, not as new test functions. This keeps the suite's size proportional to the *number of cases*, not the number of `def test_...` functions, and makes coverage gaps visible (an empty or thin fixture table is an obvious gap; a missing `def test_...` isn't).

**Explicit non-goal:** these levels test that code does what it was coded to do. They do not judge whether a generated answer is a *good* answer — that's [Evaluation](0017-evaluation-as-first-class-layer.md)'s job, deliberately kept separate.

## Consequences

### Positive
- Test levels map 1:1 onto architectural boundaries already defined by the ports (ADR-0001) — no new seams to invent.
- Data-driven fixtures make the suite's coverage legible (row count = case count) and cheap to extend (add a row, not a function).
- Component/Unit and Component Integration levels need no live external services (LLM, vector DB) — fast, free, deterministic; fits the CI/CD fast-gate ([ADR-0019](0019-cicd-pipeline-layered-by-cost-and-speed.md)).

### Negative
- Four named levels is more structure than a two-line "we wrote some tests" — worth the clarity given testing is explicitly graded, but requires actually organizing the test directory to match (`tests/unit`, `tests/integration`, `tests/system`, `tests/acceptance`).
- Fixture tables need upkeep as the Canonical Model's shape evolves — acceptable, same cost any fixture-based suite carries.

## Alternatives Considered

One flat `tests/` directory with no level distinction — rejected, makes it hard to tell "fast, always-run" tests from anything requiring the real (if small) corpus, and loses the direct traceability to FR1–FR7 that the Acceptance level provides.

Example-based tests only (one hardcoded case per `def test_...`) — rejected in favor of data-driven fixtures as the default, per ISTQB's data-driven testing technique; example-based tests remain fine for one-off edge cases that don't fit a table.

## Related Decisions

- [ADR-0001](0001-hexagonal-architecture-ports-and-adapters.md) — the ports that define Component/Unit test boundaries
- [ADR-0007](0007-resolver-scope-bounded-anti-corruption-layer.md) — source of the Component Integration golden-test fixtures
- [ADR-0017](0017-evaluation-as-first-class-layer.md) — the complementary, empirical-quality layer this ADR is explicitly distinguished from
- [ADR-0019](0019-cicd-pipeline-layered-by-cost-and-speed.md) — where each test level runs in the pipeline
