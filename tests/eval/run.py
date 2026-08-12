"""Evaluation KPI runner — ADR-0017, `docs/quality/evaluation-strategy.md`.

Runs against the real, already-ingested indexes (SQLite + Chroma — this
expects `task ingest:run` to have already populated `cdm.db`/`chroma_data`,
the same precondition the API's `lifespan` has) and, on the semantic-search
path, the real LLM (Anthropic or Gemini, selected via `LLM_PROVIDER` —
ADR-0024). Invoked via `task eval:run` on the CI/CD slow gate only
(ADR-0019) — this makes live LLM calls and costs real money/time, unlike
anything in tests/unit through tests/acceptance.

Each KPI layer is computed independently against the *stage* it measures
(Entity Matcher, StructuredIndex, VectorIndex) rather than only inspecting
the final pipeline answer — this is what makes a bad result diagnosable
(ADR-0017's whole point), not just a single opaque pass/fail.

If no LLM provider credential is available, questions that reach
generation are marked unavailable rather than crashing the run — every
metric except Faithfulness and templated-vs-generated Answer Relevancy
still computes fully without it.
"""

import argparse
import json
from collections.abc import Iterable
from datetime import UTC, datetime
from statistics import mean

from app.adapters.llm_factory import build_llm
from app.adapters.structured_index_sqlite import SQLiteStructuredIndex
from app.adapters.vector_index_chroma import ChromaVectorIndex
from app.domain.entity_matcher import match
from app.domain.pipeline import QueryResponse, answer_query
from app.domain.ports import LLM
from app.ingestion.resolver import discover_entities, resolve_all
from app.ingestion.run import (
    _BANKING_MANIFEST,
    _CHROMA_PATH,
    _COMMON_MANIFEST,
    _CORPUS_ROOT,
    _DB_PATH,
)
from app.ingestion.validate import validate
from tests.eval.dataset import EVAL_QUESTIONS, EvalQuestion

_VECTOR_K = 5


def _bare(name: str) -> str:
    return name.split(":", 1)[-1]


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


# -- Data Quality -------------------------------------------------------------


def _data_quality_metrics() -> dict:
    """Re-derives the Validation Pass output fresh (ADR-0014) — not stored
    anywhere after ingestion, so this is the only place it's available."""
    discovered = discover_entities(_BANKING_MANIFEST, _CORPUS_ROOT, "banking") + discover_entities(
        _COMMON_MANIFEST, _CORPUS_ROOT, "crmCommon"
    )
    entities, errors = resolve_all(discovered)
    report = validate(entities, entities_discovered=len(discovered), entities_skipped=len(errors))
    resolution_rate = report.entities_resolved / report.entities_discovered if discovered else 0.0
    unresolved_rate = (
        len(report.unresolved_references) / report.relationships_discovered
        if report.relationships_discovered
        else 0.0
    )
    return {
        "resolution_rate": resolution_rate,
        "entities_resolved": report.entities_resolved,
        "entities_discovered": report.entities_discovered,
        "unresolved_rate": unresolved_rate,
        "unresolved_count": len(report.unresolved_references),
        "relationships_discovered": report.relationships_discovered,
    }


def _data_quality_section(m: dict) -> str:
    return (
        "## Data Quality\n\n"
        f"- Entity resolution rate: {_pct(m['resolution_rate'])} "
        f"({m['entities_resolved']}/{m['entities_discovered']})\n"
        f"- Unresolved-reference rate: {_pct(m['unresolved_rate'])} "
        f"({m['unresolved_count']}/{m['relationships_discovered']})\n"
    )


# -- Entity Matching ------------------------------------------------------------


def _entity_matching_accuracy(questions: Iterable[EvalQuestion], known_entities: frozenset[str]):
    # entity_discovery questions are open-ended free text with no literal
    # entity mention (by design — they exercise vector search, not the
    # Entity Matcher) and expected_entities there is an illustrative sample,
    # not something the Matcher is meant to resolve. Scoring them here would
    # always read as a Matcher failure for a case it was never meant to handle.
    scored = [q for q in questions if q.expected_entities and q.category != "entity_discovery"]
    rows = []
    correct = 0
    for q in scored:
        result = match(q.question, known_entities)
        got, want = set(result.candidates), set(q.expected_entities)
        ok = got == want
        correct += ok
        rows.append((q.id, ok, sorted(want), sorted(got)))
    accuracy = correct / len(scored) if scored else None
    return accuracy, rows


# -- Structured Retrieval (attributes) -----------------------------------------


def _structured_retrieval_pr(questions: Iterable[EvalQuestion], structured: SQLiteStructuredIndex):
    scored = [q for q in questions if q.expected_attributes]
    precisions, recalls, rows = [], [], []
    for q in scored:
        entity = q.expected_entities[0]
        got = {a.name for a in structured.get_attributes(entity).attributes}
        want = set(q.expected_attributes)
        tp = len(got & want)
        precision = tp / len(got) if got else 0.0
        recall = tp / len(want) if want else 0.0
        precisions.append(precision)
        recalls.append(recall)
        rows.append((q.id, precision, recall))
    return (
        mean(precisions) if precisions else None,
        mean(recalls) if recalls else None,
        rows,
    )


# -- Structured Retrieval (single-hop relationships) ---------------------------


def _relationship_pr(questions: Iterable[EvalQuestion], structured: SQLiteStructuredIndex):
    scored = [q for q in questions if q.category == "relationship_retrieval"]
    precisions, recalls, rows = [], [], []
    for q in scored:
        entity = q.expected_entities[0]
        result = structured.get_relationships(entity)
        got = {t for rel in result.relationships for t in rel.targets}
        want = set(q.expected_relationship_targets)
        tp = len(got & want)
        precision = tp / len(got) if got else (1.0 if not want else 0.0)
        recall = tp / len(want) if want else 1.0
        precisions.append(precision)
        recalls.append(recall)
        rows.append((q.id, precision, recall))
    return (
        mean(precisions) if precisions else None,
        mean(recalls) if recalls else None,
        rows,
    )


# -- Relationship Traversal (path correctness) ---------------------------------


def _traversal_correctness(questions: Iterable[EvalQuestion], structured: SQLiteStructuredIndex):
    scored = [q for q in questions if q.category == "multi_hop" or q.expected_path or q.id == "adv-03"]
    rows = []
    correct = 0
    for q in scored:
        source, target = q.expected_entities[0], q.expected_entities[1]
        result = structured.traverse(source, target=target, max_depth=2)
        got_path = result.path if result.found else ()
        ok = got_path == q.expected_path
        correct += ok
        rows.append((q.id, ok, q.expected_path, got_path))
    accuracy = correct / len(scored) if scored else None
    return accuracy, rows


# -- Vector Retrieval (Recall@K, Context Precision) ----------------------------


def _vector_retrieval_metrics(questions: Iterable[EvalQuestion], vector: ChromaVectorIndex):
    scored = [q for q in questions if q.category == "entity_discovery"]
    recalls, precisions, rows = [], [], []
    for q in scored:
        hits = vector.semantic_search(q.question, k=_VECTOR_K).hits
        retrieved = {h.entity for h in hits}
        want = set(q.expected_entities)
        tp = len(retrieved & want)
        recall_at_k = tp / len(want) if want else None
        context_precision = tp / len(retrieved) if retrieved else 0.0
        if recall_at_k is not None:
            recalls.append(recall_at_k)
        precisions.append(context_precision)
        rows.append((q.id, recall_at_k, context_precision, sorted(retrieved)))
    return (
        mean(recalls) if recalls else None,
        mean(precisions) if precisions else None,
        rows,
    )


# -- Full pipeline pass (grounding, refusal, faithfulness, relevancy) ---------


def _run_full_pipeline(
    questions: Iterable[EvalQuestion],
    structured: SQLiteStructuredIndex,
    vector: ChromaVectorIndex,
    llm: LLM,
    known_entities: frozenset[str],
) -> list[tuple[EvalQuestion, QueryResponse | None, str | None]]:
    results: list[tuple[EvalQuestion, QueryResponse | None, str | None]] = []
    for q in questions:
        try:
            response = answer_query(q.question, structured, vector, llm, known_entities)
            results.append((q, response, None))
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any LLM-call failure
            # (missing/invalid ANTHROPIC_API_KEY, network, rate limit, ...) must
            # not abort the whole eval run; the question is just marked unavailable.
            results.append((q, None, str(exc)))
    return results


def _refusal_accuracy(results):
    scored = [(q, r) for q, r, err in results if r is not None]
    if not scored:
        return None, None, []
    tp = fp = fn = tn = 0
    rows = []
    for q, r in scored:
        refused = not r.grounded
        if q.expect_refusal and refused:
            tp += 1
        elif q.expect_refusal and not refused:
            fn += 1
        elif not q.expect_refusal and refused:
            fp += 1
        else:
            tn += 1
        rows.append((q.id, q.expect_refusal, refused))
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    return precision, recall, rows


def _faithfulness(results):
    """RAGAS Faithfulness, mapped operationally onto the Grounding Validator's
    supported-claim check (ADR-0010, ADR-0017) — only meaningful on the
    semantic/LLM-generation route; templated answers trivially pass."""
    scored = [r for _, r, err in results if r is not None and r.route == "semantic"]
    if not scored:
        return None, 0
    supported = sum(1 for r in scored if r.verified)
    return supported / len(scored), len(scored)


def _completeness(results):
    scored = [
        (q, r) for q, r, err in results if r is not None and q.expected_attributes and q.category != "adversarial"
    ]
    if not scored:
        return None
    rates = []
    for q, r in scored:
        present = sum(1 for a in q.expected_attributes if a in r.answer)
        rates.append(present / len(q.expected_attributes))
    return mean(rates)


def _answer_relevancy(results):
    """Simplified, operational proxy for RAGAS Answer Relevancy: does the
    answer explicitly engage with the entity/entities the question was
    about? Not RAGAS's embedding-similarity computation — a deliberate
    simplification appropriate to a ~25-question dataset, per
    docs/quality/evaluation-strategy.md's own "not a complicated evaluation
    framework" guidance."""
    scored = [(q, r) for q, r, err in results if r is not None and q.expected_entities]
    if not scored:
        return None
    rates = []
    for q, r in scored:
        mentioned = sum(1 for e in q.expected_entities if _bare(e) in r.answer or e in r.answer)
        rates.append(mentioned / len(q.expected_entities))
    return mean(rates)


def _llm_unavailable_count(results) -> int:
    return sum(1 for _, r, err in results if r is None)


def _diagnostics_section(entity_rows, attr_rows, rel_rows, path_rows, vec_rows, refusal_rows) -> str:
    """Failures only, per stage — the diagnosability ADR-0017 exists for:
    a bad result should be traceable to entity mismatch, structured-lookup
    gap, traversal miss, or vector-recall miss, not one opaque "wrong"."""
    parts = ["## Stage Diagnostics (failures only)", ""]
    start_len = len(parts)

    entity_failures = [row for row in entity_rows if not row[1]]
    if entity_failures:
        parts.append("**Entity matching:**")
        parts += [f"- {qid}: expected {want}, got {got}" for qid, _ok, want, got in entity_failures]

    path_failures = [row for row in path_rows if not row[1]]
    if path_failures:
        parts.append("\n**Traversal path correctness:**")
        parts += [
            f"- {qid}: expected {want or '(not found)'}, got {got or '(not found)'}"
            for qid, _ok, want, got in path_failures
        ]

    low_attr = [row for row in attr_rows if row[1] < 1.0 or row[2] < 1.0]
    if low_attr:
        parts.append("\n**Structured attribute retrieval (< 100% precision or recall):**")
        parts += [f"- {qid}: precision={p:.2f}, recall={r:.2f}" for qid, p, r in low_attr]

    low_rel = [row for row in rel_rows if row[1] < 1.0 or row[2] < 1.0]
    if low_rel:
        parts.append("\n**Single-hop relationship retrieval (< 100% precision or recall):**")
        parts += [f"- {qid}: precision={p:.2f}, recall={r:.2f}" for qid, p, r in low_rel]

    low_vec = [row for row in vec_rows if row[1] is not None and row[1] < 1.0]
    if low_vec:
        parts.append("\n**Vector retrieval (< 100% Recall@K):**")
        parts += [f"- {qid}: recall={recall:.2f}, retrieved={retrieved}" for qid, recall, _p, retrieved in low_vec]

    refusal_failures = [row for row in refusal_rows if row[1] != row[2]]
    if refusal_failures:
        parts.append("\n**Refusal decision (expected vs. actual):**")
        parts += [
            f"- {qid}: expected refusal={expected}, got refusal={actual}"
            for qid, expected, actual in refusal_failures
        ]

    if len(parts) == start_len:
        parts.append("All stage-level checks passed exactly.")

    return "\n".join(parts) + "\n"


# -- Report rendering -----------------------------------------------------------


def _render_report(
    structured: SQLiteStructuredIndex, vector: ChromaVectorIndex, llm: LLM
) -> tuple[str, dict]:
    known_entities = frozenset(structured.list_entities())
    questions = EVAL_QUESTIONS

    data_quality = _data_quality_metrics()
    entity_accuracy, entity_rows = _entity_matching_accuracy(questions, known_entities)
    attr_precision, attr_recall, attr_rows = _structured_retrieval_pr(questions, structured)
    rel_precision, rel_recall, rel_rows = _relationship_pr(questions, structured)
    path_accuracy, path_rows = _traversal_correctness(questions, structured)
    vec_recall, vec_precision, vec_rows = _vector_retrieval_metrics(questions, vector)

    results = _run_full_pipeline(questions, structured, vector, llm, known_entities)
    refusal_precision, refusal_recall, refusal_rows = _refusal_accuracy(results)
    faithfulness, faithfulness_n = _faithfulness(results)
    completeness = _completeness(results)
    relevancy = _answer_relevancy(results)
    unavailable = _llm_unavailable_count(results)

    dataset_line = (
        f"Dataset: {len(questions)} questions across 8 categories "
        "(`tests/eval/dataset.py`). Produced by `task eval:run` — CI/CD slow gate (ADR-0019)."
    )
    faithfulness_line = (
        "- Faithfulness (Grounding Validator supported-claim rate, semantic-path only): "
        f"{_pct(faithfulness)} ({faithfulness_n} questions reached generation)"
    )
    relevancy_line = (
        "- Answer relevancy (expected entities engaged in answer text, simplified proxy — see module docstring): "
        f"{_pct(relevancy)}"
    )
    vector_line = (
        f"- Vector Recall@{_VECTOR_K}: {_pct(vec_recall)}; Context Precision: {_pct(vec_precision)} "
        "(entity_discovery's expected_entities are illustrative samples, not an "
        "exhaustive relevant set, so Context Precision reads low by construction "
        "— Recall@K is the meaningful number for this category)"
    )

    lines = [
        "# Evaluation Report",
        "",
        dataset_line,
        "",
        _data_quality_section(data_quality),
        "## Retrieval Quality",
        "",
        f"- Entity-matching accuracy: {_pct(entity_accuracy)} ({len(entity_rows)} questions)",
        f"- Structured attribute retrieval — precision: {_pct(attr_precision)}, recall: {_pct(attr_recall)}",
        f"- Single-hop relationship retrieval — precision: {_pct(rel_precision)}, recall: {_pct(rel_recall)}",
        f"- Graph traversal path correctness: {_pct(path_accuracy)} ({len(path_rows)} questions)",
        vector_line,
        "",
        "## Answer Quality",
        "",
        f"- Refusal accuracy — precision: {_pct(refusal_precision)}, recall: {_pct(refusal_recall)}",
        faithfulness_line,
        f"- Answer completeness (expected attributes present in answer text): {_pct(completeness)}",
        relevancy_line,
    ]
    if unavailable:
        lines.append(
            f"\n> {unavailable} question(s) could not be scored end-to-end — "
            "no live LLM call succeeded (ANTHROPIC_API_KEY missing/invalid, or a "
            "network error). Every metric above except Faithfulness and Answer "
            "Relevancy is independent of this and is fully computed."
        )

    lines += ["", _diagnostics_section(entity_rows, attr_rows, rel_rows, path_rows, vec_rows, refusal_rows)]

    lines += ["", "## Per-Question Detail", ""]
    lines.append("| ID | Category | Route | Grounded | Verified | Notes |")
    lines.append("|---|---|---|---|---|---|")
    for q, r, err in results:
        if r is not None:
            lines.append(f"| {q.id} | {q.category} | {r.route} | {r.grounded} | {r.verified} | |")
        else:
            lines.append(f"| {q.id} | {q.category} | - | - | - | unavailable: {err} |")

    kpis = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%d"),
        "question_count": len(questions),
        "data_quality": {
            "entity_resolution_rate": data_quality["resolution_rate"],
            "unresolved_reference_rate": data_quality["unresolved_rate"],
        },
        "retrieval": {
            "entity_matching_accuracy": entity_accuracy,
            "structured_precision": attr_precision,
            "structured_recall": attr_recall,
            "relationship_precision": rel_precision,
            "relationship_recall": rel_recall,
            "traversal_accuracy": path_accuracy,
            "vector_recall_at_k": vec_recall,
            "vector_context_precision": vec_precision,
        },
        "answer_quality": {
            "refusal_precision": refusal_precision,
            "refusal_recall": refusal_recall,
            "faithfulness": faithfulness,
            "faithfulness_n": faithfulness_n,
            "completeness": completeness,
            "relevancy": relevancy,
        },
        "unavailable_count": unavailable,
    }

    return "\n".join(lines) + "\n", kpis


# UI KPI snapshot (ADR-0026) — baked into the UI bundle at build time, not
# fetched live, so showing it costs nothing and needs no backend endpoint.
_UI_SNAPSHOT_PATH = "ui/src/eval-snapshot.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the evaluation dataset and produce a KPI report.")
    parser.add_argument("--report", default="docs/eval-report.md")
    parser.add_argument("--ui-snapshot", default=_UI_SNAPSHOT_PATH)
    args = parser.parse_args()

    structured = SQLiteStructuredIndex(db_path=_DB_PATH)
    vector = ChromaVectorIndex(persist_path=_CHROMA_PATH)
    llm = build_llm()

    report, kpis = _render_report(structured, vector, llm)
    with open(args.report, "w") as f:
        f.write(report)
    print(f"Wrote {args.report}")

    with open(args.ui_snapshot, "w") as f:
        json.dump(kpis, f, indent=2)
        f.write("\n")
    print(f"Wrote {args.ui_snapshot}")


if __name__ == "__main__":
    main()
