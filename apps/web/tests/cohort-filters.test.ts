import assert from "node:assert/strict";
import { test } from "node:test";
import {
  DEFAULT_FILTERS,
  cohortQuery,
  filterSummary,
  hasActiveFilters,
  skillOptions,
  type CohortFilters,
} from "../lib/cohort-filters";
import { studentDirectory } from "../lib/student-directory";

const f = (over: Partial<CohortFilters>): CohortFilters => ({ ...DEFAULT_FILTERS, ...over });

test("defaults are left out of the query so the key is stable", () => {
  assert.deepEqual(cohortQuery("sde-backend", DEFAULT_FILTERS), { role_id: "sde-backend" });
  assert.deepEqual(cohortQuery("sde-backend", f({ minLevel: "strong", skillMatch: "any" })), { role_id: "sde-backend" });
});

test("skills repeat, and match mode and evidence level are sent with them", () => {
  const query = cohortQuery(
    "sde-backend",
    f({ skills: ["python", "docker"], skillMatch: "any", minLevel: "strong", minScore: 65, sort: "score_desc", limit: 2 }),
  );
  assert.deepEqual(query, {
    role_id: "sde-backend",
    skill: ["python", "docker"],
    skill_match: "any",
    min_level: "strong",
    min_score: 65,
    sort: "score_desc",
    limit: 2,
  });
});

test("bands and the at-risk toggle are sent when set", () => {
  assert.deepEqual(cohortQuery("r", f({ bands: ["ready", "developing"], atRiskOnly: true })), {
    role_id: "r",
    at_risk_only: true,
    band: ["ready", "developing"],
  });
});

test("the query does not share arrays with the filters", () => {
  const filters = f({ skills: ["python"] });
  const query = cohortQuery("r", filters);
  filters.skills.push("sql");
  assert.deepEqual(query.skill, ["python"]);
});

test("hasActiveFilters is false for the defaults and true for any change", () => {
  assert.equal(hasActiveFilters(DEFAULT_FILTERS), false);
  assert.equal(hasActiveFilters(f({ minScore: 50 })), true);
  assert.equal(hasActiveFilters(f({ bands: ["ready"] })), true);
  assert.equal(hasActiveFilters(f({ sort: "name" })), true);
  assert.equal(hasActiveFilters(f({ skills: ["python"] })), true);
  assert.equal(hasActiveFilters(f({ atRiskOnly: true })), true);
});

test("the summary reads like the request", () => {
  const names = { docker: "Docker", python: "Python" };
  assert.equal(
    filterSummary(f({ skills: ["docker"], minScore: 65, sort: "score_desc", limit: 2 }), names),
    "Best 2 students with Docker (strong or moderate evidence), score 65 or higher, best first",
  );
  assert.equal(filterSummary(DEFAULT_FILTERS, names), "Students, weakest first");
  assert.equal(
    filterSummary(f({ skills: ["python", "docker"], skillMatch: "any", minLevel: "strong" }), names),
    "Students with Python or Docker (strong evidence), weakest first",
  );
  assert.match(filterSummary(f({ skills: ["go"] }), names), /with go /);
});

test("skill options list the role first by importance and drop duplicates", () => {
  const options = skillOptions(
    {
      skills: [
        { skill_id: "sql", skill_name: "SQL", importance: 2 },
        { skill_id: "python", skill_name: "Python", importance: 3 },
      ],
    },
    {
      unverified_rate_by_skill: [
        { skill_id: "sql", skill_name: "SQL", claimed_by: 9, unverified_rate: 10 },
        { skill_id: "redis", skill_name: "Redis", claimed_by: 4, unverified_rate: 50 },
        { skill_id: "go", skill_name: "Go", claimed_by: 7, unverified_rate: 20 },
      ],
      top_missing_skills: [
        { skill_id: "go", skill_name: "Go", students: 3 },
        { skill_id: "kubernetes", skill_name: "Kubernetes", students: 12 },
      ],
    },
  );
  assert.deepEqual(options.map((o) => o.id), ["python", "sql", "go", "redis", "kubernetes"]);
  assert.deepEqual(skillOptions(undefined, undefined), []);
});

test("directory search keeps the order the service returned", () => {
  const row = (name: string, department: string) =>
    ({ profile_id: name, name, department, score: 1, band: "ready", coverage: 1, at_risk: false, matched_skills: [] }) as never;
  const rows = [row("Zoe", "CSE"), row("Ada", "IT"), row("Leo", "CSE")];
  assert.deepEqual(studentDirectory(rows, " cse ").map((s: { name: string }) => s.name), ["Zoe", "Leo"]);
});
