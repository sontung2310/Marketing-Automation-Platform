import { useEffect, useState } from "react";

/** The three arrangements in ui-spec §2, keyed by the theme.css breakpoints. */
export type LayoutMode = "MOBILE" | "TABLET" | "DESKTOP";

const QUERIES: { mode: LayoutMode; query: string }[] = [
  { mode: "DESKTOP", query: "(min-width: 1281px)" },
  { mode: "TABLET", query: "(min-width: 901px)" },
];

function currentMode(): LayoutMode {
  if (typeof window === "undefined" || !window.matchMedia) return "DESKTOP";
  return QUERIES.find(({ query }) => window.matchMedia(query).matches)?.mode ?? "MOBILE";
}

export function useLayoutMode(): LayoutMode {
  const [mode, setMode] = useState<LayoutMode>(currentMode);

  useEffect(() => {
    const lists = QUERIES.map(({ query }) => window.matchMedia(query));
    const update = () => setMode(currentMode());
    for (const list of lists) list.addEventListener("change", update);
    update();
    return () => {
      for (const list of lists) list.removeEventListener("change", update);
    };
  }, []);

  return mode;
}
