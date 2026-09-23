import type { ReactNode } from "react";

interface EmptyStateProps {
  message: string;
  children?: ReactNode;
}

/** Direct, useful copy. Never an apology (ui-spec §5). */
export function EmptyState({ message, children }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-start gap-2 p-3">
      <p className="text-small text-text-muted">{message}</p>
      {children}
    </div>
  );
}
