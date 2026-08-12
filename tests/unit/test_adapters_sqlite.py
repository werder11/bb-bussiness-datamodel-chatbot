"""Component/Unit tests for SQLiteStructuredIndex — ADR-0004, ADR-0009."""

from concurrent.futures import ThreadPoolExecutor

from app.adapters.structured_index_sqlite import SQLiteStructuredIndex
from app.domain.models import Attribute, Entity, Relationship


def build_index() -> SQLiteStructuredIndex:
    idx = SQLiteStructuredIndex(":memory:")
    idx.load(
        [
            Entity(
                name="banking:Account",
                description="A bank account.",
                attributes=(Attribute(name="accountId", data_type="entityId", is_nullable=False),),
                relationships=(
                    Relationship(name="lead", targets=("Lead",), kind="single"),
                    Relationship(
                        name="customer", targets=("Account", "Contact"), kind="polymorphic"
                    ),
                ),
                source_path="banking/Account.cdm.json",
            ),
            Entity(
                name="crmCommon:Lead",
                description="A sales lead.",
                attributes=(Attribute(name="leadId", data_type="entityId", is_nullable=False),),
                source_path="crm/Lead.cdm.json",
            ),
            Entity(
                name="crmCommon:Contact",
                description="A contact person.",
                attributes=(Attribute(name="contactId", data_type="entityId", is_nullable=False),),
                relationships=(
                    Relationship(name="organization", targets=("Organization",), kind="single"),
                ),
                source_path="crm/Contact.cdm.json",
            ),
            Entity(
                name="crmCommon:Organization",
                description="A business organization.",
                attributes=(Attribute(name="organizationId", data_type="entityId", is_nullable=False),),
                source_path="crm/Organization.cdm.json",
            ),
        ]
    )
    return idx


class TestReconnectPreservesData:
    def test_opening_an_existing_populated_db_file_does_not_wipe_it(self, tmp_path):
        db_path = tmp_path / "reconnect.db"
        writer = SQLiteStructuredIndex(db_path)
        writer.load(
            [
                Entity(
                    name="banking:Account",
                    attributes=(Attribute(name="accountId", data_type="entityId"),),
                    relationships=(Relationship(name="lead", targets=("Lead",), kind="single"),),
                    source_path="banking/Account.cdm.json",
                ),
                Entity(
                    name="crmCommon:Lead",
                    attributes=(Attribute(name="leadId", data_type="entityId"),),
                    source_path="crm/Lead.cdm.json",
                ),
            ]
        )
        del writer  # simulates the ingestion process exiting

        reopened = SQLiteStructuredIndex(db_path)

        assert reopened.list_entities() == ("banking:Account", "crmCommon:Lead")
        assert reopened.get_attributes("banking:Account").found is True

    def test_traversal_adjacency_survives_a_reconnect(self, tmp_path):
        db_path = tmp_path / "reconnect_traverse.db"
        writer = SQLiteStructuredIndex(db_path)
        writer.load(
            [
                Entity(
                    name="banking:Account",
                    relationships=(Relationship(name="lead", targets=("Lead",), kind="single"),),
                    source_path="banking/Account.cdm.json",
                ),
                Entity(name="crmCommon:Lead", source_path="crm/Lead.cdm.json"),
            ]
        )
        del writer

        reopened = SQLiteStructuredIndex(db_path)
        result = reopened.traverse("banking:Account", target="crmCommon:Lead", max_depth=1)

        assert result.found is True
        assert result.path == ("banking:Account", "crmCommon:Lead")


class TestListEntities:
    def test_returns_all_loaded_entity_names_sorted(self):
        idx = build_index()
        assert idx.list_entities() == (
            "banking:Account",
            "crmCommon:Contact",
            "crmCommon:Lead",
            "crmCommon:Organization",
        )

    def test_empty_index_returns_empty_tuple(self):
        idx = SQLiteStructuredIndex(":memory:")
        assert idx.list_entities() == ()


class TestGetAttributes:
    def test_known_entity(self):
        idx = build_index()
        result = idx.get_attributes("banking:Account")
        assert result.found is True
        assert result.attributes == (
            Attribute(name="accountId", data_type="entityId", is_nullable=False),
        )

    def test_unknown_entity(self):
        idx = build_index()
        result = idx.get_attributes("banking:Nonexistent")
        assert result.found is False
        assert result.attributes == ()


class TestGetRelationships:
    def test_single_hop_grouped_by_relationship(self):
        idx = build_index()
        result = idx.get_relationships("banking:Account")
        assert result.found is True
        by_name = {r.name: r for r in result.relationships}
        assert set(by_name["customer"].targets) == {"Account", "Contact"}
        assert by_name["customer"].kind == "polymorphic"
        assert by_name["lead"].targets == ("Lead",)

    def test_unknown_entity(self):
        idx = build_index()
        result = idx.get_relationships("banking:Ghost")
        assert result.found is False


class TestTraverse:
    def test_direct_hop_found(self):
        idx = build_index()
        result = idx.traverse("banking:Account", target="crmCommon:Lead", max_depth=2)
        assert result.found is True
        assert result.path == ("banking:Account", "crmCommon:Lead")

    def test_two_hop_found_within_depth(self):
        idx = build_index()
        # banking:Account -> crmCommon:Contact (polymorphic "customer") -> crmCommon:Organization
        result = idx.traverse("banking:Account", target="crmCommon:Organization", max_depth=2)
        assert result.found is True
        assert result.path == ("banking:Account", "crmCommon:Contact", "crmCommon:Organization")
        assert len(result.relationships) == 2

    def test_beyond_depth_not_found(self):
        idx = build_index()
        result = idx.traverse("banking:Account", target="crmCommon:Organization", max_depth=1)
        assert result.found is False

    def test_unresolvable_target_not_found(self):
        idx = build_index()
        result = idx.traverse("banking:Account", target="banking:DoesNotExist", max_depth=2)
        assert result.found is False

    def test_unknown_source_entity(self):
        idx = build_index()
        result = idx.traverse("banking:Ghost", target="crmCommon:Lead")
        assert result.found is False


class TestIdempotentLoad:
    def test_reload_does_not_accumulate_duplicates(self):
        idx = build_index()
        idx.load(
            [
                Entity(
                    name="banking:Account",
                    attributes=(Attribute(name="accountId", data_type="entityId"),),
                    source_path="banking/Account.cdm.json",
                )
            ]
        )
        result = idx.get_attributes("banking:Account")
        assert len(result.attributes) == 1
        # entities from the first load() are gone after the second (clear-then-write)
        assert idx.get_attributes("crmCommon:Lead").found is False


class TestConcurrentAccess:
    """Regression for a real bug: FastAPI runs each request on a threadpool
    worker thread, and this adapter shares one sqlite3.Connection across
    all of them (check_same_thread=False). Without a lock serializing
    access, concurrent execute()/fetchall() calls on that shared connection
    interleaved and produced corrupted rows — found live via a Playwright
    run that fired concurrent /query and /evaluate requests and got back
    an Attribute with name=None. The lock in __init__ fixes it; this test
    hammers the adapter from many threads to catch a regression if it's
    ever removed."""

    def test_concurrent_reads_never_return_corrupted_rows(self):
        idx = build_index()

        def read_once(_: int) -> bool:
            attrs = idx.get_attributes("banking:Account")
            rels = idx.get_relationships("crmCommon:Contact")
            traversal = idx.traverse("banking:Account", target="crmCommon:Organization")
            return (
                attrs.found
                and all(a.name is not None and a.data_type is not None for a in attrs.attributes)
                and rels.found
                and all(r.name is not None for r in rels.relationships)
                and traversal.found
            )

        with ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(read_once, range(200)))

        assert all(results)
