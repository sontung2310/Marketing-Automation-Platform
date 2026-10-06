import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useTheme } from "./useTheme";

// A controllable prefers-color-scheme query: flip `systemDark` and fire change.
let systemDark = false;
const listeners = new Set<() => void>();

beforeEach(() => {
  systemDark = false;
  listeners.clear();
  localStorage.clear();
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query: string) =>
      ({
        media: query,
        get matches() {
          return query.includes("dark") && systemDark;
        },
        addEventListener: (_: string, listener: () => void) => listeners.add(listener),
        removeEventListener: (_: string, listener: () => void) => listeners.delete(listener),
      }) as unknown as MediaQueryList,
  );
});

afterEach(() => vi.restoreAllMocks());

const theme = () => document.documentElement.dataset.theme;
const setSystemDark = (dark: boolean) =>
  act(() => {
    systemDark = dark;
    for (const listener of listeners) listener();
  });

describe("useTheme", () => {
  it("follows the system with no stored choice, live", () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current.preference).toBe("SYSTEM");
    expect(theme()).toBe("light");

    setSystemDark(true);
    expect(theme()).toBe("dark");
  });

  it("stores an override that ignores the system, and System clears it", () => {
    const { result } = renderHook(() => useTheme());

    act(() => result.current.setPreference("DARK"));
    expect(theme()).toBe("dark");
    expect(localStorage.getItem("theme")).toBe("dark");

    setSystemDark(false);
    expect(theme()).toBe("dark");

    act(() => result.current.setPreference("SYSTEM"));
    expect(theme()).toBe("light");
    expect(localStorage.getItem("theme")).toBeNull();
  });

  it("treats a prototype key in storage as no choice", () => {
    localStorage.setItem("theme", "constructor");
    const { result } = renderHook(() => useTheme());
    expect(result.current.preference).toBe("SYSTEM");
  });

  it("follows the system when storage is blocked, and a choice still applies", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    systemDark = true;
    const { result } = renderHook(() => useTheme());
    expect(result.current.preference).toBe("SYSTEM");
    expect(theme()).toBe("dark");

    act(() => result.current.setPreference("LIGHT"));
    expect(theme()).toBe("light");
  });

  it("restores a stored choice on load", () => {
    localStorage.setItem("theme", "dark");
    const { result } = renderHook(() => useTheme());
    expect(result.current.preference).toBe("DARK");
    expect(theme()).toBe("dark");
  });
});
