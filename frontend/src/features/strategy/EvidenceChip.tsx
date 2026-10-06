import type { Evidence, EvidenceKind } from "../../api";
import { cn } from "../../lib/cn";
import { EVIDENCE_HAS_TARGET, useWorkspace } from "../workspace/workspaceContext";

/** The short prefix a chip shows, keyed by evidence kind (agents-spec §6.2). */
const PREFIX: Record<EvidenceKind, string> = {
  activity: "act",
  trend: "trd",
  influencer: "inf",
  company: "co",
};

const CHIP =
  "inline-flex min-h-3 items-center gap-1 rounded-sm border border-border bg-surface-card px-1 py-0.5 text-left text-small text-text";

interface EvidenceChipProps {
  evidence: Evidence;
  /** Following a chip navigates to the item, so the sheet gets out of the way. */
  onNavigate?: () => void;
}

export function EvidenceChip({ evidence, onNavigate }: EvidenceChipProps) {
  const { highlight } = useWorkspace();
  const prefix = (
    <span className="font-semibold tracking-label text-text-muted uppercase">
      {PREFIX[evidence.kind]}
    </span>
  );

  // Company context has no row on the page. A chip for it stays a label rather
  // than a button that would close the sheet and then find nothing.
  if (!EVIDENCE_HAS_TARGET[evidence.kind]) {
    return (
      <span title={evidence.id} className={cn(CHIP, "text-text-muted")}>
        {prefix}
        {evidence.note}
      </span>
    );
  }

  return (
    <button
      type="button"
      title={evidence.id}
      onClick={() => {
        onNavigate?.();
        highlight(evidence.id, evidence.kind);
      }}
      className={cn(CHIP, "cursor-pointer")}
    >
      {prefix}
      {evidence.note}
    </button>
  );
}
