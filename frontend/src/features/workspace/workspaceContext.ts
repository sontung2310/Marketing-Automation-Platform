import { createContext, useContext } from "react";

import type {
  AgentHint,
  AgentName,
  ExecutionOutput,
  RouteDecision,
  RunRequest,
  RunStatus,
  RunStep,
  StrategyOutput,
  ToolCall,
} from "../../api";

/** One agent run as the transcript and the Strategy panel see it. */
export interface RunState {
  id: string;
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
}

export type TranscriptEntry =
  | { kind: "marketer"; id: string; text: string }
  | { kind: "router"; id: string; message: string; options: string[]; pointsAtFeed: boolean }
  | { kind: "run"; id: string };

export interface WorkspaceValue {
  /** The Execution composer's text. "Do this" writes here and sends nothing. */
  draft: string;
  setDraft: (draft: string) => void;
  agentHint: AgentHint;
  setAgentHint: (hint: AgentHint) => void;
  /** Execution-side conversation only; Strategy output never enters it. */
  transcript: TranscriptEntry[];
  runs: Record<string, RunState>;
  /** The Strategy run currently in flight, shown in the Strategy panel. */
  activeStrategyRunId: string | null;
  /** `label` is what the turn header shows; it defaults to the run's intent. */
  startRun: (request: RunRequest, label?: string) => void;
  /** Scroll to and flash-highlight an evidence target anywhere on the page. */
  highlightedId: string | null;
  highlight: (id: string) => void;
}

export const WorkspaceContext = createContext<WorkspaceValue | null>(null);

export function useWorkspace(): WorkspaceValue {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return value;
}

/** DOM id an evidence chip scrolls to. Every highlightable item uses it. */
export function evidenceTargetId(id: string): string {
  return `evidence-${id}`;
}
