import { expect, test } from "@playwright/test";

// All questions here are real, previously-verified sample queries (the same
// ones the UI's own "sample query" chips use) — every assertion below is
// against a deterministic route, so this suite needs zero LLM credentials.

test.describe("page load", () => {
  test("loads the app shell", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle("CDM RAG Chatbot");
    await expect(page.locator("#entity-panel h1")).toHaveText("CDM Entities");
    await expect(page.locator("#chat-panel h1")).toHaveText("CDM RAG Chatbot");
    await expect(page.locator("#question-input")).toBeVisible();
  });

  test("renders all five sample query chips", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator(".sample-chip")).toHaveCount(5);
    await expect(page.locator(".sample-chip", { hasText: "Attributes (structured)" })).toBeVisible();
    await expect(page.locator(".sample-chip", { hasText: "2-hop traversal" })).toBeVisible();
    await expect(page.locator(".sample-chip", { hasText: "Ambiguous name collision" })).toBeVisible();
    await expect(page.locator(".sample-chip", { hasText: "Semantic (LLM)" })).toBeVisible();
    await expect(page.locator(".sample-chip", { hasText: "Out of scope (refusal)" })).toBeVisible();
  });
});

test.describe("structured route", () => {
  test("attribute question is template-rendered with correct badges", async ({ page }) => {
    await page.goto("/");
    await page.locator(".sample-chip", { hasText: "Attributes (structured)" }).click();

    const question = page.locator(".message.question").last();
    await expect(question).toHaveText("What are the attributes of banking:Account?");

    const answer = page.locator(".message.answer").last();
    await expect(answer).toBeVisible({ timeout: 15_000 });
    await expect(answer.locator(".answer-text")).toContainText("accountId");
    await expect(answer.locator(".badge.route-structured")).toHaveText("structured");
    await expect(answer.locator(".badge-ok")).toHaveCount(2); // grounded + verified
    await expect(answer.locator(".matched-entities .entity-link")).toHaveText("banking:Account");
  });
});

test.describe("traversal route", () => {
  test("2-hop relationship question uses bounded traversal", async ({ page }) => {
    await page.goto("/");
    await page.locator(".sample-chip", { hasText: "2-hop traversal" }).click();

    const answer = page.locator(".message.answer").last();
    await expect(answer).toBeVisible({ timeout: 15_000 });
    await expect(answer.locator(".badge.route-traversal")).toHaveText("traversal");
    await expect(answer.locator(".answer-text")).toContainText("crmCommon:Contact");
    await expect(answer.locator(".answer-text")).toContainText("crmCommon:Organization");
  });
});

test.describe("ambiguous collision", () => {
  test("real Account/Contact namespace collision asks for disambiguation", async ({ page }) => {
    await page.goto("/");
    await page.locator(".sample-chip", { hasText: "Ambiguous name collision" }).click();

    const answer = page.locator(".message.answer").last();
    await expect(answer).toBeVisible({ timeout: 15_000 });
    await expect(answer.locator(".answer-text")).toContainText("ambiguous");
    await expect(answer.locator(".badge.route-none")).toHaveText("refused");
    await expect(answer.locator(".matched-entities .entity-link")).toHaveCount(2);
  });
});

test.describe("out-of-scope refusal", () => {
  test("refuses rather than fabricating an answer", async ({ page }) => {
    await page.goto("/");
    await page.locator(".sample-chip", { hasText: "Out of scope (refusal)" }).click();

    const answer = page.locator(".message.answer").last();
    await expect(answer).toBeVisible({ timeout: 15_000 });
    await expect(answer.locator(".answer-text")).toHaveText(
      "I don't have information about that in the ingested CDM scope.",
    );
    await expect(answer.locator(".badge.route-none")).toHaveText("refused");
    await expect(answer.locator(".matched-entities")).toHaveCount(0);
  });
});

test.describe("free-text input", () => {
  test("typing a question and pressing Ask submits it", async ({ page }) => {
    await page.goto("/");
    await page.locator("#question-input").fill("What are the attributes of banking:Bank?");
    await page.locator("#query-form button[type=submit]").click();

    await expect(page.locator("#question-input")).toHaveValue("");
    const answer = page.locator(".message.answer").last();
    await expect(answer).toBeVisible({ timeout: 15_000 });
    await expect(answer.locator(".badge.route-structured")).toBeVisible();
  });

  test("input is disabled while a request is in flight, then re-enabled", async ({ page }) => {
    // The real deterministic route answers in well under a second — too
    // fast to reliably observe the transient "pending" state against real
    // network timing. Delaying the real response (not faking its content)
    // isolates the thing under test: the disabled/pending UI state, not
    // request speed.
    await page.route("**/query", async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      await new Promise((resolve) => setTimeout(resolve, 300));
      await route.continue();
    });

    await page.goto("/");
    const input = page.locator("#question-input");
    await input.fill("What are the attributes of banking:Account?");
    await page.locator("#query-form button[type=submit]").click();

    await expect(page.locator(".message.answer.pending")).toBeVisible();
    await expect(page.locator(".message.answer").last()).toBeVisible({ timeout: 15_000 });
    await expect(input).toBeEnabled();
    await expect(input).toBeFocused();
  });
});

test.describe("matched entity links", () => {
  test("clicking a matched entity opens its detail panel", async ({ page }) => {
    await page.goto("/");
    await page.locator(".sample-chip", { hasText: "Attributes (structured)" }).click();
    await expect(page.locator(".message.answer").last()).toBeVisible({ timeout: 15_000 });

    await page.locator(".matched-entities .entity-link", { hasText: "banking:Account" }).click();
    await expect(page.locator("#detail-panel")).toBeVisible();
    await expect(page.locator("#detail-content h2")).toHaveText("banking:Account");
    await expect(page.locator("#detail-content")).toContainText("accountId");
  });
});
