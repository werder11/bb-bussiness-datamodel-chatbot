import { getEntity, listEntities, postEvaluate, postQuery } from "./api";
import evalSnapshotData from "./eval-snapshot.json";
import type {
  AnswerComparison,
  EntityDetailResponse,
  EvalSnapshot,
  PipelineStage,
  QueryResponse,
} from "./types";

const evalSnapshot = evalSnapshotData as EvalSnapshot;

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  opts: { class?: string; text?: string } = {},
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (opts.class) node.className = opts.class;
  if (opts.text !== undefined) node.textContent = opts.text;
  return node;
}

function byId<T extends HTMLElement>(id: string): T {
  const node = document.getElementById(id);
  if (!node) throw new Error(`missing #${id}`);
  return node as T;
}

// -- Entity panel -----------------------------------------------------------

const entityList = byId<HTMLUListElement>("entity-list");
const entityFilter = byId<HTMLInputElement>("entity-filter");
const detailPanel = byId<HTMLElement>("detail-panel");
const detailContent = byId<HTMLDivElement>("detail-content");
const detailClose = byId<HTMLButtonElement>("detail-close");

let allEntities: string[] = [];

function renderEntityList(filterText: string): void {
  const needle = filterText.trim().toLowerCase();
  const visible = needle ? allEntities.filter((e) => e.toLowerCase().includes(needle)) : allEntities;

  entityList.replaceChildren(
    ...visible.map((name) => {
      const li = el("li");
      const button = el("button", { text: name });
      button.type = "button";
      button.addEventListener("click", () => void openEntityDetail(name));
      li.appendChild(button);
      return li;
    }),
  );
}

async function openEntityDetail(name: string): Promise<void> {
  detailPanel.hidden = false;
  detailContent.replaceChildren(el("p", { class: "loading", text: `Loading ${name}...` }));

  try {
    const detail = await getEntity(name);
    renderEntityDetail(detail);
  } catch (err) {
    detailContent.replaceChildren(
      el("p", { class: "error", text: err instanceof Error ? err.message : String(err) }),
    );
  }
}

function renderEntityDetail(detail: EntityDetailResponse): void {
  const container = el("div");
  container.appendChild(el("h2", { text: detail.entity }));

  container.appendChild(el("h3", { text: `Attributes (${detail.attributes.length})` }));
  const attrList = el("ul", { class: "attr-list" });
  for (const attr of detail.attributes) {
    const li = el("li");
    li.appendChild(el("span", { class: "attr-name", text: attr.name }));
    li.appendChild(el("span", { class: "attr-type", text: attr.data_type }));
    if (attr.description) li.appendChild(el("p", { class: "attr-desc", text: attr.description }));
    attrList.appendChild(li);
  }
  container.appendChild(attrList);

  container.appendChild(el("h3", { text: `Relationships (${detail.relationships.length})` }));
  const relList = el("ul", { class: "rel-list" });
  for (const rel of detail.relationships) {
    const li = el("li");
    li.appendChild(el("span", { class: "rel-name", text: rel.name }));
    li.appendChild(el("span", { class: "rel-kind", text: rel.kind }));
    li.appendChild(el("p", { class: "rel-targets", text: rel.targets.join(", ") }));
    relList.appendChild(li);
  }
  container.appendChild(relList);

  detailContent.replaceChildren(container);
}

detailClose.addEventListener("click", () => {
  detailPanel.hidden = true;
});

// -- Info panel -------------------------------------------------------------
// Reuses the same slide-over as entity detail — one "read more" pattern for
// the whole app, not a second accordion/modal bolted on separately. The
// legend below is built from the real .badge/.route-* classes that
// renderAnswer() already emits, so it's never at risk of drifting out of
// sync with what a real answer actually shows.

interface RouteLegendEntry {
  route: QueryResponse["route"];
  explanation: string;
}

const ROUTE_LEGEND: RouteLegendEntry[] = [
  {
    route: "structured",
    explanation: "Direct attribute or single-hop relationship. Template-rendered — the model is never called.",
  },
  {
    route: "traversal",
    explanation: "A bounded two-hop relationship path. Same as structured: template-rendered, not generated.",
  },
  {
    route: "semantic",
    explanation: "No deterministic hit. The model answers from retrieved context only — nothing else.",
  },
  {
    route: "none",
    explanation:
      "Nothing relevant was retrieved, or the name exists in two namespaces and needs disambiguating. Refusing is correct here, not a failure.",
  },
];

function openInfoPanel(): void {
  const container = el("div");
  container.appendChild(el("h2", { text: "How this works" }));
  container.appendChild(
    el("div", { class: "info-trace", text: "question → match entity → route → answer" }),
  );
  container.appendChild(
    el("p", {
      class: "info-intro",
      text: "Every question is checked against the 44 ingested CDM entities, then routed automatically. Two of the four routes never touch the model at all.",
    }),
  );

  const routeLegend = el("ul", { class: "legend-list" });
  for (const entry of ROUTE_LEGEND) {
    const li = el("li");
    li.appendChild(el("span", { class: `badge route-${entry.route}`, text: routeLabel(entry.route) }));
    li.appendChild(el("p", { text: entry.explanation }));
    routeLegend.appendChild(li);
  }
  container.appendChild(routeLegend);

  const groundingLegend = el("ul", { class: "legend-list" });
  const groundedLi = el("li");
  groundedLi.appendChild(el("span", { class: "badge badge-ok", text: "grounded" }));
  groundedLi.appendChild(el("p", { text: "Real evidence was retrieved before answering." }));
  groundingLegend.appendChild(groundedLi);
  const verifiedLi = el("li");
  verifiedLi.appendChild(el("span", { class: "badge badge-ok", text: "verified" }));
  verifiedLi.appendChild(
    el("p", {
      text: "The answer's claims all check out against that evidence. If they didn't, you'd see a refusal instead of an unverified answer.",
    }),
  );
  groundingLegend.appendChild(verifiedLi);
  container.appendChild(groundingLegend);

  container.appendChild(
    el("p", {
      class: "info-footer",
      text: "Microsoft Common Data Model — Banking + common objects, 44 entities.",
    }),
  );

  detailContent.replaceChildren(container);
  detailPanel.hidden = false;
}

byId<HTMLButtonElement>("info-button").addEventListener("click", openInfoPanel);

// -- Evaluation panel ---------------------------------------------------
// A build-time snapshot of the last real `task eval:run` (ADR-0026) — not
// a live value, so viewing it costs nothing and needs no backend endpoint.
// Reuses the same slide-over as the info/entity panels.

function fmtPct(value: number | null): string {
  return value === null ? "n/a" : `${Math.round(value * 100)}%`;
}

function kpiTier(value: number): "kpi-good" | "kpi-mid" | "kpi-low" {
  if (value >= 0.9) return "kpi-good";
  if (value >= 0.7) return "kpi-mid";
  return "kpi-low";
}

function kpiRow(label: string, value: number | null, note?: string): HTMLElement {
  const row = el("div", { class: "kpi-row" });
  const head = el("div", { class: "kpi-row-head" });
  head.appendChild(el("span", { class: "kpi-row-label", text: label }));
  head.appendChild(el("span", { class: "kpi-row-value", text: fmtPct(value) }));
  row.appendChild(head);

  if (value !== null) {
    const track = el("div", { class: "kpi-bar-track" });
    const fill = el("div", { class: `kpi-bar-fill ${kpiTier(value)}` });
    fill.style.width = `${Math.round(value * 100)}%`;
    track.appendChild(fill);
    row.appendChild(track);
  } else {
    row.appendChild(el("p", { class: "kpi-na", text: "No questions exercised this path." }));
  }

  if (note) row.appendChild(el("p", { class: "kpi-row-note", text: note }));
  return row;
}

function openEvalPanel(): void {
  const s = evalSnapshot;
  const container = el("div");
  container.appendChild(el("h2", { text: "Evaluation" }));
  container.appendChild(
    el("p", {
      class: "info-intro",
      text: `Snapshot from the last live \`task eval:run\` — ${s.question_count} questions across 8 categories, generated ${s.generated_at}. Not live: this doesn't run on page load, since the answer-quality metrics need real LLM calls.`,
    }),
  );

  container.appendChild(el("p", { class: "kpi-section-title", text: "Retrieval quality" }));
  container.appendChild(kpiRow("Entity-matching accuracy", s.retrieval.entity_matching_accuracy));
  container.appendChild(kpiRow("Structured attribute precision", s.retrieval.structured_precision));
  container.appendChild(kpiRow("Structured attribute recall", s.retrieval.structured_recall));
  container.appendChild(kpiRow("Relationship precision", s.retrieval.relationship_precision));
  container.appendChild(kpiRow("Relationship recall", s.retrieval.relationship_recall));
  container.appendChild(kpiRow("Traversal path correctness", s.retrieval.traversal_accuracy));
  container.appendChild(kpiRow(`Vector Recall@5`, s.retrieval.vector_recall_at_k));
  container.appendChild(
    kpiRow(
      "Vector context precision",
      s.retrieval.vector_context_precision,
      "Reads low by construction — the expected-entities list for this category is an illustrative sample, not an exhaustive relevant set. Recall@K is the meaningful number here.",
    ),
  );

  container.appendChild(el("p", { class: "kpi-section-title", text: "Answer quality" }));
  container.appendChild(kpiRow("Refusal precision", s.answer_quality.refusal_precision));
  container.appendChild(kpiRow("Refusal recall", s.answer_quality.refusal_recall));
  container.appendChild(
    kpiRow(
      "Faithfulness",
      s.answer_quality.faithfulness,
      `${s.answer_quality.faithfulness_n} question(s) reached generation — templated answers trivially pass and aren't counted here.`,
    ),
  );
  container.appendChild(kpiRow("Answer completeness", s.answer_quality.completeness));
  container.appendChild(kpiRow("Answer relevancy", s.answer_quality.relevancy));

  container.appendChild(el("p", { class: "kpi-section-title", text: "Data quality" }));
  container.appendChild(kpiRow("Entity resolution rate", s.data_quality.entity_resolution_rate));
  container.appendChild(
    kpiRow(
      "Unresolved relationship references",
      s.data_quality.unresolved_reference_rate,
      "Informational, not a defect count — references outside this project's deliberately scoped 44-entity corpus.",
    ),
  );

  if (s.unavailable_count > 0) {
    container.appendChild(
      el("p", {
        class: "info-footer",
        text: `${s.unavailable_count} question(s) weren't scored end-to-end in this run — no live LLM call succeeded (key missing/invalid, rate limit, or a network error). Every metric above except Faithfulness and Answer Relevancy is unaffected by this.`,
      }),
    );
  }

  detailContent.replaceChildren(container);
  detailPanel.hidden = false;
}

byId<HTMLButtonElement>("eval-button").addEventListener("click", openEvalPanel);

// -- Score-an-answer panel -----------------------------------------------
// The interactive counterpart to the static snapshot above: type any
// question plus the answer you'd expect, and this runs the real pipeline
// (same code path as the chat box — real entity match, real retrieval,
// a real LLM call on the semantic route) and compares what it actually
// said to what you typed. Comparison is a plain word-overlap check
// (app/domain/comparison.py) — no external eval framework, no embedding
// model, nothing beyond what the pipeline already computes. The pipeline
// view is always shown here (unlike the chat box, where it's opt-in),
// since the entire point of this panel is inspecting one answer closely.

function similarityBar(value: number): HTMLElement {
  const track = el("div", { class: "kpi-bar-track" });
  const fill = el("div", { class: `kpi-bar-fill ${kpiTier(value)}` });
  fill.style.width = `${Math.round(value * 100)}%`;
  track.appendChild(fill);
  return track;
}

function termsRow(label: string, terms: string[], chipClass: string, empty: string): HTMLElement {
  const block = el("div");
  block.appendChild(el("p", { class: "stage-detail-line", text: label }));
  if (terms.length === 0) {
    block.appendChild(el("p", { class: "stage-detail-line dim", text: empty }));
    return block;
  }
  const row = el("div", { class: "chip-row" });
  terms.forEach((term) => row.appendChild(el("span", { class: `chip ${chipClass}`, text: term })));
  block.appendChild(row);
  return block;
}

function renderComparison(comparison: AnswerComparison): HTMLElement {
  const box = el("div", { class: "comparison-block" });
  const head = el("div", { class: "kpi-row-head" });
  head.appendChild(el("span", { class: "kpi-row-label", text: "Text similarity" }));
  head.appendChild(el("span", { class: "kpi-row-value", text: `${Math.round(comparison.similarity * 100)}%` }));
  box.appendChild(head);
  box.appendChild(similarityBar(comparison.similarity));

  box.appendChild(
    termsRow("Shared terms (in both):", comparison.shared_terms, "chip-found", "No overlapping terms."),
  );
  box.appendChild(
    termsRow(
      "Missing (in your desired answer, not in the real one):",
      comparison.missing_terms,
      "chip-missing",
      "Nothing missing — every term in your desired answer showed up in the real answer.",
    ),
  );
  box.appendChild(
    termsRow(
      "Extra (in the real answer, not in your desired one):",
      comparison.extra_terms,
      "chip-extra",
      "The real answer didn't introduce anything beyond your desired answer.",
    ),
  );

  return box;
}

function openEvaluatePanel(): void {
  const container = el("div");
  container.appendChild(el("h2", { text: "Score an answer" }));
  container.appendChild(
    el("p", {
      class: "info-intro",
      text: "Ask a real question, then type the answer you'd expect. This runs the real pipeline — same code as the chat box — and compares its actual answer to yours by word overlap. Not a RAGAS/DeepEval call, just a transparent, zero-cost comparison.",
    }),
  );

  const form = el("form", { class: "evaluate-form" });
  const questionInput = el("input", { class: "evaluate-input" }) as HTMLInputElement;
  questionInput.type = "text";
  questionInput.placeholder = "e.g. What are the attributes of banking:Account?";
  questionInput.required = true;
  questionInput.autocomplete = "off";

  const answerInput = el("textarea", { class: "evaluate-textarea" }) as HTMLTextAreaElement;
  answerInput.placeholder = "The answer you'd expect...";
  answerInput.required = true;
  answerInput.rows = 3;

  const submitBtn = el("button", { text: "Run comparison" });
  submitBtn.type = "submit";

  form.appendChild(el("label", { class: "evaluate-label", text: "Question" }));
  form.appendChild(questionInput);
  form.appendChild(el("label", { class: "evaluate-label", text: "Desired answer" }));
  form.appendChild(answerInput);
  form.appendChild(submitBtn);

  const results = el("div", { class: "evaluate-results" });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const question = questionInput.value.trim();
    const expectedAnswer = answerInput.value.trim();
    if (!question || !expectedAnswer) return;

    submitBtn.disabled = true;
    results.replaceChildren(el("p", { class: "loading", text: "Running the real pipeline..." }));

    postEvaluate(question, expectedAnswer)
      .then((response) => {
        const box = el("div");
        box.appendChild(renderAnswer(response.query, { showPipeline: true }));
        box.appendChild(el("p", { class: "kpi-section-title", text: "Comparison" }));
        box.appendChild(renderComparison(response.comparison));
        results.replaceChildren(box);
      })
      .catch((err) => {
        results.replaceChildren(
          el("p", { class: "error", text: err instanceof Error ? err.message : String(err) }),
        );
      })
      .finally(() => {
        submitBtn.disabled = false;
      });
  });

  container.appendChild(form);
  container.appendChild(results);

  detailContent.replaceChildren(container);
  detailPanel.hidden = false;
}

byId<HTMLButtonElement>("evaluate-button").addEventListener("click", openEvaluatePanel);

const pipelineToggle = byId<HTMLButtonElement>("pipeline-toggle");
pipelineToggle.addEventListener("click", () => {
  pipelineViewEnabled = !pipelineViewEnabled;
  pipelineToggle.setAttribute("aria-pressed", String(pipelineViewEnabled));
  pipelineToggle.classList.toggle("active", pipelineViewEnabled);
});

entityFilter.addEventListener("input", () => renderEntityList(entityFilter.value));

async function loadEntities(): Promise<void> {
  try {
    const { entities } = await listEntities();
    allEntities = [...entities].sort();
    renderEntityList("");
  } catch (err) {
    entityList.replaceChildren(
      el("li", { class: "error", text: err instanceof Error ? err.message : String(err) }),
    );
  }
}

// -- Chat panel ---------------------------------------------------------

const messages = byId<HTMLDivElement>("messages");
const form = byId<HTMLFormElement>("query-form");
const input = byId<HTMLInputElement>("question-input");

function routeLabel(route: QueryResponse["route"]): string {
  switch (route) {
    case "structured":
      return "structured";
    case "traversal":
      return "traversal";
    case "semantic":
      return "semantic (LLM)";
    case "none":
      return "refused";
  }
}

// -- Pipeline view --------------------------------------------------------
// Routing status (done/failed/skipped) is still derived client-side from
// route/verified/error (ADR-0027) — but stage *detail*, and everything a
// clicked node zooms into, now comes from response.debug (ADR-0028): real
// intermediate values captured as the real pipeline computed them, not
// guessed. What used to be an honest gap ("the original Entity Matcher
// output isn't recoverable on the semantic route") is fixed by that field
// existing, not just documented as unrecoverable.

let pipelineViewEnabled = false;

function deriveStages(response: QueryResponse): PipelineStage[] {
  const { route, verified, answer, error, debug } = response;
  const matchDetail = `${debug.entity_match_kind}${debug.entity_match_candidates.length ? ": " + debug.entity_match_candidates.join(", ") : ""}`;

  if (route === "none" && answer.startsWith("That name is ambiguous")) {
    return [
      { name: "Entity Match", status: "failed", detail: matchDetail },
      { name: "Router", status: "skipped", detail: "never reached" },
      { name: "Retrieval", status: "skipped" },
      { name: "Grounding Guard", status: "skipped" },
      { name: "Generate (LLM)", status: "skipped" },
      { name: "Validator", status: "skipped" },
    ];
  }

  if (route === "structured" || route === "traversal") {
    return [
      { name: "Entity Match", status: "done", detail: matchDetail },
      { name: "Router", status: "done", detail: `intent: ${debug.intent}` },
      {
        name: "Retrieval",
        status: "done",
        detail: route === "traversal" ? "bounded 2-hop traversal" : "structured index lookup",
      },
      { name: "Grounding Guard", status: "skipped", detail: "not needed — deterministic" },
      { name: "Generate (LLM)", status: "skipped", detail: "template-rendered, model never called" },
      { name: "Validator", status: "skipped", detail: "trivially satisfied by construction" },
    ];
  }

  const passedCutoff = debug.vector_hits.filter((h) => h.passed_cutoff).length;
  const retrievalDetail = `embed query (local) + vector search — ${debug.vector_hits.length} hit(s) considered, ${passedCutoff} passed cutoff`;
  const guardDetail = `cutoff ${debug.similarity_cutoff} — ${passedCutoff}/${debug.vector_hits.length} hit(s) passed`;

  if (route === "semantic" && error !== null) {
    // The LLM call itself failed (rate limit, timeout, ...) — the Validator
    // never ran at all. Without `error`, this looks identical to a real
    // Validator rejection (grounded=true, verified=false) — that conflation
    // is exactly the bug this field exists to fix (found live: a Gemini
    // free-tier quota hit was mislabeled as "Validator failed").
    return [
      { name: "Entity Match", status: "done", detail: matchDetail },
      { name: "Router", status: "done", detail: `intent: ${debug.intent}` },
      { name: "Retrieval", status: "done", detail: retrievalDetail },
      { name: "Grounding Guard", status: "done", detail: guardDetail },
      { name: "Generate (LLM)", status: "failed", detail: error },
      { name: "Validator", status: "skipped", detail: "never reached — the model call failed first" },
    ];
  }

  if (route === "semantic") {
    return [
      { name: "Entity Match", status: "done", detail: matchDetail },
      { name: "Router", status: "done", detail: `intent: ${debug.intent}` },
      { name: "Retrieval", status: "done", detail: retrievalDetail },
      { name: "Grounding Guard", status: "done", detail: guardDetail },
      { name: "Generate (LLM)", status: "done", detail: "model called" },
      {
        name: "Validator",
        status: verified ? "done" : "failed",
        detail: verified
          ? "claims supported by context"
          : `unsupported claim — ${debug.validator_missing_tokens.length} cited term(s) not found in context`,
      },
    ];
  }

  // route === "none", not ambiguous: guard-level refusal (grounded=false) —
  // fell through to semantic search, but nothing cleared the cutoff.
  return [
    { name: "Entity Match", status: "done", detail: matchDetail },
    { name: "Router", status: "done", detail: `intent: ${debug.intent}` },
    { name: "Retrieval", status: "done", detail: retrievalDetail },
    { name: "Grounding Guard", status: "failed", detail: `${guardDetail} — refused before calling the model` },
    { name: "Generate (LLM)", status: "skipped", detail: "model never called" },
    { name: "Validator", status: "skipped" },
  ];
}

// -- Zoom view — clicking a node opens an inline detail drawer directly
// under the track it belongs to (not the side slide-over — the point is to
// stay next to the exact node clicked, since a message bubble can be deep
// in scrollback). One drawer per message; clicking the open node again, or
// a different node, toggles/swaps it.

function scoreBar(score: number, cutoff: number | null): HTMLElement {
  const row = el("div", { class: "hit-row" });
  const pass = cutoff !== null && score >= cutoff;
  row.appendChild(el("span", { class: `hit-score ${pass ? "hit-pass" : "hit-fail"}`, text: score.toFixed(3) }));
  return row;
}

function renderStageDetail(stageName: string, response: QueryResponse): HTMLElement {
  const d = response.debug;
  const box = el("div", { class: "stage-detail" });

  if (stageName === "Entity Match") {
    box.appendChild(el("p", { class: "stage-detail-line", text: `Match kind: ${d.entity_match_kind}` }));
    if (d.entity_match_candidates.length) {
      const list = el("div", { class: "chip-row" });
      d.entity_match_candidates.forEach((name) => {
        const chip = el("button", { class: "entity-chip", text: name });
        chip.type = "button";
        chip.addEventListener("click", () => void openEntityDetail(name));
        list.appendChild(chip);
      });
      box.appendChild(list);
    } else {
      box.appendChild(el("p", { class: "stage-detail-line", text: "No vocabulary mention recognized." }));
    }
    return box;
  }

  if (stageName === "Router") {
    box.appendChild(
      el("p", {
        class: "stage-detail-line",
        text: d.intent ? `Classified intent: ${d.intent}` : "Never reached — the Entity Matcher stopped the query first.",
      }),
    );
    return box;
  }

  if (stageName === "Retrieval") {
    if (d.vector_hits.length === 0) {
      box.appendChild(
        el("p", {
          class: "stage-detail-line",
          text: "Deterministic hit — see the rendered answer above for the exact structured/traversal result.",
        }),
      );
      return box;
    }
    d.vector_hits.forEach((hit) => {
      const row = el("div", { class: "hit-block" });
      const head = el("div", { class: "hit-head" });
      const link = el("button", { class: "entity-link", text: hit.entity });
      link.type = "button";
      link.addEventListener("click", () => void openEntityDetail(hit.entity));
      head.appendChild(link);
      head.appendChild(scoreBar(hit.score, d.similarity_cutoff));
      row.appendChild(head);
      row.appendChild(el("pre", { class: "console-block small", text: hit.snippet }));
      box.appendChild(row);
    });
    return box;
  }

  if (stageName === "Grounding Guard") {
    if (d.vector_hits.length === 0) {
      box.appendChild(el("p", { class: "stage-detail-line", text: "Not needed — the answer came from the deterministic path." }));
      return box;
    }
    box.appendChild(el("p", { class: "stage-detail-line", text: `Similarity cutoff: ${d.similarity_cutoff}` }));
    d.vector_hits.forEach((hit) => {
      const row = el("div", { class: "hit-row" });
      row.appendChild(el("span", { class: "hit-entity", text: hit.entity }));
      row.appendChild(el("span", { class: `hit-score ${hit.passed_cutoff ? "hit-pass" : "hit-fail"}`, text: hit.score.toFixed(3) }));
      row.appendChild(el("span", { class: "hit-verdict", text: hit.passed_cutoff ? "passed" : "cut" }));
      box.appendChild(row);
    });
    return box;
  }

  if (stageName === "Generate (LLM)") {
    const context = d.vector_hits.filter((h) => h.passed_cutoff).map((h) => h.snippet);
    if (context.length === 0 && d.llm_raw_answer === null && response.error === null) {
      box.appendChild(el("p", { class: "stage-detail-line", text: "Template-rendered — the model is never called on this path." }));
      return box;
    }
    box.appendChild(el("p", { class: "stage-detail-line", text: "Context passed to the model:" }));
    box.appendChild(el("pre", { class: "console-block", text: context.join("\n\n") }));
    if (response.error !== null) {
      box.appendChild(el("p", { class: "stage-detail-line", text: "The call itself failed:" }));
      box.appendChild(el("pre", { class: "console-block error", text: response.error }));
    } else if (d.llm_raw_answer !== null) {
      const blocked = !response.verified;
      box.appendChild(
        el("p", { class: "stage-detail-line", text: blocked ? "Raw model output — this is what got blocked, not what you saw:" : "Raw model output:" }),
      );
      box.appendChild(el("pre", { class: `console-block${blocked ? " blocked" : ""}`, text: d.llm_raw_answer }));
    }
    return box;
  }

  // Validator
  if (d.validator_cited_tokens.length === 0 && response.error === null && d.llm_raw_answer === null) {
    box.appendChild(el("p", { class: "stage-detail-line", text: "Trivially satisfied — a template-rendered answer is built only from retrieved facts." }));
    return box;
  }
  if (response.error !== null) {
    box.appendChild(el("p", { class: "stage-detail-line", text: "Never reached — the model call failed before there was anything to validate." }));
    return box;
  }
  box.appendChild(el("p", { class: "stage-detail-line", text: "Capitalized terms cited in the answer, checked against the retrieved context:" }));
  const chipRow = el("div", { class: "chip-row" });
  d.validator_cited_tokens.forEach((token) => {
    const missing = d.validator_missing_tokens.includes(token);
    chipRow.appendChild(el("span", { class: `chip ${missing ? "chip-missing" : "chip-found"}`, text: token }));
  });
  box.appendChild(chipRow);
  if (d.validator_missing_tokens.length === 0) {
    box.appendChild(el("p", { class: "stage-detail-line dim", text: "Every cited term appears in the retrieved context." }));
  }
  return box;
}

function renderPipelineTrace(response: QueryResponse): HTMLElement {
  const wrapper = el("div", { class: "pipeline-wrapper" });
  const track = el("div", { class: "pipeline-track" });
  const drawer = el("div", { class: "pipeline-drawer", text: "" });
  drawer.hidden = true;
  let openStage: string | null = null;

  const stages = deriveStages(response);
  stages.forEach((stage, i) => {
    const node = el("button", { class: `pipeline-node pipeline-${stage.status}` });
    node.type = "button";
    node.title = stage.detail ?? stage.status;
    node.appendChild(el("span", { class: "pipeline-node-name", text: stage.name }));
    node.appendChild(el("span", { class: "pipeline-node-status", text: stage.status }));
    node.addEventListener("click", () => {
      if (openStage === stage.name) {
        drawer.hidden = true;
        openStage = null;
        return;
      }
      openStage = stage.name;
      drawer.replaceChildren(
        el("div", { class: "pipeline-drawer-label", text: stage.name }),
        renderStageDetail(stage.name, response),
      );
      drawer.hidden = false;
    });
    track.appendChild(node);
    if (i < stages.length - 1) track.appendChild(el("span", { class: "pipeline-connector", text: "→" }));
  });

  wrapper.appendChild(track);
  wrapper.appendChild(drawer);
  return wrapper;
}

function renderAnswer(response: QueryResponse, options: { showPipeline?: boolean } = {}): HTMLElement {
  const bubble = el("div", { class: "message answer" });
  bubble.appendChild(el("p", { class: "answer-text", text: response.answer }));

  const badges = el("div", { class: "badges" });
  badges.appendChild(el("span", { class: `badge route-${response.route}`, text: routeLabel(response.route) }));
  badges.appendChild(
    el("span", { class: `badge ${response.grounded ? "badge-ok" : "badge-warn"}`, text: response.grounded ? "grounded" : "not grounded" }),
  );
  badges.appendChild(
    el("span", { class: `badge ${response.verified ? "badge-ok" : "badge-warn"}`, text: response.verified ? "verified" : "unverified" }),
  );
  bubble.appendChild(badges);

  if (response.matched_entities.length > 0) {
    const matched = el("p", { class: "matched-entities" });
    matched.appendChild(document.createTextNode("Matched: "));
    response.matched_entities.forEach((name, i) => {
      const link = el("button", { class: "entity-link", text: name });
      link.type = "button";
      link.addEventListener("click", () => void openEntityDetail(name));
      matched.appendChild(link);
      if (i < response.matched_entities.length - 1) matched.appendChild(document.createTextNode(", "));
    });
    bubble.appendChild(matched);
  }

  if (options.showPipeline ?? pipelineViewEnabled) {
    bubble.appendChild(renderPipelineTrace(response));
  }

  return bubble;
}

function submitQuestion(question: string): void {
  messages.appendChild(el("div", { class: "message question", text: question }));
  input.disabled = true;

  const pending = el("div", { class: "message answer pending", text: "Thinking..." });
  messages.appendChild(pending);
  messages.scrollTop = messages.scrollHeight;

  postQuery(question)
    .then((response) => {
      pending.replaceWith(renderAnswer(response));
    })
    .catch((err) => {
      pending.replaceWith(
        el("div", { class: "message answer error", text: err instanceof Error ? err.message : String(err) }),
      );
    })
    .finally(() => {
      input.disabled = false;
      input.focus();
      messages.scrollTop = messages.scrollHeight;
    });
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  input.value = "";
  submitQuestion(question);
});

// -- Sample queries -------------------------------------------------------
// Real questions, each verified live against the real corpus + a real LLM
// call (task eval:run) to actually exercise the route/badge it's labeled
// for here — not guessed to be plausible.

const SAMPLE_QUERIES: { label: string; question: string }[] = [
  { label: "Attributes (structured)", question: "What are the attributes of banking:Account?" },
  { label: "2-hop traversal", question: "How does crmCommon:Contact relate to crmCommon:Organization?" },
  { label: "Ambiguous name collision", question: "What are the attributes of Contact?" },
  { label: "Semantic (LLM)", question: "What entities describe a customer's financial holdings?" },
  { label: "Out of scope (refusal)", question: "What is the capital of France?" },
];

const sampleQueriesContainer = byId<HTMLDivElement>("sample-queries");
sampleQueriesContainer.replaceChildren(
  ...SAMPLE_QUERIES.map((sample) => {
    const button = el("button", { class: "sample-chip", text: sample.label });
    button.type = "button";
    button.title = sample.question;
    button.addEventListener("click", () => submitQuestion(sample.question));
    return button;
  }),
);

void loadEntities();
