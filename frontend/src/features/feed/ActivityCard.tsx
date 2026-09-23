import type { Activity, ItemAction } from "../../api";
import { Badge } from "../../components/ds/Badge";
import { Button } from "../../components/ds/Button";
import { Icon } from "../../components/ds/Icon";
import { cn } from "../../lib/cn";
import { displayUrl, money, relativeTime, signedPercent } from "../../lib/format";
import { evidenceTargetId } from "../workspace/workspaceContext";
import { ActivityTypeBadge } from "./ActivityTypeBadge";

interface ActivityCardProps {
  activity: Activity;
  onAction: (action: ItemAction) => void;
  highlighted?: boolean;
}

export function ActivityCard({ activity, onAction, highlighted }: ActivityCardProps) {
  const primary = activity.actions.find((action) => action.primary) ?? activity.actions[0];
  const secondary = activity.actions.filter((action) => action !== primary);
  const delta = activity.price
    ? ((activity.price.after - activity.price.before) / activity.price.before) * 100
    : null;

  return (
    <article
      id={evidenceTargetId(activity.id)}
      aria-label={activity.title}
      className={cn(
        "flex flex-col gap-1 border-b border-border p-2 transition-colors duration-300",
        highlighted ? "bg-surface-selected" : "bg-surface-card",
      )}
    >
      <div className="flex items-center gap-1">
        {activity.is_new ? (
          <>
            <span aria-hidden="true" className="h-1 w-1 flex-none rounded-full bg-primary" />
            <span className="sr-only">Unseen</span>
          </>
        ) : null}
        <ActivityTypeBadge activityType={activity.activity_type} />
        {activity.is_simulated ? <Badge tone="brand">🧪 SIMULATED</Badge> : null}
        {activity.is_mock && !activity.is_simulated ? (
          <Badge title="Demo data, not a detected change">MOCK</Badge>
        ) : null}
        <span className="ml-auto text-small text-text-muted">
          {relativeTime(activity.detected_at)}
        </span>
      </div>

      <span className="text-small text-text-muted">
        {activity.competitor_name} · {activity.channel}
        {activity.author ? ` · ${activity.author.name}, ${activity.author.role}` : ""}
      </span>

      <h3 className="line-clamp-2 text-h3 text-text">{activity.title}</h3>

      {activity.price && delta !== null ? (
        <p className="text-body text-text">
          {money(activity.price.before, activity.price.currency)} →{" "}
          <b>{money(activity.price.after, activity.price.currency)}</b>{" "}
          <span className="font-semibold text-text-unfavorable">{signedPercent(delta)}</span>
        </p>
      ) : null}

      {activity.url ? (
        <a
          href={activity.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-0.5 self-start text-small text-text-muted"
        >
          {displayUrl(activity.url)}
          <Icon name="externalLink" size={12} />
        </a>
      ) : null}

      <div className="flex items-center gap-2 pt-0.5">
        {secondary.map((action) => (
          <Button key={action.action} variant="quiet" onClick={() => onAction(action)}>
            {action.label}
          </Button>
        ))}
        {primary ? (
          <Button variant="primary" className="ml-auto" onClick={() => onAction(primary)}>
            {primary.label}
          </Button>
        ) : null}
      </div>
    </article>
  );
}
