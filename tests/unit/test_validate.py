"""Component/Unit tests for the Validation Pass — ADR-0014, data-driven per ADR-0018."""

from app.domain.models import Attribute, Entity, Relationship
from app.ingestion.validate import validate


def entity(name: str, attrs=(), rels=(), source_path="x.cdm.json") -> Entity:
    return Entity(name=name, attributes=attrs, relationships=rels, source_path=source_path)


class TestDuplicateNames:
    def test_no_duplicates_in_clean_set(self):
        report = validate([entity("banking:Account"), entity("crmCommon:Account")], 2, 0)
        assert report.duplicate_names == ()

    def test_duplicate_name_flagged(self):
        report = validate([entity("banking:Account"), entity("banking:Account")], 2, 0)
        assert len(report.duplicate_names) == 1
        assert report.duplicate_names[0].name == "banking:Account"


class TestUnresolvedReferences:
    def test_relationship_to_known_entity_is_fine(self):
        entities = [
            entity(
                "banking:Account",
                attrs=(Attribute(name="accountId", data_type="entityId"),),
                rels=(Relationship(name="lead", targets=("crmCommon:Lead",), kind="single"),),
            ),
            entity("crmCommon:Lead", attrs=(Attribute(name="leadId", data_type="entityId"),)),
        ]
        report = validate(entities, 2, 0)
        assert report.unresolved_references == ()
        assert report.relationships_discovered == 1

    def test_relationship_to_unknown_entity_flagged(self):
        entities = [
            entity(
                "banking:Account",
                attrs=(Attribute(name="accountId", data_type="entityId"),),
                rels=(Relationship(name="lead", targets=("crmCommon:Lead",), kind="single"),),
            ),
        ]
        report = validate(entities, 1, 0)
        assert len(report.unresolved_references) == 1
        assert report.unresolved_references[0].target == "crmCommon:Lead"

    def test_polymorphic_relationship_all_targets_checked(self):
        entities = [
            entity(
                "banking:Case",
                rels=(
                    Relationship(
                        name="customer", targets=("banking:Account", "crmCommon:Contact"), kind="polymorphic"
                    ),
                ),
            ),
            entity("banking:Account", attrs=(Attribute(name="accountId", data_type="entityId"),)),
            # crmCommon:Contact deliberately absent
        ]
        report = validate(entities, 2, 0)
        assert len(report.unresolved_references) == 1
        assert report.unresolved_references[0].target == "crmCommon:Contact"


class TestMissingIdentifiers:
    def test_entity_with_id_attribute_passes(self):
        report = validate([entity("banking:Account", attrs=(Attribute(name="accountId", data_type="entityId"),))], 1, 0)
        assert report.missing_identifiers == ()

    def test_entity_without_id_attribute_flagged(self):
        report = validate([entity("banking:Branch", attrs=(Attribute(name="branchName", data_type="string"),))], 1, 0)
        assert len(report.missing_identifiers) == 1
        assert report.missing_identifiers[0].entity == "banking:Branch"


class TestSummaryFormat:
    def test_matches_adr_0014_example_shape(self):
        report = validate(
            [entity("banking:Account", attrs=(Attribute(name="accountId", data_type="entityId"),))],
            entities_discovered=2,
            entities_skipped=1,
        )
        summary = report.summary()
        assert "2 entities discovered, 1 resolved, 1 skipped" in summary
        assert "0 relationships discovered, 0 unresolved references" in summary
