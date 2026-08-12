"""Query pipeline orchestration — `docs/design/workflows.md#query-workflow`.

Wired against the port Protocols (`app/domain/ports.py`), not concrete
adapters, so it's testable with fakes (ADR-0001, ADR-0018).

Only Entity Matcher (ADR-0011) and Router (ADR-0006) ever select a single
route per query — the Router has no "mixed" intent — so the "mix of
structured + semantic evidence" case ADR-0016 anticipates isn't built
here; a structured/traversal miss simply falls through to semantic search
rather than being combined with it. Revisit if the evaluation set
(ADR-0017) shows this loses real answers.
"""

import re
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.entity_matcher import MatchResult, match
from app.domain.ports import LLM, StructuredIndex, VectorIndex
from app.domain.router import classify
from app.domain.templates import (
    render_attributes,
    render_relationship,
    render_traversal,
)
from app.domain.tracing import RetrievalTrace, build_trace

_REFUSAL = "I don't have information about that in the ingested CDM scope."

# Tuned against real cosine-similarity scores from the real corpus + real
# embedder (ADR-0005; see tests/eval/ for the dataset this was validated
# against). Genuinely on-topic questions scored 0.43-0.69; genuinely
# off-topic questions scored 0.06-0.24. One adversarial question ("summarize
# the fraud-detection rules embedded in banking:Account") scored 0.51 purely
# from lexical overlap with real entity names despite asking about something
# the corpus doesn't contain — that's expected and correct: the Guard isn't
# meant to catch embellishment-on-plausible-context, the post-generation
# Grounding Validator (ADR-0010) is.
_DEFAULT_SIMILARITY_CUTOFF = 0.4

# Grounding Validator (ADR-0010): best-effort string containment. Common
# capitalized words are excluded so sentence-initial words don't trigger a
# false "unsupported claim" refusal — the ADR itself documents this check
# as blunt, not a hard guarantee. The discourse-marker words below (based,
# given, according, ...) were added after tuning against real Gemini output
# (ADR-0024): Gemini's default hedging phrasing ("Based on the provided
# context, ...") was tripping the validator on "Based" and refusing answers
# that were, in fact, fully grounded.
_CITED_TOKEN_PATTERN = re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")
_COMMON_CAPITALIZED_WORDS = frozenset(
    {
        "the", "this", "that", "these", "those", "it", "is", "are", "a", "an", "no", "yes", "if",
        "based", "given", "according", "additionally", "however", "furthermore", "therefore",
        "note", "please", "here", "there", "while", "since", "unfortunately", "overall",
        "context", "provided", "answer", "question", "information", "in", "on",
        "to", "for", "with", "and", "or", "but", "so", "as", "of", "from", "defined",
    }
)


class VectorHitDebug(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity: str
    score: float
    snippet: str
    passed_cutoff: bool


class PipelineDebug(BaseModel):
    """Per-query stage detail — ADR-0028. Nothing here changes what the
    pipeline *does*; it's a record of intermediate values already computed
    along the way, captured instead of discarded, for the UI's pipeline
    "zoom view" to show. Every field defaults to empty/None so a branch that
    never reaches a given stage just leaves it unpopulated, honestly."""

    model_config = ConfigDict(frozen=True)

    entity_match_kind: Literal["exact", "fuzzy", "ambiguous", "none"]
    entity_match_candidates: tuple[str, ...] = ()
    intent: Literal["attributes", "relationship", "semantic"] | None = None
    vector_hits: tuple[VectorHitDebug, ...] = ()
    similarity_cutoff: float | None = None
    # The model's actual output, even when the Validator rejected it and the
    # client-facing `answer` became the fixed refusal instead — otherwise
    # there would be no way to show what actually got blocked and why.
    llm_raw_answer: str | None = None
    validator_cited_tokens: tuple[str, ...] = ()
    validator_missing_tokens: tuple[str, ...] = ()


class QueryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    answer: str
    matched_entities: tuple[str, ...]
    route: Literal["structured", "traversal", "semantic", "none"]
    grounded: bool  # pre-generation Grounding Guard (ADR-0005): was there any evidence?
    verified: bool  # post-generation Grounding Validator (ADR-0010): was the answer supported?
    # Set only when the LLM call itself failed (rate limit, timeout, ...) and
    # this response is a fallback refusal rather than the Grounding Validator
    # rejecting a real answer — ADR-0010's "Provider-Call Failures" section.
    # Exposed here (not just on RetrievalTrace) so a client can tell those
    # two verified=false cases apart — the UI pipeline view needs exactly
    # this distinction (ADR-0027) and silently conflating them is misleading.
    error: str | None = None
    debug: PipelineDebug


def _cited_tokens(answer: str) -> frozenset[str]:
    return frozenset(
        token
        for token in _CITED_TOKEN_PATTERN.findall(answer)
        if token.lower() not in _COMMON_CAPITALIZED_WORDS
    )


def _verify_grounding(answer: str, context: tuple[str, ...]) -> bool:
    context_blob = " ".join(context).lower()
    return all(token.lower() in context_blob for token in _cited_tokens(answer))


def answer_query(
    question: str,
    structured: StructuredIndex,
    vector: VectorIndex,
    llm: LLM,
    known_entities: frozenset[str],
    *,
    similarity_cutoff: float = _DEFAULT_SIMILARITY_CUTOFF,
    trace_sink: Callable[[RetrievalTrace], None] | None = None,
) -> QueryResponse:
    def respond(
        answer: str,
        matched_entities: tuple[str, ...],
        route: Literal["structured", "traversal", "semantic", "none"],
        *,
        grounded: bool,
        verified: bool,
        debug: PipelineDebug,
        error: str | None = None,
    ) -> QueryResponse:
        trace = build_trace(
            query=question,
            matched_entities=matched_entities,
            route=route,
            grounded=grounded,
            verified=verified,
            error=error,
        )
        if trace_sink is not None:
            trace_sink(trace)
        return QueryResponse(
            query=question,
            answer=answer,
            matched_entities=matched_entities,
            route=route,
            grounded=grounded,
            verified=verified,
            error=error,
            debug=debug,
        )

    def debug_for(
        matched_result: MatchResult,
        intent_kind: Literal["attributes", "relationship", "semantic"] | None = None,
        vector_hits: tuple[VectorHitDebug, ...] = (),
        similarity_cutoff_used: float | None = None,
        llm_raw_answer: str | None = None,
        cited: frozenset[str] = frozenset(),
        missing: frozenset[str] = frozenset(),
    ) -> PipelineDebug:
        return PipelineDebug(
            entity_match_kind=matched_result.kind,
            entity_match_candidates=matched_result.candidates,
            intent=intent_kind,
            vector_hits=vector_hits,
            similarity_cutoff=similarity_cutoff_used,
            llm_raw_answer=llm_raw_answer,
            validator_cited_tokens=tuple(sorted(cited)),
            validator_missing_tokens=tuple(sorted(missing)),
        )

    matched = match(question, known_entities)

    if matched.kind == "ambiguous":
        answer = (
            "That name is ambiguous in the ingested CDM scope — did you mean "
            + " or ".join(matched.candidates)
            + "?"
        )
        return respond(
            answer, matched.candidates, "none", grounded=False, verified=False,
            debug=debug_for(matched),
        )

    intent = classify(question, matched)

    if intent.kind == "attributes" and intent.entities:
        entity = intent.entities[0]
        attrs_result = structured.get_attributes(entity)
        if attrs_result.found:
            answer = render_attributes(entity, attrs_result.attributes)
            return respond(
                answer, (entity,), "structured", grounded=True, verified=True,
                debug=debug_for(matched, intent.kind),
            )

    elif intent.kind == "relationship" and intent.entities:
        if len(intent.entities) >= 2:
            source, target = intent.entities[0], intent.entities[1]
            traversal = structured.traverse(source, target=target, max_depth=2)
            if traversal.found:
                answer = render_traversal(
                    traversal.source_entity, traversal.path, traversal.relationships
                )
                return respond(
                    answer, (source, target), "traversal", grounded=True, verified=True,
                    debug=debug_for(matched, intent.kind),
                )
        else:
            entity = intent.entities[0]
            rels_result = structured.get_relationships(entity)
            if rels_result.found and rels_result.relationships:
                answer = render_relationship(entity, rels_result.relationships)
                return respond(
                    answer, (entity,), "structured", grounded=True, verified=True,
                    debug=debug_for(matched, intent.kind),
                )

    # Fallback: intent.kind == "semantic", or a structured/traversal lookup
    # above found nothing for a matched entity.
    search = vector.semantic_search(question, k=5)
    vector_hits_debug = tuple(
        VectorHitDebug(
            entity=hit.entity,
            score=hit.score,
            snippet=hit.snippet,
            passed_cutoff=hit.score >= similarity_cutoff,
        )
        for hit in search.hits
    )
    grounded_hits = tuple(hit for hit in search.hits if hit.score >= similarity_cutoff)
    if not grounded_hits:
        return respond(
            _REFUSAL, matched.candidates, "none", grounded=False, verified=False,
            debug=debug_for(matched, intent.kind, vector_hits_debug, similarity_cutoff),
        )

    context = tuple(hit.snippet for hit in grounded_hits)
    matched_entities = tuple(hit.entity for hit in grounded_hits)
    try:
        generated = llm.generate(question, context)
    except Exception as exc:  # noqa: BLE001 — any provider failure (rate limit,
        # timeout, transient error) degrades to the same refusal a rejected
        # claim gets, rather than propagating into a raw 500 (found live,
        # ADR-0010's "Provider-Call Failures" addendum — real evidence was
        # retrieved, so grounded=True; there's no generated text to stand
        # behind, so verified=False, same as an unsupported-claim refusal).
        return respond(
            _REFUSAL, matched_entities, "semantic", grounded=True, verified=False, error=str(exc),
            debug=debug_for(matched, intent.kind, vector_hits_debug, similarity_cutoff),
        )
    verified = _verify_grounding(generated, context)
    cited = _cited_tokens(generated)
    context_blob = " ".join(context).lower()
    missing = frozenset(token for token in cited if token.lower() not in context_blob)
    answer = generated if verified else _REFUSAL
    debug = debug_for(
        matched, intent.kind, vector_hits_debug, similarity_cutoff,
        llm_raw_answer=generated, cited=cited, missing=missing,
    )
    return respond(answer, matched_entities, "semantic", grounded=True, verified=verified, debug=debug)
