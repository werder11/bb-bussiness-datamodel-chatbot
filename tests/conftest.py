"""Shared fixtures for the System and Acceptance test levels (ADR-0018).

`api_client` wires a real FastAPI app to a real (small, in-memory) SQLite
index and a real (fake-embedded) Chroma index via `dependency_overrides` —
never through `lifespan`, so no live sentence-transformers model or
Anthropic client is ever constructed (ADR-0019's fast-gate requirement).
"""

import pytest
from fastapi.testclient import TestClient

from app.adapters.structured_index_sqlite import SQLiteStructuredIndex
from app.adapters.vector_index_chroma import ChromaVectorIndex
from app.api import main as api_main
from app.domain.models import Attribute, Entity, Relationship


def _fake_embedder(texts):
    # 4D one-hot: the 4th axis is reserved for "none of the known topics",
    # kept orthogonal to the other three so an off-topic query gets exactly
    # zero cosine similarity against every stored entity chunk, not just a
    # low one — deliberately, so the Grounding Guard cutoff test is exact.
    vectors = []
    for text in texts:
        lowered = text.lower()
        if "account" in lowered:
            vectors.append([1.0, 0.0, 0.0, 0.0])
        elif "contact" in lowered:
            vectors.append([0.0, 1.0, 0.0, 0.0])
        elif "organization" in lowered:
            vectors.append([0.0, 0.0, 1.0, 0.0])
        else:
            vectors.append([0.0, 0.0, 0.0, 1.0])
    return vectors


FIXTURE_CORPUS = (
    Entity(
        name="banking:Account",
        description="A bank account.",
        attributes=(Attribute(name="accountId", data_type="entityId", is_nullable=False),),
        relationships=(Relationship(name="customer", targets=("Account", "Contact"), kind="polymorphic"),),
        source_path="banking/Account.cdm.json",
    ),
    Entity(
        name="crmCommon:Contact",
        description="A contact person.",
        attributes=(Attribute(name="contactId", data_type="entityId", is_nullable=False),),
        relationships=(Relationship(name="organization", targets=("Organization",), kind="single"),),
        source_path="crm/Contact.cdm.json",
    ),
    Entity(
        name="crmCommon:Organization",
        description="A business organization.",
        attributes=(Attribute(name="organizationId", data_type="entityId", is_nullable=False),),
        source_path="crm/Organization.cdm.json",
    ),
)


class FakeLLM:
    def __init__(self, response: str = "a generated answer") -> None:
        self.response = response
        self.last_call = None

    def generate(self, question, context):
        self.last_call = (question, context)
        return self.response


@pytest.fixture
def api_client(tmp_path):
    structured = SQLiteStructuredIndex(db_path=":memory:")
    structured.load(FIXTURE_CORPUS)
    vector = ChromaVectorIndex(persist_path=tmp_path / "chroma", embedder=_fake_embedder)
    vector.load(FIXTURE_CORPUS)
    llm = FakeLLM()
    known_entities = frozenset(structured.list_entities())

    api_main.app.dependency_overrides[api_main.get_structured_index] = lambda: structured
    api_main.app.dependency_overrides[api_main.get_vector_index] = lambda: vector
    api_main.app.dependency_overrides[api_main.get_llm] = lambda: llm
    api_main.app.dependency_overrides[api_main.get_known_entities] = lambda: known_entities

    try:
        yield TestClient(api_main.app)
    finally:
        api_main.app.dependency_overrides.clear()
