import { expect, test, type Page } from "@playwright/test";
import type { QueryResponse } from "../../src/types";

// The semantic/LLM route costs real money and is rate-limited (Gemini's
// free tier: 20 req/day — this project has hit that limit more than once
// during manual testing). These specs intercept `/query` at the network
// layer instead of spending quota, using response shapes copied verbatim
// from real captured API responses earlier in this project's development
// (see ADR-0028/ADR-0029) — the UI code under test has no idea the network
// layer is mocked, so this still exercises the real rendering logic for
// routes that are otherwise expensive/flaky to hit live in CI.

async function mockQuery(page: Page, response: QueryResponse): Promise<void> {
  await page.route("**/query", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(response) });
  });
}

const VECTOR_HITS = [
  {
    entity: "banking:CustomerFinancialHolding",
    score: 0.6277056336402893,
    snippet: "banking:CustomerFinancialHolding: Financial holdings owned by the customer.",
    passed_cutoff: true,
  },
  {
    entity: "banking:FinancialHolding",
    score: 0.5591483116149902,
    snippet: "banking:FinancialHolding: Accounts, loans, investments, credit lines and savings accounts held by a customer.",
    passed_cutoff: true,
  },
];

test.describe("pipeline view — semantic route, Validator passed (mocked)", () => {
  test("shows the real generated answer and every stage done", async ({ page }) => {
    await mockQuery(page, {
      query: "What entities describe a customer's financial holdings?",
      answer: "banking:CustomerFinancialHolding and banking:FinancialHolding describe this.",
      matched_entities: VECTOR_HITS.map((h) => h.entity),
      route: "semantic",
      grounded: true,
      verified: true,
      error: null,
      debug: {
        entity_match_kind: "none",
        entity_match_candidates: [],
        intent: "semantic",
        vector_hits: VECTOR_HITS,
        similarity_cutoff: 0.4,
        llm_raw_answer: "banking:CustomerFinancialHolding and banking:FinancialHolding describe this.",
        validator_cited_tokens: ["CustomerFinancialHolding", "FinancialHolding"],
        validator_missing_tokens: [],
      },
    });

    await page.goto("/");
    await page.locator("#pipeline-toggle").click();
    await page.locator(".sample-chip", { hasText: "Semantic (LLM)" }).click();

    const answer = page.locator(".message.answer").last();
    await expect(answer).toBeVisible();
    await expect(answer.locator(".badge.route-semantic")).toHaveText("semantic (LLM)");
    await expect(answer.locator(".badge-ok")).toHaveCount(2); // grounded + verified

    const track = page.locator(".pipeline-track").last();
    const nodes = track.locator(".pipeline-node");
    for (let i = 0; i < 6; i++) {
      await expect(nodes.nth(i)).toHaveClass(/pipeline-done/);
    }

    await track.locator(".pipeline-node", { hasText: "Retrieval" }).click();
    const drawer = page.locator(".pipeline-drawer").last();
    await expect(drawer).toContainText("banking:CustomerFinancialHolding");
    await expect(drawer.locator(".hit-score").first()).toContainText("0.628");
  });
});

test.describe("pipeline view — semantic route, Validator rejected (mocked)", () => {
  test("blocks the raw answer, shows missing cited terms, still route=semantic", async ({ page }) => {
    await mockQuery(page, {
      query: "Tell me about Account",
      answer: "I don't have information about that in the ingested CDM scope.",
      matched_entities: VECTOR_HITS.map((h) => h.entity),
      route: "semantic",
      grounded: true,
      verified: false,
      error: null,
      debug: {
        entity_match_kind: "none",
        entity_match_candidates: [],
        intent: "semantic",
        vector_hits: VECTOR_HITS,
        similarity_cutoff: 0.4,
        llm_raw_answer: "Account also has a field called FraudScore, which is unusual.",
        validator_cited_tokens: ["Account", "FraudScore"],
        validator_missing_tokens: ["FraudScore"],
      },
    });

    await page.goto("/");
    await page.locator("#pipeline-toggle").click();
    await page.locator(".sample-chip", { hasText: "Semantic (LLM)" }).click();

    const answer = page.locator(".message.answer").last();
    await expect(answer).toBeVisible();
    await expect(answer.locator(".answer-text")).toHaveText(
      "I don't have information about that in the ingested CDM scope.",
    );
    await expect(answer.locator(".badge-warn")).toHaveCount(1); // unverified (grounded is still ok)

    const track = page.locator(".pipeline-track").last();
    const nodes = track.locator(".pipeline-node");
    await expect(nodes.nth(4)).toHaveClass(/pipeline-done/); // Generate (LLM) — model was called
    await expect(nodes.nth(5)).toHaveClass(/pipeline-failed/); // Validator — rejected it

    await track.locator(".pipeline-node", { hasText: "Validator" }).click();
    const drawer = page.locator(".pipeline-drawer").last();
    await expect(drawer.locator(".chip-missing")).toHaveText("FraudScore");
    await expect(drawer.locator(".chip-found")).toHaveText("Account");

    await track.locator(".pipeline-node", { hasText: "Generate (LLM)" }).click();
    await expect(drawer).toContainText("this is what got blocked, not what you saw");
    await expect(drawer.locator(".console-block.blocked")).toContainText("FraudScore");
  });
});

test.describe("pipeline view — semantic route, LLM call itself failed (mocked)", () => {
  test("blames Generate (LLM), not the Validator, and shows the real provider error", async ({ page }) => {
    await mockQuery(page, {
      query: "What entities describe a customer's financial holdings?",
      answer: "I don't have information about that in the ingested CDM scope.",
      matched_entities: VECTOR_HITS.map((h) => h.entity),
      route: "semantic",
      grounded: true,
      verified: false,
      error: "429 RESOURCE_EXHAUSTED. Quota exceeded for metric: generate_content_free_tier_requests, limit: 20.",
      debug: {
        entity_match_kind: "none",
        entity_match_candidates: [],
        intent: "semantic",
        vector_hits: VECTOR_HITS,
        similarity_cutoff: 0.4,
        llm_raw_answer: null,
        validator_cited_tokens: [],
        validator_missing_tokens: [],
      },
    });

    await page.goto("/");
    await page.locator("#pipeline-toggle").click();
    await page.locator(".sample-chip", { hasText: "Semantic (LLM)" }).click();
    await expect(page.locator(".message.answer").last()).toBeVisible();

    const track = page.locator(".pipeline-track").last();
    const nodes = track.locator(".pipeline-node");
    await expect(nodes.nth(4)).toHaveClass(/pipeline-failed/); // Generate (LLM) — the real failure
    await expect(nodes.nth(5)).toHaveClass(/pipeline-skipped/); // Validator — never reached

    await track.locator(".pipeline-node", { hasText: "Generate (LLM)" }).click();
    const drawer = page.locator(".pipeline-drawer").last();
    await expect(drawer).toContainText("429 RESOURCE_EXHAUSTED");

    await track.locator(".pipeline-node", { hasText: "Validator" }).click();
    await expect(drawer).toContainText("Never reached");
  });
});
