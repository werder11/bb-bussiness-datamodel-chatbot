"""Component/Unit tests for the Canonical Model — ADR-0018.

Data-driven where the cases naturally form a table; example-based for
the one-off frozen-instance/validation-error checks that don't.
"""

import pytest
from pydantic import ValidationError

from app.domain.models import Attribute, Entity, Relationship
from app.domain.provenance import IngestionRun


def make_entity(**overrides) -> Entity:
    defaults = {
        "name": "banking:Account",
        "description": "A banking account.",
        "attributes": (Attribute(name="accountId", data_type="entityId"),),
        "relationships": (),
        "traits": (),
        "source_path": "FinancialServices/RetailBankingCoreDataModel/Account.cdm.json",
    }
    defaults.update(overrides)
    return Entity(**defaults)


class TestAttribute:
    def test_minimal_valid_attribute(self):
        attr = Attribute(name="accountId", data_type="entityId")
        assert attr.name == "accountId"
        assert attr.is_nullable is True
        assert attr.description is None

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            Attribute(data_type="string")  # type: ignore[call-arg]

    def test_frozen_mutation_raises(self):
        attr = Attribute(name="accountId", data_type="entityId")
        with pytest.raises(ValidationError):
            attr.name = "other"  # type: ignore[misc]


class TestRelationship:
    @pytest.mark.parametrize(
        "kind,targets",
        [
            ("single", ("crmCommon:Lead",)),
            ("party", ("banking:Account",)),
            ("polymorphic", ("banking:Account", "crmCommon:Contact")),
        ],
    )
    def test_valid_kinds(self, kind, targets):
        rel = Relationship(name="customer", targets=targets, kind=kind)
        assert rel.kind == kind
        assert rel.targets == targets

    def test_invalid_kind_rejected(self):
        with pytest.raises(ValidationError):
            Relationship(name="customer", targets=("banking:Account",), kind="bogus")  # type: ignore[arg-type]


class TestEntity:
    def test_minimal_valid_entity(self):
        entity = make_entity()
        assert entity.name == "banking:Account"
        assert len(entity.attributes) == 1

    def test_frozen_mutation_raises(self):
        entity = make_entity()
        with pytest.raises(ValidationError):
            entity.name = "other"  # type: ignore[misc]

    def test_missing_source_path_raises(self):
        with pytest.raises(ValidationError):
            Entity(name="banking:Account")  # type: ignore[call-arg]

    def test_defaults_are_empty_tuples(self):
        entity = make_entity(attributes=(), relationships=(), traits=())
        assert entity.attributes == ()
        assert entity.relationships == ()
        assert entity.traits == ()


class TestIngestionRun:
    def test_holds_entities_and_commit(self):
        run = IngestionRun(source_commit="abc123", entities=(make_entity(),))
        assert run.source_commit == "abc123"
        assert len(run.entities) == 1

    def test_frozen_mutation_raises(self):
        run = IngestionRun(source_commit="abc123", entities=())
        with pytest.raises(ValidationError):
            run.source_commit = "def456"  # type: ignore[misc]
