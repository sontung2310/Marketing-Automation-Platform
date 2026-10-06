import { useMemo, useState } from "react";

import { ApiError, type Recommendation } from "../../api";
import { EmptyState } from "../../components/ds/EmptyState";
import { ErrorState } from "../../components/ds/ErrorState";
import { Panel, PanelCount } from "../../components/ds/Panel";
import { SkeletonList } from "../../components/ds/Skeleton";
import { Spinner } from "../../components/ds/Spinner";
import { useRecommendations } from "../../hooks/queries";
import { cn } from "../../lib/cn";
import { useWorkspace } from "../workspace/workspaceContext";

import { RecommendationSheet } from "./RecommendationSheet";

const STATUS_COLOR: Record<Recommendation["status"], string> = {
  OPEN: "text-text-favorable",
  IN_PROGRESS: "text-text-attention",
  DONE: "text-text-muted",
};

const PRIORITY_CLASS: Record<Recommendation["priority"], string> = {
  HIGH: "bg-primary-light text-accent",
  MEDIUM: "bg-surface-page text-text-muted",
  LOW: "bg-surface-page text-text-muted",
};

export function StrategyPanel() {
  const recommendations = useRecommendations();
  const { runs, activeStrategyRunId, startRun } = useWorkspace();
  const [openId, setOpenId] = useState<string | null>(null);

  const items = useMemo(() => recommendations.data?.items ?? [], [recommendations.data]);
  const grouped = useMemo(() => {
    const byRun = new Map<string, Recommendation[]>();
    for (const item of items) {
      const group = byRun.get(item.run_id);
      if (group) group.push(item);
      else byRun.set(item.run_id, [item]);
    }
    return [...byRun.values()];
  }, [items]);

  const open = items.find((item) => item.id === openId) ?? null;
  // The latest Strategy run stays tracked after it ends, so a failure keeps its
  // message and Retry here instead of vanishing (ui-spec §8).
  const latestRun = activeStrategyRunId ? runs[activeStrategyRunId] : undefined;
  const activeRun = latestRun?.status === "RUNNING" ? latestRun : undefined;
  const failedRun = latestRun?.error ? latestRun : undefined;
  const latestStep = activeRun?.steps.at(-1)?.label ?? "Planning";

  return (
    <Panel
      className="flex-none"
      title="Strategy recommendations"
      icon="target"
      meta={
        activeRun ? (
          <Spinner label={latestStep} />
        ) : (
          <PanelCount>{items.filter((item) => item.status === "OPEN").length} open</PanelCount>
        )
      }
    >
      {failedRun?.error ? (
        <ErrorState
          message={failedRun.error.message}
          retryLabel="Retry run"
          onRetry={() => startRun(failedRun.request, failedRun.trigger_label, { retry: true })}
        />
      ) : null}

      {recommendations.isPending ? <SkeletonList rows={3} label="Loading recommendations" /> : null}

      {recommendations.isError ? (
        <ErrorState
          message={
            recommendations.error instanceof ApiError
              ? recommendations.error.message
              : "Recommendations unavailable."
          }
          onRetry={() => void recommendations.refetch()}
        />
      ) : null}

      {recommendations.isSuccess && items.length === 0 && !latestRun?.error && !activeRun ? (
        <EmptyState message="No open recommendations — ask Strategy for a plan." />
      ) : null}

      {grouped.map((group) => (
        <div key={group[0]?.run_id}>
          <p className="border-b border-border bg-surface-page px-2 py-1 text-small text-text-muted">
            From: {group[0]?.run_label ?? group[0]?.run_id}
          </p>
          {group.map((recommendation) => (
            <button
              key={recommendation.id}
              type="button"
              aria-expanded={openId === recommendation.id}
              onClick={() => setOpenId(recommendation.id)}
              className={cn(
                "grid w-full cursor-pointer layout-recommendation-row gap-x-1 border-b border-border px-2 py-1 text-left transition-colors",
                openId === recommendation.id ? "bg-surface-selected" : "bg-surface-card",
              )}
            >
              <span className="text-accent row-span-2 text-small font-medium">
                {recommendation.ordinal}
              </span>
              <span className="flex min-w-0 items-center gap-1">
                <span
                  className={cn(
                    "flex-none rounded-sm px-0.5 text-small font-medium tracking-label",
                    PRIORITY_CLASS[recommendation.priority],
                  )}
                >
                  {recommendation.priority}
                </span>
                <span className="truncate text-body font-medium text-text">
                  {recommendation.title}
                </span>
              </span>
              <span
                className={cn(
                  "self-start text-small font-medium tracking-label",
                  STATUS_COLOR[recommendation.status],
                )}
              >
                {recommendation.status}
              </span>
              <span className="col-span-2 truncate text-small text-text-muted">
                {recommendation.next_action
                  ? `Next: ${recommendation.next_action.brief}`
                  : "Nothing to do yet, watching"}
              </span>
            </button>
          ))}
        </div>
      ))}

      {open ? <RecommendationSheet recommendation={open} onClose={() => setOpenId(null)} /> : null}
    </Panel>
  );
}
