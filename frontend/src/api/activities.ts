import { buildQuery, getJson, openStream, postJson } from "./client";
import type { Activity, ActivityPage, ActivityQuery, SimulateBody } from "./types";

export function fetchActivities(query: ActivityQuery): Promise<ActivityPage> {
  return getJson<ActivityPage>(
    `/activities${buildQuery({
      activity_types: query.activity_types,
      competitor_ids: query.competitor_ids,
      channels: query.channels,
      since: query.since,
      cursor: query.cursor,
      limit: query.limit,
    })}`,
  );
}

export function markActivitiesSeen(upTo: string): Promise<{ updated: number }> {
  return postJson<{ updated: number }>("/activities/mark-seen", { up_to: upTo });
}

export function simulateActivity(body: SimulateBody): Promise<Activity> {
  return postJson<Activity>("/activities/simulate", body);
}

export function openActivityStream(): EventSource {
  return openStream("/activities/stream");
}
