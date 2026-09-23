import { useEffect, useRef, type KeyboardEvent } from "react";

import { AGENT_HINTS, type AgentHint } from "../../api";
import { Button } from "../../components/ds/Button";
import { Icon } from "../../components/ds/Icon";
import { Menu, MenuItem } from "../../components/ds/Menu";
import { useWorkspace } from "./workspaceContext";

const AGENT_COPY: Record<AgentHint, { label: string; description: string }> = {
  AUTO: { label: "Auto", description: "The router picks the agent" },
  STRATEGY: { label: "Strategy", description: "Decide what to do next" },
  EXECUTION: { label: "Execution", description: "Make the deliverable" },
};

const MAX_ROWS = 6;
/** The body token: 15px at line-height 1.5 (theme.css). */
const LINE_HEIGHT_PX = 22.5;

/** Docked beneath the transcript and always reachable (ui-spec §7). */
export function Composer() {
  const { draft, setDraft, agentHint, setAgentHint, startRun } = useWorkspace();
  const textarea = useRef<HTMLTextAreaElement>(null);

  // Grow with the content up to six lines, then scroll inside the field. This
  // is a measurement, not styling: the height depends on the rendered content,
  // so it cannot be a token class. Recorded in ui-spec §7.
  useEffect(() => {
    const element = textarea.current;
    if (!element) return;
    element.style.height = "auto";
    element.style.height = `${Math.min(element.scrollHeight, MAX_ROWS * LINE_HEIGHT_PX)}px`;
  }, [draft]);

  const send = () => {
    const message = draft.trim();
    if (!message) return;
    setDraft("");
    startRun({ message, agent_hint: agentHint });
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  };

  return (
    <div className="flex flex-col rounded-lg border border-border-strong bg-surface-card">
      <label htmlFor="composer" className="sr-only">
        Message the Execution agent
      </label>
      <textarea
        id="composer"
        ref={textarea}
        rows={2}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask Execution for a deliverable…"
        className="resize-none bg-transparent px-2 pt-2 pb-1 text-body text-text outline-none"
      />
      <div className="flex items-center gap-1 px-1 pb-1">
        <Menu
          label="Choose the agent"
          placement="up"
          trigger={AGENT_COPY[agentHint].label}
          triggerClassName="text-text"
        >
          {(close) => (
            <>
              {AGENT_HINTS.map((hint) => (
                <MenuItem
                  key={hint}
                  role="menuitemradio"
                  checked={agentHint === hint}
                  description={AGENT_COPY[hint].description}
                  onSelect={() => {
                    setAgentHint(hint);
                    close();
                  }}
                >
                  {AGENT_COPY[hint].label}
                </MenuItem>
              ))}
            </>
          )}
        </Menu>
        <span className="ml-auto text-small text-text-muted">Shift+Enter for a new line</span>
        <Button
          variant="primary"
          aria-label="Send"
          className="h-4 w-4 justify-center rounded-lg px-0"
          disabled={draft.trim().length === 0}
          onClick={send}
        >
          <Icon name="send" />
        </Button>
      </div>
    </div>
  );
}
