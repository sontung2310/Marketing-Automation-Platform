import { useEffect, useMemo, useState } from "react";

import type { Activity, ItemAction } from "../../api";
import { ApiError } from "../../api";
import { Badge } from "../../components/ds/Badge";
import { Button } from "../../components/ds/Button";
import { EmptyState } from "../../components/ds/EmptyState";
import { ErrorState } from "../../components/ds/ErrorState";
import { LiveRegion } from "../../components/ds/LiveRegion";
import { Panel } from "../../components/ds/Panel";
import { SkeletonList } from "../../components/ds/Skeleton";
import { useActivities, useMarkSeen } from "../../hooks/queries";
import { useWorkspace } from "../workspace/workspaceContext";
import { ActivityCard } from "./ActivityCard";
import { FeedFilters, type FeedFilterState } from "./FeedFilters";
import { useActivityStream } from "./useActivityStream";

const EMPTY_MESSAGE =
  "No competitor activity in the last 30 days — run the pipelines or simulate a signal.";
const MARK_SEEN_DELAY_MS = 2000;

export function ActivityFeed() {
  const [filters, setFilters] = useState<FeedFilterState>({
    activityType: null,
    competitorId: null,
  });
  const query = useMemo(
    () => ({
      activity_types: filters.activityType ? [filters.activityType] : undefined,
      competitor_ids: filters.competitorId ? [filters.competitorId] : undefined,
    }),
    [filters],
  );

  const activities = useActivities(query);
  const markSeen = useMarkSeen();
  const { startRun, highlightedId, highlight } = useWorkspace();
  const { inserted, announcement, paused } = useActivityStream();

  const items: Activity[] = useMemo(() => {
    const pages = activities.data?.pages.flatMap((page) => page.items) ?? [];
    const known = new Set(pages.map((item) => item.id));
    return [...inserted.filter((item) => !known.has(item.id)), ...pages];
  }, [activities.data, inserted]);

  const unseenCount = (activities.data?.pages[0]?.unseen_count ?? 0) + inserted.length;
  const newest = items[0]?.detected_at;

  // The feed is "at the top" on load: two seconds later the NEW dots clear.
  useEffect(() => {
    if (!newest || unseenCount === 0) return;
    const timer = setTimeout(() => markSeen.mutate(newest), MARK_SEEN_DELAY_MS);
    return () => clearTimeout(timer);
    // markSeen is a stable mutation object; re-running on it would loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [newest, unseenCount]);

  // An evidence chip can cite an item further down the feed than the pages
  // loaded so far. Page towards it so the highlight has something to land on.
  useEffect(() => {
    if (!highlightedId || items.some((item) => item.id === highlightedId)) return;
    if (!activities.hasNextPage || activities.isFetchingNextPage) return;
    void activities.fetchNextPage();
  }, [highlightedId, items, activities]);

  const competitors = useMemo(() => {
    const byId = new Map(items.map((item) => [item.competitor_id, item.competitor_name]));
    return [...byId].map(([id, name]) => ({ id, name }));
  }, [items]);

  const onAction = (activity: Activity, action: ItemAction) => {
    highlight(activity.id);
    startRun(
      { trigger: { kind: "FEED_ACTION", ref_id: activity.id, action: action.action } },
      [action.action, action.deliverable_type ?? activity.activity_type].join(" · "),
    );
  };

  return (
    <Panel
      className="flex-none"
      title="Competitor activity"
      meta={unseenCount > 0 ? <Badge tone="brand">{unseenCount} new</Badge> : null}
    >
      <LiveRegion message={announcement} />

      {paused ? (
        <p
          role="status"
          className="border-b border-border bg-surface-page px-2 py-1 text-small text-text-attention"
        >
          Live updates paused — reconnecting…
        </p>
      ) : null}

      <FeedFilters competitors={competitors} value={filters} onChange={setFilters} />

      {activities.isPending ? <SkeletonList rows={4} label="Loading competitor activity" /> : null}

      {activities.isError ? (
        <ErrorState
          message={
            activities.error instanceof ApiError
              ? activities.error.message
              : "Competitor activity is unavailable."
          }
          onRetry={() => void activities.refetch()}
        />
      ) : null}

      {activities.isSuccess && items.length === 0 ? <EmptyState message={EMPTY_MESSAGE} /> : null}

      {items.map((activity) => (
        <ActivityCard
          key={activity.id}
          activity={activity}
          highlighted={highlightedId === activity.id}
          onAction={(action) => onAction(activity, action)}
        />
      ))}

      {activities.hasNextPage ? (
        <div className="p-2">
          <Button
            onClick={() => void activities.fetchNextPage()}
            disabled={activities.isFetchingNextPage}
          >
            {activities.isFetchingNextPage ? "Loading more…" : "Load more"}
          </Button>
        </div>
      ) : null}
    </Panel>
  );
}
