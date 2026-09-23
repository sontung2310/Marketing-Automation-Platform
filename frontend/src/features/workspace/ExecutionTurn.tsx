import { useState } from "react";

import type { ExecutionOutput } from "../../api";
import { Button } from "../../components/ds/Button";
import { Icon, type IconName } from "../../components/ds/Icon";
import { Spinner } from "../../components/ds/Spinner";
import { useElapsedSeconds } from "../../hooks/useElapsedSeconds";
import { useWorkspace } from "./workspaceContext";
import { cn } from "../../lib/cn";
import { DeliverableCard } from "./DeliverableCard";
import type { RunState } from "./workspaceContext";

/** Which glyph a tool row shows. Unknown tools fall back to the data icon. */
const TOOL_ICON: Record<string, IconName> = {
  get_company_context: "database",
  list_competitors: "database",
  search_competitor_activity: "search",
  get_competitor_activity: "search",
  summarize_competitor_activity: "search",
  search_trends: "search",
  search_influencers: "search",
  get_influencer: "database",
  get_recommendation: "database",
};

function isExecutionOutput(output: RunState["output"]): output is ExecutionOutput {
  return output !== null && "message" in output;
}

/**
 * One Execution run, as structured blocks rather than a chat bubble: the agent
 * label and trigger, one collapsed thinking and tool line, then the answer and
 * the deliverable (ui-spec §3).
 */
export function ExecutionTurn({ run }: { run: RunState }) {
  const [open, setOpen] = useState(false);
  const { startRun } = useWorkspace();
  const running = run.status === "RUNNING";
  const output = isExecutionOutput(run.output) ? run.output : null;
  const elapsedSeconds = useElapsedSeconds(run.started_at, run.finished_at);
  const latestStep = run.steps.at(-1)?.label ?? "Starting the run";

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1 text-small text-text-muted">
        <span className="font-semibold text-text">EXECUTION</span>
        <span>{run.trigger_label}</span>
      </div>

      {run.steps.length > 0 || run.tool_calls.length > 0 ? (
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          className="inline-flex h-3.5 cursor-pointer items-center gap-1 self-start text-small text-text-muted"
        >
          <Icon name="clock" />
          <span>
            Thought for {elapsedSeconds}s, used {run.tool_calls.length}{" "}
            {run.tool_calls.length === 1 ? "tool" : "tools"}
          </span>
          <span className={cn("transition-transform", open && "rotate-90")}>
            <Icon name="chevronRight" size={14} />
          </span>
        </button>
      ) : null}

      {open ? (
        <ol className="flex flex-col gap-1">
          {run.steps.map((step, index) => (
            <li key={`${step.label}-${index}`} className="flex items-center gap-1 text-small">
              <span className="text-text-muted">
                <Icon name="idea" size={14} />
              </span>
              <span className="text-text-muted">{step.label}</span>
            </li>
          ))}
          {run.tool_calls.map((call, index) => (
            <li key={`${call.tool}-${index}`} className="flex items-center gap-1">
              <span className="text-text-muted">
                <Icon name={TOOL_ICON[call.tool] ?? "database"} size={14} />
              </span>
              <span className="flex h-3.5 flex-1 items-center gap-1 rounded-sm border border-border px-1 text-small">
                <span className="font-semibold text-text">{call.args_summary}</span>
                <span className="text-text-muted">{call.tool}</span>
                {call.result_count !== null ? (
                  <span className="text-text-muted">{call.result_count} results</span>
                ) : null}
                <span className="ml-auto text-text-muted">
                  {(call.duration_ms / 1000).toFixed(1)}s
                </span>
              </span>
            </li>
          ))}
        </ol>
      ) : null}

      {running ? <Spinner label={latestStep} meta={`${elapsedSeconds}s`} /> : null}

      {output ? <p className="text-body text-text">{output.message}</p> : null}

      {output?.deliverable ? (
        <DeliverableCard
          deliverable={output.deliverable}
          qualityCheck={output.quality_check}
          proposedActions={output.proposed_actions}
        />
      ) : null}

      {output && output.assumptions.length > 0 ? (
        <ul className="flex flex-col gap-0.5 text-small text-text-muted">
          {output.assumptions.map((assumption) => (
            <li key={assumption}>Assumption: {assumption}</li>
          ))}
        </ul>
      ) : null}

      {run.error ? (
        <div role="alert" className="flex items-center gap-1 text-small text-text">
          <span>{run.error.message}</span>
          <Button
            variant="quiet"
            className="text-small"
            onClick={() => startRun(run.request, run.trigger_label)}
          >
            Retry run
          </Button>
        </div>
      ) : null}
    </div>
  );
}
