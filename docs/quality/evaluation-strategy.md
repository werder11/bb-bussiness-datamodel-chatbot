# Evaluation Strategy

Evaluation is a first-class layer spanning ingestion, retrieval, and generation — not a category of unit test ([ADR-0017](../adr/0017-evaluation-as-first-class-layer.md)). It measures three things independently, matching [Architecture: Components](../architecture/components.md):

```
                         Evaluation
                             │
          ┌──────────────────┼──────────────────┐
          ↓                  ↓                  ↓
    Data Quality        Retrieval Quality    Answer Quality
          │                  │                  │
   schema validity      entity matching      faithfulness /
   relationship           accuracy          supported-claim rate
   resolution            structured P/R      answer relevancy
   completeness           path correctness    completeness
   (Validation Pass)      Recall@K, context    refusal accuracy
                          precision/recall
                          (vector path)
```

## Per-Stage Query Path

Rather than grading only the final response, each stage is measured independently so a bad answer is diagnosable — entity mismatch, retrieval miss, or generation embellishment, not one opaque "wrong":

```
                    Query
                      │
             ┌────────┴────────┐
             ↓                 ↓
       Entity Resolution    Intent Classification
             │                 │
             └────────┬────────┘
                       ↓
                Retrieval Quality
                       │
                       ↓
                Evidence Quality
                       │
                       ↓
                Generation Quality
                       │
                       ↓
               Grounding / Refusal
```

## KPI Table

Named, industry-recognized metrics are used wherever one fits, rather than inventing bespoke ones — stronger, checkable positioning for "non-hallucinated" than a prompt instruction. RAGAS defines Faithfulness, Answer Relevancy, Context Precision, and Context Recall for RAG systems specifically; ISTQB CT-AI v2.0 anchors data-quality characteristics in ISO/IEC 25059 and names accuracy/precision/recall/F1 as standard ML functional-performance metrics.

| Layer | Metric | Standard / Source | What it's computed from |
|---|---|---|---|
| Data Quality (ingestion) | Entity resolution rate, unresolved-reference rate | ISTQB CT-AI v2.0 (ISO/IEC 25059 data-quality characteristics) | Validation Pass summary ([ADR-0014](../adr/0014-explicit-validation-pass.md)) |
| Entity Resolution | Accuracy | Standard classification metric | Eval set: expected entity vs. matched entity |
| Structured Retrieval | Precision / Recall | Standard IR | Eval set: expected attribute/relationship set vs. retrieved set |
| Relationship Traversal | Path correctness | Graph-specific (project-defined) | Eval set: expected path vs. traversed path, within the depth-2 cap ([ADR-0009](../adr/0009-relationship-traversal-bounded-to-depth-2.md)) |
| Vector Retrieval | Recall@K, Context Precision, Context Recall | Standard IR (Recall@K) + RAGAS (Context Precision/Recall) | Eval set questions routed to the semantic path |
| Grounding (LLM path) | Faithfulness / supported-claim rate | RAGAS (Faithfulness) | Grounding Validator output ([ADR-0010](../adr/0010-post-generation-grounding-verification.md)) |
| Answer Quality | Answer Relevancy, completeness | RAGAS (Answer Relevancy) + project-defined completeness check | Generated/templated answer vs. expected answer |
| Out-of-scope handling | Refusal accuracy (precision/recall on the refusal decision) | Standard classification metric, applied to a binary refuse/answer decision | Eval set's deliberately out-of-scope questions |

RAGAS's LLM-graded metrics (Faithfulness, Answer Relevancy) apply to the **LLM-generation path only** — template-rendered deterministic answers ([ADR-0016](../adr/0016-deterministic-hits-template-rendered.md)) are checked by exact-match correctness instead, since there's no generative variance to score.

## Evaluation Dataset

A small, version-controlled dataset of ~20-30 questions, schema-validated like everything else ([ADR-0021](../adr/0021-schema-based-design-at-port-boundaries.md)), covering:

- **Entity discovery** — "What banking entities are available?"
- **Attribute retrieval** — "What are the core attributes of Account?"
- **Relationship retrieval** — "How does Contact relate to Organization?"
- **Multi-hop relationships** — questions requiring the bounded graph traversal ([ADR-0009](../adr/0009-relationship-traversal-bounded-to-depth-2.md))
- **Paraphrased questions** — tests the Entity Matcher and Intent Classification ([ADR-0011](../adr/0011-entity-name-matching-closed-vocabulary.md), [ADR-0006](../adr/0006-intent-classification-swappable-strategy.md))
- **Ambiguous questions** — especially the Account/Contact name collision ([Domain](../domain/domain-model.md#name-collision-account-and-contact))
- **Out-of-scope questions** — entities outside the ingested corpus; concepts outside the selected CDM scope
- **Adversarial / hallucination-probing questions** — questions containing plausible but nonexistent attributes or relationships, specifically designed to try to make the system fabricate rather than refuse

For a dataset this size, manual review plus the deterministic checks above is the right level of tooling — not a complicated evaluation framework. This is distinct from the ingestion Validation Pass ([ADR-0014](../adr/0014-explicit-validation-pass.md)): validation checks the Canonical Model's internal integrity; the eval set checks end-to-end answer quality. Both are demoable evidence for the walkthrough slides.

Dataset and runner live under `tests/eval/` ([Design: Subsystem Design](../design/subsystem-design.md#project-layout)), invoked via `task eval:run` on the CI/CD slow gate only ([Operations: CI/CD](../operations/ci-cd.md)).

## Evaluation as an Architecture Feedback Loop

The evaluation set isn't graded once and filed away — it's the mechanism that tunes the architecture's own tunables:

```
             Source CDM
                 │
                 ▼
        Canonical Data Model
                 │
                 ▼
             Retrieval
                 │
                 ▼
             Generation
                 │
                 ▼
             Evaluation
                 │
                 └──────────────┐
                                ▼
                         Architecture /
                         retrieval tuning
```

Concretely, the eval set tunes: the Grounding Guard's vector similarity cutoff ([ADR-0005](../adr/0005-explicit-grounding-guard-before-generation.md)), the chunking strategy (once decided, [`FINDINGS.md §7`](../../FINDINGS.md#7-open-architecture-decisions)), Entity Matcher fuzzy-match behavior ([ADR-0011](../adr/0011-entity-name-matching-closed-vocabulary.md)), the graph traversal depth cap ([ADR-0009](../adr/0009-relationship-traversal-bounded-to-depth-2.md)), Intent Classification routing rules ([ADR-0006](../adr/0006-intent-classification-swappable-strategy.md)), the Grounding Validator's matching strategy ([ADR-0010](../adr/0010-post-generation-grounding-verification.md)), and generation prompts once an LLM adapter is chosen.

This is the point of treating evaluation as architecture, not an afterthought: **"non-hallucinating RAG" is an empirically evaluated property, not a prompt instruction.**
