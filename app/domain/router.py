"""Intent Classification — ADR-0006 (swappable strategy; this module is the
default rule-based variant, fully unit-tested as a pure function).

Sits downstream of the Entity Matcher (`app/domain/entity_matcher.py`,
ADR-0011): "which entity is this about" is already answered by the time
`classify` runs — this module only answers "what does the user want to know
about it." Ambiguity (`MatchResult.kind == "ambiguous"`) is not resolved
here; `entities` is passed through as-is for the pipeline (Phase 5) to act
on, since asking for clarification is an orchestration concern, not a
classification one.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.entity_matcher import MatchResult

_RELATIONSHIP_KEYWORDS = ("relat", "connect", "link", "between", "associat")
_ATTRIBUTE_KEYWORDS = ("attribute", "field", "propert", "column", "core data")


class Intent(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["attributes", "relationship", "semantic"]
    # Namespaced entity names carried through from the MatchResult, in
    # first-mention order. Empty for a query the Entity Matcher found no
    # vocabulary hit for.
    entities: tuple[str, ...] = ()


def classify(query: str, matched: MatchResult) -> Intent:
    if matched.kind == "none":
        return Intent(kind="semantic")

    lowered = query.lower()
    if any(keyword in lowered for keyword in _RELATIONSHIP_KEYWORDS):
        return Intent(kind="relationship", entities=matched.candidates)
    if any(keyword in lowered for keyword in _ATTRIBUTE_KEYWORDS):
        return Intent(kind="attributes", entities=matched.candidates)
    return Intent(kind="semantic", entities=matched.candidates)
