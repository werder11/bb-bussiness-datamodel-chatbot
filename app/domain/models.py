"""Canonical CDM Semantic Model — the vendor-independent domain core.

Frozen (immutable) per ADR-0021: instances are derived once at ingestion
time and never mutated, so an accidental in-place edit becomes a hard
error rather than a silent data-integrity bug.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Trait(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    value: str | None = None


class Attribute(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    data_type: str
    description: str | None = None
    is_nullable: bool = True


class Relationship(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    # One target for "single"/"party"; 2+ for "polymorphic" (e.g. the
    # Customer group resolving to either Account or Contact — FINDINGS §5).
    targets: tuple[str, ...]
    kind: Literal["single", "polymorphic", "party"]


class Entity(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str  # namespaced, e.g. "banking:Account" vs "crmCommon:Account" — ADR-0007
    description: str | None = None
    attributes: tuple[Attribute, ...] = ()
    relationships: tuple[Relationship, ...] = ()
    traits: tuple[Trait, ...] = ()
    source_path: str  # provenance — ADR-0015
