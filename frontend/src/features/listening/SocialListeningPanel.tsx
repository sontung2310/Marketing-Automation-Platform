import { Panel } from "../../components/ds/Panel";
import { SkeletonList } from "../../components/ds/Skeleton";
import { useCompany } from "../../hooks/queries";
import { InfluencerTable } from "./InfluencerTable";
import { TrackedKeywordEditor } from "./TrackedKeywordEditor";
import { TrendList } from "./TrendList";

export function SocialListeningPanel() {
  const company = useCompany();
  const keywords = company.data?.tracked_keywords;

  return (
    <div className="flex min-h-0 scrollbar-thin flex-col gap-2 overflow-y-auto">
      <Panel
        className="flex-none"
        title="Social listening"
        meta={
          keywords ? (
            <span className="text-small text-text-muted">{keywords.length} keywords</span>
          ) : null
        }
      >
        {keywords ? (
          <TrackedKeywordEditor keywords={keywords} />
        ) : (
          <SkeletonList rows={5} label="Loading tracked keywords" />
        )}
        <TrendList />
      </Panel>
      <InfluencerTable />
    </div>
  );
}
