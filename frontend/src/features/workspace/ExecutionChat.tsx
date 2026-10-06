import { useEffect, useRef } from "react";

import { Button } from "../../components/ds/Button";
import { EmptyState } from "../../components/ds/EmptyState";
import { Panel, PanelCount } from "../../components/ds/Panel";
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
  const requests = transcript.filter((entry) => entry.kind === "run");
  const working = requests.some((entry) => runs[entry.id]?.status === "RUNNING");
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "end" });
  }, [transcript, runs]);

  return (
    <Panel
      title="Execution agent"
      icon="pen"
      className="flex min-h-0 flex-1 flex-col"
      meta={
        <>
          {working ? (
            <span className="flex items-center gap-0.5 text-small text-text-muted">
              <span
                aria-hidden="true"
                className="h-0.75 w-0.75 rounded-full bg-secondary ring-3 ring-secondary-light"
              />
              Working
            </span>
          ) : null}
          <PanelCount>{requests.length} requests</PanelCount>
        </>
      }
    >
      <div
        role="log"
        aria-live="polite"
        aria-label="Execution transcript"
        className="min-h-0 flex-1 scrollbar-thin overflow-y-auto px-3 pt-3 pb-2"
      >
        <div className="mx-auto flex w-full max-w-80 flex-col gap-3">
          {transcript.length === 0 ? (
            <EmptyState message="Pick an item from the feed, or ask Execution for a deliverable." />
          ) : null}

          {transcript.map((entry) => {
            if (entry.kind === "marketer") {
              return (
                <p
                  key={entry.id}
                  className="max-w-4/5 self-end rounded-lg bg-surface-muted px-2 py-1 text-body text-text"
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
        <div className="mx-auto flex w-full max-w-80 flex-col gap-1">
          <div role="group" aria-label="Try" className="flex flex-wrap justify-center gap-1">
            {PROMPT_CHIPS.map((chip) => (
              <Button key={chip} className="rounded-md px-2" onClick={() => setDraft(chip)}>
                {chip}
              </Button>
            ))}
          </div>
          <Composer />
        </div>
      </div>
    </Panel>
  );
}
