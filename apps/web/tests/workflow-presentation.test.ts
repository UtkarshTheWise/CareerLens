import test from "node:test";
import assert from "node:assert/strict";
import type { components } from "@careerlens/api-client";
import { studentDirectory } from "../lib/student-directory";
import { trackerView, deadlineLabel } from "../lib/tracker-view";
import { choiceText, timerNotice } from "../lib/quiz-presentation";
import { scoreHistory } from "../lib/score-history";
type Schema = components["schemas"];
test("target-role history never compares scores for different roles", () => {
  const scans: Schema["AnalysisSummary"][] = [
    {
      id: "a",
      role_id: "frontend",
      status: "done",
      score: 40,
      created_at: "2026-10-01T00:00:00Z",
    },
    {
      id: "b",
      role_id: "backend",
      status: "done",
      score: 95,
      created_at: "2026-10-07T00:00:00Z",
    },
    {
      id: "c",
      role_id: "frontend",
      status: "done",
      score: 50,
      created_at: "2026-10-03T00:00:00Z",
    },
  ];
  assert.deepEqual(
    scoreHistory(scans, "frontend").weekly.map((p) => p.primary),
    [40, 50],
  );
  assert.deepEqual(scoreHistory(scans, "design").yearly, []);
});
test("student search and support sorting preserve returned values and source order", () => {
  const rows: Schema["CohortStudent"][] = [
    {
      profile_id: "b",
      name: "Zoe",
      department: "CSE",
      score: 60,
      band: "developing",
      coverage: 50,
      at_risk: false,
    },
    {
      profile_id: "a",
      name: "Ada",
      department: "Design",
      score: 20,
      band: "not_ready",
      coverage: 90,
      at_risk: true,
    },
    {
      profile_id: "c",
      name: "Leo",
      department: "CSE",
      score: 60,
      band: "developing",
      coverage: 50,
      at_risk: false,
    },
  ];
  const before = JSON.stringify(rows);
  assert.deepEqual(
    studentDirectory(rows, "  cSe ", "readiness").map((s) => s.name),
    ["Leo", "Zoe"],
  );
  assert.deepEqual(
    studentDirectory(rows, "", "coverage").map((s) => s.name),
    ["Leo", "Zoe", "Ada"],
  );
  assert.deepEqual(studentDirectory(rows, "missing", "name"), []);
  assert.equal(JSON.stringify(rows), before);
});
test("tracker sorts absent deadlines last and uses company/title search without altering server status", () => {
  const make = (
    id: string,
    company: string,
    deadline: string | null,
    updated_at: string,
  ): Schema["Application"] => ({
    id,
    profile_id: "profile",
    company,
    title: "Engineer",
    deadline,
    status: "saved",
    created_at: "2026-10-01T00:00:00Z",
    updated_at,
  });
  const rows = [
    make("a", "Alpha", null, "2026-10-03T00:00:00Z"),
    make("b", "Beta", "2026-10-09", "2026-10-02T00:00:00Z"),
    make("c", "Gamma", "2026-10-08", "2026-10-01T00:00:00Z"),
  ];
  const before = JSON.stringify(rows);
  assert.deepEqual(
    trackerView(rows, " engineer ", "deadline").map((a) => a.id),
    ["c", "b", "a"],
  );
  assert.deepEqual(
    trackerView(rows, "Beta", "updated").map((a) => a.id),
    ["b"],
  );
  assert.equal(JSON.stringify(rows), before);
});
test("deadline wording follows the visitor calendar day and rejects rollover dates", () => {
  const today = new Date(2026, 9, 8, 23, 59);
  assert.equal(deadlineLabel("2026-10-08", today)?.note, "Due today");
  assert.equal(deadlineLabel("2026-10-09", today)?.note, "Due tomorrow");
  assert.equal(deadlineLabel("2026-10-07", today)?.note, "Deadline passed");
  assert.equal(deadlineLabel("2026-02-30", today), null);
  assert.equal(deadlineLabel("2026-10-16", today)?.soon, false);
});
test("feedback resolves only returned choice IDs and falls back honestly without cached options", () => {
  const q: Schema["QuizQuestion"] = {
    id: "q",
    order: 1,
    type: "mcq",
    category: "code_reading",
    prompt: "Explain",
    skill_ids: [],
    options: [{ id: "a", text: "Await the transaction" }],
    answered: false,
  };
  assert.equal(choiceText(q, "a"), "Await the transaction");
  assert.equal(choiceText(q, "unknown"), "unknown");
  assert.equal(choiceText(undefined, "a"), "a");
});
test("timer announcements change only at meaningful thresholds, not every second", () => {
  assert.equal(timerNotice(null), "");
  assert.equal(timerNotice(31), "");
  assert.equal(timerNotice(30), timerNotice(11));
  assert.equal(timerNotice(10), timerNotice(1));
  assert.notEqual(timerNotice(11), timerNotice(10));
  assert.match(timerNotice(0), /Time is up/);
});
