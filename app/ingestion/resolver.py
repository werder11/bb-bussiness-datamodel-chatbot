"""Resolver — Anti-Corruption Layer between raw CDM JSON and the Canonical Model.

Scope per ADR-0007: single-hop `extendsEntity` composition, single-hop
attribute-group composition within one file, and the three entityAttribute
(relationship) shapes actually found in the CDM source during research
(FINDINGS §5, confirmed against real files this session):

1. Simple:              {"entity": {"entityReference": "Lead"}, "name": "originatingLead"}
2. Polymorphic:         {"entity": {"entityReference": {"entityName": "Customer",
                           "hasAttributes": [{"entity": {"entityReference": "Contact"}, "name": "contactOption"},
                                              {"entity": {"entityReference": "Account"}, "name": "accountOption"}]}},
                          "name": "customer"}
3. Party/FK-op:         {"name": "ContactFrom", "dataType": "entityId",
                          "entity": {"source": "Contact", "operations": [...]}}
4. Polymorphic-via-source (real Fi_card.cdm.json "Cardholder", found by running
   against the full corpus — not documented anywhere before this):
                        {"entity": {"source": {"entityReference": {"entityName": "FICardCardholderOptions",
                           "hasAttributes": [{"entity": {"source": "Account"}, "name": "accountOption"},
                                              {"entity": {"source": "Contact"}, "name": "contactOption"}]}}}}

Deeper polymorphic base-shape resolution (e.g. "base_Account/Account", not a
literal file in the CDM repo) is explicitly out of scope and left unresolved,
not silently approximated — the entity keeps its own directly-defined
attributes only. Per-entity failures are skipped and logged (ADR-0012), never
aborting the whole run.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.domain.models import Attribute, Entity, Relationship, Trait

_ROOT_EXTENDS = "CdmEntity"


@dataclass(frozen=True)
class ResolveError:
    entity_name: str
    source_path: str
    reason: str


def discover_entities(
    manifest_path: Path, corpus_root: Path, namespace: str
) -> list[tuple[str, Path, str]]:
    """Walk one manifest, returning (entity_name, file_path, namespace) tuples.

    `entityPath` values look like "Account.cdm.json/Account" (relative to the
    manifest's own directory) or "/core/.../Address.cdm.json/Address" (a
    leading "/" means relative to `corpus_root`, i.e. schemaDocuments/).
    """
    manifest = json.loads(manifest_path.read_text())
    manifest_dir = manifest_path.parent
    discovered: list[tuple[str, Path, str]] = []
    for entry in manifest.get("entities", []):
        entity_path: str = entry["entityPath"]
        file_part = entity_path.rsplit("/", 1)[0]
        file_path = (
            corpus_root / file_part.lstrip("/")
            if file_part.startswith("/")
            else manifest_dir / file_part
        )
        discovered.append((entry["entityName"], file_path, namespace))
    return discovered


def _data_type_str(raw: object) -> str:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        ref = raw.get("dataTypeReference")
        if isinstance(ref, str):
            return ref
    return "unknown"


def _unwrap_ref(node: dict) -> dict | str | None:
    """Follow `entityReference`/`source` wrapper keys until hitting a plain
    entity-name string, or a dict carrying `hasAttributes` (the polymorphic
    options list). CDM nests these wrappers to arbitrary (but always
    single-hop, same-file) depth — e.g. the real Fi_card.cdm.json wraps a
    polymorphic Account/Contact choice as `entity.source.entityReference.
    hasAttributes`, two levels deeper than the simple `entity.entityReference`
    case (FINDINGS-session discovery, not in the original docs)."""
    if "hasAttributes" in node:
        return node
    inner = node.get("entityReference", node.get("source"))
    if isinstance(inner, str):
        return inner
    if isinstance(inner, dict):
        return _unwrap_ref(inner)
    return None


def _extract_ref(entity_ref: dict) -> tuple[str, ...] | None:
    """Return the target entity name(s) named by an entityAttribute's `entity`
    object, or None if the shape isn't recognized."""
    unwrapped = _unwrap_ref(entity_ref)
    if isinstance(unwrapped, str):
        return (unwrapped,)
    if isinstance(unwrapped, dict):
        targets: list[str] = []
        for option in unwrapped.get("hasAttributes", []):
            option_entity = option.get("entity")
            if isinstance(option_entity, dict):
                option_targets = _extract_ref(option_entity)
                if option_targets:
                    targets.extend(option_targets)
        if targets:
            return tuple(targets)
    return None


def _parse_member(member: dict, entity_name: str, source_path: str) -> Attribute | Relationship | None:
    if not isinstance(member, dict):
        # A bare string member references a shared attribute group *by name*,
        # defined elsewhere — cross-file, multi-hop, out of scope (ADR-0007).
        return None

    entity_ref = member.get("entity")
    name = member.get("name")
    if not isinstance(name, str):
        # ValueError, not TypeError: this is malformed CDM data, not a Python
        # type-contract violation — resolve_entity() catches ValueError
        # uniformly to produce a ResolveError (ADR-0012).
        raise ValueError(f"{entity_name} ({source_path}): member missing a 'name'")  # noqa: TRY004

    if entity_ref is None:
        return Attribute(
            name=name,
            data_type=_data_type_str(member.get("dataType", "unknown")),
            description=member.get("description"),
            is_nullable=member.get("isNullable", True),
        )

    targets = _extract_ref(entity_ref)
    if targets is None:
        raise ValueError(f"{entity_name} ({source_path}): unrecognized entity-reference shape on '{name}'")

    kind: Literal["single", "polymorphic", "party"]
    if len(targets) > 1:
        kind = "polymorphic"
    elif "entityReference" in entity_ref:
        kind = "single"
    else:
        kind = "party"
    return Relationship(name=name, targets=targets, kind=kind)


def _parse_own_members(
    definition: dict, entity_name: str, source_path: str
) -> tuple[tuple[Attribute, ...], tuple[Relationship, ...]]:
    attributes: list[Attribute] = []
    relationships: list[Relationship] = []
    for group in definition.get("hasAttributes", []):
        members = group.get("attributeGroupReference", {}).get("members", [])
        for member in members:
            parsed = _parse_member(member, entity_name, source_path)
            if isinstance(parsed, Attribute):
                attributes.append(parsed)
            elif isinstance(parsed, Relationship):
                relationships.append(parsed)
    return tuple(attributes), tuple(relationships)


def resolve_entity(entity_name: str, path: Path, namespace: str) -> Entity | ResolveError:
    """Parse a single `.cdm.json` file into a namespaced Canonical Model Entity.

    Namespacing (`f"{namespace}:{entity_name}"`) is how the Account/Contact
    name collision (FINDINGS §5) gets disambiguated — ADR-0007.
    """
    source_path = str(path)
    try:
        doc = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return ResolveError(entity_name=entity_name, source_path=source_path, reason=str(exc))

    definitions = doc.get("definitions", [])
    definition = next((d for d in definitions if d.get("entityName") == entity_name), None)
    if definition is None:
        return ResolveError(
            entity_name=entity_name,
            source_path=source_path,
            reason=f"no definition named '{entity_name}' found in {source_path}",
        )

    try:
        attributes, relationships = _parse_own_members(definition, entity_name, source_path)
    except ValueError as exc:
        return ResolveError(entity_name=entity_name, source_path=source_path, reason=str(exc))

    traits = tuple(_parse_trait(t) for t in definition.get("exhibitsTraits", []) if isinstance(t, dict))

    return Entity(
        name=f"{namespace}:{entity_name}",
        description=definition.get("description"),
        attributes=attributes,
        relationships=relationships,
        traits=traits,
        source_path=source_path,
    )


def _parse_trait(raw: dict) -> Trait:
    name = raw.get("traitReference")
    return Trait(name=name) if isinstance(name, str) else Trait(name="unknown")


def resolve_all(
    discovered: list[tuple[str, Path, str]],
) -> tuple[list[Entity], list[ResolveError]]:
    """Resolve every discovered entity, plus a second pass merging single-hop
    `extendsEntity` (ADR-0007). Never aborts on one bad entity (ADR-0012)."""
    entities: list[Entity] = []
    errors: list[ResolveError] = []
    raw_extends: dict[str, str | None] = {}

    for entity_name, path, namespace in discovered:
        result = resolve_entity(entity_name, path, namespace)
        if isinstance(result, ResolveError):
            errors.append(result)
            continue
        entities.append(result)
        try:
            doc = json.loads(path.read_text())
            definition = next(
                d for d in doc.get("definitions", []) if d.get("entityName") == entity_name
            )
            raw_extends[result.name] = definition.get("extendsEntity")
        except (OSError, json.JSONDecodeError, StopIteration):
            raw_extends[result.name] = None

    by_name = {e.name: e for e in entities}
    merged: list[Entity] = []
    for entity in entities:
        extends = raw_extends.get(entity.name)
        parent = None
        if extends and extends != _ROOT_EXTENDS and "/" not in extends:
            namespace = entity.name.split(":", 1)[0]
            parent = by_name.get(f"{namespace}:{extends}")
        if parent is None:
            merged.append(entity)
        else:
            merged.append(
                entity.model_copy(
                    update={
                        "attributes": parent.attributes + entity.attributes,
                        "relationships": parent.relationships + entity.relationships,
                    }
                )
            )

    return merged, errors
