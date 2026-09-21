// The only module allowed to call the backend (AGENTS.md §2).

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export interface ApiErrorBody {
  error: { code: string; message: string; details?: Record<string, unknown> };
}

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export async function getJson<T>(path: string, init?: RequestInit): Promise<T> {
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
