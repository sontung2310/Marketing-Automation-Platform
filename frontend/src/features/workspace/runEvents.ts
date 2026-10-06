import type { RunEvent } from "../../api";

import type { RunState } from "./workspaceContext";

/**
 * Applies one streamed event to a run. The reducer is exhaustive over the SSE
 * event table in docs/api-contract.md, so a new event type is a compile error.
 */
export function applyEvent(run: RunState, event: RunEvent): RunState {
  // A reconnect may replay events already applied; `seq` makes that a no-op.
  if (event.seq <= run.last_seq) return run;
  return { ...reduceEvent(run, event), last_seq: event.seq };
}

function reduceEvent(run: RunState, event: RunEvent): RunState {
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
