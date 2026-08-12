"""Component/Unit tests for the query pipeline — `docs/design/workflows.md#query-workflow`.

All three ports are faked (structurally satisfying the Protocols in
app/domain/ports.py) so this exercises real routing/grounding logic
without any real DB, Chroma, or LLM call (ADR-0018's fast-gate requirement).
"""

from app.domain.models import Attribute, Relationship
from app.domain.pipeline import _REFUSAL, answer_query
from app.domain.ports import (
    AttributesResult,
    RelationshipsResult,
    SemanticHit,
    SemanticSearchResult,
    TraversalResult,
)


class FakeStructuredIndex:
    def __init__(self, attributes=None, relationships=None, traversals=None):
        self._attributes = attributes or {}
        self._relationships = relationships or {}
        self._traversals = traversals or {}

    def get_attributes(self, entity):
        if entity in self._attributes:
            return AttributesResult(entity=entity, found=True, attributes=self._attributes[entity])
        return AttributesResult(entity=entity, found=False)

    def get_relationships(self, entity):
        if entity in self._relationships:
            return RelationshipsResult(
                entity=entity, found=True, relationships=self._relationships[entity]
            )
        return RelationshipsResult(entity=entity, found=False)

    def traverse(self, entity, target=None, max_depth=2):
        result = self._traversals.get((entity, target))
        return result or TraversalResult(source_entity=entity, found=False)


class FakeVectorIndex:
    def __init__(self, hits=()):
        self._hits = tuple(hits)

    def semantic_search(self, query, k=5):
        return SemanticSearchResult(query=query, hits=self._hits[:k])


class FakeLLM:
    def __init__(self, response="a generated answer", raises=None):
        self.response = response
        self.raises = raises
        self.last_call = None

    def generate(self, question, context):
        self.last_call = (question, context)
        if self.raises is not None:
            raise self.raises
        return self.response


class TestDeterministicAttributesRoute:
    def test_found_attributes_are_template_rendered_without_an_llm_call(self):
        structured = FakeStructuredIndex(
            attributes={
                "banking:Account": (Attribute(name="accountId", data_type="entityId", is_nullable=False),)
            }
        )
        llm = FakeLLM()

        response = answer_query(
            "What are Account's attributes?",
            structured,
            FakeVectorIndex(),
            llm,
            frozenset({"banking:Account"}),
        )

        assert response.route == "structured"
        assert response.grounded is True
        assert response.verified is True
        assert "accountId" in response.answer
        assert llm.last_call is None
        assert response.debug.entity_match_kind == "exact"
        assert response.debug.intent == "attributes"
        assert response.debug.vector_hits == ()


class TestTraversalRoute:
    def test_two_entity_relationship_query_uses_bounded_traversal(self):
        traversal = TraversalResult(
            source_entity="crmCommon:Contact",
            found=True,
            path=("crmCommon:Contact", "crmCommon:Customer", "crmCommon:Organization"),
            relationships=(
                Relationship(name="customer", targets=("crmCommon:Organization",), kind="polymorphic"),
            ),
        )
        structured = FakeStructuredIndex(
            traversals={("crmCommon:Contact", "crmCommon:Organization"): traversal}
        )

        response = answer_query(
            "How does Contact relate to Organization?",
            structured,
            FakeVectorIndex(),
            FakeLLM(),
            frozenset({"crmCommon:Contact", "crmCommon:Organization"}),
        )

        assert response.route == "traversal"
        assert response.grounded is True
        assert "crmCommon:Contact" in response.answer
        assert "crmCommon:Organization" in response.answer


class TestAmbiguousMatch:
    def test_name_collision_returns_clarification_without_touching_llm_or_vector(self):
        llm = FakeLLM()

        response = answer_query(
            "Tell me about Account",
            FakeStructuredIndex(),
            FakeVectorIndex(),
            llm,
            frozenset({"banking:Account", "crmCommon:Account"}),
        )

        assert response.route == "none"
        assert response.grounded is False
        assert set(response.matched_entities) == {"banking:Account", "crmCommon:Account"}
        assert llm.last_call is None
        assert response.debug.entity_match_kind == "ambiguous"
        assert set(response.debug.entity_match_candidates) == {"banking:Account", "crmCommon:Account"}


class TestSemanticRoute:
    def test_grounded_semantic_hit_is_answered_via_llm(self):
        hits = (
            SemanticHit(
                entity="banking:Account",
                score=0.9,
                snippet="banking:Account: A bank account.\nAttributes: accountId",
            ),
        )
        llm = FakeLLM(response="Account has the attribute accountId.")

        response = answer_query(
            "Tell me something about accounts",
            FakeStructuredIndex(),
            FakeVectorIndex(hits=hits),
            llm,
            frozenset(),
        )

        assert response.route == "semantic"
        assert response.grounded is True
        assert response.verified is True
        assert response.answer == "Account has the attribute accountId."
        assert llm.last_call is not None
        assert response.debug.vector_hits[0].entity == "banking:Account"
        assert response.debug.vector_hits[0].score == 0.9
        assert response.debug.vector_hits[0].passed_cutoff is True
        assert response.debug.llm_raw_answer == "Account has the attribute accountId."
        assert response.debug.validator_missing_tokens == ()

    def test_below_cutoff_hit_is_refused_without_calling_the_llm(self):
        hits = (SemanticHit(entity="banking:Account", score=0.1, snippet="banking:Account: ..."),)
        llm = FakeLLM()

        response = answer_query(
            "some off-scope question",
            FakeStructuredIndex(),
            FakeVectorIndex(hits=hits),
            llm,
            frozenset(),
        )

        assert response.route == "none"
        assert response.grounded is False
        assert response.verified is False
        assert response.answer == _REFUSAL
        assert llm.last_call is None

    def test_no_hits_at_all_is_refused(self):
        response = answer_query(
            "anything", FakeStructuredIndex(), FakeVectorIndex(hits=()), FakeLLM(), frozenset()
        )

        assert response.route == "none"
        assert response.grounded is False
        assert response.answer == _REFUSAL

    def test_grounding_validator_catches_an_unsupported_claim_and_refuses(self):
        hits = (
            SemanticHit(
                entity="banking:Account",
                score=0.9,
                snippet="banking:Account: A bank account.\nAttributes: accountId",
            ),
        )
        llm = FakeLLM(response="Account also has a field called FraudScore, which is unusual.")

        response = answer_query(
            "Tell me about Account",
            FakeStructuredIndex(),
            FakeVectorIndex(hits=hits),
            llm,
            frozenset(),
        )

        assert response.route == "semantic"
        assert response.grounded is True
        assert response.verified is False
        assert response.answer == _REFUSAL
        assert response.error is None  # a real Validator rejection, not a provider failure
        assert response.debug.llm_raw_answer == "Account also has a field called FraudScore, which is unusual."
        assert "FraudScore" in response.debug.validator_missing_tokens

    def test_llm_call_failure_degrades_to_refusal_not_a_crash(self):
        """Regression: a real Gemini rate-limit error, raised from
        llm.generate(), propagated as an unhandled exception all the way to
        a raw 500 — found by running the live pipeline against the real
        Gemini API and actually hitting the free tier's quota, not by
        reading the code."""
        hits = (
            SemanticHit(
                entity="banking:Account",
                score=0.9,
                snippet="banking:Account: A bank account.",
            ),
        )
        llm = FakeLLM(raises=RuntimeError("429 RESOURCE_EXHAUSTED"))
        captured = []

        response = answer_query(
            "Tell me about Account",
            FakeStructuredIndex(),
            FakeVectorIndex(hits=hits),
            llm,
            frozenset(),
            trace_sink=captured.append,
        )

        assert response.route == "semantic"
        assert response.grounded is True
        assert response.verified is False
        assert response.answer == _REFUSAL
        assert "429 RESOURCE_EXHAUSTED" in (captured[0].error or "")
        # Exposed on the response itself, not just the trace log — a client
        # (e.g. the UI's pipeline view, ADR-0027) needs to tell "the LLM
        # call failed" apart from "the Validator rejected a real answer";
        # both look identical (grounded=True, verified=False) without this.
        assert "429 RESOURCE_EXHAUSTED" in (response.error or "")
        # Never assigned — the call raised before returning anything, so the
        # UI's Generate (LLM) zoom view has nothing to show as "raw output."
        assert response.debug.llm_raw_answer is None

    def test_grounded_answer_with_hedging_discourse_marker_is_not_refused(self):
        """Regression: a real Gemini response opening with "Based on the
        provided context, ..." was refused because "Based" isn't in the
        ingested context — found by running the live pipeline against the
        real Gemini API, not by reading the code."""
        hits = (
            SemanticHit(
                entity="banking:Account",
                score=0.9,
                snippet="banking:Account: A bank account. Relationships: relatesTo -> banking:Relationship",
            ),
        )
        llm = FakeLLM(
            response=(
                "Based on the provided context, banking:Account relates to "
                "banking:Relationship."
            )
        )

        response = answer_query(
            "How is Account connected to other entities?",
            FakeStructuredIndex(),
            FakeVectorIndex(hits=hits),
            llm,
            frozenset(),
        )

        assert response.route == "semantic"
        assert response.verified is True

    def test_structured_miss_falls_back_to_semantic_search(self):
        structured = FakeStructuredIndex(attributes={})  # "banking:Account" not present
        hits = (
            SemanticHit(
                entity="banking:Account",
                score=0.9,
                snippet="banking:Account: A bank account.\nAttributes: accountId",
            ),
        )
        llm = FakeLLM(response="Account has the attribute accountId.")

        response = answer_query(
            "What are Account's attributes?",
            structured,
            FakeVectorIndex(hits=hits),
            llm,
            frozenset({"banking:Account"}),
        )

        assert response.route == "semantic"
        assert llm.last_call is not None


class TestTraceSink:
    def test_trace_sink_receives_one_trace_matching_the_response(self):
        structured = FakeStructuredIndex(
            attributes={
                "banking:Account": (Attribute(name="accountId", data_type="entityId", is_nullable=False),)
            }
        )
        captured = []

        response = answer_query(
            "What are Account's attributes?",
            structured,
            FakeVectorIndex(),
            FakeLLM(),
            frozenset({"banking:Account"}),
            trace_sink=captured.append,
        )

        assert len(captured) == 1
        assert captured[0].route == response.route
        assert captured[0].grounded == response.grounded
        assert captured[0].verified == response.verified
