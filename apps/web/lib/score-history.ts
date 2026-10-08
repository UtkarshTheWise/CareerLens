import type { components } from "@careerlens/api-client";
import type { TrendPeriod, TrendPoint } from "@/components/career/trend-card";
export function scoreHistory(
  rows: components["schemas"]["AnalysisSummary"][],
  roleId?: string,
): Record<TrendPeriod, TrendPoint[]> {
  const scans = rows
    .filter(
      (r) =>
        r.status === "done" &&
        (!roleId || r.role_id === roleId) &&
        r.score != null &&
        Number.isFinite(r.score) &&
        Number.isFinite(Date.parse(r.created_at)),
    )
    .sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at));
  const latest = Date.parse(scans.at(-1)?.created_at || "");
  const points = (days: number) =>
    scans
      .filter((r) => latest - Date.parse(r.created_at) < days * 86400000)
      .map((r) => ({
        label:
          new Intl.DateTimeFormat("en", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
            timeZone: "UTC",
          }).format(new Date(r.created_at)) + " UTC",
        primary: r.score!,
      }));
  return { weekly: points(7), monthly: points(31), yearly: points(366) };
}
