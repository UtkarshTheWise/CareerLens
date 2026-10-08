import assert from "node:assert/strict";
import { test } from "node:test";
import {
  consistencyDatasets,
  simulationChanges,
  type Schema,
} from "../lib/report-presentation";
test("consistency chart preserves source counts and zero weeks, groups by week start and does not mutate input", () => {
  const weeks = [
    { week_start: "2027-01-04", count: 2 },
    { week_start: "2026-12-28", count: 7 },
    { week_start: "2026-12-21", count: 0 },
  ];
  const original = structuredClone(weeks);
  const data = consistencyDatasets(weeks);
  assert.deepEqual(
    data.weekly.map((point) => point.primary),
    [0, 7, 2],
  );
  assert.deepEqual(data.monthly, [
    { label: "2026-12", primary: 7 },
    { label: "2027-01", primary: 2 },
  ]);
  assert.deepEqual(data.yearly, [
    { label: "2026", primary: 7 },
    { label: "2027", primary: 2 },
  ]);
  assert.ok(data.weekly.every((point) => !("secondary" in point)));
  assert.deepEqual(weeks, original);
});
test("absent consistency data does not create a timeline or a score", () => {
  assert.deepEqual(consistencyDatasets([]), {
    weekly: [],
    monthly: [],
    yearly: [],
  });
});
test("simulation sends only eligible, missing selected signals for known code projects", () => {
  const code: Schema["ProjectAudit"] = {
    project_id: "code",
    title: "Synthetic",
    kind: "code",
    score: 70,
    counted_in_score: true,
    detected_skills: [],
    flags: [],
    self_reported: false,
    signals: {
      tests: true,
      ci: false,
      demo_url: false,
      license: false,
      readme: false,
      deploy_config: false,
      authored_commits: 10,
      total_commits: 10,
    },
  };
  const design: Schema["ProjectAudit"] = {
    ...code,
    project_id: "design",
    kind: "design",
    signals: null,
  };
  assert.deepEqual(
    simulationChanges(
      {
        code: ["tests", "ci", "ci", "deploy_config"],
        design: ["tests"],
        unknown: ["ci"],
      },
      [code, design],
    ),
    [{ project_id: "code", add_signals: ["ci"] }],
  );
  assert.deepEqual(simulationChanges({ code: [] }, [code]), []);
});
