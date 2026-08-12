import { expect, test } from "@playwright/test";

test.describe("How this works panel", () => {
  test("opens with the route legend and grounding legend", async ({ page }) => {
    await page.goto("/");
    await page.locator("#info-button").click();

    const panel = page.locator("#detail-panel");
    await expect(panel).toBeVisible();
    await expect(page.locator("#detail-content h2")).toHaveText("How this works");
    await expect(page.locator("#detail-content")).toContainText("question → match entity → route → answer");

    const legendBadges = page.locator("#detail-content .legend-list .badge");
    await expect(legendBadges).toHaveCount(6); // 4 routes + grounded + verified
    await expect(page.locator("#detail-content .badge.route-structured")).toBeVisible();
    await expect(page.locator("#detail-content .badge.route-semantic")).toBeVisible();
  });

  test("close button hides it", async ({ page }) => {
    await page.goto("/");
    await page.locator("#info-button").click();
    await expect(page.locator("#detail-panel")).toBeVisible();
    await page.locator("#detail-close").click();
    await expect(page.locator("#detail-panel")).toBeHidden();
  });
});

test.describe("Evaluation panel", () => {
  test("opens with real KPI numbers from the last eval snapshot", async ({ page }) => {
    await page.goto("/");
    await page.locator("#eval-button").click();

    const panel = page.locator("#detail-panel");
    await expect(panel).toBeVisible();
    await expect(page.locator("#detail-content h2")).toHaveText("Evaluation");
    await expect(page.locator("#detail-content")).toContainText("27 questions across 8 categories");

    await expect(page.locator("#detail-content", { hasText: "Entity-matching accuracy" })).toBeVisible();
    await expect(page.locator("#detail-content", { hasText: "Faithfulness" })).toBeVisible();
    // 8 retrieval + 5 answer-quality + 2 data-quality rows — see openEvalPanel() in main.ts.
    await expect(page.locator("#detail-content .kpi-row")).toHaveCount(15);
  });

  test("switching between info and eval panels swaps content in place", async ({ page }) => {
    await page.goto("/");
    await page.locator("#info-button").click();
    await expect(page.locator("#detail-content h2")).toHaveText("How this works");

    await page.locator("#eval-button").click();
    await expect(page.locator("#detail-content h2")).toHaveText("Evaluation");
    await expect(page.locator("#detail-panel")).toBeVisible();
  });
});
