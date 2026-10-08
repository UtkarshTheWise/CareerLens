import type { components } from "@careerlens/api-client";
type Student = components["schemas"]["CohortStudent"];
export type StudentSort = "name" | "readiness" | "coverage";
export function studentDirectory(
  rows: Student[],
  search: string,
  sort: StudentSort,
) {
  const term = search.trim().toLocaleLowerCase();
  return rows
    .filter((s) =>
      (s.name + " " + (s.department || "")).toLocaleLowerCase().includes(term),
    )
    .sort((a, b) => {
      const byName =
        a.name.localeCompare(b.name) ||
        a.profile_id.localeCompare(b.profile_id);
      if (sort === "name") return byName;
      const av = sort === "readiness" ? a.score : a.coverage,
        bv = sort === "readiness" ? b.score : b.coverage;
      if (av == null) return bv == null ? byName : 1;
      if (bv == null) return -1;
      return av - bv || byName;
    });
}
