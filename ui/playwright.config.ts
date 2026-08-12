import { defineConfig, devices } from "@playwright/test";

// E2E (ADR-0029) — a real browser against the real FastAPI app, serving the
// real built UI. Deliberately needs zero LLM credentials: every assertion
// exercises a deterministic route (structured/traversal/ambiguous/refused)
// or intercepts `/query` at the network layer for the semantic-route UI
// cases (pipeline-semantic.spec.ts) — same "no live calls, no cost" spirit
// as the Python fast gate (ADR-0018/0019), extended to the browser layer.
// `webServer.cwd` points at the repo root because app/api/main.py resolves
// cdm.db / chroma_data / ui/dist as paths relative to the process cwd, not
// this config file's location.
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:8000",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: ".venv/bin/uvicorn app.api.main:app --host 0.0.0.0 --port 8000",
    cwd: "..",
    url: "http://localhost:8000/health",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
