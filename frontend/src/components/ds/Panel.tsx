import { useId, type ReactNode } from "react";

interface PanelProps {
  title: string;
  children: ReactNode;
}

/** White bordered panel with an uppercase label heading (design system: Card). */
export function Panel({ title, children }: PanelProps) {
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="rounded-lg border border-border bg-surface-card p-3"
    >
      <h2
        id={headingId}
        className="mb-2 text-small font-semibold tracking-label text-text-muted uppercase"
      >
        {title}
      </h2>
      {children}
    </section>
  );
}
