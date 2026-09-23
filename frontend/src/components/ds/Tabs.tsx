import { cn } from "../../lib/cn";

export interface TabOption<T extends string> {
  value: T;
  label: string;
}

interface TabsProps<T extends string> {
  label: string;
  options: readonly TabOption<T>[];
  value: T;
  onChange: (value: T) => void;
}

/** Underlined tab strip. Selection carries a border, not colour alone. */
export function Tabs<T extends string>({ label, options, value, onChange }: TabsProps<T>) {
  return (
    <div
      role="tablist"
      aria-label={label}
      className="flex scrollbar-thin gap-2 overflow-x-auto border-b border-border px-2"
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
              "cursor-pointer border-b-2 py-1 text-small font-semibold tracking-label whitespace-nowrap uppercase",
              selected ? "border-primary text-text" : "border-transparent text-text-muted",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
