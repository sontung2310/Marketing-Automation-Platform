import { useId, type ReactNode } from "react";

import { cn } from "../../lib/cn";

interface PanelProps {
  title: string;
  /** Right-aligned meta text or control in the panel header. */
  meta?: ReactNode;
  className?: string;
  children: ReactNode;
}

/** White bordered region with an uppercase label heading (design system: Card). */
export function Panel({ title, meta, className, children }: PanelProps) {
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className={cn(
        "overflow-hidden rounded-md border border-border-strong bg-surface-card",
        className,
      )}
    >
      <div className="flex items-center gap-1 border-b border-border-strong px-2 py-1">
        <h2
          id={headingId}
          className="text-small font-semibold tracking-label text-text-muted uppercase"
        >
          {title}
        </h2>
        {meta ? <div className="ml-auto flex items-center gap-1">{meta}</div> : null}
      </div>
      {children}
    </section>
  );
}
