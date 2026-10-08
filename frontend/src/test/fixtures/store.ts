// In-memory stand-in for the Platform API's state, so the fixture server can
// honour writes (keyword edits, simulate, mark-seen, approvals) the same way
// the real service will. Step 6 deletes this file, not a component.

import type { ActivityType, ItemActionName } from "../../api/enums";
import type {
  Activity,
  ItemAction,
  ProposedAction,
  Recommendation,
  Run,
  Session,
} from "../../api/types";
import {
  failedRunScript,
  RUN_SCRIPTS,
  recommendations,
  runs,
  session,
  type ScriptedEvent,
} from "./agents";
import { activities, company } from "./records";

export interface SimulationTemplate {
  competitor_id: string;
  competitor_name: string;
  channel: Activity["channel"];
  title: string;
  summary: string;
  url: string;
  author?: Activity["author"];
  price?: Activity["price"];
}

/**
 * One template per ActivityType, each targeting a fictional competitor with a
 * `.example` URL (data-contract §5). Simulation never touches a real company.
 */
const SIMULATION_TEMPLATES: Record<ActivityType, SimulationTemplate> = {
  NEW_BLOG: {
    competitor_id: "cpt_brightlane",
    competitor_name: "Brightlane Marketing",
    channel: "WEBSITE",
    title: "A field guide to measuring brand search lift",
    summary: "Published a guide on attributing brand search to campaign activity.",
    url: "https://brightlane.example/blog/brand-search-lift",
  },
  SOCIAL_POST: {
    competitor_id: "cpt_kestrel",
    competitor_name: "Kestrel Growth Co.",
    channel: "LINKEDIN",
    title: "A carousel on writing briefs people can act on",
    summary: "Shared a LinkedIn carousel about briefs that survive contact with the work.",
    url: "https://kestrel.example/posts/actionable-briefs",
  },
  EXECUTIVE_POST: {
    competitor_id: "cpt_kestrel",
    competitor_name: "Kestrel Growth Co.",
    channel: "LINKEDIN",
    title: "Agencies that still bill by the hour are selling the wrong thing",
    summary: "CEO Jordan Bell argued that hourly billing misprices judgement.",
    url: "https://kestrel.example/posts/hourly-billing",
    author: { name: "Jordan Bell", role: "CEO" },
  },
  NEW_PRODUCT: {
    competitor_id: "cpt_brightlane",
    competitor_name: "Brightlane Marketing",
    channel: "WEBSITE",
    title: "Introduced a fractional CMO package",
    summary: "Added a senior fractional offer to the services page.",
    url: "https://brightlane.example/services/fractional-cmo",
  },
  PRODUCT_REMOVED: {
    competitor_id: "cpt_kestrel",
    competitor_name: "Kestrel Growth Co.",
    channel: "WEBSITE",
    title: "Retired its SEO starter package",
    summary: "Removed the entry-level SEO package from the services page.",
    url: "https://kestrel.example/services",
  },
  PRICE_CHANGE: {
    competitor_id: "cpt_brightlane",
    competitor_name: "Brightlane Marketing",
    channel: "WEBSITE",
    title: "Cut its retainer starting price",
    summary: "Published a lower starting price for monthly retainers.",
    url: "https://brightlane.example/pricing",
    price: { before: 2500, after: 1990, currency: "AUD" },
  },
  PROMOTION: {
    competitor_id: "cpt_kestrel",
    competitor_name: "Kestrel Growth Co.",
    channel: "LINKEDIN",
    title: "20% off annual retainers until 31 Oct",
    summary: "Announced a time-limited discount on annual retainers.",
    url: "https://kestrel.example/offers/annual-retainer",
    price: { before: 4100, after: 3280, currency: "AUD" },
  },
  CAMPAIGN_LAUNCH: {
    competitor_id: "cpt_brightlane",
    competitor_name: "Brightlane Marketing",
    channel: "LINKEDIN",
    title: "Launched the Grow with AI webinar series",
    summary: "Started a four-part webinar campaign on applied AI for marketers.",
    url: "https://brightlane.example/campaigns/grow-with-ai",
  },
  PAGE_UPDATE: {
    competitor_id: "cpt_kestrel",
    competitor_name: "Kestrel Growth Co.",
    channel: "WEBSITE",
    title: "Rewrote its services page around AI",
    summary: "Reframed the services page copy around AI-assisted delivery.",
    url: "https://kestrel.example/services",
  },
};

const SOCIAL_DELIVERABLE: Partial<Record<Activity["channel"], ItemAction["deliverable_type"]>> = {
  LINKEDIN: "LINKEDIN_POST",
  X: "X_POST",
  INSTAGRAM: "INSTAGRAM_POST",
};

const WHY_IT_MATTERS: ItemAction = {
  action: "WHY_IT_MATTERS",
  label: "Why it matters",
  agent: "STRATEGY",
  primary: false,
};

const CREATE_SIMILAR_LABEL = {
  NEW_BLOG: "Create a similar blog",
  SOCIAL_POST: "Create a similar post",
  EXECUTIVE_POST: "Draft a CEO post",
} as const;

const PLAN_A_RESPONSE: ItemAction = {
  action: "RESPONSE_PLAN",
  label: "Plan a response",
  agent: "STRATEGY",
  primary: true,
};

/**
 * docs/specs.md §6, keyed by activity type so a tenth type is a compile error
 * rather than a silent "Plan a response". The real API computes this; the UI
 * never does.
 */
const PRIMARY_ACTION: Record<ActivityType, (channel: Activity["channel"]) => ItemAction[]> = {
  NEW_BLOG: () => [
    {
      action: "CREATE_SIMILAR",
      label: CREATE_SIMILAR_LABEL.NEW_BLOG,
      agent: "EXECUTION",
      deliverable_type: "BLOG_DRAFT",
      primary: true,
    },
    WHY_IT_MATTERS,
  ],
  SOCIAL_POST: (channel) => [
    {
      action: "CREATE_SIMILAR",
      label: CREATE_SIMILAR_LABEL.SOCIAL_POST,
      agent: "EXECUTION",
      deliverable_type: SOCIAL_DELIVERABLE[channel] ?? "LINKEDIN_POST",
      primary: true,
    },
    WHY_IT_MATTERS,
  ],
  EXECUTIVE_POST: () => [
    {
      action: "CREATE_SIMILAR",
      label: CREATE_SIMILAR_LABEL.EXECUTIVE_POST,
      agent: "EXECUTION",
      deliverable_type: "CEO_POST",
      primary: true,
    },
    WHY_IT_MATTERS,
  ],
  NEW_PRODUCT: () => [PLAN_A_RESPONSE],
  PRODUCT_REMOVED: () => [PLAN_A_RESPONSE],
  PRICE_CHANGE: () => [PLAN_A_RESPONSE],
  PROMOTION: () => [PLAN_A_RESPONSE],
  CAMPAIGN_LAUNCH: () => [PLAN_A_RESPONSE],
  PAGE_UPDATE: () => [PLAN_A_RESPONSE],
};

function actionsFor(activity_type: ActivityType, channel: Activity["channel"]): ItemAction[] {
  return PRIMARY_ACTION[activity_type](channel);
}

/** Which agent a deterministic trigger routes to (docs/agents-spec.md §5). */
export const TRIGGER_AGENT: Record<ItemActionName, Run["agent"]> = {
  CREATE_SIMILAR: "EXECUTION",
  DRAFT_OUTREACH: "EXECUTION",
  DO_THIS: "EXECUTION",
  WHY_IT_MATTERS: "STRATEGY",
  RESPONSE_PLAN: "STRATEGY",
  USE_TREND: "STRATEGY",
  GENERATE_STRATEGY: "STRATEGY",
};

/** Only these competitors may carry simulated activity (docs/specs.md §3). */
const FICTIONAL_COMPETITOR_IDS = new Set(["cpt_brightlane", "cpt_kestrel"]);

export class ValidationError extends Error {}
export class ConflictError extends Error {}

let counter = 0;
const nextId = (prefix: string) => `${prefix}_${(counter += 1).toString().padStart(4, "0")}`;

export interface RunTicket {
  run: Run;
  script: ScriptedEvent[];
}

class FixtureStore {
  activities: Activity[] = [...activities];
  trackedKeywords: string[] = [...company.tracked_keywords];
  recommendations: Recommendation[] = [...recommendations];
  session: Session = { ...session, runs: [...session.runs] };
  readonly actions = new Map<string, ProposedAction>();
  readonly tickets = new Map<string, RunTicket>();
  private readonly listeners = new Set<(activity: Activity) => void>();
  private nextRunFailure: { code: string; message: string } | null = null;

  constructor() {
    for (const run of runs) {
      if (run.agent === "EXECUTION" && run.output) {
        for (const action of run.output.proposed_actions) this.actions.set(action.id, action);
      }
    }
  }

  onActivity(listener: (activity: Activity) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * Replaces the tracked keywords. Trims, rejects empty terms and enforces
   * 1–20 case-insensitively unique terms, preserving the first spelling
   * (api-contract, `PUT /company/tracked-keywords`).
   */
  setTrackedKeywords(input: unknown): string[] {
    if (!Array.isArray(input))
      throw new ValidationError("tracked_keywords must be a list of terms");
    const canonical: string[] = [];
    const seen = new Set<string>();
    for (const raw of input) {
      const term = typeof raw === "string" ? raw.trim() : "";
      if (!term) throw new ValidationError("Every tracked keyword must be a non-empty term");
      const key = term.toLocaleLowerCase();
      if (seen.has(key)) throw new ValidationError(`"${term}" is already tracked`);
      seen.add(key);
      canonical.push(term);
    }
    if (canonical.length < 1 || canonical.length > 20) {
      throw new ValidationError("Track between 1 and 20 keywords");
    }
    this.trackedKeywords = canonical;
    return canonical;
  }

  markSeen(upTo: string): number {
    let updated = 0;
    for (const activity of this.activities) {
      if (activity.is_new && activity.detected_at <= upTo) {
        activity.is_new = false;
        updated += 1;
      }
    }
    return updated;
  }

  get unseenCount(): number {
    return this.activities.filter((activity) => activity.is_new).length;
  }

  simulate(activity_type: ActivityType | null, competitor_id: string | null): Activity {
    if (competitor_id && !FICTIONAL_COMPETITOR_IDS.has(competitor_id)) {
      throw new ValidationError(
        "Simulated activity can only be created for fictional demo competitors",
      );
    }
    const types = Object.keys(SIMULATION_TEMPLATES) as ActivityType[];
    const type = activity_type ?? (types[Math.floor(Math.random() * types.length)] as ActivityType);
    const template = SIMULATION_TEMPLATES[type];
    const activity: Activity = {
      id: nextId("act_sim"),
      competitor_id: template.competitor_id,
      competitor_name: template.competitor_name,
      activity_type: type,
      channel: template.channel,
      title: template.title,
      summary: template.summary,
      url: template.url,
      author: template.author ?? null,
      price: template.price ?? null,
      engagement: null,
      detected_at: new Date().toISOString(),
      is_mock: true,
      is_simulated: true,
      is_new: true,
      actions: actionsFor(type, template.channel),
    };
    this.activities.unshift(activity);
    for (const listener of this.listeners) listener(activity);
    return activity;
  }

  startRun(agent: Run["agent"], intent: string, message: string | null): RunTicket {
    const runId = nextId("run");
    const seed = { id: runId, session_id: this.session.id, intent, message };
    const failure = this.nextRunFailure;
    this.nextRunFailure = null;
    const ticket: RunTicket = {
      run: RUN_SCRIPTS[agent].start(seed),
      script: failure ? failedRunScript(runId, failure) : RUN_SCRIPTS[agent].events(runId),
    };
    this.tickets.set(runId, ticket);
    return ticket;
  }

  /** Makes the next started run stream `run.failed` (e2e only). */
  failNextRun(error: { code: string; message: string }): void {
    this.nextRunFailure = error;
  }

  /** The next run stream ends after this seq, as the server's scheduled close does. */
  streamCut: number | null = null;

  takeStreamCut(): number | null {
    const cut = this.streamCut;
    this.streamCut = null;
    return cut;
  }

  approve(actionId: string, overrides?: Record<string, unknown>): ProposedAction {
    const action = this.actions.get(actionId);
    if (!action) throw new ConflictError(`Action ${actionId} not found`);
    if (action.status !== "PROPOSED") {
      throw new ConflictError(`Action ${actionId} is already ${action.status}`);
    }
    const executed: ProposedAction = {
      ...action,
      payload: { ...action.payload, ...overrides },
      status: "EXECUTED",
      receipt: {
        receipt_id: nextId("rcp"),
        status: "SCHEDULED",
        channel: "LINKEDIN",
        scheduled_for: String(overrides?.scheduled_for ?? action.payload.scheduled_for ?? ""),
      },
      updated_at: new Date().toISOString(),
    };
    this.actions.set(actionId, executed);
    return executed;
  }

  discard(actionId: string): ProposedAction {
    const action = this.actions.get(actionId);
    if (!action) throw new ConflictError(`Action ${actionId} not found`);
    if (action.status !== "PROPOSED") {
      throw new ConflictError(`Action ${actionId} is already ${action.status}`);
    }
    const discarded: ProposedAction = {
      ...action,
      status: "DISCARDED",
      updated_at: new Date().toISOString(),
    };
    this.actions.set(actionId, discarded);
    return discarded;
  }
}

export const store = new FixtureStore();
