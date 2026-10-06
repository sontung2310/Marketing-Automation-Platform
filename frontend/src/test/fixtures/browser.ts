import { HttpResponse, http } from "msw";

import { setupWorker } from "msw/browser";

import { handlers } from "./handlers";
import { store } from "./store";

/** An endpoint an e2e spec wants to answer with the documented error envelope. */
export interface FixtureFailure {
  path: string;
  /** GET unless given, e.g. "post" for a refused POST /runs. */
  method?: "get" | "post";
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
    /** Makes the next run stream `run.failed` instead of completing. */
    __fixtureRunFailure?: { code: string; message: string };
    /** Ends the next run stream after this seq, like the server's scheduled close. */
    __fixtureRunStreamCut?: number;
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

  if (window.__fixtureRunFailure) store.failNextRun(window.__fixtureRunFailure);
  if (window.__fixtureRunStreamCut) store.streamCut = window.__fixtureRunStreamCut;

  for (const { path, method = "get", status, code, message } of window.__fixtureFailures ?? []) {
    worker.use(
      http[method](path, () =>
        HttpResponse.json({ error: { code, message, details: {} } }, { status }),
      ),
    );
  }
}
