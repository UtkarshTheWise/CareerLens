import type { components } from "@careerlens/api-client";
type Student = components["schemas"]["CohortStudent"];
export type StudentSort = "name" | "readiness" | "coverage";
/**
 * Name/department search. The service filters and orders the list (see cohort-filters.ts), so with no `sort`
 * the order it returned is kept. A `sort` is still honoured for callers that want a local order.
 */
export function studentDirectory(
  rows: Student[],
  search: string,
  sort?: StudentSort,
) {
  const term = search.trim().toLocaleLowerCase();
  const found = rows.filter((s) =>
    (s.name + " " + (s.department || "")).toLocaleLowerCase().includes(term),
  );
  if (!sort) return found;
  return found.sort((a, b) => {
    const byName =
      a.name.localeCompare(b.name) || a.profile_id.localeCompare(b.profile_id);
    if (sort === "name") return byName;
    const av = sort === "readiness" ? a.score : a.coverage,
      bv = sort === "readiness" ? b.score : b.coverage;
    if (av == null) return bv == null ? byName : 1;
    if (bv == null) return -1;
    return av - bv || byName;
  });
}
