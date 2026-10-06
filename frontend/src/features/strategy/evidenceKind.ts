import type { EvidenceKind } from "../../api";
import type { IconName } from "../../components/ds/Icon";

/**
 * How each evidence kind reads on a recommendation card's signal lines and in
 * the sheet's chips (agents-spec §6.2). Trends are the favourable signal; the
 * rest stay quiet.
 */
export const EVIDENCE_KIND: Record<EvidenceKind, { label: string; icon: IconName; tile: string }> =
  {
    trend: { label: "Trend", icon: "trendUp", tile: "bg-secondary-light text-text-favorable" },
    activity: { label: "Competitor", icon: "pulse", tile: "bg-surface-muted text-text-muted" },
    influencer: { label: "Influencer", icon: "people", tile: "bg-surface-muted text-text-muted" },
    company: { label: "Company", icon: "database", tile: "bg-surface-muted text-text-muted" },
  };
