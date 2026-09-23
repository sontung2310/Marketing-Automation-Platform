// Every server read the workspace does. One TanStack Query hook per endpoint,
// so §5's loading, empty, error and Retry states come from one pattern.

import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  approveAction,
  discardAction,
  fetchActivities,
  fetchCompany,
  fetchInfluencers,
  fetchRecommendations,
  fetchSession,
  fetchTrends,
  markActivitiesSeen,
  saveTrackedKeywords,
  simulateActivity,
  startRun,
} from "../api";
import type { ActivityPage, ActivityQuery, Channel } from "../api";

export const queryKeys = {
  company: ["company"] as const,
  activities: (query: ActivityQuery) => ["activities", query] as const,
  trends: (channel: Channel | "ALL") => ["trends", channel] as const,
  influencers: ["influencers"] as const,
  recommendations: ["recommendations"] as const,
  session: (sessionId: string | null) => ["session", sessionId] as const,
};

export function useCompany() {
  return useQuery({ queryKey: queryKeys.company, queryFn: fetchCompany });
}

export function useActivities(query: ActivityQuery) {
  return useInfiniteQuery({
    queryKey: queryKeys.activities(query),
    queryFn: ({ pageParam }) => fetchActivities({ ...query, cursor: pageParam ?? undefined }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage: ActivityPage) => lastPage.next_cursor,
  });
}

export function useTrends(channel: Channel | "ALL") {
  return useQuery({
    queryKey: queryKeys.trends(channel),
    queryFn: () => fetchTrends(channel === "ALL" ? undefined : [channel]),
  });
}

export function useInfluencers() {
  return useQuery({ queryKey: queryKeys.influencers, queryFn: () => fetchInfluencers() });
}

export function useRecommendations() {
  return useQuery({ queryKey: queryKeys.recommendations, queryFn: () => fetchRecommendations() });
}

export function useSession(sessionId: string | null) {
  return useQuery({
    queryKey: queryKeys.session(sessionId),
    queryFn: () => fetchSession(sessionId ?? ""),
    enabled: sessionId !== null,
    retry: false,
  });
}

export function useSaveTrackedKeywords() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: saveTrackedKeywords,
    onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.company }),
  });
}

export function useSimulateActivity() {
  return useMutation({ mutationFn: simulateActivity });
}

export function useMarkSeen() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: markActivitiesSeen,
    onSuccess: () => client.invalidateQueries({ queryKey: ["activities"] }),
  });
}

export function useStartRun() {
  return useMutation({ mutationFn: startRun });
}

export function useApproveAction() {
  return useMutation({
    mutationFn: (input: { actionId: string; overrides?: Record<string, unknown> }) =>
      approveAction(input.actionId, input.overrides),
  });
}

export function useDiscardAction() {
  return useMutation({ mutationFn: discardAction });
}
