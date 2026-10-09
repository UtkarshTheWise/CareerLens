import type { components } from "@careerlens/api-client";
import type { OperationInputs } from "./api/operations";

type Schema = components["schemas"];
type Band = Schema["Band"];
export type MinLevel = "strong" | "moderate" | "weak" | "unverified";
export type CohortSort = "score_asc" | "score_desc" | "coverage_desc" | "name";
export type CohortQuery = OperationInputs["listCohortStudents"]["query"];

/** What a company can ask for when looking through a cohort. Evidence comes from the service; nothing is scored here. */
export interface CohortFilters {
  skills: string[];
  skillMatch: "all" | "any";
  minLevel: MinLevel;
  minScore: number | null;
  bands: Band[];
  sort: CohortSort;
  limit: number | null;
  atRiskOnly: boolean;
}

export const DEFAULT_FILTERS: CohortFilters = {
  skills: [],
  skillMatch: "all",
  minLevel: "moderate",
  minScore: null,
  bands: [],
  sort: "score_asc",
  limit: null,
  atRiskOnly: false,
};

export const LEVEL_LABELS: Record<MinLevel, string> = {
  strong: "Strong only",
  moderate: "Strong or moderate (verified)",
  weak: "Includes weak mentions",
  unverified: "Includes unverified claims",
};
const LEVEL_PHRASES: Record<MinLevel, string> = {
  strong: "strong evidence",
  moderate: "strong or moderate evidence",
  weak: "weak, moderate or strong evidence",
  unverified: "any evidence, including unverified claims",
};
export const SORT_LABELS: Record<CohortSort, string> = {
  score_asc: "Weakest first",
  score_desc: "Best first",
  coverage_desc: "Coverage: highest first",
  name: "Name A–Z",
};
export const BAND_LABELS: Record<Band, string> = { not_ready: "Not ready", developing: "Developing", ready: "Ready" };
export const SCORE_CHOICES = [50, 65, 75] as const;
export const LIMIT_CHOICES = [2, 5, 10, 20] as const;

/** Query for listCohortStudents and exportCohort. Defaults are left out so the query key stays stable. */
export function cohortQuery(roleId: string, f: CohortFilters): CohortQuery {
  const query: CohortQuery = { role_id: roleId };
  if (f.atRiskOnly) query.at_risk_only = true;
  if (f.skills.length) {
    query.skill = [...f.skills];
    if (f.skillMatch !== DEFAULT_FILTERS.skillMatch) query.skill_match = f.skillMatch;
    if (f.minLevel !== DEFAULT_FILTERS.minLevel) query.min_level = f.minLevel;
  }
  if (f.minScore != null) query.min_score = f.minScore;
  if (f.bands.length) query.band = [...f.bands];
  if (f.sort !== DEFAULT_FILTERS.sort) query.sort = f.sort;
  if (f.limit != null) query.limit = f.limit;
  return query;
}

export function hasActiveFilters(f: CohortFilters): boolean {
  return (
    f.atRiskOnly ||
    f.skills.length > 0 ||
    f.minScore != null ||
    f.bands.length > 0 ||
    f.limit != null ||
    f.sort !== DEFAULT_FILTERS.sort ||
    (f.skills.length > 0 && (f.skillMatch !== DEFAULT_FILTERS.skillMatch || f.minLevel !== DEFAULT_FILTERS.minLevel))
  );
}

function joinNames(names: string[], word: string): string {
  if (names.length <= 1) return names.join("");
  return names.slice(0, -1).join(", ") + " " + word + " " + names[names.length - 1];
}

/** One sentence describing the request, e.g. "Best 2 students with Docker (strong or moderate evidence), score 65 or higher". */
export function filterSummary(f: CohortFilters, skillNames: Record<string, string>): string {
  const parts: string[] = [];
  const who = f.limit != null ? `${f.sort === "score_desc" ? "Best " : "Up to "}${f.limit} students` : "Students";
  let head = who;
  if (f.skills.length) {
    const names = f.skills.map((id) => skillNames[id] ?? id);
    head += ` with ${joinNames(names, f.skillMatch === "all" ? "and" : "or")} (${LEVEL_PHRASES[f.minLevel]})`;
  }
  parts.push(head);
  if (f.minScore != null) parts.push(`score ${f.minScore} or higher`);
  if (f.bands.length) parts.push(`band ${joinNames(f.bands.map((b) => BAND_LABELS[b].toLowerCase()), "or")}`);
  if (f.atRiskOnly) parts.push("at risk only");
  parts.push(SORT_LABELS[f.sort].toLowerCase());
  return parts.join(", ");
}

export interface SkillOption {
  id: string;
  name: string;
}

/** Skills a company can ask for: the role's own skills by importance, then skills students claim in this cohort. */
export function skillOptions(
  role: Pick<Schema["Role"], "skills"> | undefined,
  insights: Pick<Schema["CohortInsights"], "unverified_rate_by_skill" | "top_missing_skills"> | undefined,
): SkillOption[] {
  const seen = new Set<string>();
  const out: SkillOption[] = [];
  const add = (id: string, name: string) => {
    if (seen.has(id)) return;
    seen.add(id);
    out.push({ id, name });
  };
  [...(role?.skills ?? [])]
    .sort((a, b) => b.importance - a.importance || a.skill_name.localeCompare(b.skill_name))
    .forEach((s) => add(s.skill_id, s.skill_name));
  [...(insights?.unverified_rate_by_skill ?? [])]
    .sort((a, b) => b.claimed_by - a.claimed_by || a.skill_name.localeCompare(b.skill_name))
    .forEach((s) => add(s.skill_id, s.skill_name));
  (insights?.top_missing_skills ?? []).forEach((s) => add(s.skill_id, s.skill_name));
  return out;
}
