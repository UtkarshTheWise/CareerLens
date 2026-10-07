import test from "node:test";
import assert from "node:assert/strict";
import type { components } from "@careerlens/api-client";
import { answerPayload, cooldownSeconds, currentQuestion, duration, secondsLeft } from "../lib/quiz";
type Schema = components["schemas"];
const question: Schema["QuizQuestion"] = { id: "q1", order: 1, type: "mcq", category: "code_reading", prompt: "Explain this flow.", skill_ids: [], options: [{ id: "a", text: "Option A" }], answered: false };
test("server remaining time decreases across elapsed, suspended and backward monotonic samples without resetting to time limit", () => {
  assert.equal(secondsLeft(8, 1000, 1000), 8);
  assert.equal(secondsLeft(8, 1000, 3501), 6);
  assert.equal(secondsLeft(8, 1000, 13000), 0);
  assert.equal(secondsLeft(8, 1000, 0), 8);
});
test("answer payload uses only eligible options, clips written answers and records verify focus events", () => {
  assert.deepEqual(answerPayload(question, "verify", "a", "ignored", 1234.5, 2), { question_id: "q1", choice_id: "a", text: null, time_taken_ms: 1235, focus_lost_count: 2 });
  assert.equal(answerPayload(question, "verify", "invented", "", -10, 0).choice_id, null);
  const short = answerPayload({ ...question, type: "short_answer" }, "practice", "a", "x".repeat(2001), 500, 7);
  assert.equal(short.text?.length, 2000); assert.equal(short.choice_id, null); assert.equal(short.focus_lost_count, 0);
});
test("quiz resume selects only the first server-unanswered question without changing source order", () => {
  const quiz: Schema["Quiz"] = { id: "quiz", analysis_id: "analysis", project_id: "project", project_title: "Project", mode: "verify", status: "in_progress", total_questions: 3, created_at: "2026-10-07T00:00:00Z", questions: [{ ...question, id: "third", order: 3 }, { ...question, answered: true }, { ...question, id: "second", order: 2 }] };
  assert.equal(currentQuestion(quiz)?.id, "second"); assert.equal(quiz.questions[0].id, "third");
  assert.equal(currentQuestion({ ...quiz, questions: [] }), undefined);
  assert.equal(currentQuestion({ ...quiz, questions: quiz.questions.map(q => ({ ...q, answered: true })) }), undefined);
});
test("cooldown handles supplied timestamps, expiry and missing timing without inventing eligibility", () => {
  const now = Date.parse("2026-10-07T17:00:00Z");
  assert.equal(cooldownSeconds("2026-10-07T17:01:00Z", now), 60);
  assert.equal(cooldownSeconds("2026-10-07T16:00:00Z", now), 0);
  assert.equal(cooldownSeconds("not-a-date", now), null);
  assert.equal(cooldownSeconds(null, now), null);
  assert.equal(duration(3661), "1:01:01"); assert.equal(duration(5), "0:05");
});
