"""Ingestion CLI — `task ingest:run` / `task ingest:clean`.

Wires Discover -> Resolve -> Validate -> Project end to end
(`docs/design/workflows.md#ingestion-workflow`, ADR-0002): both indexes are
cleared and rewritten from scratch on every run, so re-running is always
safe.
"""

import argparse
import os
from pathlib import Path

from app.adapters.structured_index_sqlite import SQLiteStructuredIndex
from app.adapters.vector_index_chroma import ChromaVectorIndex, Embedder
from app.ingestion.resolver import discover_entities, resolve_all
from app.ingestion.validate import validate

_CORPUS_ROOT = Path("cdm-source/schemaDocuments")
_BANKING_MANIFEST = (
    _CORPUS_ROOT
    / "FinancialServices/RetailBankingCoreDataModel/RetailBankingCoreDataModel.manifest.cdm.json"
)
_COMMON_MANIFEST = _CORPUS_ROOT / "manifests/bankingAccelerator.manifest.cdm.json"

_DB_PATH = os.environ.get("CDM_DB_PATH", "cdm.db")
_CHROMA_PATH = os.environ.get("CDM_CHROMA_PATH", "chroma_data")


def run(
    *, clean_only: bool = False, embedder: Embedder | None = None
) -> tuple[SQLiteStructuredIndex, ChromaVectorIndex]:
    structured = SQLiteStructuredIndex(db_path=_DB_PATH)
    vector = ChromaVectorIndex(persist_path=_CHROMA_PATH, embedder=embedder)

    if clean_only:
        structured.load([])
        vector.load([])
        print("Cleared structured and semantic indexes.")
        return structured, vector

    discovered = discover_entities(_BANKING_MANIFEST, _CORPUS_ROOT, "banking") + discover_entities(
        _COMMON_MANIFEST, _CORPUS_ROOT, "crmCommon"
    )
    entities, errors = resolve_all(discovered)
    report = validate(entities, entities_discovered=len(discovered), entities_skipped=len(errors))

    structured.load(entities)
    vector.load(entities)

    print(report.summary())
    for error in errors:
        print(f"  skipped {error.entity_name} ({error.source_path}): {error.reason}")

    return structured, vector


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CDM ingestion pipeline.")
    parser.add_argument(
        "--clean-only", action="store_true", help="Clear both indexes without re-ingesting."
    )
    args = parser.parse_args()
    run(clean_only=args.clean_only)


if __name__ == "__main__":
    main()
