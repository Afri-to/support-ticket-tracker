import { defineConfig, devices } from "@playwright/test";

// The end-to-end tests run the real stack: the API serves the built dashboard
// (as in production) against a real PostgreSQL database.
// Build first:  VITE_API_URL="" npm run build
const PORT = 8010;
const DATABASE_URL =
  process.env.E2E_DATABASE_URL ?? "postgresql+psycopg://postgres:postgres@localhost:5432/tickets_e2e";

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: `${process.env.PYTHON ?? "python"} -m uvicorn app.main:app --port ${PORT}`,
    cwd: "../backend",
    url: `http://127.0.0.1:${PORT}/health`,
    reuseExistingServer: !process.env.CI,
    env: {
      DATABASE_URL,
      SECURE_COOKIES: "false",
      SEED_DEMO: "true",
      FRONTEND_DIST: "../frontend/dist",
    },
  },
});
