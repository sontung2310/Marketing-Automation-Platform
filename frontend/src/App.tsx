import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { SegmentedSwitcher } from "./components/ds/SegmentedSwitcher";
import { Tabs } from "./components/ds/Tabs";
import { ActivityFeed } from "./features/feed/ActivityFeed";
import { SocialListeningPanel } from "./features/listening/SocialListeningPanel";
import { StrategyPanel } from "./features/strategy/StrategyPanel";
import { TopBar } from "./features/topbar/TopBar";
import { ExecutionChat } from "./features/workspace/ExecutionChat";
import { WorkspaceProvider } from "./features/workspace/WorkspaceProvider";
import { useLayoutMode, type LayoutMode } from "./hooks/useLayoutMode";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

function InsightsRail() {
  return (
    <div className="flex min-h-0 scrollbar-thin flex-col gap-2 overflow-y-auto">
      <StrategyPanel />
      <ActivityFeed />
    </div>
  );
}

function Region({ children }: { children: ReactNode }) {
  return <div className="flex min-h-0 min-w-0 flex-col">{children}</div>;
}

/** Three regions side by side at the 1440×900 design target. */
function DesktopLayout() {
  return (
    <>
      <Region>
        <SocialListeningPanel />
      </Region>
      <Region>
        <ExecutionChat />
      </Region>
      <Region>
        <InsightsRail />
      </Region>
    </>
  );
}

const TABLET_TABS = [
  { value: "WORKSPACE" as const, label: "Workspace" },
  { value: "LISTENING" as const, label: "Listening" },
];

/** At 1280px and below, listening folds into the centre shell as a tab. */
function TabletLayout() {
  const [tab, setTab] = useState<"WORKSPACE" | "LISTENING">("WORKSPACE");
  return (
    <>
      <Region>
        <Tabs label="Centre region" options={TABLET_TABS} value={tab} onChange={setTab} />
        {tab === "WORKSPACE" ? <ExecutionChat /> : <SocialListeningPanel />}
      </Region>
      <Region>
        <InsightsRail />
      </Region>
    </>
  );
}

const MOBILE_REGIONS = [
  { value: "FEED" as const, label: "Feed" },
  { value: "WORKSPACE" as const, label: "Workspace" },
  { value: "INSIGHTS" as const, label: "Insights" },
];

/** At 900px and below, one column with the bottom segmented switcher. */
function MobileLayout() {
  const [region, setRegion] = useState<"FEED" | "WORKSPACE" | "INSIGHTS">("WORKSPACE");
  return (
    <Region>
      <div className="flex min-h-0 flex-1 scrollbar-thin flex-col gap-2 overflow-y-auto">
        {region === "FEED" ? <ActivityFeed /> : null}
        {region === "WORKSPACE" ? (
          <>
            <StrategyPanel />
            <ExecutionChat />
          </>
        ) : null}
        {region === "INSIGHTS" ? <SocialListeningPanel /> : null}
      </div>
      <SegmentedSwitcher
        label="Workspace region"
        options={MOBILE_REGIONS}
        value={region}
        onChange={setRegion}
        className="mt-2"
      />
    </Region>
  );
}

const LAYOUTS: Record<LayoutMode, () => ReactNode> = {
  DESKTOP: DesktopLayout,
  TABLET: TabletLayout,
  MOBILE: MobileLayout,
};

function Workspace() {
  const mode = useLayoutMode();
  const Layout = LAYOUTS[mode];
  return (
    <div className="flex h-screen flex-col overflow-x-hidden bg-surface-page">
      <TopBar />
      <main className="grid min-h-0 flex-1 layout-workspace gap-2 p-3">
        <Layout />
      </main>
    </div>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <WorkspaceProvider>
        <Workspace />
      </WorkspaceProvider>
    </QueryClientProvider>
  );
}
