import { getJson, postJson, streamUrl } from "./client";
import type { Run, RunRequest, RunResponse, Session } from "./types";

export function startRun(body: RunRequest): Promise<RunResponse> {
  return postJson<RunResponse>("/runs", body);
}

export function fetchRun(runId: string): Promise<Run> {
  return getJson<Run>(`/runs/${runId}`);
}

export function fetchSession(sessionId: string): Promise<Session> {
  return getJson<Session>(`/sessions/${sessionId}`);
}

export function runStreamUrl(runId: string): string {
  return streamUrl(`/runs/${runId}/events`);
}
