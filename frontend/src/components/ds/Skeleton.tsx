import { cn } from "../../lib/cn";

interface SkeletonListProps {
  /** How many placeholder rows this region shows while loading (ui-spec §5). */
  rows: number;
  label: string;
  className?: string;
}

/** Loading placeholder. Always labelled, so the wait is announced, not just drawn. */
export function SkeletonList({ rows, label, className }: SkeletonListProps) {
  return (
    <div aria-busy="true" aria-label={label} className={cn("flex flex-col gap-1 p-2", className)}>
      {Array.from({ length: rows }, (_, index) => (
        <span key={index} className="h-3 animate-pulse rounded-sm bg-surface-muted" />
      ))}
    </div>
  );
}
