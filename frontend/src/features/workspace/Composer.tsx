import type { KeyboardEvent } from "react";

import { Button } from "../../components/ds/Button";
import { Icon } from "../../components/ds/Icon";
import { useWorkspace } from "./workspaceContext";

/**
 * Docked beneath the transcript and always reachable (ui-spec §7). The centre
 * belongs to Execution alone, so there is no agent to choose: Strategy is
 * reached from a feed item, and a strategy-shaped message comes back as one
 * clarification line pointing at the feed.
 */
export function Composer() {
  const { draft, setDraft, sendDraft: send } = useWorkspace();

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
        rows={2}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask Execution for a deliverable…"
        className="composer-autogrow resize-none bg-transparent px-2 pt-2 pb-1 text-body text-text outline-none"
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
