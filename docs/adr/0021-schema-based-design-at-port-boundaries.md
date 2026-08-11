# ADR-0021: Schema-Based Design at Every Port Boundary

**Status:** Accepted
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

The Hexagonal Architecture ([ADR-0001](0001-hexagonal-architecture-ports-and-adapters.md)) defines ports (`StructuredIndex`, `VectorIndex`, `LLM`) and a Canonical Model ([ADR-0007](0007-resolver-scope-bounded-anti-corruption-layer.md)) that crosses several stages (Resolver → Validation → both projections). Passing loose dicts across these boundaries would silently reintroduce exactly the kind of shape-drift risk the Validation Pass ([ADR-0014](0014-explicit-validation-pass.md)) and the ports themselves exist to prevent, and would make "unit-testable against fakes" (ADR-0001's whole justification) weaker in practice — a fake that doesn't share a real schema with its adapter can drift silently.

## Decision

Every port boundary and every external-facing contract is an explicit, typed schema (Pydantic models, since the stack is Python/FastAPI), validated at the boundary rather than passed as `dict`:

- **Canonical Model** — `Entity`, `Attribute`, `Relationship`, `Trait` as Pydantic models, including the provenance fields from [ADR-0015](0015-canonical-model-provenance.md). This is the schema the Validation Pass ([ADR-0014](0014-explicit-validation-pass.md)) checks records against.
- **`StructuredIndex` / `VectorIndex` records** — typed request/response models per port method (`get_attributes(entity: str) -> AttributesResult`, etc.), so fakes used in Component/Unit tests ([ADR-0018](0018-testing-strategy-istqb-aligned.md)) are structurally guaranteed to match real adapters.
- **API contracts** — FastAPI request/response models (native Pydantic), documented automatically via the generated OpenAPI schema — no separate API doc to keep in sync.
- **Evaluation dataset records** — a Pydantic model per eval question (`question`, `category`, `expected_entities`, `expected_answer_type`, ...), so the evaluation dataset ([ADR-0017](0017-evaluation-as-first-class-layer.md)) itself is schema-validated, not a loosely-shaped CSV/JSON that can silently rot.

## Consequences

### Positive
- Shape drift is caught at the boundary (a validation error) instead of surfacing later as a confusing retrieval bug.
- FastAPI's OpenAPI schema generation comes for free once request/response models exist — no hand-maintained API doc.
- Fakes used in tests are schema-checked against the same models real adapters return, closing a gap plain-dict fakes would leave open.

### Negative
- More upfront model definitions before any adapter is written — small cost, paid once per boundary, not per feature.

## Alternatives Considered

Loose dicts/`TypedDict` with no runtime validation — rejected, no validation at the boundary means shape drift is only caught by a downstream `KeyError` or, worse, silently wrong data reaching the Grounding Guard.

## Implementation Notes

Pydantic v2. Canonical Model instances are frozen (`model_config = ConfigDict(frozen=True)`) — the model is derived once at ingestion time and never mutated afterward, so immutability catches accidental in-place edits during retrieval as a hard error rather than a silent data-integrity bug.

## Related Decisions

- [ADR-0001](0001-hexagonal-architecture-ports-and-adapters.md) — the ports these schemas define the contracts for
- [ADR-0007](0007-resolver-scope-bounded-anti-corruption-layer.md) / [ADR-0014](0014-explicit-validation-pass.md) — the Canonical Model and validation this ADR gives a concrete schema to
- [ADR-0017](0017-evaluation-as-first-class-layer.md) — the evaluation dataset this ADR also schema-validates
