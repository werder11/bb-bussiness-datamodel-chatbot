"""Component/Unit tests for ChromaVectorIndex — ADR-0023.

Chroma itself runs for real (local, no network); the embedder is a fake,
deterministic function so these stay fast/free unit tests per ADR-0018 —
no `sentence-transformers` model download.
"""

from app.adapters.vector_index_chroma import ChromaVectorIndex, entity_to_chunk
from app.domain.models import Attribute, Entity


def fake_embedder(texts):
    """Deterministic 3D one-hot-ish embedding keyed on document content, so
    cosine similarity gives a predictable, exact nearest match in tests."""
    vectors = []
    for text in texts:
        lowered = text.lower()
        if "account" in lowered:
            vectors.append([1.0, 0.0, 0.0])
        elif "contact" in lowered:
            vectors.append([0.0, 1.0, 0.0])
        else:
            vectors.append([0.0, 0.0, 1.0])
    return vectors


def build_index(tmp_path) -> ChromaVectorIndex:
    return ChromaVectorIndex(persist_path=tmp_path / "chroma", embedder=fake_embedder)


ACCOUNT = Entity(
    name="banking:Account",
    description="A bank account.",
    attributes=(Attribute(name="accountId", data_type="entityId"),),
    source_path="banking/Account.cdm.json",
)
CONTACT = Entity(
    name="crmCommon:Contact",
    description="A contact person.",
    attributes=(Attribute(name="contactId", data_type="entityId"),),
    source_path="crm/Contact.cdm.json",
)


class TestChunking:
    def test_one_chunk_per_entity_includes_name_description_attrs_rels(self):
        chunk = entity_to_chunk(ACCOUNT)
        assert "banking:Account" in chunk
        assert "A bank account." in chunk
        assert "accountId" in chunk

    def test_entity_with_no_attributes_or_relationships(self):
        bare = Entity(name="banking:Bare", source_path="x.cdm.json")
        chunk = entity_to_chunk(bare)
        assert "Attributes: none" in chunk
        assert "Relationships: none" in chunk


class TestSemanticSearch:
    def test_empty_index_returns_no_hits(self, tmp_path):
        idx = build_index(tmp_path)
        result = idx.semantic_search("anything")
        assert result.hits == ()

    def test_query_matches_nearest_entity(self, tmp_path):
        idx = build_index(tmp_path)
        idx.load([ACCOUNT, CONTACT])

        result = idx.semantic_search("Tell me about an Account")
        assert result.hits[0].entity == "banking:Account"
        assert result.hits[0].score > 0.99  # identical fake vectors -> cosine similarity 1.0

    def test_k_limits_result_count(self, tmp_path):
        idx = build_index(tmp_path)
        idx.load([ACCOUNT, CONTACT])

        result = idx.semantic_search("Account", k=1)
        assert len(result.hits) == 1


class TestIdempotentLoad:
    def test_reload_replaces_not_accumulates(self, tmp_path):
        idx = build_index(tmp_path)
        idx.load([ACCOUNT, CONTACT])
        idx.load([ACCOUNT])

        result = idx.semantic_search("Contact", k=5)
        entity_ids = {hit.entity for hit in result.hits}
        assert "crmCommon:Contact" not in entity_ids
