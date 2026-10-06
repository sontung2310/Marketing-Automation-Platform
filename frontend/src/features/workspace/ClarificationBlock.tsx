import { Button } from "../../components/ds/Button";
import { useWorkspace } from "./workspaceContext";

interface ClarificationBlockProps {
  message: string;
  options: string[];
  /** A Strategy-shaped question points at the feed instead (ui-spec §3). */
  pointsAtFeed: boolean;
}

export function ClarificationBlock({ message, options, pointsAtFeed }: ClarificationBlockProps) {
  const { setDraft } = useWorkspace();

  return (
    <div className="flex flex-col gap-1">
      <p className="text-body text-text">{message}</p>
      {pointsAtFeed ? (
        <p className="text-small text-text-muted">
          Ask Strategy from a feed item instead — every card carries its own action.
        </p>
      ) : null}
      <div className="flex flex-wrap gap-1">
        {options.map((option) => (
          <Button key={option} wrap onClick={() => setDraft(option)}>
            {option}
          </Button>
        ))}
      </div>
    </div>
  );
}
