// MSW handlers implementing docs/api-contract.md against the in-memory store.
// The same set backs dev mode, Vitest and Playwright, so one drift in a shape
// fails everywhere at once. Step 6 removes this layer; nothing above it moves.

import { HttpResponse, http, type HttpResponseResolver } from "msw";

import type { ActivityType, Channel } from "../../api/enums";
import type { Activity, RunResponse } from "../../api/types";
import { RUN_SCRIPTS, recommendations, session } from "./agents";
import { company, influencers, trends } from "./records";
import { ConflictError, TRIGGER_AGENT, ValidationError, store } from "./store";

const BASE = "/api";

function envelope(code: string, message: string, status: number) {
  return HttpResponse.json({ error: { code, message, details: {} } }, { status });
}

/** Turns the store's domain errors into the documented error envelope. */
function guard(resolver: HttpResponseResolver): HttpResponseResolver {
  return async (info) => {
    try {
      return await resolver(info);
    } catch (error) {
      if (error instanceof ValidationError) return envelope("VALIDATION_ERROR", error.message, 422);
      if (error instanceof ConflictError) return envelope("CONFLICT", error.message, 409);
      throw error;
    }
  };
}

function csv(url: URL, key: string): string[] | null {
  const raw = url.searchParams.get(key);
  return raw ? raw.split(",").filter(Boolean) : null;
}

function sse(
  produce: (
    send: (id: number, type: string, data: unknown) => void,
  ) => Promise<void> | (() => void),
): Response {
  const encoder = new TextEncoder();
  let cleanup: (() => void) | undefined;
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const send = (id: number, type: string, data: unknown) => {
        controller.enqueue(
          encoder.encode(`id: ${id}\nevent: ${type}\ndata: ${JSON.stringify(data)}\n\n`),
        );
      };
      const result = produce(send);
      if (typeof result === "function") cleanup = result;
      else {
        await result;
        controller.close();
      }
    },
    cancel() {
      cleanup?.();
    },
  });
  return new HttpResponse(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const handlers = [
  http.get(`${BASE}/company`, () =>
    HttpResponse.json({ ...company, tracked_keywords: store.trackedKeywords }),
  ),

  http.put(
    `${BASE}/company/tracked-keywords`,
    guard(async ({ request }) => {
      const body = (await request.json()) as { tracked_keywords?: unknown };
      return HttpResponse.json({
        tracked_keywords: store.setTrackedKeywords(body.tracked_keywords),
      });
    }),
  ),

  http.get(`${BASE}/activities`, ({ request }) => {
    const url = new URL(request.url);
    const types = csv(url, "activity_types") as ActivityType[] | null;
    const competitors = csv(url, "competitor_ids");
    const channels = csv(url, "channels") as Channel[] | null;
    const limit = Math.min(Number(url.searchParams.get("limit") ?? 20), 50);
    const cursor = url.searchParams.get("cursor");

    const matching = store.activities.filter(
      (activity) =>
        (!types || types.includes(activity.activity_type)) &&
        (!competitors || competitors.includes(activity.competitor_id)) &&
        (!channels || channels.includes(activity.channel)),
    );
    const offset = cursor ? Number(cursor) : 0;
    const page = matching.slice(offset, offset + limit);
    const nextOffset = offset + page.length;
    return HttpResponse.json({
      items: page,
      next_cursor: nextOffset < matching.length ? String(nextOffset) : null,
      unseen_count: store.unseenCount,
    });
  }),

  http.post(`${BASE}/activities/mark-seen`, async ({ request }) => {
    const body = (await request.json()) as { up_to: string };
    return HttpResponse.json({ updated: store.markSeen(body.up_to) });
  }),

  http.post(
    `${BASE}/activities/simulate`,
    guard(async ({ request }) => {
      const body = (await request.json()) as {
        activity_type: ActivityType | null;
        competitor_id: string | null;
      };
      const activity = store.simulate(body.activity_type, body.competitor_id);
      return HttpResponse.json(activity, { status: 201 });
    }),
  ),

  http.get(`${BASE}/activities/stream`, () =>
    sse((send) => {
      let seq = 0;
      const unsubscribe = store.onActivity((activity: Activity) => {
        seq += 1;
        send(seq, "activity.created", activity);
      });
      return unsubscribe;
    }),
  ),

  http.get(`${BASE}/trends`, ({ request }) => {
    const channels = csv(new URL(request.url), "channels") as Channel[] | null;
    return HttpResponse.json({
      items: channels ? trends.filter((trend) => channels.includes(trend.channel)) : trends,
    });
  }),

  http.get(`${BASE}/influencers`, () => HttpResponse.json({ items: influencers })),

  http.get(`${BASE}/recommendations`, () => HttpResponse.json({ items: store.recommendations })),

  http.post(`${BASE}/runs`, async ({ request }) => {
    const body = (await request.json()) as {
      message?: string;
      agent_hint?: "AUTO" | "STRATEGY" | "EXECUTION";
      trigger?: { kind: string; ref_id: string; action: keyof typeof TRIGGER_AGENT };
    };

    const answer = body.message ? ROUTER_ANSWERS[body.message] : undefined;
    if (answer) {
      return HttpResponse.json<RunResponse>({
        run_id: null,
        session_id: session.id,
        route: { method: "CLASSIFIER", reason: answer.reason, confidence: 0.4 },
        response: answer.response,
      });
    }

    const agent =
      body.trigger?.action !== undefined
        ? TRIGGER_AGENT[body.trigger.action]
        : body.agent_hint && body.agent_hint !== "AUTO"
          ? body.agent_hint
          : "EXECUTION";
    const label = body.trigger ? `${body.trigger.action} · ${body.trigger.ref_id}` : "Chat request";
    const ticket = store.startRun(
      agent,
      body.trigger?.action ?? "FREEFORM",
      body.message ?? null,
      label,
    );

    return HttpResponse.json<RunResponse>(
      {
        run_id: ticket.run.id,
        session_id: session.id,
        agent,
        intent: ticket.run.intent,
        route: ticket.run.route,
      },
      { status: 202 },
    );
  }),

  http.get(`${BASE}/runs/:runId/events`, ({ params, request }) => {
    const runId = String(params.runId);
    const ticket = store.tickets.get(runId);
    if (!ticket) return envelope("NOT_FOUND", `Run ${runId} not found`, 404);

    const lastEventId = Number(request.headers.get("Last-Event-ID") ?? 0);
    return sse(async (send) => {
      let elapsed = 0;
      for (const scripted of ticket.script) {
        await sleep(scripted.delay_ms - elapsed);
        elapsed = scripted.delay_ms;
        if (scripted.event.seq <= lastEventId) continue;
        send(scripted.event.seq, scripted.event.type, scripted.event);
      }
      ticket.run.status = "SUCCEEDED";
      ticket.run.finished_at = new Date().toISOString();
    });
  }),

  http.get(`${BASE}/runs/:runId`, ({ params }) => {
    const ticket = store.tickets.get(String(params.runId));
    return ticket
      ? HttpResponse.json(ticket.run)
      : envelope("NOT_FOUND", `Run ${String(params.runId)} not found`, 404);
  }),

  http.get(`${BASE}/sessions/:sessionId`, ({ params }) =>
    String(params.sessionId) === session.id
      ? HttpResponse.json(store.session)
      : envelope("NOT_FOUND", `Session ${String(params.sessionId)} not found`, 404),
  ),

  http.post(
    `${BASE}/actions/:actionId/approve`,
    guard(async ({ params, request }) => {
      const body = (await request.json().catch(() => null)) as {
        payload_overrides?: Record<string, unknown>;
      } | null;
      return HttpResponse.json(store.approve(String(params.actionId), body?.payload_overrides));
    }),
  ),

  http.post(
    `${BASE}/actions/:actionId/discard`,
    guard(({ params }) => HttpResponse.json(store.discard(String(params.actionId)))),
  ),
];

/**
 * Scripted router replies for the two message shapes the router answers without
 * starting a run (api-contract, `POST /runs`). A lookup table, not a matcher:
 * the real classifier arrives with Step 6.4.
 */
const ROUTER_ANSWERS: Record<
  string,
  {
    reason: string;
    response: {
      status: "NEEDS_CLARIFICATION" | "OUT_OF_SCOPE";
      message: string;
      clarification_options: string[];
    };
  }
> = {
  LinkedIn: {
    reason: "Too little to route on",
    response: {
      status: "NEEDS_CLARIFICATION",
      message: "What would you like for LinkedIn?",
      clarification_options: [
        "Draft a LinkedIn post",
        "Plan a LinkedIn response",
        "Show LinkedIn trends",
      ],
    },
  },
  "What's the weather in Sydney?": {
    reason: "Not a marketing request",
    response: {
      status: "OUT_OF_SCOPE",
      message: "This workspace covers marketing strategy and deliverables.",
      clarification_options: [],
    },
  },
};

export { recommendations, RUN_SCRIPTS };
