import "@testing-library/jest-dom/vitest";

import { afterAll, afterEach, beforeAll } from "vitest";

import { server } from "./fixtures/server";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

/**
 * jsdom has no EventSource. Component tests assert the rendered regions, not
 * the streams, so a quiet stub keeps the app code free of environment checks;
 * the streams themselves are covered by the Playwright specs.
 */
class SilentEventSource {
  close(): void {}
  addEventListener(): void {}
  removeEventListener(): void {}
  onerror: (() => void) | null = null;
  onopen: (() => void) | null = null;
}

if (!("EventSource" in globalThis)) {
  Object.defineProperty(globalThis, "EventSource", {
    value: SilentEventSource,
    writable: true,
    configurable: true, // a hook test swaps in a scripted fake
  });
}

// jsdom implements no layout, so scrolling is a no-op and no media query
// matches. Component tests therefore run in the desktop arrangement, and the
// responsive behaviour is covered by the Playwright viewport specs.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}

if (!window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      media: query,
      matches: query.includes("1281"),
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList;
}
