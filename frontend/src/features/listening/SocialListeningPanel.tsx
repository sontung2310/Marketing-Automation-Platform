import { ApiError } from "../../api";
import { ErrorState } from "../../components/ds/ErrorState";
import { Panel, PanelCount } from "../../components/ds/Panel";
import { SkeletonList } from "../../components/ds/Skeleton";
import { useCompany, useTrends } from "../../hooks/queries";
import { InfluencerTable } from "./InfluencerTable";
import { TrackedKeywordEditor } from "./TrackedKeywordEditor";
import { TrendList } from "./TrendList";

export function SocialListeningPanel() {
  const company = useCompany();
  const keywords = company.data?.tracked_keywords;
  const trendCount = useTrends("ALL").data?.items.length;

  return (
    <div className="flex min-h-0 scrollbar-thin flex-col gap-2 overflow-y-auto">
      <Panel
        className="flex-none"
        title="Social listening"
        icon="listening"
        meta={
          keywords ? (
            <PanelCount>
              {keywords.length} keywords
              {trendCount === undefined ? "" : ` · ${trendCount} trends`}
            </PanelCount>
          ) : null
        }
      >
        {company.isError ? (
          <ErrorState
            message={
              company.error instanceof ApiError
                ? company.error.message
                : "The company context is unavailable."
            }
            onRetry={() => void company.refetch()}
          />
        ) : null}
        {company.isPending ? <SkeletonList rows={5} label="Loading tracked keywords" /> : null}
        {keywords ? <TrackedKeywordEditor keywords={keywords} /> : null}
        <TrendList />
      </Panel>
      <InfluencerTable />
    </div>
  );
}
