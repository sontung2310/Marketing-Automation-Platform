import { useState } from "react";

import { ApiError, type Channel, type Trend } from "../../api";
import { Badge } from "../../components/ds/Badge";
import { Button } from "../../components/ds/Button";
import { EmptyState } from "../../components/ds/EmptyState";
import { ErrorState } from "../../components/ds/ErrorState";
import { SkeletonList } from "../../components/ds/Skeleton";
import { Tabs } from "../../components/ds/Tabs";
import { useTrends } from "../../hooks/queries";
import { cn } from "../../lib/cn";
import { signedPercent } from "../../lib/format";
import { evidenceTargetId, useWorkspace } from "../workspace/workspaceContext";

type TrendTab = Channel | "ALL";

const TABS: readonly { value: TrendTab; label: string }[] = [
  { value: "ALL", label: "All" },
  { value: "LINKEDIN", label: "LinkedIn" },
  { value: "X", label: "X" },
  { value: "REDDIT", label: "Reddit" },
  { value: "NEWS", label: "News" },
];

const DIRECTION_COLOR: Record<Trend["direction"], string> = {
  RISING: "text-text-favorable",
  FALLING: "text-text-unfavorable",
  STEADY: "text-text-muted",
};

export function TrendList() {
  const [tab, setTab] = useState<TrendTab>("ALL");
  const trends = useTrends(tab);
  const { startRun, highlightedId } = useWorkspace();

  return (
    <>
      <Tabs label="Platform" options={TABS} value={tab} onChange={setTab} />

      {trends.isPending ? <SkeletonList rows={5} label="Loading trends" /> : null}

      {trends.isError ? (
        <ErrorState
          message={trends.error instanceof ApiError ? trends.error.message : "Trends unavailable."}
          onRetry={() => void trends.refetch()}
        />
      ) : null}

      {trends.isSuccess && trends.data.items.length === 0 ? (
        <EmptyState message="No trends computed yet." />
      ) : null}

      {trends.data?.items.map((trend) => (
        <div
          key={trend.id}
          id={evidenceTargetId(trend.id)}
          className={cn(
            "group flex items-center gap-1 border-b border-border px-2 py-1 transition-colors duration-300",
            highlightedId === trend.id ? "bg-surface-selected" : "bg-surface-card",
          )}
        >
          <span className="flex min-w-0 flex-col">
            <span className="flex min-w-0 items-center gap-1">
              <span className="truncate text-body font-semibold text-text">{trend.topic}</span>
              {trend.is_mock ? <Badge title="Demo data, not a measured trend">MOCK</Badge> : null}
            </span>
            <span className="flex items-center gap-1 text-small text-text-muted">
              {trend.channel} · {trend.mention_count} mentions
              {trend.actions.map((action) => (
                <Button
                  key={action.action}
                  variant="quiet"
                  className="text-small opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100"
                  onClick={() =>
                    startRun({
                      trigger: { kind: "TREND", ref_id: trend.id, action: action.action },
                    })
                  }
                >
                  {action.label}
                </Button>
              ))}
            </span>
          </span>
          <span
            className={cn(
              "ml-auto flex-none text-h3 font-semibold",
              DIRECTION_COLOR[trend.direction],
            )}
          >
            {signedPercent(trend.momentum_pct)}
          </span>
        </div>
      ))}
    </>
  );
}
