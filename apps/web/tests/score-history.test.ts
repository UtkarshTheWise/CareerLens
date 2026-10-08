import test from "node:test";
import assert from "node:assert/strict";
import { scoreHistory } from "../lib/score-history";
test("history preserves completed scan values, bounds periods to latest scan and rejects invalid data", () => {
  const rows = [
    {
      id: "a",
      role_id: "r",
      status: "done" as const,
      created_at: "2026-10-01T00:00:00Z",
      score: 40,
    },
    {
      id: "b",
      role_id: "r",
      status: "done" as const,
      created_at: "2026-10-09T00:00:00Z",
      score: 61,
    },
    {
      id: "c",
      role_id: "r",
      status: "collecting" as const,
      created_at: "2026-10-10T00:00:00Z",
      score: 80,
    },
    {
      id: "d",
      role_id: "r",
      status: "done" as const,
      created_at: "invalid",
      score: 99,
    },
  ];
  const before = JSON.stringify(rows),
    d = scoreHistory(rows);
  assert.deepEqual(
    d.weekly.map((p) => p.primary),
    [61],
  );
  assert.deepEqual(
    d.monthly.map((p) => p.primary),
    [40, 61],
  );
  assert.equal(JSON.stringify(rows), before);
  assert.deepEqual(scoreHistory([]).yearly, []);
});
