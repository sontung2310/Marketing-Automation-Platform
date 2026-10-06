import { useCallback, useEffect, useState } from "react";

/** ui-spec §3: the TopBar's Light | Dark | System menu. */
export type ThemePreference = "LIGHT" | "DARK" | "SYSTEM";

// The pre-paint script in index.html reads the same key and values, so the
// first frame already matches what this hook will apply.
const STORAGE_KEY = "theme";
const STORED: Record<string, ThemePreference> = { light: "LIGHT", dark: "DARK" };
const DARK_QUERY = "(prefers-color-scheme: dark)";

function readPreference(): ThemePreference {
  try {
    const stored = localStorage.getItem(STORAGE_KEY) ?? "";
    // Own keys only: "constructor" must not resolve to Object's prototype.
    return Object.hasOwn(STORED, stored) ? (STORED[stored] as ThemePreference) : "SYSTEM";
  } catch {
    return "SYSTEM"; // storage blocked: follow the system
  }
}

function writePreference(preference: ThemePreference): void {
  try {
    if (preference === "SYSTEM") localStorage.removeItem(STORAGE_KEY);
    else localStorage.setItem(STORAGE_KEY, preference.toLowerCase());
  } catch {
    // Storage blocked: the choice lasts for this page only.
  }
}

function applyTheme(preference: ThemePreference): void {
  const dark =
    preference === "DARK" || (preference === "SYSTEM" && window.matchMedia(DARK_QUERY).matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
}

export function useTheme() {
  const [preference, setPreferenceState] = useState<ThemePreference>(readPreference);

  useEffect(() => {
    applyTheme(preference);
    if (preference !== "SYSTEM") return;
    const list = window.matchMedia(DARK_QUERY);
    const update = () => applyTheme("SYSTEM");
    list.addEventListener("change", update);
    return () => list.removeEventListener("change", update);
  }, [preference]);

  const setPreference = useCallback((next: ThemePreference) => {
    writePreference(next);
    setPreferenceState(next);
  }, []);

  return { preference, setPreference };
}
