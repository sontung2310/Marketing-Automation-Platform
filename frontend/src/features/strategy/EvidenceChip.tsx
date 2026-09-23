import type { Evidence, EvidenceKind } from "../../api";
import { useWorkspace } from "../workspace/workspaceContext";

/** The short prefix a chip shows, keyed by evidence kind (agents-spec §6.2). */
const PREFIX: Record<EvidenceKind, string> = {
  activity: "act",
  trend: "trd",
  influencer: "inf",
  company: "co",
};

interface EvidenceChipProps {
  evidence: Evidence;
  /** Following a chip navigates to the item, so the sheet gets out of the way. */
  onNavigate?: () => void;
}

export function EvidenceChip({ evidence, onNavigate }: EvidenceChipProps) {
  const { highlight } = useWorkspace();

  return (
    <button
      type="button"
      title={evidence.id}
      onClick={() => {
        onNavigate?.();
        highlight(evidence.id);
      }}
      className="inline-flex h-3 cursor-pointer items-center gap-1 rounded-sm border border-border bg-surface-card px-1 text-small text-text"
    >
      <span className="font-semibold tracking-label text-text-muted uppercase">
        {PREFIX[evidence.kind]}
      </span>
      {evidence.note}
    </button>
  );
}
