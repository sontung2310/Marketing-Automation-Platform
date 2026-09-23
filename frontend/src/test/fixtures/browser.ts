import { HttpResponse, http } from "msw";

import { setupWorker } from "msw/browser";

import { handlers } from "./handlers";

/** An endpoint an e2e spec wants to answer with the documented error envelope. */
export interface FixtureFailure {
  path: string;
  status: number;
  code: string;
  message: string;
}

declare global {
  interface Window {
    /**
     * Queued by an e2e spec through `addInitScript`, so the failure is in place
     * before the app's first request and survives a reload.
     */
    __fixtureFailures?: FixtureFailure[];
  }
}

/**
 * The fixture API in the browser, started only when VITE_USE_FIXTURES is set in
 * a dev build. A production build never imports this module.
 *
 * Playwright's own request routing cannot override these responses, because the
 * service worker answers before the request reaches the network. The controls
 * below are how an e2e spec makes a region fail.
 */
export async function startFixtureWorker(): Promise<void> {
  const worker = setupWorker(...handlers);
  await worker.start({ quiet: true, onUnhandledRequest: "bypass" });

  for (const { path, status, code, message } of window.__fixtureFailures ?? []) {
    worker.use(
      http.get(path, () =>
        HttpResponse.json({ error: { code, message, details: {} } }, { status }),
      ),
    );
  }
}
