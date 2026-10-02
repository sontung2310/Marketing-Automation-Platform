import { useEffect, useState } from "react";

/**
 * Seconds a run has been going. While it is still running the value ticks every
 * second, which is what keeps the transcript visibly alive during a long step
 * (docs/specs.md §8: no run goes more than 10 s without a UI update).
 */
export function useElapsedSeconds(startedAt: string, finishedAt: string | null): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (finishedAt) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [finishedAt]);

  const end = finishedAt ? new Date(finishedAt).getTime() : now;
  return Math.max(1, Math.round((end - new Date(startedAt).getTime()) / 1000));
}
