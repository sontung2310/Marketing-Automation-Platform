import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./styles/theme.css";

const root = document.getElementById("root");
if (!root) throw new Error("Missing #root element");

/**
 * Until Step 6 ships the Platform API, a dev build can serve it from the typed
 * MSW fixtures. A production build never imports the worker.
 */
async function startFixtures(): Promise<void> {
  if (!import.meta.env.DEV || import.meta.env.VITE_USE_FIXTURES !== "1") return;
  const { startFixtureWorker } = await import("./test/fixtures/browser");
  await startFixtureWorker();
}

void startFixtures().then(() => {
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});
