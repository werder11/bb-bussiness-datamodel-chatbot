"""SQLite adapter for the `StructuredIndex` port — ADR-0004 (embedded, no DB
server) + ADR-0009 (bounded BFS traversal over a plain adjacency dict, no
graph database).
"""

import sqlite3
import threading
from collections import defaultdict, deque
from collections.abc import Iterable
from pathlib import Path

from app.domain.models import Attribute, Entity, Relationship
from app.domain.ports import AttributesResult, RelationshipsResult, TraversalResult

_CREATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    name TEXT PRIMARY KEY,
    description TEXT,
    source_path TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attributes (
    entity_name TEXT NOT NULL,
    name TEXT NOT NULL,
    data_type TEXT NOT NULL,
    description TEXT,
    is_nullable INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS relationships (
    entity_name TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    target TEXT NOT NULL
);
"""

# Used by load() only — connecting to an already-populated db (e.g. the API
# opening the file a prior `task ingest:run` wrote) must never wipe it, so
# the constructor uses _CREATE_SCHEMA (idempotent, additive) instead.
_CLEAR_SCHEMA = """
DELETE FROM attributes;
DELETE FROM relationships;
DELETE FROM entities;
"""


def _bare(name: str) -> str:
    return name.split(":", 1)[-1]


class SQLiteStructuredIndex:
    """Implements the `StructuredIndex` Protocol (app/domain/ports.py)."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        # check_same_thread=False is required since FastAPI runs each sync
        # handler in a threadpool worker thread (a different thread per
        # request) — but sqlite3.Connection is not safe for *concurrent*
        # use from multiple threads even with that flag: two overlapping
        # execute()/fetchall() calls on the same connection can interleave
        # and return corrupted rows (found live — a Playwright run firing
        # concurrent /evaluate and /query requests against the same
        # dev-server process produced Attribute rows with name=None).
        # The lock below serializes all access, closing that gap. RLock
        # (not Lock) because get_attributes/get_relationships/traverse each
        # call the internal _entity_exists() helper, which also acquires it.
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.executescript(_CREATE_SCHEMA)
        self._conn.commit()
        self._adjacency: dict[str, list[tuple[str, Relationship]]] = defaultdict(list)
        self._rebuild_adjacency()

    def _rebuild_adjacency(self) -> None:
        """Reconstruct the in-memory traversal adjacency from whatever's
        already persisted — needed when connecting to an existing db file,
        since the adjacency cache itself isn't persisted (ADR-0009: plain
        adjacency dict, not a stored structure)."""
        with self._lock:
            by_bare: dict[str, list[str]] = defaultdict(list)
            for (name,) in self._conn.execute("SELECT name FROM entities").fetchall():
                by_bare[_bare(name)].append(name)

            grouped: dict[tuple[str, str, str], list[str]] = defaultdict(list)
            rows = self._conn.execute(
                "SELECT entity_name, name, kind, target FROM relationships"
            ).fetchall()
            for entity_name, name, kind, target in rows:
                grouped[(entity_name, name, kind)].append(target)

            for (entity_name, name, kind), targets in grouped.items():
                rel = Relationship(name=name, kind=kind, targets=tuple(targets))  # type: ignore[arg-type]
                for target in targets:
                    resolved = self._resolve_target(entity_name, target, by_bare)
                    self._adjacency[entity_name].append((resolved, rel))

    def load(self, entities: Iterable[Entity]) -> None:
        """Idempotent clear-then-write (ADR-0002)."""
        with self._lock:
            self._conn.executescript(_CLEAR_SCHEMA)
            self._adjacency = defaultdict(list)

            entities = list(entities)
            by_bare: dict[str, list[str]] = defaultdict(list)
            for entity in entities:
                by_bare[_bare(entity.name)].append(entity.name)

            for entity in entities:
                self._conn.execute(
                    "INSERT INTO entities (name, description, source_path) VALUES (?, ?, ?)",
                    (entity.name, entity.description, entity.source_path),
                )
                self._conn.executemany(
                    "INSERT INTO attributes (entity_name, name, data_type, description, is_nullable) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [
                        (entity.name, a.name, a.data_type, a.description, int(a.is_nullable))
                        for a in entity.attributes
                    ],
                )
                for rel in entity.relationships:
                    for target in rel.targets:
                        self._conn.execute(
                            "INSERT INTO relationships (entity_name, name, kind, target) VALUES (?, ?, ?, ?)",
                            (entity.name, rel.name, rel.kind, target),
                        )
                        resolved = self._resolve_target(entity.name, target, by_bare)
                        self._adjacency[entity.name].append((resolved, rel))
            self._conn.commit()

    @staticmethod
    def _resolve_target(source: str, target: str, by_bare: dict[str, list[str]]) -> str:
        """Relationship targets are bare CDM names (e.g. "Contact"); resolve
        to a namespaced entity name, preferring the source's own namespace
        when a bare name is ambiguous across namespaces. Falls back to the
        bare name unresolved (a dangling reference — surfaced by Validation)."""
        candidates = by_bare.get(_bare(target), [])
        source_namespace = source.split(":", 1)[0]
        same_namespace = [c for c in candidates if c.startswith(f"{source_namespace}:")]
        if same_namespace:
            return same_namespace[0]
        if candidates:
            return candidates[0]
        return target

    def list_entities(self) -> tuple[str, ...]:
        with self._lock:
            rows = self._conn.execute("SELECT name FROM entities ORDER BY name").fetchall()
            return tuple(r[0] for r in rows)

    def _entity_exists(self, entity: str) -> bool:
        with self._lock:
            return (
                self._conn.execute("SELECT 1 FROM entities WHERE name = ?", (entity,)).fetchone()
                is not None
            )

    def get_attributes(self, entity: str) -> AttributesResult:
        with self._lock:
            if not self._entity_exists(entity):
                return AttributesResult(entity=entity, found=False)
            rows = self._conn.execute(
                "SELECT name, data_type, description, is_nullable FROM attributes WHERE entity_name = ?",
                (entity,),
            ).fetchall()
            attributes = tuple(
                Attribute(name=r[0], data_type=r[1], description=r[2], is_nullable=bool(r[3]))
                for r in rows
            )
            return AttributesResult(entity=entity, found=True, attributes=attributes)

    def get_relationships(self, entity: str) -> RelationshipsResult:
        with self._lock:
            if not self._entity_exists(entity):
                return RelationshipsResult(entity=entity, found=False)
            rows = self._conn.execute(
                "SELECT name, kind, target FROM relationships WHERE entity_name = ?", (entity,)
            ).fetchall()
            grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
            for name, kind, target in rows:
                grouped[(name, kind)].append(target)
            relationships = tuple(
                Relationship(name=name, kind=kind, targets=tuple(targets))  # type: ignore[arg-type]
                for (name, kind), targets in grouped.items()
            )
            return RelationshipsResult(entity=entity, found=True, relationships=relationships)

    def traverse(self, entity: str, target: str | None = None, max_depth: int = 2) -> TraversalResult:
        with self._lock:
            if not self._entity_exists(entity):
                return TraversalResult(source_entity=entity, found=False)

            target_bare = _bare(target) if target else None
            visited = {entity}
            queue: deque[tuple[str, tuple[str, ...], tuple[Relationship, ...]]] = deque(
                [(entity, (entity,), ())]
            )
            while queue:
                current, path, rels = queue.popleft()
                if len(path) - 1 >= max_depth:
                    continue
                for neighbor, rel in self._adjacency.get(current, ()):
                    new_path = (*path, neighbor)
                    new_rels = (*rels, rel)
                    if target is not None and (neighbor == target or _bare(neighbor) == target_bare):
                        return TraversalResult(
                            source_entity=entity, found=True, path=new_path, relationships=new_rels
                        )
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, new_path, new_rels))
            return TraversalResult(source_entity=entity, found=False)
