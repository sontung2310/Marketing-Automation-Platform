import { postJson } from "./client";
import type { ProposedAction } from "./types";

export function approveAction(
  actionId: string,
  payloadOverrides?: Record<string, unknown>,
): Promise<ProposedAction> {
  return postJson<ProposedAction>(
    `/actions/${actionId}/approve`,
    payloadOverrides ? { payload_overrides: payloadOverrides } : undefined,
  );
}

export function discardAction(actionId: string): Promise<ProposedAction> {
  return postJson<ProposedAction>(`/actions/${actionId}/discard`);
}
