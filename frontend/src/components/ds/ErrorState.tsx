import { Button } from "./Button";

interface ErrorStateProps {
  /** The API error envelope's message, shown verbatim (api-contract). */
  message: string;
  onRetry: () => void;
  retryLabel?: string;
}

export function ErrorState({ message, onRetry, retryLabel = "Retry" }: ErrorStateProps) {
  return (
    <div role="alert" className="flex flex-col items-start gap-2 p-3">
      <p className="text-small text-text">{message}</p>
      <Button onClick={onRetry}>{retryLabel}</Button>
    </div>
  );
}
