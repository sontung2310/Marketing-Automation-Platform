import type { ButtonHTMLAttributes, ReactNode } from "react";

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
  children: ReactNode;
}

/** The only button in the workspace. One primary per card (ui-spec §8). */
export function Button({ variant = "secondary", className, children, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      {...rest}
      className={cn(
        "inline-flex flex-none cursor-pointer items-center gap-1 whitespace-nowrap disabled:cursor-default",
        VARIANT[variant],
        className,
      )}
    >
      {children}
    </button>
  );
}
