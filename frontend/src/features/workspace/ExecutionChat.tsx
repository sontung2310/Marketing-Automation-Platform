import { useEffect, useRef } from "react";

import { Button } from "../../components/ds/Button";
import { EmptyState } from "../../components/ds/EmptyState";
import { Panel } from "../../components/ds/Panel";
import { ClarificationBlock } from "./ClarificationBlock";
import { Composer } from "./Composer";
import { ExecutionTurn } from "./ExecutionTurn";
import { useWorkspace } from "./workspaceContext";

const PROMPT_CHIPS = [
  "Draft a CEO post",
  "Turn trend #1 into a blog outline",
  "Rewrite the last draft for X",
];

export function ExecutionChat() {
  const { transcript, runs, setDraft } = useWorkspace();
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [transcript, runs]);

  return (
    <Panel
      title="Execution agent"
      className="flex min-h-0 flex-1 flex-col"
      meta={
        <span className="text-small text-text-muted">
          Session · {transcript.filter((entry) => entry.kind === "run").length} requests
        </span>
      }
    >
      <div
        aria-live="polite"
        aria-label="Execution transcript"
        className="min-h-0 flex-1 scrollbar-thin overflow-y-auto px-3 pt-3 pb-2"
      >
        <div className="mx-auto flex w-full max-w-80 flex-col gap-3">
          {transcript.length === 0 ? (
            <EmptyState message="Pick an item from the feed, or ask Execution for a deliverable.">
              <div className="flex flex-wrap gap-1">
                {PROMPT_CHIPS.map((chip) => (
                  <Button key={chip} onClick={() => setDraft(chip)}>
                    {chip}
                  </Button>
                ))}
              </div>
            </EmptyState>
          ) : null}

          {transcript.map((entry) => {
            if (entry.kind === "marketer") {
              return (
                <p
                  key={entry.id}
                  className="max-w-4/5 self-end rounded-lg bg-surface-page px-2 py-1 text-body text-text"
                >
                  {entry.text}
                </p>
              );
            }
            if (entry.kind === "router") {
              return (
                <ClarificationBlock
                  key={entry.id}
                  message={entry.message}
                  options={entry.options}
                  pointsAtFeed={entry.pointsAtFeed}
                />
              );
            }
            const run = runs[entry.id];
            return run ? <ExecutionTurn key={entry.id} run={run} /> : null;
          })}
          <div ref={bottom} />
        </div>
      </div>

      <div className="px-3 pb-2">
        <div className="mx-auto w-full max-w-80">
          <Composer />
        </div>
      </div>
    </Panel>
  );
}
