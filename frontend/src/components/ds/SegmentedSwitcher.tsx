import { cn } from "../../lib/cn";

interface SegmentedSwitcherProps<T extends string> {
  label: string;
  options: readonly { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
}

/** Bottom switcher for the one-column layout at 900px and below (ui-spec §2). */
export function SegmentedSwitcher<T extends string>({
  label,
  options,
  value,
  onChange,
  className,
}: SegmentedSwitcherProps<T>) {
  return (
    <div
      role="tablist"
      aria-label={label}
      className={cn(
        "flex gap-0.5 rounded-sm border border-border-strong bg-surface-card p-0.5",
        className,
      )}
    >
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(option.value)}
            className={cn(
              "h-4 flex-1 cursor-pointer rounded-sm text-small font-medium",
              selected ? "bg-primary-light text-text-accent" : "text-text-muted",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
