import { Panel } from "./components/ds/Panel";

// Layout shell per docs/ui-spec.md §2. Regions are filled in roadmap Step 7.
const REGIONS = [
  {
    id: "feed",
    title: "Competitor activity",
    empty: "No competitor activity in the last 30 days — run the pipelines or simulate a signal.",
  },
  {
    id: "workspace",
    title: "Workspace",
    empty: "Pick an item from the feed, or ask for a plan or a deliverable below.",
  },
  { id: "insights", title: "Insights", empty: "No trends computed yet." },
] as const;

export function App() {
  return (
    <div className="min-h-screen">
      <header className="flex items-baseline gap-2 border-b border-border bg-surface-card px-3 py-2">
        <h1 className="text-h3 text-text">Marketing workspace</h1>
        <span className="text-small text-text-muted">Marketing Eye</span>
      </header>
      <main className="grid layout-workspace gap-2 p-3">
        {REGIONS.map((region) => (
          <Panel key={region.id} title={region.title}>
            <p className="text-text-muted">{region.empty}</p>
          </Panel>
        ))}
      </main>
    </div>
  );
}
