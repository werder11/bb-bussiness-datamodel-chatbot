"""Entity Matcher — ADR-0011 (closed-vocabulary exact + fuzzy matching, not NER/ML).

Runs immediately after the API boundary, upstream of Intent Classification
(`app/domain/router.py`, ADR-0006). Matches free-text query mentions against
the closed, namespaced entity-name vocabulary (`banking:Account` vs
`crmCommon:Account`, ADR-0007). On a genuine name collision, both candidates
are surfaced (`kind="ambiguous"`) rather than silently guessing one.
"""

import difflib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

_FUZZY_CUTOFF = 0.75


class MatchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    kind: Literal["exact", "fuzzy", "ambiguous", "none"]
    # Namespaced entity names, in first-mention order. For "ambiguous", these
    # are the colliding candidates for the one ambiguous mention only — any
    # other, unambiguous mention in the same query is dropped (ADR-0011: a
    # collision must be resolved/clarified before anything else proceeds).
    candidates: tuple[str, ...] = ()


def _bare_name(entity_name: str) -> str:
    return entity_name.split(":", 1)[-1]


def _group_by_bare_name(known_entities: frozenset[str]) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for full in known_entities:
        grouped.setdefault(_bare_name(full), []).append(full)
    return {bare: tuple(sorted(fulls)) for bare, fulls in grouped.items()}


def _full_name_hits(query: str, known_entities: frozenset[str]) -> list[tuple[int, str]]:
    """A fully-qualified `namespace:EntityName` mention (e.g. a user echoing
    back the exact wording this module's own ambiguity message suggests)
    disambiguates on its own — it must not fall through to the bare-name
    collision check below, or a query built from our own clarification
    prompt would loop right back into "ambiguous"."""
    positioned = []
    for full in known_entities:
        match = re.search(rf"\b{re.escape(full)}\b", query, re.IGNORECASE)
        if match:
            positioned.append((match.start(), full))
    positioned.sort(key=lambda item: item[0])
    return positioned


def _exact_hits(query: str, bare_to_full: dict[str, tuple[str, ...]]) -> list[tuple[str, tuple[str, ...]]]:
    positioned = []
    for bare, fulls in bare_to_full.items():
        match = re.search(rf"\b{re.escape(bare)}\b", query, re.IGNORECASE)
        if match:
            positioned.append((match.start(), bare, fulls))
    positioned.sort(key=lambda item: item[0])
    return [(bare, fulls) for _, bare, fulls in positioned]


def _fuzzy_hits(query: str, bare_to_full: dict[str, tuple[str, ...]]) -> list[tuple[str, tuple[str, ...]]]:
    seen: dict[str, tuple[str, ...]] = {}
    for token in re.findall(r"[A-Za-z]+", query):
        for bare in difflib.get_close_matches(token, bare_to_full.keys(), n=1, cutoff=_FUZZY_CUTOFF):
            seen.setdefault(bare, bare_to_full[bare])
    return list(seen.items())


def match(query: str, known_entities: frozenset[str]) -> MatchResult:
    full_hits = _full_name_hits(query, known_entities)
    if full_hits:
        candidates = tuple(dict.fromkeys(full for _, full in full_hits))
        return MatchResult(query=query, kind="exact", candidates=candidates)

    bare_to_full = _group_by_bare_name(known_entities)

    hits = _exact_hits(query, bare_to_full)
    kind: Literal["exact", "fuzzy"] = "exact"
    if not hits:
        hits = _fuzzy_hits(query, bare_to_full)
        kind = "fuzzy"
    if not hits:
        return MatchResult(query=query, kind="none", candidates=())

    collisions = [fulls for _, fulls in hits if len(fulls) > 1]
    if collisions:
        candidates = tuple(dict.fromkeys(full for fulls in collisions for full in fulls))
        return MatchResult(query=query, kind="ambiguous", candidates=candidates)

    candidates = tuple(dict.fromkeys(fulls[0] for _, fulls in hits))
    return MatchResult(query=query, kind=kind, candidates=candidates)
