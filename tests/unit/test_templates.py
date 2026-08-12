"""Component/Unit tests for deterministic answer templates — ADR-0016."""

from app.domain.models import Attribute, Relationship
from app.domain.templates import (
    render_attributes,
    render_relationship,
    render_traversal,
)


class TestRenderAttributes:
    def test_lists_each_attribute(self):
        answer = render_attributes(
            "banking:Account",
            (
                Attribute(name="accountId", data_type="entityId", is_nullable=False),
                Attribute(name="balance", data_type="decimal"),
            ),
        )
        assert "banking:Account" in answer
        assert "accountId" in answer
        assert "balance" in answer

    def test_empty_attributes_says_so_without_crashing(self):
        answer = render_attributes("banking:Bare", ())
        assert "no recorded attributes" in answer


class TestRenderRelationship:
    def test_lists_each_relationship_with_targets_and_kind(self):
        answer = render_relationship(
            "banking:Account",
            (Relationship(name="customer", targets=("Account", "Contact"), kind="polymorphic"),),
        )
        assert "customer" in answer
        assert "Account/Contact" in answer
        assert "polymorphic" in answer

    def test_empty_relationships_says_so_without_crashing(self):
        answer = render_relationship("banking:Bare", ())
        assert "no recorded relationships" in answer


class TestRenderTraversal:
    def test_renders_full_path_and_relationships_used(self):
        answer = render_traversal(
            "crmCommon:Contact",
            ("crmCommon:Contact", "crmCommon:Customer", "crmCommon:Organization"),
            (Relationship(name="customer", targets=("crmCommon:Organization",), kind="polymorphic"),),
        )
        assert "crmCommon:Contact" in answer
        assert "crmCommon:Organization" in answer
        assert "customer" in answer

    def test_short_path_reports_not_found(self):
        answer = render_traversal("crmCommon:Contact", ("crmCommon:Contact",), ())
        assert "No path was found" in answer
