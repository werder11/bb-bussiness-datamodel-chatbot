import { expect, test } from "@playwright/test";

// Deterministic-route pipeline view coverage (ADR-0027/0028) — no mocking
// needed here since structured/traversal/ambiguous never touch the LLM.
// See pipeline-view-semantic.spec.ts for the LLM-path cases, which mock
// `/query` instead of spending real quota.

test.describe("pipeline view toggle", () => {
  test("is off by default — no track renders on a normal answer", async ({ page }) => {
    await page.goto("/");
    await page.locator(".sample-chip", { hasText: "Attributes (structured)" }).click();
    await expect(page.locator(".message.answer").last()).toBeVisible({ timeout: 15_000 });
    await expect(page.locator(".pipeline-track")).toHaveCount(0);
  });

  test("toggling on adds aria-pressed and the active class", async ({ page }) => {
    await page.goto("/");
    const toggle = page.locator("#pipeline-toggle");
    await expect(toggle).toHaveAttribute("aria-pressed", "false");

    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-pressed", "true");
    await expect(toggle).toHaveClass(/active/);

    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-pressed", "false");
    await expect(toggle).not.toHaveClass(/active/);
  });

  test("only affects answers submitted after it's turned on", async ({ page }) => {
    await page.goto("/");
    await page.locator(".sample-chip", { hasText: "Attributes (structured)" }).click();
    await expect(page.locator(".message.answer").last()).toBeVisible({ timeout: 15_000 });
    await expect(page.locator(".pipeline-track")).toHaveCount(0);

    await page.locator("#pipeline-toggle").click();
    await page.locator(".sample-chip", { hasText: "2-hop traversal" }).click();
    await expect(page.locator(".message.answer").last()).toBeVisible({ timeout: 15_000 });

    // Exactly one trace — the second (post-toggle) answer only.
    await expect(page.locator(".pipeline-track")).toHaveCount(1);
  });
});

test.describe("pipeline view — structured route", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.locator("#pipeline-toggle").click();
    await page.locator(".sample-chip", { hasText: "Attributes (structured)" }).click();
    await expect(page.locator(".message.answer").last()).toBeVisible({ timeout: 15_000 });
  });

  test("shows six correctly-labeled stages, deterministic ones done, LLM ones skipped", async ({ page }) => {
    const track = page.locator(".pipeline-track").last();
    const nodes = track.locator(".pipeline-node");
    await expect(nodes).toHaveCount(6);

    const names = await nodes.locator(".pipeline-node-name").allTextContents();
    expect(names).toEqual(["Entity Match", "Router", "Retrieval", "Grounding Guard", "Generate (LLM)", "Validator"]);

    await expect(nodes.nth(0)).toHaveClass(/pipeline-done/); // Entity Match
    await expect(nodes.nth(1)).toHaveClass(/pipeline-done/); // Router
    await expect(nodes.nth(2)).toHaveClass(/pipeline-done/); // Retrieval
    await expect(nodes.nth(3)).toHaveClass(/pipeline-skipped/); // Grounding Guard
    await expect(nodes.nth(4)).toHaveClass(/pipeline-skipped/); // Generate (LLM)
    await expect(nodes.nth(5)).toHaveClass(/pipeline-skipped/); // Validator
  });

  test("clicking Entity Match opens a drawer with the real match kind and candidate", async ({ page }) => {
    const track = page.locator(".pipeline-track").last();
    await track.locator(".pipeline-node", { hasText: "Entity Match" }).click();

    const drawer = page.locator(".pipeline-drawer").last();
    await expect(drawer).toBeVisible();
    await expect(drawer.locator(".pipeline-drawer-label")).toHaveText("Entity Match");
    await expect(drawer).toContainText("exact");
    await expect(drawer.locator(".entity-chip", { hasText: "banking:Account" })).toBeVisible();
  });

  test("clicking Generate (LLM) explains the model was never called", async ({ page }) => {
    const track = page.locator(".pipeline-track").last();
    await track.locator(".pipeline-node", { hasText: "Generate (LLM)" }).click();

    const drawer = page.locator(".pipeline-drawer").last();
    await expect(drawer).toBeVisible();
    await expect(drawer).toContainText("model is never called");
  });

  test("clicking the same node again collapses the drawer", async ({ page }) => {
    const track = page.locator(".pipeline-track").last();
    const node = track.locator(".pipeline-node", { hasText: "Router" });
    const drawer = page.locator(".pipeline-drawer").last();

    await node.click();
    await expect(drawer).toBeVisible();
    await node.click();
    await expect(drawer).toBeHidden();
  });

  test("clicking a different node swaps the drawer content", async ({ page }) => {
    const track = page.locator(".pipeline-track").last();
    const drawer = page.locator(".pipeline-drawer").last();

    await track.locator(".pipeline-node", { hasText: "Entity Match" }).click();
    await expect(drawer.locator(".pipeline-drawer-label")).toHaveText("Entity Match");

    await track.locator(".pipeline-node", { hasText: "Router" }).click();
    await expect(drawer.locator(".pipeline-drawer-label")).toHaveText("Router");
    await expect(drawer).toContainText("attributes");
  });

  test("clicking an entity chip inside the drawer opens that entity's detail panel", async ({ page }) => {
    const track = page.locator(".pipeline-track").last();
    await track.locator(".pipeline-node", { hasText: "Entity Match" }).click();

    const drawer = page.locator(".pipeline-drawer").last();
    await drawer.locator(".entity-chip", { hasText: "banking:Account" }).click();

    await expect(page.locator("#detail-panel")).toBeVisible();
    await expect(page.locator("#detail-content h2")).toHaveText("banking:Account");
  });
});

test.describe("pipeline view — ambiguous route", () => {
  test("Entity Match fails, every later stage is skipped", async ({ page }) => {
    await page.goto("/");
    await page.locator("#pipeline-toggle").click();
    await page.locator(".sample-chip", { hasText: "Ambiguous name collision" }).click();
    await expect(page.locator(".message.answer").last()).toBeVisible({ timeout: 15_000 });

    const track = page.locator(".pipeline-track").last();
    const nodes = track.locator(".pipeline-node");
    await expect(nodes.nth(0)).toHaveClass(/pipeline-failed/); // Entity Match
    for (let i = 1; i < 6; i++) {
      await expect(nodes.nth(i)).toHaveClass(/pipeline-skipped/);
    }
  });
});
