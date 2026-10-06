import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

import { cn } from "../../lib/cn";

export type ButtonVariant = "primary" | "secondary" | "quiet" | "icon";

const VARIANT: Record<ButtonVariant, string> = {
  primary:
    "h-4.5 rounded-sm bg-primary-hover px-2 text-body font-semibold text-white transition-colors hover:bg-primary-strong disabled:bg-border-strong",
  secondary:
    "h-4 rounded-sm border border-border bg-surface-card px-1 text-small text-text transition-colors hover:border-border-strong",
  quiet: "h-4 text-body font-semibold text-text-muted transition-colors hover:text-text",
  icon: "grid h-4 w-4 place-items-center rounded-sm text-text-muted transition-colors hover:bg-surface-page hover:text-text",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  /** Let a long label wrap onto more lines instead of overflowing. */
  wrap?: boolean;
  children: ReactNode;
}

/** The only button in the workspace. One primary per card (ui-spec §8). */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", wrap = false, className, children, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      {...rest}
      className={cn(
        "inline-flex flex-none cursor-pointer items-center gap-1 disabled:cursor-default",
        wrap ? "h-auto min-h-4 max-w-full py-0.5 text-left" : "whitespace-nowrap",
        VARIANT[variant],
        className,
      )}
    >
      {children}
    </button>
  );
});
