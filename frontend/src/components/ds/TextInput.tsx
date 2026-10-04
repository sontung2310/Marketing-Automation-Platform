import { useId, type InputHTMLAttributes } from "react";

import { cn } from "../../lib/cn";

interface TextInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "id"> {
  label: string;
  /** Shown as text under the field; validation never relies on colour. */
  error?: string;
  labelHidden?: boolean;
}

export function TextInput({ label, error, labelHidden, className, ...rest }: TextInputProps) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <span className="flex flex-col gap-0.5">
      <label htmlFor={id} className={cn("text-small text-text-muted", labelHidden && "sr-only")}>
        {label}
      </label>
      <input
        id={id}
        type="text"
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        {...rest}
        className={cn(
          "h-4 rounded-sm border border-border-strong bg-surface-card px-1 text-small text-text",
          className,
        )}
      />
      {error ? (
        <span id={errorId} className="text-small text-text-unfavorable">
          {error}
        </span>
      ) : null}
    </span>
  );
}
