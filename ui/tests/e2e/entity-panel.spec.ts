import { expect, test } from "@playwright/test";

test.describe("entity panel", () => {
  test("lists all 44 ingested entities on load", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("#entity-list li")).toHaveCount(44);
  });

  test("filter narrows the list live", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("#entity-list li")).toHaveCount(44);

    await page.locator("#entity-filter").fill("Account");
    const filtered = page.locator("#entity-list li");
    await expect(filtered.first()).toBeVisible();
    const count = await filtered.count();
    expect(count).toBeGreaterThan(0);
    expect(count).toBeLessThan(44);
    for (const text of await filtered.allTextContents()) {
      expect(text.toLowerCase()).toContain("account");
    }
  });

  test("filter with no matches empties the list without erroring", async ({ page }) => {
    await page.goto("/");
    await page.locator("#entity-filter").fill("zzz-does-not-exist-zzz");
    await expect(page.locator("#entity-list li")).toHaveCount(0);
  });

  test("clicking an entity opens its detail panel with attributes and relationships", async ({ page }) => {
    await page.goto("/");
    await page.locator("#entity-filter").fill("banking:Account");
    await page.locator("#entity-list li button", { hasText: "banking:Account" }).click();

    const panel = page.locator("#detail-panel");
    await expect(panel).toBeVisible();
    await expect(page.locator("#detail-content h2")).toHaveText("banking:Account");
    await expect(page.locator("#detail-content")).toContainText("Attributes");
    await expect(page.locator("#detail-content")).toContainText("accountId");
    await expect(page.locator("#detail-content")).toContainText("Relationships");
  });

  test("close button hides the detail panel", async ({ page }) => {
    await page.goto("/");
    await page.locator("#entity-filter").fill("banking:Account");
    await page.locator("#entity-list li button", { hasText: "banking:Account" }).click();
    await expect(page.locator("#detail-panel")).toBeVisible();

    await page.locator("#detail-close").click();
    await expect(page.locator("#detail-panel")).toBeHidden();
  });

  test("real Account/Contact namespace collision — both appear as distinct entities", async ({ page }) => {
    await page.goto("/");
    await page.locator("#entity-filter").fill("Account");
    const names = await page.locator("#entity-list li button").allTextContents();
    expect(names).toContain("banking:Account");
    expect(names).toContain("crmCommon:Account");
  });
});
