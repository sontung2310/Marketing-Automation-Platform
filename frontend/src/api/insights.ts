import { buildQuery, getJson } from "./client";
import type { Channel, RecommendationStatus } from "./enums";
import type { Influencer, Recommendation, Trend } from "./types";

export function fetchTrends(channels?: Channel[]): Promise<{ items: Trend[] }> {
  return getJson<{ items: Trend[] }>(`/trends${buildQuery({ channels })}`);
}

export function fetchInfluencers(topic?: string): Promise<{ items: Influencer[] }> {
  return getJson<{ items: Influencer[] }>(`/influencers${buildQuery({ topic })}`);
}

export function fetchRecommendations(
  status: RecommendationStatus = "OPEN",
): Promise<{ items: Recommendation[] }> {
  return getJson<{ items: Recommendation[] }>(`/recommendations${buildQuery({ status })}`);
}
