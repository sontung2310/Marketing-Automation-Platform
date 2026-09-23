import { ACTIVITY_TYPES, type ActivityType } from "../../api";
import { Menu, MenuItem } from "../../components/ds/Menu";
import { Spinner } from "../../components/ds/Spinner";
import { useSimulateActivity } from "../../hooks/queries";

/** The demo trigger. All nine types plus Random (ui-spec §3). */
export function SimulateMenu() {
  const simulate = useSimulateActivity();

  const run = (activity_type: ActivityType | null, close: () => void) => {
    simulate.mutate({ activity_type, competitor_id: null });
    close();
  };

  if (simulate.isPending) {
    return (
      <span className="flex h-4 items-center rounded-sm border border-text-inverse-muted px-1">
        <Spinner label="Simulating…" />
      </span>
    );
  }

  return (
    <Menu
      label="Simulate a signal"
      trigger="🎭 Simulate a signal"
      triggerClassName="border border-text-inverse-muted text-text-inverse"
    >
      {(close) => (
        <>
          <MenuItem onSelect={() => run(null, close)}>Random</MenuItem>
          {ACTIVITY_TYPES.map((type) => (
            <MenuItem key={type} onSelect={() => run(type, close)}>
              {type}
            </MenuItem>
          ))}
        </>
      )}
    </Menu>
  );
}
