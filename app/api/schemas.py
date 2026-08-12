"""API request/response contracts — ADR-0021 ("API contracts" is its own
schema category, distinct from the Canonical Model and port records, even
where field shapes overlap with `app/domain/pipeline.py`'s `QueryResponse`).
FastAPI derives the OpenAPI schema from these automatically.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.domain.comparison import AnswerComparison
from app.domain.pipeline import QueryResponse as PipelineQueryResponse


class QueryRequest(BaseModel):
    question: str


class VectorHitDebugSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity: str
    score: float
    snippet: str
    passed_cutoff: bool


class PipelineDebugSchema(BaseModel):
    """Per-query stage detail for the UI's pipeline "zoom view" (ADR-0028) —
    a straight mirror of app/domain/pipeline.py's PipelineDebug, kept as its
    own schema per this module's docstring (API contracts are their own
    category, even where the shape overlaps the domain model)."""

    model_config = ConfigDict(frozen=True)

    entity_match_kind: Literal["exact", "fuzzy", "ambiguous", "none"]
    entity_match_candidates: tuple[str, ...]
    intent: Literal["attributes", "relationship", "semantic"] | None
    vector_hits: tuple[VectorHitDebugSchema, ...]
    similarity_cutoff: float | None
    llm_raw_answer: str | None
    validator_cited_tokens: tuple[str, ...]
    validator_missing_tokens: tuple[str, ...]


class QueryResponseSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str
    answer: str
    matched_entities: tuple[str, ...]
    route: Literal["structured", "traversal", "semantic", "none"]
    grounded: bool
    verified: bool
    error: str | None = None
    debug: PipelineDebugSchema

    @classmethod
    def from_domain(cls, response: PipelineQueryResponse) -> QueryResponseSchema:
        return cls(**response.model_dump())


class AnswerComparisonSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    similarity: float
    shared_terms: tuple[str, ...]
    missing_terms: tuple[str, ...]
    extra_terms: tuple[str, ...]


class EvaluateRequest(BaseModel):
    question: str
    expected_answer: str


class EvaluateResponseSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: QueryResponseSchema
    comparison: AnswerComparisonSchema

    @classmethod
    def from_domain(
        cls, response: PipelineQueryResponse, comparison: AnswerComparison
    ) -> EvaluateResponseSchema:
        return cls(
            query=QueryResponseSchema.from_domain(response),
            comparison=AnswerComparisonSchema(**comparison.model_dump()),
        )


class AttributeSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    data_type: str
    description: str | None = None
    is_nullable: bool = True


class RelationshipSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    targets: tuple[str, ...]
    kind: Literal["single", "polymorphic", "party"]


class EntityListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    entities: tuple[str, ...]


class EntityDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity: str
    attributes: tuple[AttributeSchema, ...]
    relationships: tuple[RelationshipSchema, ...]


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ok"]
