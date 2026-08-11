# ADR-0007: Resolver Scope Is Explicitly Bounded (Documented Anti-Corruption Layer)

**Status:** Accepted
**Date:** 2026-08-11
**Deciders:** Emre Gözütok

## Context

Per [`FINDINGS.md §5`](../../FINDINGS.md#5-the-core-challenge-multi-hop-attribute--relationship-resolution), full CDM resolution involves multi-hop `extendsEntity` chains, shared `attributeGroupReference` libraries, and polymorphic "base_X" CDS shapes not literally present as files. Full fidelity would likely require the official (heavier, semi-orphaned) Microsoft ObjectModel SDK.

## Decision

The Resolver handles single-hop `extendsEntity` and `attributeGroupReference` composition, plus explicit disambiguation of the Account/Contact name collision by source-path namespacing. Deeper polymorphic base-shape resolution is out of scope and documented as a known limitation, not silently approximated.

Correctness is verified with **fixture-based golden tests**: frozen sample `.cdm.json` inputs — one per pattern found in FINDINGS §5 — with an expected canonical-model output checked in as the test oracle.

The official Microsoft ObjectModel SDK remains available as a *future adapter* behind this same Resolver port if resolution gaps prove costly in practice — the Canonical Model's shape stays independent of it either way, so swapping resolver implementations later wouldn't ripple into the rest of the system.

## Consequences

### Positive
- Scoped, justified, testable resolution logic.
- Avoids pulling in a heavy dependency tied to a decommissioned service by default.
- Golden tests catch silent regressions when new entity shapes are encountered.
- The door to the official SDK stays open without committing to it now.

### Negative
- A small number of entities/attributes may resolve incompletely — acceptable given it's disclosed, and directly demonstrates the kind of scoping judgment expected of a senior architect.

## Alternatives Considered

Adopt the official Microsoft ObjectModel SDK now for full resolution fidelity — rejected as the default: heavier dependency, tied to a decommissioned CDM Schema Store, disproportionate to this take-home's scope. Kept as an optional future adapter instead of ruled out entirely.

## Implementation Notes

Golden-test fixtures live under `tests/integration/fixtures/` (see [`docs/design/subsystem-design.md`](../design/subsystem-design.md#project-layout)), one frozen `.cdm.json` per pattern from FINDINGS §5: single-hop `extendsEntity`, `attributeGroupReference` composition, the polymorphic `Customer` group, the explicit `Relationship` entity, and the Account/Contact name collision. Each fixture's expected Canonical Model output is checked in alongside it as the test oracle ([ADR-0018](0018-testing-strategy-istqb-aligned.md)).

## Related Decisions

- [ADR-0001](0001-hexagonal-architecture-ports-and-adapters.md) — the port this Resolver sits behind
- [ADR-0012](0012-ingestion-fails-per-entity-skip-and-log.md) — failure handling when a single entity falls outside this scope
- [ADR-0014](0014-explicit-validation-pass.md) — cross-entity integrity checking downstream of this Resolver
- [ADR-0015](0015-canonical-model-provenance.md) — metadata this Resolver attaches to its output
