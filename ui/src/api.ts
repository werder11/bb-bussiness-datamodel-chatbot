import type { EntityDetailResponse, EntityListResponse, EvaluateResponse, QueryResponse } from "./types";

// Relative paths only — same-origin in production (FastAPI serves this build
// directly, ADR-0025) and proxied to :8000 in dev (vite.config.ts). No base
// URL, no CORS config, anywhere.

async function asJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

export function listEntities(): Promise<EntityListResponse> {
  return fetch("/entities").then((r) => asJson<EntityListResponse>(r));
}

export function getEntity(name: string): Promise<EntityDetailResponse> {
  return fetch(`/entities/${encodeURIComponent(name)}`).then((r) =>
    asJson<EntityDetailResponse>(r),
  );
}

export function postQuery(question: string): Promise<QueryResponse> {
  return fetch("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  }).then((r) => asJson<QueryResponse>(r));
}

export function postEvaluate(question: string, expectedAnswer: string): Promise<EvaluateResponse> {
  return fetch("/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, expected_answer: expectedAnswer }),
  }).then((r) => asJson<EvaluateResponse>(r));
}
