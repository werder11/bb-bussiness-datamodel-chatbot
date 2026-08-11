# Subsystem Design

## Project Layout

Every port boundary and external contract is an explicit, typed schema (Pydantic) rather than a loose `dict` — [ADR-0021](../adr/0021-schema-based-design-at-port-boundaries.md). This gives the layout below a concrete shape even before adapter technology is chosen:

```
app/
  domain/            # Canonical Model (Entity/Attribute/Relationship/Trait), ports, Pydantic schemas
  adapters/          # concrete adapters behind each port (resolver, structured_index, vector_index, llm — tech TBD)
  ingestion/         # offline pipeline: resolve → validate → project
  api/               # FastAPI routes, request/response models (auto-generates OpenAPI)
tests/
  unit/              # Component/Unit level (Quality: Testing Strategy)
  integration/        # Component Integration level — fixture .cdm.json files
  system/              # System level — TestClient against the real small corpus
  acceptance/           # One test per FR1–FR7
  eval/                  # Evaluation dataset + runner — separate from tests/, see Quality: Evaluation Strategy
docs/                    # this knowledge base
tasks/                   # modular Taskfiles, see Operations: Task Automation
Taskfile.yml
Dockerfile
```

`tests/eval/` is deliberately not under the same tree philosophy as `tests/unit` through `tests/acceptance` — it holds an empirical quality report, not pass/fail assertions; see [Quality: Testing Strategy](../quality/testing-strategy.md) vs. [Quality: Evaluation Strategy](../quality/evaluation-strategy.md) for why that distinction matters.

## Subsystem Notes

### Resolver
Golden-test fixtures live under `tests/integration/fixtures/`, one frozen `.cdm.json` per pattern from [Domain: Structural Quirks](../domain/domain-model.md#structural-quirks-why-the-resolver-and-traversal-are-shaped-the-way-they-are). See [ADR-0007](../adr/0007-resolver-scope-bounded-anti-corruption-layer.md).

### Bounded Graph Traversal
Breadth-first search from the query entity, depth ≤ 2, over an adjacency structure built once at ingestion time from `entityAttribute` references plus the `Relationship` entity's records. At ~43 nodes this is O(V+E)-trivial — a plain adjacency dict, no graph database. See [ADR-0009](../adr/0009-relationship-traversal-bounded-to-depth-2.md).

### Entity Matcher
Python stdlib `difflib.get_close_matches` as the default fuzzy-match implementation — no new dependency for a 43-item vocabulary. Swappable for `rapidfuzz` later if the evaluation set shows precision issues. See [ADR-0011](../adr/0011-entity-name-matching-closed-vocabulary.md).

### Deterministic Answer Templates
Plain Python f-string templates, one per intent shape (attribute list, single-hop relationship, depth-2 traversal path) — no templating engine dependency warranted at this scale. See [ADR-0016](../adr/0016-deterministic-hits-template-rendered.md).

### Canonical Model Schema
Pydantic v2, frozen (`model_config = ConfigDict(frozen=True)`) — the model is derived once at ingestion time and never mutated, so immutability turns an accidental in-place edit into a hard error rather than a silent data-integrity bug. See [ADR-0021](../adr/0021-schema-based-design-at-port-boundaries.md).
