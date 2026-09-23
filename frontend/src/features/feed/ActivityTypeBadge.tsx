import type { ActivityType } from "../../api";
import { Badge, type BadgeTone } from "../../components/ds/Badge";

/** All nine ActivityType values, on the existing tones only (ui-spec §3). */
const TONE: Record<ActivityType, BadgeTone> = {
  NEW_BLOG: "neutral",
  SOCIAL_POST: "neutral",
  EXECUTIVE_POST: "neutral",
  PAGE_UPDATE: "neutral",
  NEW_PRODUCT: "favorable",
  CAMPAIGN_LAUNCH: "favorable",
  PRODUCT_REMOVED: "unfavorable",
  PRICE_CHANGE: "attention",
  PROMOTION: "brand",
};

export function ActivityTypeBadge({ activityType }: { activityType: ActivityType }) {
  return <Badge tone={TONE[activityType]}>{activityType}</Badge>;
}
