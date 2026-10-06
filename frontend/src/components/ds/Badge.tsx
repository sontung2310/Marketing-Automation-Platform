import type { ReactNode } from "react";

import { cn } from "../../lib/cn";

export type BadgeTone = "neutral" | "brand" | "favorable" | "unfavorable" | "attention";

const TONE: Record<BadgeTone, string> = {
  neutral: "bg-surface-muted text-text-muted",
  brand: "bg-primary-light text-accent",
  favorable: "bg-secondary-light text-text-favorable",
  unfavorable: "bg-primary-light text-text-unfavorable",
  attention: "bg-surface-muted text-text-attention",
};

interface BadgeProps {
  tone?: BadgeTone;
  title?: string;
  children: ReactNode;
}

/** Enum label. Values render verbatim, and the tone is never the only signal. */
export function Badge({ tone = "neutral", title, children }: BadgeProps) {
  return (
    <span
      title={title}
      className={cn(
        "inline-flex flex-none items-center rounded-sm px-1 text-small font-medium tracking-label uppercase",
        TONE[tone],
      )}
    >
      {children}
    </span>
  );
}
