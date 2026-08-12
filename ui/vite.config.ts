import { defineConfig } from "vite";

// Thin client only (ADR-0022/0025) — no framework, calls the existing API
// directly. The dev proxy below just avoids CORS while developing against
// `task dev:api` on :8000; the production build is served by FastAPI itself
// from the same origin, so no proxy/CORS config is needed there at all.
export default defineConfig({
  server: {
    proxy: {
      "/query": "http://localhost:8000",
      "/entities": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
  build: {
    outDir: "dist",
  },
});
