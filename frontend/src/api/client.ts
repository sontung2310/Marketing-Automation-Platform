// The only module allowed to call the backend (AGENTS.md §2). It always speaks
// HTTP to the real Platform API; fixtures stand in at the network boundary
// (src/test/fixtures), so nothing above this layer knows which is serving.

import type { ApiErrorBody } from "./types";

export const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Query values the API accepts. Arrays are sent as the documented CSV form. */
export type QueryValue = string | number | boolean | readonly string[] | undefined | null;

export function buildQuery(params: Record<string, QueryValue>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      if (value.length > 0) search.set(key, value.join(","));
      continue;
    }
    search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, init);
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
    throw new ApiError(
      body?.error.code ?? "INTERNAL",
      body?.error.message ?? `Request failed with status ${response.status}`,
      response.status,
    );
  }
  return (await response.json()) as T;
}

export function getJson<T>(path: string, init?: RequestInit): Promise<T> {
  return request<T>(path, init);
}

function withBody<T>(method: "POST" | "PUT", path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export function postJson<T>(path: string, body?: unknown): Promise<T> {
  return withBody<T>("POST", path, body);
}

export function putJson<T>(path: string, body?: unknown): Promise<T> {
  return withBody<T>("PUT", path, body);
}

/** Absolute URL for an SSE endpoint, which EventSource opens rather than fetch. */
export function streamUrl(path: string): string {
  return `${BASE_URL}${path}`;
}
