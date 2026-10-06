import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { PAUSE_AFTER_MS, useActivityStream } from "./useActivityStream";

class FakeEventSource {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;
  static instances: FakeEventSource[] = [];
  readonly CONNECTING = FakeEventSource.CONNECTING;
  readyState = FakeEventSource.CONNECTING;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;
  private listeners = new Map<string, (event: MessageEvent<string>) => void>();

  constructor(readonly url: string) {
    FakeEventSource.instances.push(this);
  }
  addEventListener(type: string, listener: (event: MessageEvent<string>) => void) {
    this.listeners.set(type, listener);
  }
  close() {
    this.closed = true;
    this.readyState = FakeEventSource.CLOSED;
  }
  open() {
    this.readyState = FakeEventSource.OPEN;
    this.onopen?.();
  }
  fail(readyState: number) {
    this.readyState = readyState;
    this.onerror?.();
  }
  emit(data: object) {
    this.listeners.get("activity.created")?.({
      data: JSON.stringify(data),
    } as MessageEvent<string>);
  }
}

const queryClient = new QueryClient();
const wrapper = ({ children }: { children: ReactNode }) => (
  <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
);

function render() {
  return renderHook(() => useActivityStream(), { wrapper });
}

function stream(index: number): FakeEventSource {
  const source = FakeEventSource.instances[index];
  if (!source) throw new Error(`no EventSource #${index}`);
  return source;
}

beforeEach(() => {
  vi.useFakeTimers();
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

test("a routine server close reconnects natively without flashing the paused bar", () => {
  const { result } = render();
  const source = stream(0);
  act(() => source.open());

  act(() => source.fail(FakeEventSource.CONNECTING));
  act(() => vi.advanceTimersByTime(PAUSE_AFTER_MS - 1));
  act(() => source.open());
  act(() => vi.advanceTimersByTime(PAUSE_AFTER_MS));

  expect(result.current.paused).toBe(false);
  expect(source.closed).toBe(false);
  expect(FakeEventSource.instances).toHaveLength(1);
});

test("a reconnect that does not open soon shows the paused bar until it does", () => {
  const { result } = render();
  const source = stream(0);

  act(() => source.fail(FakeEventSource.CONNECTING));
  act(() => vi.advanceTimersByTime(PAUSE_AFTER_MS));
  expect(result.current.paused).toBe(true);

  act(() => source.open());
  expect(result.current.paused).toBe(false);
});

test("a stream the browser gives up on is reopened with backoff", () => {
  const { result } = render();
  const first = stream(0);

  act(() => first.fail(FakeEventSource.CLOSED));
  expect(result.current.paused).toBe(true);
  act(() => vi.advanceTimersByTime(1000));

  const second = stream(1);
  const refetch = vi.spyOn(queryClient, "invalidateQueries");
  act(() => second.open());
  expect(refetch).toHaveBeenCalledWith({ queryKey: ["activities"] });
  act(() => second.emit({ id: "act_1", title: "New post" }));
  expect(result.current.inserted.map((item) => item.id)).toEqual(["act_1"]);
  expect(result.current.paused).toBe(false);
});
