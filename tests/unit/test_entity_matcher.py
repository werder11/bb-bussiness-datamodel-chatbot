"""Component/Unit tests for the Entity Matcher — ADR-0011.

Data-driven table per ADR-0018: each row is a free-text query against a
fixed, small closed vocabulary that deliberately includes a real name
collision (banking:Account vs crmCommon:Account, ADR-0007).
"""

import pytest

from app.domain.entity_matcher import match

KNOWN_ENTITIES = frozenset(
    {
        "banking:Account",
        "crmCommon:Account",
        "crmCommon:Contact",
        "crmCommon:Organization",
        "crmCommon:Lead",
    }
)

CASES = [
    pytest.param(
        "What are Contact's attributes?",
        "exact",
        ("crmCommon:Contact",),
        id="exact_single_unambiguous",
    ),
    pytest.param(
        "How does Contact relate to Organization?",
        "exact",
        ("crmCommon:Contact", "crmCommon:Organization"),
        id="exact_two_distinct_entities_in_mention_order",
    ),
    pytest.param(
        "relate Organization to Contact",
        "exact",
        ("crmCommon:Organization", "crmCommon:Contact"),
        id="exact_order_follows_query_not_alphabetical",
    ),
    pytest.param(
        "Tell me about Account",
        "ambiguous",
        ("banking:Account", "crmCommon:Account"),
        id="ambiguous_name_collision",
    ),
    pytest.param(
        "What are the attributes of crmCommon:Account?",
        "exact",
        ("crmCommon:Account",),
        id="fully_qualified_mention_disambiguates_a_collision",
    ),
    pytest.param(
        "what about Contct's attributes",
        "fuzzy",
        ("crmCommon:Contact",),
        id="fuzzy_typo_fallback",
    ),
    pytest.param(
        "What is the weather today?",
        "none",
        (),
        id="no_vocabulary_hit",
    ),
]


class TestMatch:
    @pytest.mark.parametrize("query,expected_kind,expected_candidates", CASES)
    def test_match(self, query, expected_kind, expected_candidates):
        result = match(query, KNOWN_ENTITIES)
        assert result.kind == expected_kind
        assert result.candidates == expected_candidates

    def test_query_is_preserved_on_the_result(self):
        result = match("Tell me about Lead", KNOWN_ENTITIES)
        assert result.query == "Tell me about Lead"

    def test_matching_is_case_insensitive(self):
        result = match("tell me about LEAD", KNOWN_ENTITIES)
        assert result.kind == "exact"
        assert result.candidates == ("crmCommon:Lead",)

    def test_substring_of_a_longer_word_is_not_a_false_positive(self):
        # "Lead" must not match inside "leadership" (word-boundary matching).
        result = match("Explain leadership structure", KNOWN_ENTITIES)
        assert result.kind == "none"
