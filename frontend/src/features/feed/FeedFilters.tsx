import { ACTIVITY_TYPES, type ActivityType } from "../../api";
import { Menu, MenuItem } from "../../components/ds/Menu";

export interface FeedFilterState {
  activityType: ActivityType | null;
  competitorId: string | null;
}

interface FeedFiltersProps {
  competitors: { id: string; name: string }[];
  value: FeedFilterState;
  onChange: (value: FeedFilterState) => void;
}

export function FeedFilters({ competitors, value, onChange }: FeedFiltersProps) {
  return (
    <div className="grid grid-cols-2 gap-1 border-b border-border px-2 py-1">
      <Menu
        label="Filter by activity type"
        role="listbox"
        trigger={value.activityType ?? "All types"}
        triggerClassName="border border-border bg-surface-card text-text-muted"
        fill
      >
        {(close) => (
          <>
            <MenuItem
              role="option"
              checked={value.activityType === null}
              onSelect={() => {
                onChange({ ...value, activityType: null });
                close();
              }}
            >
              All types
            </MenuItem>
            {ACTIVITY_TYPES.map((type) => (
              <MenuItem
                key={type}
                role="option"
                checked={value.activityType === type}
                onSelect={() => {
                  onChange({ ...value, activityType: type });
                  close();
                }}
              >
                {type}
              </MenuItem>
            ))}
          </>
        )}
      </Menu>

      <Menu
        label="Filter by competitor"
        role="listbox"
        trigger={
          competitors.find((competitor) => competitor.id === value.competitorId)?.name ??
          "All competitors"
        }
        triggerClassName="border border-border bg-surface-card text-text-muted"
        fill
      >
        {(close) => (
          <>
            <MenuItem
              role="option"
              checked={value.competitorId === null}
              onSelect={() => {
                onChange({ ...value, competitorId: null });
                close();
              }}
            >
              All competitors
            </MenuItem>
            {competitors.map((competitor) => (
              <MenuItem
                key={competitor.id}
                role="option"
                checked={value.competitorId === competitor.id}
                onSelect={() => {
                  onChange({ ...value, competitorId: competitor.id });
                  close();
                }}
              >
                {competitor.name}
              </MenuItem>
            ))}
          </>
        )}
      </Menu>
    </div>
  );
}
