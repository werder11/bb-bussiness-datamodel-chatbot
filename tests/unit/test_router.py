"""Component/Unit tests for the (default, rule-based) Router — ADR-0006.

Pure function, fully unit-tested directly per the ADR's own testing
guidance. `MatchResult`s are constructed directly rather than routed
through the real Entity Matcher, since Router correctness is independent
of matching correctness (covered separately in test_entity_matcher.py).
"""

import pytest

from app.domain.entity_matcher import MatchResult
from app.domain.router import classify

CASES = [
    pytest.param(
        "What are Contact's attributes?",
        MatchResult(query="x", kind="exact", candidates=("crmCommon:Contact",)),
        "attributes",
        ("crmCommon:Contact",),
        id="attributes_keyword",
    ),
    pytest.param(
        "List the core data fields for Account",
        MatchResult(query="x", kind="exact", candidates=("banking:Account",)),
        "attributes",
        ("banking:Account",),
        id="attributes_alternate_phrasing",
    ),
    pytest.param(
        "How does Contact relate to Organization?",
        MatchResult(
            query="x", kind="exact", candidates=("crmCommon:Contact", "crmCommon:Organization")
        ),
        "relationship",
        ("crmCommon:Contact", "crmCommon:Organization"),
        id="relationship_keyword_two_entities",
    ),
    pytest.param(
        "What is Lead connected to?",
        MatchResult(query="x", kind="exact", candidates=("crmCommon:Lead",)),
        "relationship",
        ("crmCommon:Lead",),
        id="relationship_keyword_single_entity",
    ),
    pytest.param(
        "Tell me about Account",
        MatchResult(query="x", kind="ambiguous", candidates=("banking:Account", "crmCommon:Account")),
        "semantic",
        ("banking:Account", "crmCommon:Account"),
        id="no_intent_keyword_falls_back_to_semantic_but_keeps_candidates",
    ),
    pytest.param(
        "What is the weather today?",
        MatchResult(query="x", kind="none", candidates=()),
        "semantic",
        (),
        id="no_match_at_all_is_semantic_with_no_entities",
    ),
]


class TestClassify:
    @pytest.mark.parametrize("query,matched,expected_kind,expected_entities", CASES)
    def test_classify(self, query, matched, expected_kind, expected_entities):
        intent = classify(query, matched)
        assert intent.kind == expected_kind
        assert intent.entities == expected_entities
