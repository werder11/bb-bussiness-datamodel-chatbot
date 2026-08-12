"""Validation Pass — cross-entity integrity checks, ADR-0014.

Distinct from per-entity Resolver failures (ADR-0012): this runs *after*
every entity has already resolved successfully, checking the batch as a
whole. Non-blocking, read-only — reports, doesn't repair.
"""

from dataclasses import dataclass

from app.domain.models import Entity


@dataclass(frozen=True)
class DuplicateEntityName:
    name: str


@dataclass(frozen=True)
class UnresolvedRelationshipReference:
    entity: str
    relationship: str
    target: str


@dataclass(frozen=True)
class DanglingAttributeReference:
    entity: str
    relationship: str
    target: str
    attribute: str


@dataclass(frozen=True)
class MissingIdentifier:
    entity: str


@dataclass(frozen=True)
class ValidationReport:
    entities_discovered: int
    entities_resolved: int
    entities_skipped: int
    relationships_discovered: int
    duplicate_names: tuple[DuplicateEntityName, ...]
    unresolved_references: tuple[UnresolvedRelationshipReference, ...]
    dangling_attribute_references: tuple[DanglingAttributeReference, ...]
    missing_identifiers: tuple[MissingIdentifier, ...]

    def summary(self) -> str:
        return (
            f"{self.entities_discovered} entities discovered, "
            f"{self.entities_resolved} resolved, "
            f"{self.entities_skipped} skipped\n"
            f"{self.relationships_discovered} relationships discovered, "
            f"{len(self.unresolved_references)} unresolved references"
        )


# CDM's own `purpose: "identifiedBy"` marks an entity's identifier attribute
# (e.g. Account.accountId) — see FINDINGS §4 and the real Account.cdm.json
# fixture data. The Resolver doesn't currently carry `purpose` onto Attribute
# (out of scope for Phase 1's schema), so this check keys off attribute name
# convention (`<entity-local-name>Id`) as the practical proxy instead.
def _has_identifier(entity: Entity) -> bool:
    local_name = entity.name.split(":", 1)[-1]
    expected = f"{local_name[0].lower()}{local_name[1:]}Id"
    return any(attr.name == expected for attr in entity.attributes) or any(
        attr.name.lower().endswith("id") for attr in entity.attributes
    )


def validate(
    entities: list[Entity], entities_discovered: int, entities_skipped: int
) -> ValidationReport:
    by_name: dict[str, list[Entity]] = {}
    for entity in entities:
        by_name.setdefault(entity.name, []).append(entity)

    duplicates = tuple(
        DuplicateEntityName(name=name) for name, group in by_name.items() if len(group) > 1
    )

    known_names = set(by_name)
    unresolved: list[UnresolvedRelationshipReference] = []
    relationship_count = 0
    for entity in entities:
        for rel in entity.relationships:
            relationship_count += 1
            for target in rel.targets:
                if target not in known_names and _bare(target) not in _bare_set(known_names):
                    unresolved.append(
                        UnresolvedRelationshipReference(
                            entity=entity.name, relationship=rel.name, target=target
                        )
                    )

    missing_identifiers = tuple(
        MissingIdentifier(entity=entity.name) for entity in entities if not _has_identifier(entity)
    )

    return ValidationReport(
        entities_discovered=entities_discovered,
        entities_resolved=len(entities),
        entities_skipped=entities_skipped,
        relationships_discovered=relationship_count,
        duplicate_names=duplicates,
        unresolved_references=tuple(unresolved),
        # Dangling attribute references (a relationship pointing at an
        # attribute, not an entity) don't occur in the current Canonical
        # Model shape — Relationship.targets always names entities, never
        # attributes — so this check is structurally always empty for now.
        # Kept as a named, typed field (not silently dropped) so the ADR-0014
        # check table stays fully represented if the model ever grows one.
        dangling_attribute_references=(),
        missing_identifiers=missing_identifiers,
    )


def _bare(name: str) -> str:
    return name.split(":", 1)[-1]


def _bare_set(names: set[str]) -> set[str]:
    return {_bare(n) for n in names}
