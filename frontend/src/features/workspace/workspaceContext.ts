import { createContext, useContext } from "react";

import type {
  AgentName,
  EvidenceKind,
  Run,
  ExecutionOutput,
  RouteDecision,
  RunRequest,
  RunStatus,
  RunStep,
  RunTrigger,
  StrategyOutput,
  ToolCall,
} from "../../api";

/** One agent run as the transcript and the Strategy panel see it. */
export interface RunState {
  id: string;
  /** What started this run, so a failed run can be retried unchanged. */
  request: RunRequest;
  agent: AgentName;
  intent: string;
  trigger_label: string;
  route: RouteDecision;
  status: RunStatus;
  steps: RunStep[];
  tool_calls: ToolCall[];
  output: StrategyOutput | ExecutionOutput | null;
  error: { code: string; message: string } | null;
  started_at: string;
  finished_at: string | null;
  /** The last event applied, so a replayed stream never applies one twice. */
  last_seq: number;
}

export type TranscriptEntry =
  | { kind: "marketer"; id: string; text: string }
  | { kind: "router"; id: string; message: string; options: string[]; pointsAtFeed: boolean }
  | { kind: "run"; id: string };

export interface WorkspaceValue {
  /** The Execution composer's text. "Do this" writes here and sends nothing. */
  draft: string;
  /**
   * `trigger` pins the item the text came from: sent unedited, the draft runs
   * that trigger, so Execution gets the recommendation itself. Any edit drops it.
   */
  setDraft: (draft: string, trigger?: RunTrigger) => void;
  sendDraft: () => void;
  /** Execution-side conversation only; Strategy output never enters it. */
  transcript: TranscriptEntry[];
  runs: Record<string, RunState>;
  /** The Strategy run currently in flight, shown in the Strategy panel. */
  activeStrategyRunId: string | null;
  /** `label` is what the turn header shows; it defaults to the run's intent. */
  /** `retry` re-sends a failed run without echoing its message again. */
  /** `echo` is what the transcript shows the marketer sent, for a trigger run. */
  startRun: (
    request: RunRequest,
    label?: string,
    options?: { retry?: boolean; echo?: string },
  ) => void;
  /** Scroll to and flash-highlight an evidence target anywhere on the page. */
  highlightedId: string | null;
  highlightedKind: EvidenceKind | null;
  highlight: (id: string, kind: EvidenceKind) => void;
}

export const WorkspaceContext = createContext<WorkspaceValue | null>(null);

export function useWorkspace(): WorkspaceValue {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return value;
}

/**
 * What a turn header shows. Derived rather than read off the API: it is
 * presentation, and no contract carries it.
 */
export function runLabel(run: Run): string {
  const deliverable = run.agent === "EXECUTION" ? run.output?.deliverable?.type : undefined;
  return [run.intent, deliverable].filter(Boolean).join(" · ");
}

/** DOM id an evidence chip scrolls to. Every highlightable item uses it. */
export function evidenceTargetId(id: string): string {
  return `evidence-${id}`;
}

/**
 * Which evidence kinds the page renders a row for. Company context is the
 * tenant's own profile: it has no row to scroll to, so a chip for it does not
 * pretend to navigate.
 */
export const EVIDENCE_HAS_TARGET: Record<EvidenceKind, boolean> = {
  activity: true,
  trend: true,
  influencer: true,
  company: false,
};
