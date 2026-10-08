import type { components } from "@careerlens/api-client";
type Application = components["schemas"]["Application"];
export type ApplicationSort = "updated" | "deadline" | "company";
export function trackerView(
  rows: Application[],
  search: string,
  sort: ApplicationSort,
) {
  const term = search.trim().toLowerCase();
  return rows
    .filter((a) => (a.company + " " + a.title).toLowerCase().includes(term))
    .sort((a, b) => {
      const stable =
        a.company.localeCompare(b.company) ||
        a.title.localeCompare(b.title) ||
        a.id.localeCompare(b.id);
      if (sort === "company") return stable;
      const av = Date.parse(
          (sort === "deadline" ? a.deadline : a.updated_at) || "",
        ),
        bv = Date.parse(
          (sort === "deadline" ? b.deadline : b.updated_at) || "",
        );
      if (!Number.isFinite(av)) return Number.isFinite(bv) ? 1 : stable;
      if (!Number.isFinite(bv)) return -1;
      return (sort === "deadline" ? av - bv : bv - av) || stable;
    });
}
export function deadlineLabel(value: string, today: Date) {
  const time = Date.parse(value);
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(value) ||
    !Number.isFinite(time) ||
    new Date(time).toISOString().slice(0, 10) !== value
  )
    return null;
  const day = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  const days = Math.round((time - day) / 86400000);
  const date = new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(time));
  return {
    date,
    note:
      days < 0
        ? "Deadline passed"
        : days === 0
          ? "Due today"
          : days === 1
            ? "Due tomorrow"
            : days <= 7
              ? "Due in " + days + " days"
              : "",
    soon: days >= 0 && days <= 7,
  };
}
