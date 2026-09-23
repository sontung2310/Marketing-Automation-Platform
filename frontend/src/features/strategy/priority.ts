import type { Priority } from "../../api";
import type { BadgeTone } from "../../components/ds/Badge";

/** HIGH reads as brand-urgent; the rest stay quiet (ui-spec §3). */
export const PRIORITY_TONE: Record<Priority, BadgeTone> = {
  HIGH: "brand",
  MEDIUM: "neutral",
  LOW: "neutral",
};
