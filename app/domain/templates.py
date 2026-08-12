"""Deterministic answer templates — ADR-0016.

Plain f-strings, one per deterministic answer shape (attribute list,
single-hop relationship, depth-2 traversal path). No templating engine —
the shape count is small and fixed.
"""

from app.domain.models import Attribute, Relationship


def render_attributes(entity: str, attributes: tuple[Attribute, ...]) -> str:
    if not attributes:
        return f"{entity} has no recorded attributes in the ingested CDM scope."
    lines = "\n".join(
        f"- {attr.name} ({attr.data_type}){' (optional)' if attr.is_nullable else ''}"
        for attr in attributes
    )
    return f"{entity} has the following attributes:\n{lines}"


def render_relationship(entity: str, relationships: tuple[Relationship, ...]) -> str:
    if not relationships:
        return f"{entity} has no recorded relationships in the ingested CDM scope."
    lines = "\n".join(
        f"- {rel.name} -> {'/'.join(rel.targets)} ({rel.kind})" for rel in relationships
    )
    return f"{entity} has the following relationships:\n{lines}"


def render_traversal(
    source: str, path: tuple[str, ...], relationships: tuple[Relationship, ...]
) -> str:
    if len(path) < 2:
        return f"No path was found from {source} within the traversal depth limit."
    hops = " -> ".join(path)
    via = ", ".join(rel.name for rel in relationships)
    return f"{path[0]} connects to {path[-1]} via: {hops} (through relationship(s): {via})."
