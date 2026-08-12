# Testing Strategy

Testing verifies the code does what it was coded to do — deterministic, pass/fail. It is deliberately kept separate from [Evaluation](evaluation-strategy.md), which measures whether the system's *output* is actually good. This split follows ISTQB's Certified Tester AI Testing (CT-AI v2.0) syllabus, which treats input-data testing, ML/AI-behavior testing, and conventional functional testing as related but distinct disciplines — see [ADR-0018](../adr/0018-testing-strategy-istqb-aligned.md) for the full rationale.

## Test Levels

Four ISTQB-style levels, each data-driven by default (test *procedure* separated from test *data*, so one procedure runs many parametrized cases — fits this system unusually well, since nearly every component is a pure function over a small, enumerable input space):

| Level | Scope | Data-driven fixture | Example |
|---|---|---|---|
| **Component/Unit** | Single function/class, fake ports, no live services | Parametrized table of (input → expected output) | Entity Matcher against a table of (query text → expected entity or "ambiguous"); Router against (query text → expected route) |
| **Component Integration** | Real components wired together, still no live external services | Fixture `.cdm.json` files checked into the repo | Resolver → Validation → Canonical Model golden tests ([ADR-0007](../adr/0007-resolver-scope-bounded-anti-corruption-layer.md)) |
| **System** | Full FastAPI app, real small ingested corpus, black-box `TestClient` | Deterministic (template-rendered) subset of the eval dataset | `POST /query "what are Account's attributes"` → assert exact attribute list |
| **Acceptance** | Traces to FR1–FR7 ([Architecture: Requirements](../architecture/README.md#requirements)) | One test per functional requirement | "system refuses an out-of-scope question" |
| **E2E** (UI, [ADR-0029](../adr/0029-playwright-e2e-tests.md)) | Real browser (Playwright) against the real running app — the only level that exercises the DOM, not the API/Python objects directly | Real captured API response shapes, for the semantic-route UI cases only | Click a sample query chip, assert the rendered badges/pipeline-view stages match the real route |

Component/Unit and Component Integration levels need no live external services — fast, free, deterministic; they're what the CI/CD fast gate runs on every push ([Operations: CI/CD](../operations/ci-cd.md)). E2E needs no live *LLM* service either (the semantic route is mocked at the network layer) but does need a browser binary installed, which is why it isn't part of `ci:fast` by default — see ADR-0029.

Directory layout: [Design: Subsystem Design](../design/subsystem-design.md#project-layout). Task entry points: `task test:unit`, `task test:integration`, `task test:system`, `task test:acceptance`, `task test:all`, `task ui:e2e` ([Operations: Task Automation](../operations/task-automation.md)).
