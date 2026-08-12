"""Interactive answer-vs-desired-answer comparison — the "evaluate this
answer against a desired answer" utility raised early in the UI work.

Deliberately NOT a RAGAS/DeepEval integration: this system already runs its
own operational-proxy metrics (`tests/eval/run.py`'s Faithfulness/Answer
Relevancy) rather than pulling in an external eval framework, per
`docs/quality/evaluation-strategy.md`'s explicit "not a complicated
evaluation framework" stance. This module extends that same philosophy to
a single, ad-hoc, user-supplied question: run it through the real pipeline,
then compare the real answer to a user-typed desired answer with a simple,
transparent, zero-cost lexical comparison — no embedding model, no live
LLM-as-judge call, nothing beyond what `answer_query` already produces.
"""

import re
from difflib import SequenceMatcher

from pydantic import BaseModel, ConfigDict

_TERM_PATTERN = re.compile(r"[a-zA-Z]{3,}")
_STOPWORDS = frozenset(
    {
        "the", "a", "an", "is", "are", "was", "were", "this", "that", "these", "those",
        "it", "its", "to", "of", "in", "on", "for", "with", "and", "or", "but", "so",
        "as", "from", "by", "be", "has", "have", "had", "not", "no", "yes", "if",
        "which", "who", "what", "where", "when", "how", "does", "do", "did", "you",
        "your", "can", "will", "would", "should", "about", "into", "than", "then",
    }
)


class AnswerComparison(BaseModel):
    model_config = ConfigDict(frozen=True)

    similarity: float  # difflib.SequenceMatcher ratio over the raw text, 0..1
    shared_terms: tuple[str, ...]  # in both the real answer and the desired answer
    missing_terms: tuple[str, ...]  # in the desired answer, not in the real answer
    extra_terms: tuple[str, ...]  # in the real answer, not in the desired answer


def _terms(text: str) -> frozenset[str]:
    return frozenset(
        term for term in (m.lower() for m in _TERM_PATTERN.findall(text)) if term not in _STOPWORDS
    )


def compare_answer(actual: str, expected: str) -> AnswerComparison:
    similarity = SequenceMatcher(None, actual.lower(), expected.lower()).ratio()
    actual_terms = _terms(actual)
    expected_terms = _terms(expected)
    return AnswerComparison(
        similarity=similarity,
        shared_terms=tuple(sorted(actual_terms & expected_terms)),
        missing_terms=tuple(sorted(expected_terms - actual_terms)),
        extra_terms=tuple(sorted(actual_terms - expected_terms)),
    )
