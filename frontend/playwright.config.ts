import { defineConfig, devices } from "@playwright/test";

const PORT = 5174;

/**
 * The workspace's end-to-end specs. Until Step 6 ships the Platform API, the
 * dev server serves it from the same typed MSW fixtures Vitest uses, so these
 * specs exercise the real components against the real contract shapes.
 */
export default defineConfig({
  testDir: "./e2e",
  // The demo story needs a real backend and real OpenAI (roadmap 8.1); it has
  // its own config and `npm run demo:e2e`, run on demand, not in this suite.
  testIgnore: /demo\.spec\.ts/,
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "list" : [["list"]],
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
    env: { VITE_USE_FIXTURES: "1" },
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
