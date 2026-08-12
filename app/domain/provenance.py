"""Per-ingestion-run provenance — ADR-0015.

Deliberately no per-field version tracking: one `source_commit` per run
is enough to audit a static, one-shot ingestion.
"""

from pydantic import BaseModel, ConfigDict

from app.domain.models import Entity


class IngestionRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_commit: str
    entities: tuple[Entity, ...]
