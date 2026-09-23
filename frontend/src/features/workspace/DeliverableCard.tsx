import { useState } from "react";

import type { Deliverable, ProposedAction, QualityCheck, QualityStatus } from "../../api";
import { Button } from "../../components/ds/Button";
import { Icon } from "../../components/ds/Icon";
import { cn } from "../../lib/cn";
import { renderMarkdown } from "../../lib/markdown";
import { ProposedActionRow } from "./ProposedActionRow";

/** Status text carries the meaning; colour only reinforces it (ui-spec §6). */
const QUALITY_COLOR: Record<QualityStatus, string> = {
  PASS: "text-text-favorable",
  FIXED: "text-text-attention",
  FLAG: "text-text-unfavorable",
};

const QUALITY_LABEL: Record<keyof Omit<QualityCheck, "notes">, string> = {
  brand_voice: "Brand voice",
  originality: "Originality",
  factual_grounding: "Grounding",
  channel_fit: "Channel fit",
};

interface DeliverableCardProps {
  deliverable: Deliverable;
  qualityCheck: QualityCheck | null;
  proposedActions: ProposedAction[];
}

export function DeliverableCard({
  deliverable,
  qualityCheck,
  proposedActions,
}: DeliverableCardProps) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(deliverable.body_markdown);
      setCopied("Copied");
    } catch {
      setCopied("Copy failed");
    }
  };

  return (
    <div className="overflow-hidden rounded-md border border-border-strong">
      <div className="flex items-center gap-2 p-2">
        <span
          aria-hidden="true"
          className="grid h-5 w-5 flex-none place-items-center rounded-sm border border-border bg-surface-page text-text-muted"
        >
          <Icon name="document" size={18} />
        </span>
        <span className="flex min-w-0 flex-col">
          <span className="truncate text-body font-semibold text-text">{deliverable.title}</span>
          <span className="text-small text-text-muted">
            {deliverable.type}
            {deliverable.channel ? ` · ${deliverable.channel}` : ""} · {deliverable.word_count}{" "}
            words
          </span>
        </span>
        <Button className="ml-auto" onClick={() => setOpen((value) => !value)}>
          {open ? "Hide" : "Open"}
        </Button>
        <Button onClick={() => void copy()}>{copied ?? "Copy"}</Button>
      </div>

      {open ? (
        <div className="flex flex-col gap-2 border-t border-border px-2 py-2">
          {renderMarkdown(deliverable.body_markdown)}
          {deliverable.variants.length > 0 ? (
            <div className="flex flex-col gap-1">
              <span className="text-small font-semibold tracking-label text-text-muted uppercase">
                Variants
              </span>
              {deliverable.variants.map((variant) => (
                <p key={variant} className="text-small text-text">
                  {variant}
                </p>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      {qualityCheck ? (
        <div className="flex flex-wrap items-center gap-1 border-t border-border bg-surface-page px-2 py-1">
          {(Object.keys(QUALITY_LABEL) as (keyof typeof QUALITY_LABEL)[]).map((key) => (
            <span key={key} className="text-small">
              <span className="text-text-muted">{QUALITY_LABEL[key]} </span>
              <span
                className={cn("font-semibold tracking-label", QUALITY_COLOR[qualityCheck[key]])}
              >
                {qualityCheck[key]}
              </span>
            </span>
          ))}
          {qualityCheck.notes.map((note) => (
            <span key={note} className="w-full text-small text-text-muted">
              {note}
            </span>
          ))}
        </div>
      ) : null}

      {proposedActions.map((action) => (
        <ProposedActionRow key={action.id} action={action} />
      ))}
    </div>
  );
}
