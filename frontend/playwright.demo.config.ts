import { defineConfig, devices } from "@playwright/test";

const PORT = 5175;

/**
 * The demo story (roadmap 8.1), against a real backend, MCP and OpenAI -
 * never the fixture dev server `playwright.config.ts` uses. The backend and
 * MCP are started separately (see README "Running the demo"); this config
 * only serves the frontend, reusing it if one is already running.
 */
export default defineConfig({
  testDir: "./e2e",
  testMatch: /demo\.spec\.ts/,
  fullyParallel: false,
  workers: 1,
  retries: 0, // --repeat-each=3 (8-A) is the flakiness check, not retries masking it
  timeout: 5 * 60_000, // one run of the whole 8-step story (8-E's own 5-minute bar)
  // CI also writes an HTML report, uploaded as an artifact (this job runs on
  // demand and spends real OpenAI budget, so its evidence is worth keeping).
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : [["list"]],
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
  ],
  webServer: {
    command: `npx vite --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
