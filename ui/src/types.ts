// Mirrors app/api/schemas.py exactly — this is a thin client (ADR-0022/0025),
// so the contract is whatever FastAPI's OpenAPI schema says it is, hand-typed
// here rather than codegen'd since it's four small shapes.

export type Route = "structured" | "traversal" | "semantic" | "none";

export interface VectorHitDebug {
  entity: string;
  score: number;
  snippet: string;
  passed_cutoff: boolean;
}

export type EntityMatchKind = "exact" | "fuzzy" | "ambiguous" | "none";
export type IntentKind = "attributes" | "relationship" | "semantic";

// Mirrors app/domain/pipeline.py's PipelineDebug via app/api/schemas.py's
// PipelineDebugSchema (ADR-0028) — real per-query intermediate values
// captured as they're computed, not derived/guessed client-side. Every
// field is populated only as far as that query's real branch went; a
// structured-route response's vector_hits is genuinely empty, not omitted.
export interface PipelineDebug {
  entity_match_kind: EntityMatchKind;
  entity_match_candidates: string[];
  intent: IntentKind | null;
  vector_hits: VectorHitDebug[];
  similarity_cutoff: number | null;
  llm_raw_answer: string | null;
  validator_cited_tokens: string[];
  validator_missing_tokens: string[];
}

export interface QueryResponse {
  query: string;
  answer: string;
  matched_entities: string[];
  route: Route;
  grounded: boolean;
  verified: boolean;
  // Set only when the LLM call itself failed (rate limit, timeout, ...) —
  // distinguishes that from the Grounding Validator rejecting a real
  // answer, since both otherwise look identical (grounded=true,
  // verified=false). See ADR-0010's "Provider-Call Failures" section and
  // ADR-0027 (the pipeline view is why the UI needs this distinction).
  error: string | null;
  debug: PipelineDebug;
}

// Mirrors app/api/schemas.py's AnswerComparisonSchema/EvaluateResponseSchema
// — the "score an answer against a desired answer" utility (POST /evaluate).
// Deliberately a plain lexical comparison, not a RAGAS/DeepEval call — see
// app/domain/comparison.py's module docstring.
export interface AnswerComparison {
  similarity: number;
  shared_terms: string[];
  missing_terms: string[];
  extra_terms: string[];
}

export interface EvaluateResponse {
  query: QueryResponse;
  comparison: AnswerComparison;
}

export interface EntityListResponse {
  entities: string[];
}

export type RelationshipKind = "single" | "polymorphic" | "party";

export interface AttributeSchema {
  name: string;
  data_type: string;
  description: string | null;
  is_nullable: boolean;
}

export interface RelationshipSchema {
  name: string;
  targets: string[];
  kind: RelationshipKind;
}

export interface EntityDetailResponse {
  entity: string;
  attributes: AttributeSchema[];
  relationships: RelationshipSchema[];
}

// A client-side reconstruction of which app/domain/pipeline.py stages ran
// for one response — derived from QueryResponse's existing route/grounded/
// verified/error fields, not a new API field (ADR-0027). The per-stage
// *content* users can click into now comes from `debug` above (ADR-0028);
// this just decides each stage's done/failed/skipped status and label.
export type StageStatus = "done" | "failed" | "skipped";

export interface PipelineStage {
  name: string;
  status: StageStatus;
  detail?: string;
}

// Mirrors the kpis dict tests/eval/run.py writes to eval-snapshot.json — a
// build-time snapshot of the last real `task eval:run`, not a live value
// (ADR-0026). Every rate is a 0-1 fraction, null where the run had nothing
// to score (e.g. no question exercises a given path).
export interface EvalSnapshot {
  generated_at: string;
  question_count: number;
  data_quality: {
    entity_resolution_rate: number | null;
    unresolved_reference_rate: number | null;
  };
  retrieval: {
    entity_matching_accuracy: number | null;
    structured_precision: number | null;
    structured_recall: number | null;
    relationship_precision: number | null;
    relationship_recall: number | null;
    traversal_accuracy: number | null;
    vector_recall_at_k: number | null;
    vector_context_precision: number | null;
  };
  answer_quality: {
    refusal_precision: number | null;
    refusal_recall: number | null;
    faithfulness: number | null;
    faithfulness_n: number;
    completeness: number | null;
    relevancy: number | null;
  };
  unavailable_count: number;
}
