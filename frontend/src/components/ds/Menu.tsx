import { useCallback, useRef, useState, type ReactNode } from "react";

import { useDismissable } from "../../hooks/useDismissable";
import { cn } from "../../lib/cn";
import { Icon } from "./Icon";

type MenuRole = "menu" | "listbox";

interface MenuProps {
  label: string;
  /** What the trigger button shows. */
  trigger: ReactNode;
  role?: MenuRole;
  /** "up" opens above the trigger, for the docked composer; "down-end" aligns
   * the overlay's right edge with the trigger's, for controls near the page edge. */
  placement?: Placement;
  triggerClassName?: string;
  children: (close: () => void) => ReactNode;
}

type Placement = "up" | "down" | "down-end";

const PLACEMENT: Record<Placement, string> = {
  up: "bottom-6 left-0",
  down: "top-5 left-0",
  "down-end": "top-5 right-0",
};

/** Trigger plus a single dismissable overlay. The workspace's only popup pattern. */
export function Menu({
  label,
  trigger,
  role = "menu",
  placement = "down",
  triggerClassName,
  children,
}: MenuProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const close = useCallback(() => setOpen(false), []);
  useDismissable(open, containerRef, close);

  return (
    <div ref={containerRef} className="relative flex-none">
      <button
        type="button"
        aria-haspopup={role}
        aria-expanded={open}
        aria-label={label}
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "inline-flex h-4 cursor-pointer items-center gap-1 rounded-sm px-1 text-small font-medium whitespace-nowrap",
          triggerClassName ?? "border border-border bg-surface-card text-text",
        )}
      >
        {trigger}
        <Icon name="chevronDown" size={12} />
      </button>
      {open ? (
        <div
          role={role}
          aria-label={label}
          className={cn(
            "absolute z-10 flex w-35 flex-col gap-0.5 rounded-lg border border-border-strong bg-surface-card p-1 shadow-overlay",
            PLACEMENT[placement],
          )}
        >
          {children(close)}
        </div>
      ) : null}
    </div>
  );
}

interface MenuItemProps {
  onSelect: () => void;
  role?: "menuitem" | "menuitemradio" | "option";
  checked?: boolean;
  description?: string;
  children: ReactNode;
}

export function MenuItem({
  onSelect,
  role = "menuitem",
  checked,
  description,
  children,
}: MenuItemProps) {
  const selectionProps =
    role === "menuitemradio"
      ? { "aria-checked": checked }
      : role === "option"
        ? { "aria-selected": checked }
        : {};
  return (
    <button
      type="button"
      role={role}
      {...selectionProps}
      onClick={onSelect}
      className={cn(
        "flex cursor-pointer flex-col items-start gap-0.5 rounded-sm p-1 text-left",
        checked ? "bg-surface-muted" : "bg-surface-card",
      )}
    >
      <span className="flex w-full items-center gap-1 text-body font-medium text-text">
        <span className="min-w-0 truncate">{children}</span>
        {checked ? (
          <span className="text-accent ml-auto">
            <Icon name="check" size={16} />
          </span>
        ) : null}
      </span>
      {description ? <span className="text-small text-text-muted">{description}</span> : null}
    </button>
  );
}
