interface SpinnerProps {
  /** Required: no spinner appears without a text label (ui-spec §8). */
  label: string;
  meta?: string;
}

export function Spinner({ label, meta }: SpinnerProps) {
  return (
    <span className="inline-flex items-center gap-1 text-small">
      <span
        aria-hidden="true"
        className="h-1.5 w-1.5 animate-spin rounded-full border-2 border-border border-t-primary"
      />
      <span className="text-text-muted">{label}</span>
      {meta ? <span className="text-text-muted">{meta}</span> : null}
    </span>
  );
}
