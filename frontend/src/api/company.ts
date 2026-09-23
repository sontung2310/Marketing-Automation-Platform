import { getJson, putJson } from "./client";
import type { Company, TrackedKeywordsBody } from "./types";

export function fetchCompany(): Promise<Company> {
  return getJson<Company>("/company");
}

export function saveTrackedKeywords(tracked_keywords: string[]): Promise<TrackedKeywordsBody> {
  return putJson<TrackedKeywordsBody>("/company/tracked-keywords", { tracked_keywords });
}
