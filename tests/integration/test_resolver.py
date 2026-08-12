"""Component Integration tests — golden tests for the Resolver against fixture
`.cdm.json` files, one per structural pattern found in FINDINGS §5 (ADR-0007,
ADR-0018). Expected outputs are asserted directly as Entity/Relationship
values rather than a parallel JSON file — one less format to keep in sync.
"""

from pathlib import Path

from app.domain.models import Attribute, Relationship
from app.ingestion.resolver import (
    ResolveError,
    discover_entities,
    resolve_all,
    resolve_entity,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestSingleHopExtends:
    def test_child_inherits_base_attributes(self):
        discovered = [
            ("BusinessParty", FIXTURES / "single_hop_extends" / "base.cdm.json", "test"),
            ("IndividualParty", FIXTURES / "single_hop_extends" / "child.cdm.json", "test"),
        ]
        entities, errors = resolve_all(discovered)

        assert errors == []
        child = next(e for e in entities if e.name == "test:IndividualParty")
        names = {a.name for a in child.attributes}
        assert names == {"partyId", "fullName"}, "child must inherit base's attribute plus its own"


class TestAttributeGroupReference:
    def test_multiple_groups_in_one_file_are_flattened(self):
        result = resolve_entity(
            "Branch", FIXTURES / "attribute_group_reference" / "entity.cdm.json", "test"
        )
        assert not isinstance(result, ResolveError)
        names = {a.name for a in result.attributes}
        assert names == {"branchId", "branchName"}


class TestPolymorphicCustomer:
    def test_customer_relationship_has_both_options_as_targets(self):
        result = resolve_entity(
            "Case", FIXTURES / "polymorphic_customer" / "entity.cdm.json", "test"
        )
        assert not isinstance(result, ResolveError)
        assert result.relationships == (
            Relationship(name="customer", targets=("Contact", "Account"), kind="polymorphic"),
        )


class TestPolymorphicViaSource:
    """The real Fi_card.cdm.json wraps its polymorphic Account/Contact choice
    inside `entity.source` rather than `entity.entityReference` — a distinct
    shape from TestPolymorphicCustomer, discovered by running the resolver
    against the real corpus (see resolver.py's `_extract_ref` docstring)."""

    def test_polymorphic_nested_under_source_key(self):
        result = resolve_entity(
            "FICard", FIXTURES / "polymorphic_via_source" / "entity.cdm.json", "test"
        )
        assert not isinstance(result, ResolveError)
        assert result.relationships == (
            Relationship(name="Cardholder", targets=("Account", "Contact"), kind="polymorphic"),
        )


class TestRelationshipEntityPartyPattern:
    def test_contact_from_and_to_resolve_as_party_relationships(self):
        result = resolve_entity(
            "Relationship", FIXTURES / "relationship_entity" / "entity.cdm.json", "test"
        )
        assert not isinstance(result, ResolveError)
        assert set(result.relationships) == {
            Relationship(name="ContactFrom", targets=("Contact",), kind="party"),
            Relationship(name="ContactTo", targets=("Contact",), kind="party"),
        }


class TestAccountContactCollision:
    def test_same_entity_name_different_namespace_stays_distinct(self):
        discovered = [
            (
                "Account",
                FIXTURES / "account_contact_collision" / "banking_account.cdm.json",
                "banking",
            ),
            (
                "Account",
                FIXTURES / "account_contact_collision" / "crm_account.cdm.json",
                "crmCommon",
            ),
        ]
        entities, errors = resolve_all(discovered)

        assert errors == []
        names = {e.name for e in entities}
        assert names == {"banking:Account", "crmCommon:Account"}

        banking = next(e for e in entities if e.name == "banking:Account")
        crm = next(e for e in entities if e.name == "crmCommon:Account")
        assert banking.attributes == (
            Attribute(name="accountId", data_type="entityId", description="Unique identifier of the account.", is_nullable=False),
        )
        # crmCommon:Account extends an unresolvable "base_Account/Account" shape
        # (not a literal file) — it keeps only its own directly-defined attribute,
        # per ADR-0007's documented (not silently approximated) limitation.
        assert crm.relationships == (
            Relationship(name="originatingLead", targets=("Lead",), kind="single"),
        )


class TestResolveEntityErrors:
    def test_missing_entity_name_in_file_returns_resolve_error(self):
        result = resolve_entity(
            "DoesNotExist", FIXTURES / "attribute_group_reference" / "entity.cdm.json", "test"
        )
        assert isinstance(result, ResolveError)
        assert "DoesNotExist" in result.reason

    def test_missing_file_returns_resolve_error_not_exception(self):
        result = resolve_entity("Ghost", FIXTURES / "does_not_exist.cdm.json", "test")
        assert isinstance(result, ResolveError)

    def test_resolve_all_skips_bad_entity_and_continues(self):
        discovered = [
            ("Ghost", FIXTURES / "does_not_exist.cdm.json", "test"),
            ("Branch", FIXTURES / "attribute_group_reference" / "entity.cdm.json", "test"),
        ]
        entities, errors = resolve_all(discovered)
        assert len(errors) == 1
        assert len(entities) == 1
        assert entities[0].name == "test:Branch"


class TestDiscoverEntities:
    def test_relative_entity_path_resolves_against_manifest_dir(self, tmp_path):
        manifest_dir = tmp_path / "RetailBankingCoreDataModel"
        manifest_dir.mkdir()
        manifest = manifest_dir / "manifest.cdm.json"
        manifest.write_text('{"entities": [{"entityName": "Account", "entityPath": "Account.cdm.json/Account"}]}')

        discovered = discover_entities(manifest, tmp_path, "banking")
        assert discovered == [("Account", manifest_dir / "Account.cdm.json", "banking")]

    def test_absolute_entity_path_resolves_against_corpus_root(self, tmp_path):
        manifest_dir = tmp_path / "manifests"
        manifest_dir.mkdir()
        manifest = manifest_dir / "manifest.cdm.json"
        manifest.write_text(
            '{"entities": [{"entityName": "Address", "entityPath": "/core/applicationCommon/Address.cdm.json/Address"}]}'
        )

        discovered = discover_entities(manifest, tmp_path, "crmCommon")
        assert discovered == [
            ("Address", tmp_path / "core" / "applicationCommon" / "Address.cdm.json", "crmCommon")
        ]
