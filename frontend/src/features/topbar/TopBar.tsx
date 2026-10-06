import { Menu, MenuItem } from "../../components/ds/Menu";
import { useCompany } from "../../hooks/queries";
import { relativeTime } from "../../lib/format";
import { SimulateMenu } from "./SimulateMenu";
import { ThemeMenu } from "./ThemeMenu";

/** The page's one inverted band: ink in light, brand red in dark. No logo (ui-spec §7). */
export function TopBar() {
  const company = useCompany();
  const lastSync = company.data?.last_sync_at;

  return (
    <header className="sticky top-0 z-30 flex h-7 flex-none items-center gap-2 bg-surface-ink px-3 text-text-inverse">
      <Menu
        label="Choose the tenant"
        trigger={company.data?.name ?? "Loading…"}
        triggerClassName="border border-text-inverse-muted text-text-inverse"
      >
        {(close) => (
          <MenuItem checked onSelect={close}>
            {company.data?.name ?? "Marketing Eye"}
          </MenuItem>
        )}
      </Menu>

      <span aria-hidden="true" className="h-2.5 w-px bg-text-inverse-muted" />

      <span className="text-small tracking-label text-text-inverse-muted uppercase">
        Marketing workspace
      </span>

      <span className="ml-auto text-small text-text-inverse-muted">
        {lastSync ? `Last sync ${relativeTime(lastSync)}` : "Last sync pending"}
      </span>

      <ThemeMenu />
      <SimulateMenu />
    </header>
  );
}
