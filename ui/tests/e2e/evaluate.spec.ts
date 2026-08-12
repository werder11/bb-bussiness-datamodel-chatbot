import { expect, test } from "@playwright/test";

// POST /evaluate — deterministic route only (structured attribute lookup),
// same reasoning as chat.spec.ts / pipeline-view.spec.ts: no live LLM call
// needed to exercise this, so it runs against the real backend for real.

test.describe("Score an answer panel", () => {
  test("opens with the comparison form", async ({ page }) => {
    await page.goto("/");
    await page.locator("#evaluate-button").click();

    const panel = page.locator("#detail-panel");
    await expect(panel).toBeVisible();
    await expect(page.locator("#detail-content h2")).toHaveText("Score an answer");
    await expect(page.locator(".evaluate-input")).toBeVisible();
    await expect(page.locator(".evaluate-textarea")).toBeVisible();
  });

  test("running a comparison shows the real answer, badges, and term overlap", async ({ page }) => {
    await page.goto("/");
    await page.locator("#evaluate-button").click();

    await page.locator(".evaluate-input").fill("What are the attributes of banking:Account?");
    await page
      .locator(".evaluate-textarea")
      .fill("Account should have an accountId field and a totally different unrelatedTerm.");
    await page.locator(".evaluate-form button[type=submit]").click();

    const results = page.locator(".evaluate-results");
    await expect(results.locator(".badge.route-structured")).toBeVisible();
    await expect(results.locator(".answer-text")).toContainText("accountId");

    await expect(results.locator(".comparison-block .kpi-row-label")).toHaveText("Text similarity");
    await expect(results.locator(".comparison-block .chip-found", { hasText: "accountid" })).toBeVisible();
    await expect(
      results.locator(".comparison-block .chip-missing", { hasText: "unrelatedterm" }),
    ).toBeVisible();
  });

  test("the pipeline view is always shown here, independent of the chat toggle", async ({ page }) => {
    await page.goto("/");
    // Deliberately not toggling #pipeline-toggle — it stays off for the chat box.
    await expect(page.locator("#pipeline-toggle")).toHaveAttribute("aria-pressed", "false");

    await page.locator("#evaluate-button").click();
    await page.locator(".evaluate-input").fill("What are the attributes of banking:Account?");
    await page.locator(".evaluate-textarea").fill("Account has an accountId.");
    await page.locator(".evaluate-form button[type=submit]").click();

    await expect(page.locator(".evaluate-results .pipeline-node")).toHaveCount(6);
    await page.locator(".evaluate-results .pipeline-node", { hasText: "Entity Match" }).click();
    await expect(page.locator(".evaluate-results .pipeline-drawer")).toBeVisible();
    await expect(page.locator(".evaluate-results .entity-chip", { hasText: "banking:Account" })).toBeVisible();
  });

  test("a whitespace-only desired answer is not submitted", async ({ page }) => {
    await page.goto("/");
    await page.locator("#evaluate-button").click();
    await page.locator(".evaluate-input").fill("What are the attributes of banking:Account?");
    // A single space passes the browser's `required` check but trims to ""
    // client-side — openEvaluatePanel()'s submit handler guards on
    // question/expectedAnswer.trim() before calling postEvaluate at all.
    await page.locator(".evaluate-textarea").fill(" ");
    await page.locator(".evaluate-form button[type=submit]").click();

    await expect(page.locator(".evaluate-results")).toBeEmpty();
  });
});
