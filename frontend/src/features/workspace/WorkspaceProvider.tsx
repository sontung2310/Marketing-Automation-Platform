import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import {
  ApiError,
  openRunStream,
  type EvidenceKind,
  type RunEvent,
  type RunRequest,
} from "../../api";
import { queryKeys, useSession, useStartRun } from "../../hooks/queries";
import {
  evidenceTargetId,
  runLabel,
  WorkspaceContext,
  type RunState,
  type TranscriptEntry,
  type WorkspaceValue,
} from "./workspaceContext";

const SESSION_STORAGE_KEY = "session_id";
/**
 * How long a highlight stays lit. It also bounds the wait for a target the feed
 * is still paging towards, so the two can never disagree: a shorter highlight
 * would cancel the pending scroll before it resolved.
 */
const HIGHLIGHT_MS = 4000;

function readStoredSession(): string | null {
  try {
    return window.localStorage.getItem(SESSION_STORAGE_KEY);
  } catch {
    return null;
  }
}

/**
 * Applies one streamed event to a run. The reducer is exhaustive over the SSE
 * event table in docs/api-contract.md, so a new event type is a compile error.
 */
function applyEvent(run: RunState, event: RunEvent): RunState {
  switch (event.type) {
    case "run.started":
      return {
        ...run,
        agent: event.data.agent,
        intent: event.data.intent,
        route: event.data.route,
      };
    case "agent.step":
      return { ...run, steps: [...run.steps, event.data] };
    case "agent.tool":
      return { ...run, tool_calls: [...run.tool_calls, event.data] };
    case "agent.text_delta":
      return run;
    case "output.final":
      return { ...run, output: event.data };
    case "run.failed":
      return { ...run, status: "FAILED", error: event.data, finished_at: event.ts };
    case "run.completed":
      return { ...run, status: event.data.status, finished_at: event.ts };
  }
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [sessionId, setSessionId] = useState<string | null>(readStoredSession);
  const [draft, setDraft] = useState("");
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [runs, setRuns] = useState<Record<string, RunState>>({});
  const [activeStrategyRunId, setActiveStrategyRunId] = useState<string | null>(null);
  const [highlightedId, setHighlightedId] = useState<string | null>(null);
  const [highlightedKind, setHighlightedKind] = useState<EvidenceKind | null>(null);
  const highlightTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const streams = useRef(new Map<string, EventSource>());
  const restoredSessionId = useRef<string | null>(null);

  const restored = useSession(sessionId);
  const startRunMutation = useStartRun();

  const highlight = useCallback((id: string, kind: EvidenceKind) => {
    setHighlightedId(id);
    setHighlightedKind(kind);
    clearTimeout(highlightTimer.current);
    highlightTimer.current = setTimeout(() => {
      setHighlightedId(null);
      setHighlightedKind(null);
    }, HIGHLIGHT_MS);
  }, []);

  useEffect(() => () => clearTimeout(highlightTimer.current), []);

  // Scroll the highlighted item into view once it exists. The feed may still be
  // paging towards it, so this waits briefly rather than resolving once.
  useEffect(() => {
    if (!highlightedId) return;
    let frame = 0;
    const deadline = performance.now() + HIGHLIGHT_MS;
    const find = () => {
      const target = document.getElementById(evidenceTargetId(highlightedId));
      if (target) {
        target.scrollIntoView({ block: "center", behavior: "smooth" });
        return;
      }
      if (performance.now() < deadline) frame = requestAnimationFrame(find);
    };
    frame = requestAnimationFrame(find);
    return () => cancelAnimationFrame(frame);
  }, [highlightedId]);

  const listen = useCallback(
    (runId: string) => {
      const source = openRunStream(runId);
      streams.current.set(runId, source);

      const onEvent = (raw: MessageEvent<string>) => {
        const event = JSON.parse(raw.data) as RunEvent;
        setRuns((current) => {
          const run = current[runId];
          return run ? { ...current, [runId]: applyEvent(run, event) } : current;
        });
        if (event.type === "run.completed" || event.type === "run.failed") {
          source.close();
          streams.current.delete(runId);
          void queryClient.invalidateQueries({ queryKey: queryKeys.recommendations });
        }
      };

      for (const type of [
        "run.started",
        "agent.step",
        "agent.tool",
        "agent.text_delta",
        "output.final",
        "run.failed",
        "run.completed",
      ]) {
        source.addEventListener(type, onEvent as EventListener);
      }
      source.onerror = () => {
        setRuns((current) => {
          const run = current[runId];
          if (!run || run.status !== "RUNNING") return current;
          return {
            ...current,
            [runId]: {
              ...run,
              status: "FAILED",
              error: { code: "UPSTREAM_UNAVAILABLE", message: "Live updates stopped." },
            },
          };
        });
        source.close();
        streams.current.delete(runId);
      };
    },
    [queryClient],
  );

  useEffect(() => {
    const open = streams.current;
    return () => {
      for (const source of open.values()) source.close();
      open.clear();
    };
  }, []);

  // Session restore: rebuild the transcript from the persisted runs, oldest
  // first. It runs once per session, prepends so a run started meanwhile is
  // kept, and skips runs the transcript already holds — the session a live run
  // adopts comes back containing that very run.
  useEffect(() => {
    const session = restored.data;
    if (!session || restoredSessionId.current === session.id) return;
    restoredSessionId.current = session.id;

    setRuns((current) => {
      const restoredRuns: Record<string, RunState> = {};
      for (const run of session.runs) {
        if (current[run.id]) continue;
        restoredRuns[run.id] = {
          ...run,
          trigger_label: runLabel(run),
          request: run.message ? { message: run.message } : { trigger: run.trigger ?? undefined },
        };
      }
      return { ...restoredRuns, ...current };
    });

    setTranscript((current) => {
      const known = new Set(
        current.filter((entry) => entry.kind === "run").map((entry) => entry.id),
      );
      const entries: TranscriptEntry[] = [];
      for (const run of session.runs) {
        if (run.agent !== "EXECUTION" || known.has(run.id)) continue;
        if (run.message) {
          entries.push({ kind: "marketer", id: `${run.id}-message`, text: run.message });
        }
        entries.push({ kind: "run", id: run.id });
      }
      return entries.length > 0 ? [...entries, ...current] : current;
    });
  }, [restored.data]);

  // Every RUNNING run has exactly one open stream. Keeping this separate from
  // the run-once restore makes it idempotent, so a remount reattaches.
  useEffect(() => {
    for (const run of Object.values(runs)) {
      if (run.status === "RUNNING" && !streams.current.has(run.id)) listen(run.id);
    }
  }, [runs, listen]);

  const startRun = useCallback(
    (request: RunRequest, label?: string, { retry = false } = {}) => {
      if (request.message && !retry) {
        setTranscript((current) => [
          ...current,
          { kind: "marketer", id: `msg-${Date.now()}`, text: request.message ?? "" },
        ]);
      }
      startRunMutation.mutate(
        { ...request, session_id: sessionId },
        {
          onError: (cause) => {
            setTranscript((current) => [
              ...current,
              {
                kind: "router",
                id: `error-${Date.now()}`,
                message:
                  cause instanceof ApiError ? cause.message : "The run could not be started.",
                options: [],
                pointsAtFeed: false,
              },
            ]);
          },
          onSuccess: (response) => {
            setSessionId(response.session_id);
            try {
              window.localStorage.setItem(SESSION_STORAGE_KEY, response.session_id);
            } catch {
              // A blocked storage quota must not stop the run.
            }

            if (response.run_id === null) {
              const pointsAtFeed = response.response.status === "OUT_OF_SCOPE";
              setTranscript((current) => [
                ...current,
                {
                  kind: "router",
                  id: `router-${Date.now()}`,
                  message: response.response.message,
                  options: response.response.clarification_options,
                  pointsAtFeed,
                },
              ]);
              return;
            }

            const run: RunState = {
              id: response.run_id,
              request,
              agent: response.agent,
              intent: response.intent,
              trigger_label: label ?? response.intent,
              route: response.route,
              status: "RUNNING",
              steps: [],
              tool_calls: [],
              output: null,
              error: null,
              started_at: new Date().toISOString(),
              finished_at: null,
            };
            setRuns((current) => ({ ...current, [run.id]: run }));
            if (run.agent === "EXECUTION") {
              setTranscript((current) => [...current, { kind: "run", id: run.id }]);
            } else {
              setActiveStrategyRunId(run.id);
            }
          },
        },
      );
    },
    [sessionId, startRunMutation],
  );

  const value = useMemo<WorkspaceValue>(
    () => ({
      draft,
      setDraft,
      transcript,
      runs,
      activeStrategyRunId,
      startRun,
      highlightedId,
      highlightedKind,
      highlight,
    }),
    [
      draft,
      transcript,
      runs,
      activeStrategyRunId,
      startRun,
      highlightedId,
      highlightedKind,
      highlight,
    ],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}
