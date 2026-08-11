# Goals

## The problem

This is a take-home case study for a **Senior Data & AI Architect** role at **reeeliance** (3rd interview stage). The full task brief is [`Business data model chatbot - task for Senior Data & AI Architect.pdf`](../../Business%20data%20model%20chatbot%20-%20task%20for%20Senior%20Data%20%26%20AI%20Architect.pdf); the working research log behind it is [`FINDINGS.md`](../../FINDINGS.md).

reeeliance helps clients achieve "AI Readiness" — moving from heterogeneous data to standardized, semantic models. The Microsoft Common Data Model (CDM) is exactly that kind of shared language for business entities. The ask: build a RAG-based API that lets someone ask natural-language questions about the CDM's Banking Model — which entities exist, their attributes, their relationships — and get answers grounded in the actual schema, not hallucinated.

## Who it's for

- **The graders** (reeeliance's technical interview panel), evaluating architecture judgment, code quality, and whether "non-hallucinated" is a real, checked property or just a claim.
- **A demo user**, asking the two example questions from the brief ("What are the core attributes of Account?", "How does Contact relate to Organization?") and variations of them, live.
- **Future maintainers** (hypothetically) — every decision here is recorded so the reasoning survives past this take-home, which is also just good practice.

## What "good" looks like

Restated from the functional/non-functional requirements in [`docs/architecture/README.md`](../architecture/README.md#requirements):

- Correct, grounded answers to attribute and relationship questions — including relationship questions that require more than one hop, since the brief's own example ("Contact ↔ Organization") turns out to need exactly that ([FINDINGS §5](../../FINDINGS.md#5-the-core-challenge-multi-hop-attribute--relationship-resolution)).
- A clear refusal, not a guess, for anything outside the ingested scope.
- Quality that's *measured*, not asserted — see [Quality](../quality/README.md).
- Judgment visible in what was deliberately **not** built, as much as in what was ([`docs/architecture/principles.md`](../architecture/principles.md#whats-deliberately-not-built-and-why)).

## Positioning for the technical walkthrough

One framing worth carrying into the 4-slide walkthrough and the live demo Q&A, since it ties the whole system together:

> Microsoft CDM is treated as an external semantic source. It's resolved into a vendor-independent Canonical Model, then projected two ways for two different purposes: a relational projection for deterministic data access, and a semantic projection for retrieval over free-text descriptions. The AI layer sits *above* this data architecture rather than replacing it — the LLM is invoked only where semantic interpretation genuinely adds value, not for operations the data layer can already answer deterministically. Evaluation measures each stage independently, using named, industry-recognized metrics (RAGAS, ISTQB CT-AI-aligned data quality), so that retrieval quality, grounding, and answer quality are measurable and continuously improvable — not just asserted.

This is the throughline for the "embedding strategy" and "how did you handle relationships" slide questions specifically: embeddings answer the semantic-projection half ([`docs/architecture/containers.md`](../architecture/containers.md)); the Resolver/Validation/traversal design answers the relationships half ([`docs/architecture/components.md`](../architecture/components.md), [`docs/adr/`](../adr/README.md)); the [Quality KPI table](../quality/evaluation-strategy.md#kpi-table) is the evidence that both actually work.
