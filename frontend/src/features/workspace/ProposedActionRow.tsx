import { useState } from "react";

import { ApiError, type ActionType, type ProposedAction } from "../../api";
import { Badge } from "../../components/ds/Badge";
import { Button } from "../../components/ds/Button";
import { Spinner } from "../../components/ds/Spinner";
import { TextInput } from "../../components/ds/TextInput";
import { useApproveAction, useDiscardAction } from "../../hooks/queries";

/** Which actions carry a schedule the marketer may edit before approving. */
const IS_SCHEDULABLE: Record<ActionType, boolean> = {
  schedule_social_post: true,
  add_to_content_calendar: true,
  create_cms_draft: false,
  create_email_draft: false,
};

export function ProposedActionRow({ action }: { action: ProposedAction }) {
  const approve = useApproveAction();
  const discard = useDiscardAction();
  const [scheduledFor, setScheduledFor] = useState(String(action.payload.scheduled_for ?? ""));

  const current = approve.data ?? discard.data ?? action;
  const pending = approve.isPending || discard.isPending;
  const failure = approve.error ?? discard.error;

  if (current.status === "EXECUTED" && current.receipt) {
    return (
      <div className="flex items-center gap-1 border-t border-border bg-surface-page px-2 py-1">
        <Badge tone="favorable">EXECUTED</Badge>
        <span className="text-small text-text">{current.summary}</span>
        <span className="ml-auto text-small text-text-muted">
          {current.receipt.receipt_id} · mock
        </span>
      </div>
    );
  }

  if (current.status === "DISCARDED") {
    return (
      <div className="flex items-center gap-1 border-t border-border bg-surface-page px-2 py-1">
        <Badge>DISCARDED</Badge>
        <span className="text-small text-text-muted">{current.summary}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1 border-t border-border bg-surface-page px-2 py-1">
      <div className="flex items-center gap-1">
        <span className="flex-none text-small font-semibold text-text">{current.action_type}</span>
        <span className="text-small text-text-muted">{current.summary}</span>
        {pending ? <Spinner label="Approving…" /> : null}
        <Button
          variant="quiet"
          className="ml-auto text-small"
          disabled={pending}
          onClick={() => discard.mutate(current.id)}
        >
          Discard
        </Button>
        <Button
          variant="primary"
          className="h-4 text-small"
          disabled={pending}
          onClick={() =>
            approve.mutate({
              actionId: current.id,
              overrides: IS_SCHEDULABLE[current.action_type]
                ? { scheduled_for: scheduledFor }
                : undefined,
            })
          }
        >
          Approve
        </Button>
      </div>

      {IS_SCHEDULABLE[current.action_type] ? (
        <TextInput
          label="Scheduled for"
          value={scheduledFor}
          onChange={(event) => setScheduledFor(event.target.value)}
        />
      ) : null}

      {failure ? (
        <p role="alert" className="text-small text-text-unfavorable">
          {failure instanceof ApiError ? failure.message : "The action could not be updated."}
        </p>
      ) : null}
    </div>
  );
}
