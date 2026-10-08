import { ApiError } from "../../api";
import { Avatar } from "../../components/ds/Avatar";
import { Badge } from "../../components/ds/Badge";
import { Button } from "../../components/ds/Button";
import { EmptyState } from "../../components/ds/EmptyState";
import { ErrorState } from "../../components/ds/ErrorState";
import { Panel, PanelCount } from "../../components/ds/Panel";
import { SkeletonList } from "../../components/ds/Skeleton";
import { useInfluencers } from "../../hooks/queries";
import { cn } from "../../lib/cn";
import { compactNumber } from "../../lib/format";
import { evidenceTargetId, useWorkspace } from "../workspace/workspaceContext";

/** Exactly two visible columns; avatars fall back to monograms (ui-spec §3). */
export function InfluencerTable() {
  const influencers = useInfluencers();
  const { startRun, highlightedId } = useWorkspace();
  const items = influencers.data?.items ?? [];

  return (
    <Panel
      className="flex-none"
      title="Influencers"
      icon="people"
      meta={influencers.isSuccess ? <PanelCount>{items.length} ranked</PanelCount> : null}
    >
      {influencers.isPending ? <SkeletonList rows={5} label="Loading influencers" /> : null}

      {influencers.isError ? (
        <ErrorState
          message={
            influencers.error instanceof ApiError
              ? influencers.error.message
              : "Influencers unavailable."
          }
          onRetry={() => void influencers.refetch()}
        />
      ) : null}

      {influencers.isSuccess && items.length === 0 ? (
        <EmptyState message="No influencers matched these keywords." />
      ) : null}

      {items.length > 0 ? (
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th
                scope="col"
                className="border-b border-border-strong px-2 py-1 text-left text-small font-medium text-text-muted"
              >
                Influencer
              </th>
              <th
                scope="col"
                className="border-b border-border-strong px-2 py-1 text-right text-small font-medium text-text-muted"
              >
                Followers
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((influencer) => (
              <tr
                key={influencer.id}
                id={evidenceTargetId(influencer.id)}
                className={cn(
                  "group transition-colors duration-300",
                  highlightedId === influencer.id ? "bg-surface-selected" : "bg-surface-card",
                )}
              >
                <td className="border-b border-border px-2 py-1">
                  <span className="flex min-w-0 items-center gap-1">
                    <Avatar name={influencer.name} src={influencer.avatar_url} />
                    <span className="flex min-w-0 flex-col">
                      <a
                        href={influencer.profile_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="truncate text-body font-medium text-text"
                      >
                        {influencer.handle}
                      </a>
                      <span className="flex items-center gap-1 text-small text-text-muted">
                        {influencer.channel}
                        {influencer.is_mock ? (
                          <Badge title="Demo data, not a discovered profile">MOCK</Badge>
                        ) : null}
                        {influencer.actions.map((action) => (
                          <Button
                            key={action.action}
                            variant="quiet"
                            size="sm"
                            className="opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100"
                            onClick={() =>
                              startRun(
                                {
                                  trigger: {
                                    kind: "INFLUENCER",
                                    ref_id: influencer.id,
                                    action: action.action,
                                  },
                                },
                                `${action.action} · ${influencer.handle}`,
                              )
                            }
                          >
                            {action.label}
                          </Button>
                        ))}
                      </span>
                    </span>
                  </span>
                </td>
                <td className="border-b border-border px-2 py-1 text-right text-body font-medium text-text tabular-nums">
                  {compactNumber(influencer.followers)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </Panel>
  );
}
