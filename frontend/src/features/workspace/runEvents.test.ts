import { expect, test } from "vitest";

import type { RunEvent } from "../../api";
import { applyEvent } from "./runEvents";
import type { RunState } from "./workspaceContext";

const run: RunState = {
  id: "run_1",
  request: { message: "Write a post" },
  agent: "EXECUTION",
  intent: "FREEFORM_DELIVERABLE",
  trigger_label: "FREEFORM_DELIVERABLE",
  route: { method: "CLASSIFIER", reason: "asked to draft", confidence: 0.9 },
  status: "RUNNING",
  steps: [],
  tool_calls: [],
  output: null,
  error: null,
  started_at: "2026-10-06T00:00:00Z",
  finished_at: null,
  last_seq: 0,
};

const step = (seq: number, label: string): RunEvent => ({
  run_id: "run_1",
  seq,
  ts: "2026-10-06T00:00:01Z",
  type: "agent.step",
  data: { label },
});

test("a replayed event is applied once", () => {
  const once = applyEvent(applyEvent(run, step(1, "Loading")), step(2, "Drafting"));
  const replayed = applyEvent(applyEvent(once, step(1, "Loading")), step(2, "Drafting"));

  expect(replayed.steps.map((s) => s.label)).toEqual(["Loading", "Drafting"]);
  expect(replayed.last_seq).toBe(2);
});
