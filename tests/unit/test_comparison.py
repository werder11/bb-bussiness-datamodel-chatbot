"""Component/Unit tests for the answer-vs-desired-answer comparison utility.

Pure function, no ports involved — data-driven per ADR-0018.
"""

import pytest

from app.domain.comparison import compare_answer

CASES = [
    pytest.param(
        "Account has attributes accountId and balance.",
        "Account has attributes accountId and balance.",
        1.0,
        {"account", "attributes", "accountid", "balance"},
        set(),
        set(),
        id="identical_text",
    ),
    pytest.param(
        "Account has attributes accountId and balance.",
        "I don't have information about that in the ingested CDM scope.",
        None,  # similarity not asserted exactly, just bounds-checked
        set(),
        {"don", "information", "ingested", "cdm", "scope"},
        {"account", "attributes", "accountid", "balance"},
        id="unrelated_refusal_vs_real_answer",
    ),
    pytest.param(
        "Account has attributes accountId, balance, and currency.",
        "Account has attributes accountId and balance.",
        None,
        {"account", "attributes", "accountid", "balance"},
        set(),
        {"currency"},
        id="actual_is_superset_of_expected",
    ),
]


@pytest.mark.parametrize("actual,expected,expected_similarity,shared,missing,extra", CASES)
def test_compare_answer(actual, expected, expected_similarity, shared, missing, extra):
    result = compare_answer(actual, expected)
    assert 0.0 <= result.similarity <= 1.0
    if expected_similarity is not None:
        assert result.similarity == pytest.approx(expected_similarity)
    assert set(result.shared_terms) == shared
    assert set(result.missing_terms) == missing
    assert set(result.extra_terms) == extra


def test_stopwords_are_excluded_from_all_term_sets():
    result = compare_answer("This is the answer and it is correct.", "This is a different answer.")
    for term_set in (result.shared_terms, result.missing_terms, result.extra_terms):
        assert "this" not in term_set
        assert "and" not in term_set
        assert "the" not in term_set


def test_empty_expected_answer_yields_no_missing_terms():
    result = compare_answer("Account has attributes accountId.", "")
    assert result.missing_terms == ()
