import type { components } from "@careerlens/api-client";
import type { TrendPoint, TrendPeriod } from "@/components/career/trend-card";
export type Schema = components["schemas"];
export type SimulationSignal = NonNullable<
  Schema["SimulationRequest"]["changes"][number]["add_signals"]
>[number];
export const signalOptions = [
  { value: "tests", label: "Add tests" },
  { value: "ci", label: "Add CI" },
  { value: "demo_url", label: "Deploy demo" },
  { value: "license", label: "Add licence" },
  { value: "readme", label: "Add README" },
] as const satisfies readonly { value: SimulationSignal; label: string }[];
// Count rollups for chart presentation only. Scores and score history are never inferred.
export function consistencyDatasets(
  weeks: Schema["ConsistencySummary"]["weeks"],
): Record<TrendPeriod, TrendPoint[]> {
  const ordered = [...weeks].sort((a, b) =>
    a.week_start.localeCompare(b.week_start),
  );
  function rollup(length: number) {
    const counts = new Map<string, number>();
    for (const week of ordered) {
      const label = week.week_start.slice(0, length);
      counts.set(label, (counts.get(label) || 0) + week.count);
    }
    return [...counts].map(([label, primary]) => ({ label, primary }));
  }
  return {
    weekly: ordered.map((week) => ({
      label: week.week_start,
      primary: week.count,
    })),
    monthly: rollup(7),
    yearly: rollup(4),
  };
}
export function simulationChanges(
  selected: Record<string, SimulationSignal[]>,
  projects: Schema["ProjectAudit"][],
): Schema["SimulationRequest"]["changes"] {
  return projects
    .filter((project) => project.kind === "code")
    .flatMap((project) => {
      const add_signals = [
        ...new Set(selected[project.project_id] || []),
      ].filter(
        (signal) =>
          signalOptions.some((option) => option.value === signal) &&
          !project.signals?.[signal],
      );
      return add_signals.length
        ? [{ project_id: project.project_id, add_signals }]
        : [];
    });
}
