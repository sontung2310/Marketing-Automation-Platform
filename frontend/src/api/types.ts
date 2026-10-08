// Wire types for the Platform API, hand-typed against docs/api-contract.md and
// docs/data-contract.md. Roadmap Step 6.6 replaces this file with types
// generated from the backend's OpenAPI export; the shapes must not drift.

import type {
  ActionType,
  ActivityType,
  AgentHint,
  AgentName,
  Channel,
  DeliverableType,
  EvidenceKind,
  ItemActionName,
  Priority,
  ProposedActionStatus,
  QualityStatus,
  RecommendationKind,
  RecommendationStatus,
  RunStatus,
  TrendDirection,
  TriggerKind,
} from "./enums";

export interface ApiErrorBody {
  error: { code: string; message: string; details?: Record<string, unknown> };
}

/** One button on a feed item, trend or recommendation. Computed server-side. */
export interface ItemAction {
  action: ItemActionName;
  label: string;
  agent: AgentName;
  deliverable_type?: DeliverableType;
  primary?: boolean;
}

// --- Company ---------------------------------------------------------------

export interface CompanyService {
  name: string;
  description: string;
  price_from: number | null;
}

export interface CompanyIcp {
  segment: string;
  pains: string[];
  goals: string[];
}

export interface BrandVoice {
  tone: string[];
  do: string[];
  dont: string[];
  sample_copy: string[];
}

export interface Spokesperson {
  name: string;
  role: string;
  voice_notes: string[];
}

export interface Company {
  id: string;
  name: string;
  website: string;
  industry: string;
  region: string;
  summary: string;
  icp: CompanyIcp[];
  positioning: string;
  services: CompanyService[];
  brand_voice: BrandVoice;
  channels: Channel[];
  spokesperson: Spokesperson;
  tracked_keywords: string[];
  content_pillars: string[];
  is_mock: boolean;
  updated_at: string;
  last_sync_at: string | null;
}

export interface TrackedKeywordsBody {
  tracked_keywords: string[];
}

// --- Competitor activity ---------------------------------------------------

export interface ActivityAuthor {
  name: string;
  role: string;
}

export interface ActivityPrice {
  before: number;
  after: number;
  currency: string;
}

export interface ActivityEngagement {
  likes: number;
  comments: number;
  shares: number;
}

export interface Activity {
  id: string;
  competitor_id: string;
  competitor_name: string;
  activity_type: ActivityType;
  channel: Channel;
  title: string;
  summary: string;
  url: string | null;
  author: ActivityAuthor | null;
  price: ActivityPrice | null;
  engagement: ActivityEngagement | null;
  detected_at: string;
  is_mock: boolean;
  is_simulated: boolean;
  is_new: boolean;
  actions: ItemAction[];
}

export interface ActivityPage {
  items: Activity[];
  next_cursor: string | null;
  unseen_count: number;
}

export interface ActivityQuery {
  activity_types?: ActivityType[];
  competitor_ids?: string[];
  channels?: Channel[];
  since?: string;
  cursor?: string;
  limit?: number;
}

export interface SimulateBody {
  activity_type: ActivityType | null;
  competitor_id: string | null;
}

// --- Insights --------------------------------------------------------------

export interface SamplePost {
  title: string;
  url: string;
  channel: Channel;
}

export interface Trend {
  id: string;
  topic: string;
  keywords: string[];
  channel: Channel;
  window_days: number;
  mention_count: number;
  momentum_pct: number;
  direction: TrendDirection;
  sentiment: number;
  sample_posts: SamplePost[];
  /** A one-line read of the conversation, when the source provides one. */
  summary?: string | null;
  computed_at: string;
  is_mock: boolean;
  actions: ItemAction[];
}

export interface InfluencerEvidence {
  title: string;
  url: string;
}

export interface Influencer {
  id: string;
  name: string;
  handle: string;
  channel: Channel;
  profile_url: string;
  avatar_url: string | null;
  followers: number;
  engagement_rate: number;
  topics: string[];
  audience_region: string;
  relevance_score: number;
  evidence: InfluencerEvidence[];
  is_mock: boolean;
  actions: ItemAction[];
}

// --- Strategy recommendations ---------------------------------------------

export interface Evidence {
  id: string;
  kind: EvidenceKind;
  note: string;
}

export interface NextAction {
  agent: "EXECUTION";
  deliverable_type: DeliverableType;
  brief: string;
}

export interface Recommendation {
  id: string;
  run_id: string;
  session_id: string;
  ordinal: number;
  kind: RecommendationKind;
  title: string;
  rationale: string;
  priority: Priority;
  channel: Channel | null;
  evidence: Evidence[];
  skills_used: string[];
  next_action: NextAction | null;
  status: RecommendationStatus;
  created_at: string;
  /**
   * How the run that produced this recommendation was triggered, for the
   * grouping header (api-contract, `GET /recommendations`). Optional so an
   * older payload groups under its run id rather than "undefined".
   */
  run_label?: string;
  actions: ItemAction[];
}

// --- Agent outputs ---------------------------------------------------------

export interface ImageSuggestion {
  placement: string;
  content: string;
  style: string;
}

export interface Deliverable {
  type: DeliverableType;
  channel: Channel | null;
  title: string;
  body_markdown: string;
  variants: string[];
  word_count: number;
  author_persona: string | null;
  image_suggestions: ImageSuggestion[];
  requested_length: RequestedLength | null;
}

export interface RequestedLength {
  min_words: number | null;
  max_words: number | null;
  max_chars: number | null;
  thread: boolean;
}

export interface QualityCheck {
  brand_voice: QualityStatus;
  originality: QualityStatus;
  factual_grounding: QualityStatus;
  channel_fit: QualityStatus;
  notes: string[];
}

export interface ProposedAction {
  id: string;
  deliverable_id: string | null;
  action_type: ActionType;
  summary: string;
  payload: Record<string, unknown>;
  status: ProposedActionStatus;
  receipt: ActionReceipt | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface ActionReceipt {
  receipt_id: string;
  status: string;
  preview_url?: string;
  channel?: Channel;
  scheduled_for?: string;
}

export interface StrategyOutput {
  status: "OK" | "NEEDS_CLARIFICATION" | "REFUSED" | "INSUFFICIENT_DATA";
  answer: string;
  implications: string[];
  recommendations: Omit<
    Recommendation,
    "id" | "run_id" | "session_id" | "status" | "created_at" | "run_label" | "actions"
  >[];
  assumptions: string[];
  data_gaps: string[];
  clarification_options: string[];
  recommendation_ids: string[];
}

export interface ExecutionOutput {
  status: "OK" | "NEEDS_CLARIFICATION" | "REFUSED";
  message: string;
  deliverable: Deliverable | null;
  quality_check: QualityCheck | null;
  evidence_ids: string[];
  skills_used: string[];
  assumptions: string[];
  proposed_actions: ProposedAction[];
  clarification_options: string[];
  deliverable_id: string | null;
  proposed_action_ids: string[];
}

// --- Runs and sessions -----------------------------------------------------

export interface RunTrigger {
  kind: TriggerKind;
  ref_id: string;
  action: ItemActionName;
}

export interface RouteDecision {
  method: "DETERMINISTIC" | "CLASSIFIER" | "EXPLICIT";
  reason: string;
  confidence: number;
}

export interface RunRequest {
  session_id?: string | null;
  message?: string;
  agent_hint?: AgentHint;
  trigger?: RunTrigger;
}

export interface RunAccepted {
  run_id: string;
  session_id: string;
  agent: AgentName;
  intent: string;
  route: RouteDecision;
}

export interface RouterAnswer {
  run_id: null;
  session_id: string;
  route: RouteDecision;
  response: {
    status: "NEEDS_CLARIFICATION" | "OUT_OF_SCOPE";
    message: string;
    clarification_options: string[];
  };
}

export type RunResponse = RunAccepted | RouterAnswer;

export interface ToolCall {
  tool: string;
  args_summary: string;
  duration_ms: number;
  result_count: number | null;
}

export interface RunStep {
  label: string;
}

interface RunBase {
  id: string;
  session_id: string;
  intent: string;
  /** The marketer's message, when the run came from the composer. */
  message: string | null;
  trigger: RunTrigger | null;
  route: RouteDecision;
  status: RunStatus;
  steps: RunStep[];
  tool_calls: ToolCall[];
  skills_loaded: string[];
  error: { code: string; message: string } | null;
  started_at: string;
  finished_at: string | null;
}

export interface StrategyRun extends RunBase {
  agent: "STRATEGY";
  output: StrategyOutput | null;
}

export interface ExecutionRun extends RunBase {
  agent: "EXECUTION";
  output: ExecutionOutput | null;
}

export type Run = StrategyRun | ExecutionRun;

export interface Session {
  id: string;
  runs: Run[];
}

// --- Server-sent events ----------------------------------------------------

interface RunEventBase {
  run_id: string;
  seq: number;
  ts: string;
}

export type RunEventPayload =
  | { type: "run.started"; data: { agent: AgentName; intent: string; route: RouteDecision } }
  | { type: "agent.step"; data: RunStep }
  | { type: "agent.tool"; data: ToolCall }
  | { type: "agent.text_delta"; data: { text: string } }
  | { type: "output.final"; data: StrategyOutput | ExecutionOutput }
  | { type: "run.failed"; data: { code: string; message: string } }
  | {
      type: "run.completed";
      data: { status: RunStatus; duration_ms: number; usage: Record<string, number> };
    };

export type RunEvent = RunEventBase & RunEventPayload;

export interface ActivityCreatedEvent {
  type: "activity.created";
  data: Activity;
}
