import { useId, type ReactNode } from "react";

import { cn } from "../../lib/cn";
import { Icon, type IconName } from "./Icon";

interface PanelProps {
  title: string;
  /** The framed glyph before the title (ui-spec §3). */
  icon: IconName;
  /** Right-aligned header content: usually a PanelCount, or a labelled status. */
  meta?: ReactNode;
  className?: string;
  children: ReactNode;
}

/** Bordered region with an icon, a sentence-case title and a count (design system: Card). */
export function Panel({ title, icon, meta, className, children }: PanelProps) {
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className={cn(
        "overflow-hidden rounded-md border border-border-strong bg-surface-card",
        className,
      )}
    >
      <div className="flex h-6 flex-none items-center gap-1 border-b border-border px-2">
        <span className="grid h-3 w-3 flex-none place-items-center rounded-sm border border-border bg-surface-card text-text shadow-xs">
          <Icon name={icon} size={14} />
        </span>
        <h2 id={headingId} className="text-body font-medium text-text">
          {title}
        </h2>
        {meta ? <div className="ml-auto flex items-center gap-1">{meta}</div> : null}
      </div>
      {children}
    </section>
  );
}

/** The header's count pill, such as `5 keywords` or `3 picks`. */
export function PanelCount({ children }: { children: ReactNode }) {
  return (
    <span className="rounded-full border border-border bg-surface-page px-1 text-small whitespace-nowrap text-text-muted">
      {children}
    </span>
  );
}
