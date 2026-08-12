"""Component Integration test for the ingestion CLI wiring (`app/ingestion/run.py`).

Exercises Discover -> Resolve -> Validate -> Project against a tiny,
self-contained fixture corpus (not the real cdm-source/ tree, and not the
real sentence-transformers embedder) — this is a wiring test, not a
re-test of the Resolver's own parsing logic (already covered by
tests/integration/test_resolver.py's golden fixtures).
"""

import json

import app.ingestion.run as run_module


def _fake_embedder(texts):
    return [[1.0, 0.0] for _ in texts]


def _write_fixture_corpus(tmp_path):
    banking_dir = tmp_path / "banking"
    banking_dir.mkdir()
    (banking_dir / "manifest.cdm.json").write_text(
        json.dumps({"entities": [{"entityName": "Account", "entityPath": "Account.cdm.json/Account"}]})
    )
    (banking_dir / "Account.cdm.json").write_text(
        json.dumps(
            {
                "definitions": [
                    {
                        "entityName": "Account",
                        "hasAttributes": [
                            {
                                "attributeGroupReference": {
                                    "members": [
                                        {"name": "accountId", "dataType": "entityId", "isNullable": False}
                                    ]
                                }
                            }
                        ],
                    }
                ]
            }
        )
    )

    common_dir = tmp_path / "common"
    common_dir.mkdir()
    (common_dir / "manifest.cdm.json").write_text(
        json.dumps({"entities": [{"entityName": "Contact", "entityPath": "Contact.cdm.json/Contact"}]})
    )
    (common_dir / "Contact.cdm.json").write_text(
        json.dumps(
            {
                "definitions": [
                    {
                        "entityName": "Contact",
                        "hasAttributes": [
                            {
                                "attributeGroupReference": {
                                    "members": [
                                        {"name": "contactId", "dataType": "entityId", "isNullable": False}
                                    ]
                                }
                            }
                        ],
                    }
                ]
            }
        )
    )

    return banking_dir / "manifest.cdm.json", common_dir / "manifest.cdm.json"


class TestRun:
    def test_full_ingestion_populates_both_indexes(self, tmp_path, monkeypatch):
        banking_manifest, common_manifest = _write_fixture_corpus(tmp_path)
        monkeypatch.setattr(run_module, "_CORPUS_ROOT", tmp_path)
        monkeypatch.setattr(run_module, "_BANKING_MANIFEST", banking_manifest)
        monkeypatch.setattr(run_module, "_COMMON_MANIFEST", common_manifest)
        monkeypatch.setattr(run_module, "_DB_PATH", str(tmp_path / "test.db"))
        monkeypatch.setattr(run_module, "_CHROMA_PATH", str(tmp_path / "chroma"))

        structured, vector = run_module.run(embedder=_fake_embedder)

        assert structured.list_entities() == ("banking:Account", "crmCommon:Contact")
        assert structured.get_attributes("banking:Account").found is True
        assert vector.semantic_search("account", k=5).hits

    def test_clean_only_clears_without_ingesting(self, tmp_path, monkeypatch):
        banking_manifest, common_manifest = _write_fixture_corpus(tmp_path)
        monkeypatch.setattr(run_module, "_CORPUS_ROOT", tmp_path)
        monkeypatch.setattr(run_module, "_BANKING_MANIFEST", banking_manifest)
        monkeypatch.setattr(run_module, "_COMMON_MANIFEST", common_manifest)
        monkeypatch.setattr(run_module, "_DB_PATH", str(tmp_path / "test.db"))
        monkeypatch.setattr(run_module, "_CHROMA_PATH", str(tmp_path / "chroma"))

        run_module.run(embedder=_fake_embedder)
        structured, _vector = run_module.run(clean_only=True, embedder=_fake_embedder)

        assert structured.list_entities() == ()
