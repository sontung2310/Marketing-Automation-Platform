import { Icon, type IconName } from "../../components/ds/Icon";
import { Menu, MenuItem } from "../../components/ds/Menu";
import { useTheme, type ThemePreference } from "../../hooks/useTheme";

const OPTIONS: Record<ThemePreference, { label: string; icon: IconName }> = {
  LIGHT: { label: "Light", icon: "sun" },
  DARK: { label: "Dark", icon: "moon" },
  SYSTEM: { label: "System", icon: "monitor" },
};

/** Light, Dark, or follow the OS (ui-spec §3). */
export function ThemeMenu() {
  const { preference, setPreference } = useTheme();

  return (
    <Menu
      label="Choose the theme"
      trigger={
        <>
          <Icon name={OPTIONS[preference].icon} size={14} />
          <span className="hidden tablet:inline">{OPTIONS[preference].label}</span>
        </>
      }
      triggerClassName="border border-text-inverse-muted text-text-inverse"
      placement="down-end"
    >
      {(close) =>
        (Object.keys(OPTIONS) as ThemePreference[]).map((option) => (
          <MenuItem
            key={option}
            role="menuitemradio"
            checked={option === preference}
            onSelect={() => {
              setPreference(option);
              close();
            }}
          >
            {OPTIONS[option].label}
          </MenuItem>
        ))
      }
    </Menu>
  );
}
