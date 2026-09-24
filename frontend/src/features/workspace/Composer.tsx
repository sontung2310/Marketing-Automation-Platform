import { useEffect, useRef, type KeyboardEvent } from "react";

import { Button } from "../../components/ds/Button";
import { Icon } from "../../components/ds/Icon";
import { useWorkspace } from "./workspaceContext";

const MAX_ROWS = 6;
/** The body token: 15px at line-height 1.5 (theme.css). */
const LINE_HEIGHT_PX = 22.5;

/**
 * Docked beneath the transcript and always reachable (ui-spec §7). The centre
 * belongs to Execution alone, so there is no agent to choose: Strategy is
 * reached from a feed item, and a strategy-shaped message comes back as one
 * clarification line pointing at the feed.
 */
export function Composer() {
  const { draft, setDraft, startRun } = useWorkspace();
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
    startRun({ message });
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  };

  return (
    // The field's own outline is suppressed so the ring can follow the rounded
    // wrapper. `focus-within` keeps it visible whenever the textarea has focus,
    // which the global :focus-visible rule cannot do from the base layer.
    <div className="flex flex-col rounded-lg border border-border-strong bg-surface-card focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-primary">
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
