// Agent-side fixtures: the Strategy recommendations the right rail shows, the
// session the workspace restores on load, and the event script a new run
// streams. Shapes follow docs/agents-spec.md §6.2/§7.2 and the SSE table in
// docs/api-contract.md.

import type {
  ExecutionOutput,
  ExecutionRun,
  Recommendation,
  Run,
  RunEvent,
  RunEventPayload,
  Session,
  StrategyOutput,
  StrategyRun,
} from "../../api/types";

export const SESSION_ID = "ses_fixture_01";
const STRATEGY_RUN_ID = "run_7a31";
const EXECUTION_RUN_ID = "run_7a2c";

const DO_THIS = {
  action: "DO_THIS",
  label: "Do this",
  agent: "EXECUTION",
} as const;

export const recommendations: Recommendation[] = [
  {
    id: "rec_0192",
    run_id: STRATEGY_RUN_ID,
    session_id: SESSION_ID,
    run_label: "Plan a response · PRICE_CHANGE",
    ordinal: 1,
    kind: "COMPETITIVE_RESPONSE",
    title: "Hold price, publish the reasoning",
    rationale:
      "Brightlane raised its executive visibility package, so matching them on price gives nothing away. Explaining why the Marketing Eye retainer stayed put turns their increase into a talking point. The move fits the brand-clarity pillar and needs no new offer.",
    priority: "HIGH",
    channel: "LINKEDIN",
    evidence: [
      {
        id: "act_seed_028",
        kind: "activity",
        note: "Raised its executive visibility package price",
      },
      { id: "act_seed_011", kind: "activity", note: "CEO post on positioning" },
    ],
    skills_used: ["pricing-response", "brand-voice"],
    next_action: {
      agent: "EXECUTION",
      deliverable_type: "LINKEDIN_POST",
      brief: "Write the LinkedIn post for recommendation #1",
    },
    status: "OPEN",
    created_at: new Date(Date.now() - 2 * 60_000).toISOString(),
    actions: [DO_THIS],
  },
  {
    id: "rec_0193",
    run_id: STRATEGY_RUN_ID,
    session_id: SESSION_ID,
    run_label: "Plan a response · PRICE_CHANGE",
    ordinal: 2,
    kind: "CONTENT_TOPIC",
    title: "Publish the AI search checklist",
    rationale:
      "AI search visibility is the fastest-rising topic across the tracked keywords. A practical checklist answers the question buyers are already asking, before a competitor does. It reuses the content-strategy service as its proof.",
    priority: "MEDIUM",
    channel: "WEBSITE",
    evidence: [{ id: "trd_seed_001", kind: "trend", note: "AI search visibility, up 142%" }],
    skills_used: ["content-planning"],
    next_action: {
      agent: "EXECUTION",
      deliverable_type: "BLOG_OUTLINE",
      brief: "Outline a blog post for recommendation #2",
    },
    status: "OPEN",
    created_at: new Date(Date.now() - 2 * 60_000).toISOString(),
    actions: [DO_THIS],
  },
  {
    id: "rec_0187",
    run_id: EXECUTION_RUN_ID,
    session_id: SESSION_ID,
    run_label: "Why it matters · EXECUTIVE_POST",
    ordinal: 1,
    kind: "MONITOR",
    title: "Watch retainer pricing",
    rationale:
      "Kestrel's CEO is arguing against hourly billing while Brightlane is repricing. If a second competitor moves its pricing model, this becomes a response rather than a watch.",
    priority: "LOW",
    channel: null,
    evidence: [
      { id: "act_seed_012", kind: "activity", note: "CEO note on making strategy visible" },
    ],
    skills_used: ["market-watch"],
    next_action: null,
    status: "OPEN",
    created_at: new Date(Date.now() - 18 * 60_000).toISOString(),
    actions: [],
  },
];

const CEO_POST_BODY = `Our retainer did not move this quarter. That was a decision, not an oversight.

When the market reprices, the easy move is to follow. We looked at what our clients actually buy from us: a team that knows their category, a plan they can defend to a board, and work that ships on the days we said it would. None of that got cheaper to deliver, and none of it got less useful to them.

So we held. What changed instead is what sits inside the same number. Every retainer now includes a quarterly positioning review, because the teams who win the next twelve months are the ones who can say what they do in a sentence a buyer repeats.

If your agency has raised its price this quarter, the fair question is what you get for the difference. Ask it. We would.`;

const executionOutput: ExecutionOutput = {
  status: "OK",
  message:
    "Drafted in first person for Marketing Eye's leader, 218 words, with a schedule proposed for Tuesday morning.",
  deliverable: {
    type: "CEO_POST",
    channel: "LINKEDIN",
    title: "Why our retainer did not move",
    body_markdown: CEO_POST_BODY,
    variants: ["Our retainer did not move. Here is what changed instead."],
    word_count: 218,
    author_persona: "Marketing Eye managing director",
  },
  quality_check: {
    brand_voice: "PASS",
    originality: "PASS",
    factual_grounding: "FIXED",
    channel_fit: "PASS",
    notes: ["Replaced an unsourced retention figure with a qualitative claim."],
  },
  evidence_ids: ["act_seed_011", "act_seed_028"],
  skills_used: ["brand-voice", "social"],
  assumptions: ["Based on demo data"],
  proposed_actions: [
    {
      id: "pac_0417",
      deliverable_id: "del_0417",
      action_type: "schedule_social_post",
      summary: "Schedule on LINKEDIN · Tue 09:00 AEST",
      payload: {
        channel: "LINKEDIN",
        scheduled_for: "2026-09-29T09:00:00+10:00",
        deliverable_id: "del_0417",
      },
      status: "PROPOSED",
      receipt: null,
      created_at: new Date(Date.now() - 17 * 60_000).toISOString(),
      updated_at: new Date(Date.now() - 17 * 60_000).toISOString(),
    },
  ],
  clarification_options: [],
  deliverable_id: "del_0417",
  proposed_action_ids: ["pac_0417"],
};

const executionRun: ExecutionRun = {
  id: EXECUTION_RUN_ID,
  session_id: SESSION_ID,
  agent: "EXECUTION",
  intent: "CREATE_SIMILAR",
  message: "Draft a CEO post about why our retainer did not move",
  trigger: { kind: "FEED_ACTION", ref_id: "act_seed_011", action: "CREATE_SIMILAR" },
  trigger_label: "CREATE_SIMILAR · CEO_POST",
  route: { method: "DETERMINISTIC", reason: "Feed action on an EXECUTIVE_POST", confidence: 1 },
  status: "SUCCEEDED",
  steps: [
    { label: "Loading company context" },
    { label: "Searching competitor activity" },
    { label: "Loading skill: brand-voice" },
  ],
  tool_calls: [
    {
      tool: "get_company_context",
      args_summary: "Loaded company context",
      duration_ms: 600,
      result_count: null,
    },
    {
      tool: "search_competitor_activity",
      args_summary: "Searched competitor activity",
      duration_ms: 1100,
      result_count: 4,
    },
  ],
  skills_loaded: ["brand-voice", "social"],
  output: executionOutput,
  error: null,
  started_at: new Date(Date.now() - 18 * 60_000).toISOString(),
  finished_at: new Date(Date.now() - 17 * 60_000).toISOString(),
};

const strategyOutput: StrategyOutput = {
  status: "OK",
  answer:
    "Brightlane repriced upward, which is an opening rather than a threat. Hold the retainer and publish the reasoning.",
  implications: [
    "Their increase makes the Marketing Eye retainer the value option without a discount.",
    "Executive visibility is where they are investing, so that is where the airtime is contested.",
  ],
  recommendations: [],
  assumptions: ["Based on demo data"],
  data_gaps: [],
  clarification_options: [],
  recommendation_ids: ["rec_0192", "rec_0193"],
};

const strategyRun: StrategyRun = {
  id: STRATEGY_RUN_ID,
  session_id: SESSION_ID,
  agent: "STRATEGY",
  intent: "RESPONSE_PLAN",
  message: null,
  trigger: { kind: "FEED_ACTION", ref_id: "act_seed_028", action: "RESPONSE_PLAN" },
  trigger_label: "RESPONSE_PLAN · PRICE_CHANGE",
  route: { method: "DETERMINISTIC", reason: "Feed action on a PRICE_CHANGE", confidence: 1 },
  status: "SUCCEEDED",
  steps: [{ label: "Loading company context" }, { label: "Searching competitor activity" }],
  tool_calls: [
    {
      tool: "get_competitor_activity",
      args_summary: "Loaded the triggering activity",
      duration_ms: 400,
      result_count: 1,
    },
  ],
  skills_loaded: ["pricing-response"],
  output: strategyOutput,
  error: null,
  started_at: new Date(Date.now() - 3 * 60_000).toISOString(),
  finished_at: new Date(Date.now() - 2 * 60_000).toISOString(),
};

export const runs: Run[] = [executionRun, strategyRun];

export const session: Session = { id: SESSION_ID, runs: [executionRun] };

/**
 * The event sequence a newly started run streams. Delays keep every gap under
 * the 10 seconds ui-spec §5 allows without a visible update.
 */
export interface ScriptedEvent {
  delay_ms: number;
  event: RunEvent;
}

function executionRunScript(runId: string, startedAt = new Date()): ScriptedEvent[] {
  let seq = 0;
  const at = (offset: number) => new Date(startedAt.getTime() + offset).toISOString();
  const next = (delay_ms: number, payload: RunEventPayload): ScriptedEvent => {
    seq += 1;
    return { delay_ms, event: { run_id: runId, seq, ts: at(delay_ms), ...payload } };
  };

  return [
    next(150, {
      type: "run.started",
      data: {
        agent: "EXECUTION",
        intent: "CREATE_SIMILAR",
        route: { method: "DETERMINISTIC", reason: "Feed action", confidence: 1 },
      },
    }),
    next(400, { type: "agent.step", data: { label: "Loading company context" } }),
    next(800, {
      type: "agent.tool",
      data: {
        tool: "get_company_context",
        args_summary: "Loaded company context",
        duration_ms: 600,
        result_count: null,
      },
    }),
    next(1200, { type: "agent.step", data: { label: "Searching competitor activity" } }),
    next(1700, {
      type: "agent.tool",
      data: {
        tool: "search_competitor_activity",
        args_summary: "Searched competitor activity",
        duration_ms: 1100,
        result_count: 4,
      },
    }),
    next(2100, { type: "agent.step", data: { label: "Loading skill: brand-voice" } }),
    next(2600, {
      type: "output.final",
      data: {
        ...executionOutput,
        deliverable_id: "del_new",
        proposed_action_ids: ["pac_new"],
      },
    }),
    next(2800, {
      type: "run.completed",
      data: {
        status: "SUCCEEDED",
        duration_ms: 2800,
        usage: { input_tokens: 4120, output_tokens: 610 },
      },
    }),
  ];
}

function strategyRunScript(runId: string, startedAt = new Date()): ScriptedEvent[] {
  let seq = 0;
  const at = (offset: number) => new Date(startedAt.getTime() + offset).toISOString();
  const next = (delay_ms: number, payload: RunEventPayload): ScriptedEvent => {
    seq += 1;
    return { delay_ms, event: { run_id: runId, seq, ts: at(delay_ms), ...payload } };
  };

  return [
    next(150, {
      type: "run.started",
      data: {
        agent: "STRATEGY",
        intent: "RESPONSE_PLAN",
        route: { method: "DETERMINISTIC", reason: "Feed action", confidence: 1 },
      },
    }),
    next(400, { type: "agent.step", data: { label: "Loading company context" } }),
    next(900, {
      type: "agent.tool",
      data: {
        tool: "get_competitor_activity",
        args_summary: "Loaded the triggering activity",
        duration_ms: 400,
        result_count: 1,
      },
    }),
    next(1400, { type: "agent.step", data: { label: "Loading skill: pricing-response" } }),
    next(2200, { type: "output.final", data: strategyOutput }),
    next(2400, {
      type: "run.completed",
      data: {
        status: "SUCCEEDED",
        duration_ms: 2400,
        usage: { input_tokens: 3980, output_tokens: 540 },
      },
    }),
  ];
}

/** The fields the fixture server fills when it starts a run. */
export interface RunSeed {
  id: string;
  session_id: string;
  intent: string;
  message: string | null;
  trigger_label: string;
}

interface RunScript<TRun extends Run> {
  start: (seed: RunSeed) => TRun;
  events: (runId: string) => ScriptedEvent[];
}

const pending = (seed: RunSeed) => ({
  ...seed,
  trigger: null,
  route: { method: "DETERMINISTIC", reason: "Fixture route", confidence: 1 } as const,
  status: "RUNNING" as const,
  steps: [],
  tool_calls: [],
  skills_loaded: [],
  output: null,
  error: null,
  started_at: new Date().toISOString(),
  finished_at: null,
});

/**
 * How each agent's run starts and what it then streams. Keyed by agent, so the
 * fixture server never branches on it.
 */
export const RUN_SCRIPTS: {
  EXECUTION: RunScript<ExecutionRun>;
  STRATEGY: RunScript<StrategyRun>;
} = {
  EXECUTION: {
    start: (seed) => ({ ...pending(seed), agent: "EXECUTION" }),
    events: executionRunScript,
  },
  STRATEGY: {
    start: (seed) => ({ ...pending(seed), agent: "STRATEGY" }),
    events: strategyRunScript,
  },
};

/** A run that gets partway and then fails, for the §5 Execution error state. */
export function failedRunScript(
  runId: string,
  error: { code: string; message: string },
  startedAt = new Date(),
): ScriptedEvent[] {
  const at = (offset: number) => new Date(startedAt.getTime() + offset).toISOString();
  return [
    {
      delay_ms: 150,
      event: {
        run_id: runId,
        seq: 1,
        ts: at(150),
        type: "run.started",
        data: {
          agent: "EXECUTION",
          intent: "CREATE_SIMILAR",
          route: { method: "DETERMINISTIC", reason: "Feed action", confidence: 1 },
        },
      },
    },
    {
      delay_ms: 500,
      event: {
        run_id: runId,
        seq: 2,
        ts: at(500),
        type: "agent.step",
        data: { label: "Loading company context" },
      },
    },
    {
      delay_ms: 900,
      event: { run_id: runId, seq: 3, ts: at(900), type: "run.failed", data: error },
    },
  ];
}
