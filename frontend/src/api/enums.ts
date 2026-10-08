// Enum values from docs/data-contract.md §2 and docs/agents-spec.md §6.2/§7.2.
// Each is a runtime tuple plus its union type, so filters and registries can be
// keyed by the enum and checked for exhaustiveness at compile time.

export const ACTIVITY_TYPES = [
  "NEW_BLOG",
  "SOCIAL_POST",
  "EXECUTIVE_POST",
  "NEW_PRODUCT",
  "PRODUCT_REMOVED",
  "PRICE_CHANGE",
  "PROMOTION",
  "CAMPAIGN_LAUNCH",
  "PAGE_UPDATE",
] as const;
export type ActivityType = (typeof ACTIVITY_TYPES)[number];

export const CHANNELS = [
  "WEBSITE",
  "LINKEDIN",
  "X",
  "INSTAGRAM",
  "FACEBOOK",
  "YOUTUBE",
  "REDDIT",
  "NEWS",
  "TIKTOK",
] as const;
export type Channel = (typeof CHANNELS)[number];

export const TREND_DIRECTIONS = ["RISING", "STEADY", "FALLING"] as const;
export type TrendDirection = (typeof TREND_DIRECTIONS)[number];

export const PRIORITIES = ["HIGH", "MEDIUM", "LOW"] as const;
export type Priority = (typeof PRIORITIES)[number];

export const AGENTS = ["STRATEGY", "EXECUTION"] as const;
export type AgentName = (typeof AGENTS)[number];

export const AGENT_HINTS = ["AUTO", "STRATEGY", "EXECUTION"] as const;
export type AgentHint = (typeof AGENT_HINTS)[number];

export const DELIVERABLE_TYPES = [
  "BLOG_DRAFT",
  "BLOG_OUTLINE",
  "LINKEDIN_POST",
  "X_POST",
  "INSTAGRAM_POST",
  "CEO_POST",
  "EMAIL",
  "AD_COPY",
  "RESPONSE_BRIEF",
  "INFLUENCER_OUTREACH",
] as const;
export type DeliverableType = (typeof DELIVERABLE_TYPES)[number];

export const RECOMMENDATION_KINDS = [
  "CONTENT_TOPIC",
  "COMPETITIVE_RESPONSE",
  "INFLUENCER_PARTNERSHIP",
  "CHANNEL_PLAY",
  "MONITOR",
] as const;
export type RecommendationKind = (typeof RECOMMENDATION_KINDS)[number];

export const RECOMMENDATION_STATUSES = ["OPEN", "IN_PROGRESS", "DONE"] as const;
export type RecommendationStatus = (typeof RECOMMENDATION_STATUSES)[number];

export const QUALITY_STATUSES = ["PASS", "FIXED", "FLAG"] as const;
export type QualityStatus = (typeof QUALITY_STATUSES)[number];

export const ACTION_TYPES = [
  "schedule_social_post",
  "create_cms_draft",
  "create_email_draft",
  "add_to_content_calendar",
] as const;
export type ActionType = (typeof ACTION_TYPES)[number];

export const PROPOSED_ACTION_STATUSES = [
  "PROPOSED",
  "APPROVED",
  "EXECUTED",
  "DISCARDED",
  "FAILED",
] as const;
export type ProposedActionStatus = (typeof PROPOSED_ACTION_STATUSES)[number];

export const EVIDENCE_KINDS = ["activity", "trend", "influencer", "company"] as const;
export type EvidenceKind = (typeof EVIDENCE_KINDS)[number];

export const RUN_STATUSES = [
  "RUNNING",
  "SUCCEEDED",
  "FAILED",
  "NEEDS_CLARIFICATION",
  "REFUSED",
] as const;
export type RunStatus = (typeof RUN_STATUSES)[number];

/** Item-action names computed server-side from docs/specs.md §6. */
export const ITEM_ACTIONS = [
  "CREATE_SIMILAR",
  "WHY_IT_MATTERS",
  "RESPONSE_PLAN",
  "USE_TREND",
  "DRAFT_OUTREACH",
  "DO_THIS",
  "GENERATE_STRATEGY",
] as const;
export type ItemActionName = (typeof ITEM_ACTIONS)[number];

export const TRIGGER_KINDS = [
  "FEED_ACTION",
  "RECOMMENDATION",
  "TREND",
  "INFLUENCER",
  "COMPANY",
] as const;
export type TriggerKind = (typeof TRIGGER_KINDS)[number];
