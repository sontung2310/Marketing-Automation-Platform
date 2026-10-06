import type { Recommendation } from "../../api";
import { Badge, type BadgeTone } from "../../components/ds/Badge";
import { Button } from "../../components/ds/Button";
import { Sheet } from "../../components/ds/Sheet";
import { EVIDENCE_HAS_TARGET, useWorkspace } from "../workspace/workspaceContext";
import { EvidenceChip } from "./EvidenceChip";
import { PRIORITY_TONE } from "./priority";

interface RecommendationSheetProps {
  recommendation: Recommendation;
  onClose: () => void;
}

const STATUS_TONE: Record<Recommendation["status"], BadgeTone> = {
  OPEN: "favorable",
  IN_PROGRESS: "attention",
  DONE: "neutral",
};

/**
 * The 520px detail pop-out. "Do this" writes the brief into the Execution
 * composer and sends nothing (ui-spec §4).
 */
export function RecommendationSheet({ recommendation, onClose }: RecommendationSheetProps) {
  const { setDraft } = useWorkspace();
  const next = recommendation.next_action;

  return (
    <Sheet
      label={`Recommendation ${recommendation.ordinal}`}
      onClose={onClose}
      header={
        <>
          <span className="text-h2 text-text-accent">{recommendation.ordinal}</span>
          <Badge tone={PRIORITY_TONE[recommendation.priority]}>{recommendation.priority}</Badge>
          <Badge>{recommendation.kind}</Badge>
          <Badge tone={STATUS_TONE[recommendation.status]}>{recommendation.status}</Badge>
        </>
      }
      footer={
        <>
          <span className="flex-1 text-small text-text-muted">
            {next
              ? "Do this writes the request into the Execution input. Nothing sends until you press Send."
              : "Nothing is being asked of you yet. This row updates if the signal repeats."}
          </span>
          {next ? (
            <Button
              variant="primary"
              onClick={() => {
                setDraft(next.brief, {
                  kind: "RECOMMENDATION",
                  ref_id: recommendation.id,
                  action: "DO_THIS",
                });
                onClose();
              }}
            >
              Do this
            </Button>
          ) : null}
        </>
      }
    >
      <h3 className="text-h3 text-text">{recommendation.title}</h3>

      <dl className="grid grid-cols-3 gap-1 text-small">
        <dt className="font-medium tracking-label text-text-muted uppercase">Make</dt>
        <dd className="col-span-2 text-body text-text">
          {next ? next.deliverable_type : "Nothing yet"}
        </dd>
        <dt className="font-medium tracking-label text-text-muted uppercase">Channel</dt>
        <dd className="col-span-2 text-body text-text">{recommendation.channel ?? "—"}</dd>
      </dl>

      <p className="text-body text-text">{recommendation.rationale}</p>

      <div className="flex flex-col gap-1">
        <span className="text-small font-medium tracking-label text-text-muted uppercase">
          Based on
        </span>
        <div className="flex flex-wrap gap-1">
          {recommendation.evidence.map((evidence) => (
            <EvidenceChip key={evidence.id} evidence={evidence} onNavigate={onClose} />
          ))}
        </div>
        {recommendation.evidence.some((evidence) => !EVIDENCE_HAS_TARGET[evidence.kind]) ? (
          <span className="text-small text-text-muted">
            Greyed evidence is the company context, which has no row to open.
          </span>
        ) : null}
      </div>

      <span className="text-small text-text-muted">
        {recommendation.run_id} · skills: {recommendation.skills_used.join(", ") || "none"}
      </span>
    </Sheet>
  );
}
