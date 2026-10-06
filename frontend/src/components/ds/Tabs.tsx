import { cn } from "../../lib/cn";

export interface TabOption<T extends string> {
  value: T;
  label: string;
  /** Shown after the label, e.g. how many rows the tab holds. */
  count?: number;
}

type TabsVariant = "underline" | "segmented";

interface TabsProps<T extends string> {
  label: string;
  options: readonly TabOption<T>[];
  value: T;
  onChange: (value: T) => void;
  variant?: TabsVariant;
}

// Selection is never colour alone: a border (underline) or a raised fill (segmented).
const STYLE: Record<
  TabsVariant,
  { wrapper: string; list: string; tab: string; on: string; off: string }
> = {
  underline: {
    wrapper: "",
    list: "flex scrollbar-thin gap-2 overflow-x-auto border-b border-border px-2",
    tab: "border-b-2 py-1 text-small font-medium tracking-label whitespace-nowrap uppercase",
    on: "border-primary text-text",
    off: "border-transparent text-text-muted",
  },
  segmented: {
    wrapper: "border-b border-border px-2 py-1",
    list: "grid auto-cols-fr grid-flow-col gap-px rounded-md border border-border bg-surface-muted p-px",
    tab: "inline-flex h-3.5 items-center justify-center gap-0.5 rounded-sm px-0.5 text-small font-medium whitespace-nowrap transition-colors",
    on: "bg-surface-card text-text shadow-xs",
    off: "text-text-muted hover:text-text",
  },
};

/** A tab strip: underlined, or a segmented control. */
export function Tabs<T extends string>({
  label,
  options,
  value,
  onChange,
  variant = "underline",
}: TabsProps<T>) {
  const style = STYLE[variant];
  return (
    <div className={style.wrapper}>
      <div role="tablist" aria-label={label} className={style.list}>
        {options.map((option) => {
          const selected = option.value === value;
          return (
            <button
              key={option.value}
              type="button"
              role="tab"
              aria-selected={selected}
              onClick={() => onChange(option.value)}
              className={cn("cursor-pointer", style.tab, selected ? style.on : style.off)}
            >
              {option.label}
              {/* The space keeps the accessible name "All 16", not "All16". */}
              {option.count === undefined ? null : " "}
              {option.count === undefined ? null : (
                <span
                  className={cn("text-micro", selected ? "text-text-accent" : "text-text-muted")}
                >
                  {option.count}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
