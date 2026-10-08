import { useMemo, useState } from "react";

import { ApiError } from "../../api";
import { Badge } from "../../components/ds/Badge";
import { Button } from "../../components/ds/Button";
import { EmptyState } from "../../components/ds/EmptyState";
import { ErrorState } from "../../components/ds/ErrorState";
import { Panel, PanelCount } from "../../components/ds/Panel";
import { Icon } from "../../components/ds/Icon";
import { SkeletonList } from "../../components/ds/Skeleton";
import { Spinner } from "../../components/ds/Spinner";
import type { StrategyOutput } from "../../api";
import { useCompany, useRecommendations } from "../../hooks/queries";
import { cn } from "../../lib/cn";
import { useWorkspace } from "../workspace/workspaceContext";

import { EVIDENCE_KIND } from "./evidenceKind";
import { PRIORITY_TONE } from "./priority";
import { RecommendationSheet } from "./RecommendationSheet";

const MAX_SIGNALS = 3;

/** Two digits, as the canvas numbers its picks: 1 → "01". */
const padOrdinal = (ordinal: number) => String(ordinal).padStart(2, "0");

/** The latest Strategy run's answer, implications and gaps, so an analysis
 * without picks (Why it matters) is still visible (ui-spec §3). */
function LatestAnalysis({ output }: { output: StrategyOutput }) {
  return (
    <section
      aria-label="Latest analysis"
      className="flex flex-col gap-1 border-b border-border bg-surface-muted px-2 py-1.5"
    >
      <span className="text-small font-medium tracking-label text-text-muted uppercase">
        Latest analysis
      </span>
      <p className="text-body text-text">{output.answer}</p>
      {output.implications.length > 0 ? (
        <ul className="flex list-disc flex-col gap-0.5 pl-2 text-small text-text">
          {output.implications.map((implication) => (
            <li key={implication}>{implication}</li>
          ))}
        </ul>
      ) : null}
      {output.data_gaps.length > 0 ? (
        <p className="text-small text-text-muted">Gaps: {output.data_gaps.join(" · ")}</p>
      ) : null}
    </section>
  );
}

export function StrategyPanel() {
  const recommendations = useRecommendations();
  const company = useCompany();
  const { runs, activeStrategyRunId, strategyRunning, startRun } = useWorkspace();
  const [openId, setOpenId] = useState<string | null>(null);

  const items = useMemo(() => recommendations.data?.items ?? [], [recommendations.data]);
  const open = items.find((item) => item.id === openId) ?? null;
  // The latest Strategy run stays tracked after it ends, so a failure keeps its
  // message and Retry here instead of vanishing (ui-spec §8).
  const latestRun = activeStrategyRunId ? runs[activeStrategyRunId] : undefined;
  const activeRun = latestRun?.status === "RUNNING" ? latestRun : undefined;
  const failedRun = latestRun?.error ? latestRun : undefined;
  const latestStep = activeRun?.steps.at(-1)?.label ?? "Planning";
  // The latest successful Strategy run, so a newer run in flight or failing keeps it.
  const analysis = useMemo(() => {
    const done = Object.values(runs).filter(
      (run) => run.agent === "STRATEGY" && run.status === "SUCCEEDED" && run.output,
    );
    const latest = done.sort((a, b) => b.started_at.localeCompare(a.started_at))[0];
    return (latest?.output as StrategyOutput | undefined) ?? null;
  }, [runs]);
  const companyId = company.data?.id;

  return (
    <Panel
      className="flex-none"
      title="Strategy recommendations"
      icon="target"
      meta={
        <>
          {activeRun ? (
            <Spinner label={latestStep} />
          ) : (
            <PanelCount>
              {items.length} {items.length === 1 ? "pick" : "picks"}
            </PanelCount>
          )}
          <Button
            variant="outline"
            size="sm"
            disabled={strategyRunning || !companyId}
            onClick={() =>
              companyId &&
              startRun(
                { trigger: { kind: "COMPANY", ref_id: companyId, action: "GENERATE_STRATEGY" } },
                "Generate strategy",
              )
            }
          >
            Generate strategy
          </Button>
        </>
      }
    >
      {failedRun?.error ? (
        <ErrorState
          message={failedRun.error.message}
          retryLabel="Retry run"
          onRetry={() => startRun(failedRun.request, failedRun.trigger_label, { retry: true })}
        />
      ) : null}

      {analysis ? <LatestAnalysis output={analysis} /> : null}

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
        <EmptyState message="No strategy yet. Generate strategy to get the team's plays." />
      ) : null}

      {items.map((recommendation) => (
        <article
          key={recommendation.id}
          aria-label={recommendation.title}
          className={cn(
            "flex flex-col gap-1 border-b border-border px-2 pt-1.5 pb-2 transition-colors duration-300",
            openId === recommendation.id ? "bg-surface-selected" : "bg-surface-card",
          )}
        >
          <div className="flex min-h-3.5 items-center gap-1">
            <span className="text-small font-medium text-text-accent">
              {padOrdinal(recommendation.ordinal)}
            </span>
            <Badge tone={PRIORITY_TONE[recommendation.priority]}>{recommendation.priority}</Badge>
            <Button
              aria-label={`Open plan for ${recommendation.title}`}
              aria-expanded={openId === recommendation.id}
              onClick={() => setOpenId(recommendation.id)}
              variant="outline"
              size="sm"
              className="ml-auto"
            >
              <Icon name="list" size={12} />
              Open plan
              <Icon name="chevronRight" size={12} />
            </Button>
          </div>

          <h3 className="text-body font-medium text-text">{recommendation.title}</h3>
          {recommendation.insight ? (
            <p className="line-clamp-2 text-small text-text">{recommendation.insight}</p>
          ) : null}
          {recommendation.audience ? (
            <p className="text-small text-text-muted">For {recommendation.audience}</p>
          ) : null}

          <ul className="flex flex-col gap-0.5">
            {recommendation.evidence.slice(0, MAX_SIGNALS).map((evidence) => {
              const kind = EVIDENCE_KIND[evidence.kind];
              return (
                <li
                  key={evidence.id}
                  className="grid layout-signal-row items-start gap-x-1 text-small text-text"
                >
                  <span
                    aria-hidden="true"
                    className={cn("grid h-2.25 w-2.25 place-items-center rounded-sm", kind.tile)}
                  >
                    <Icon name={kind.icon} size={12} />
                  </span>
                  <span className="text-text-muted">{kind.label}</span>
                  <span>{evidence.note}</span>
                </li>
              );
            })}
          </ul>
        </article>
      ))}

      {items.length > 0 ? (
        <p className="px-2 py-1 text-small text-text-muted">
          Moves without a pick stay in the competitor feed.
        </p>
      ) : null}

      {open ? <RecommendationSheet recommendation={open} onClose={() => setOpenId(null)} /> : null}
    </Panel>
  );
}
