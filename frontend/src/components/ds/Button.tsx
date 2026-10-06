import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

import { cn } from "../../lib/cn";

export type ButtonVariant =
  "primary" | "secondary" | "outline" | "quiet" | "quietInverse" | "icon" | "chip";
export type ButtonSize = "md" | "sm" | "square";

// Colour and state only. Height, padding, radius and type live in SIZE, so a
// caller never overrides them through className: cn() does not merge, and two
// conflicting utilities would resolve by stylesheet order, not intent.
const VARIANT: Record<ButtonVariant, string> = {
  primary:
    "bg-primary-hover font-medium text-white transition-colors hover:bg-primary-strong disabled:bg-border-strong",
  secondary:
    "border border-border bg-surface-card text-text transition-colors hover:border-border-strong",
  /** A raised secondary that inverts on hover: the card's one way in, e.g. Open plan. */
  outline:
    "border border-border bg-surface-card font-medium text-text shadow-xs transition-colors hover:border-text hover:bg-text hover:text-surface-card",
  quiet: "font-medium text-text-muted transition-colors hover:text-text",
  /** Quiet, on the inverted TopBar band. */
  quietInverse: "font-medium text-text-inverse transition-colors hover:text-text-inverse-muted",
  icon: "grid place-items-center text-text-muted transition-colors hover:bg-surface-muted hover:text-text",
  chip: "border border-border bg-surface-card text-text transition-colors hover:border-border-strong hover:bg-surface-muted",
};

const SIZE: Record<ButtonVariant, { md: string } & Partial<Record<ButtonSize, string>>> = {
  primary: {
    md: "h-4.5 rounded-sm px-2 text-body",
    sm: "h-3.5 rounded-sm px-1.25 text-small",
    square: "h-4 w-4 justify-center rounded-md",
  },
  secondary: { md: "h-4 rounded-sm px-1 text-small", sm: "h-3.5 rounded-sm px-1 text-small" },
  outline: { md: "h-4 rounded-sm px-1 text-small", sm: "h-3.5 rounded-sm px-1 text-small" },
  quiet: { md: "h-4 text-body", sm: "h-3 text-small" },
  quietInverse: { md: "h-4 text-body", sm: "h-3 text-small" },
  icon: { md: "h-4 w-4 rounded-sm", sm: "h-2.5 w-2.5 rounded-sm" },
  chip: { md: "h-4 rounded-md px-2 text-small" },
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** Let a long label wrap onto more lines instead of overflowing. */
  wrap?: boolean;
  children: ReactNode;
}

/** The only button in the workspace. One primary per card (ui-spec §8). */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", size = "md", wrap = false, className, children, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      {...rest}
      className={cn(
        "inline-flex flex-none cursor-pointer items-center gap-1 disabled:cursor-default",
        VARIANT[variant],
        SIZE[variant][size] ?? SIZE[variant].md,
        wrap ? "h-auto min-h-4 max-w-full py-0.5 text-left" : "whitespace-nowrap",
        className,
      )}
    >
      {children}
    </button>
  );
});
