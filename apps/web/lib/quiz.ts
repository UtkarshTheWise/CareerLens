import type { components } from "@careerlens/api-client";
type Schema = components["schemas"];
const created = new WeakSet<Schema["Quiz"]>();
const receipts = new WeakMap<Schema["Quiz"], number>();
export function markQuizReceived(quiz: Schema["Quiz"]) {
  receipts.set(quiz, performance.now());
  return quiz;
}
export function markQuizCreated(quiz: Schema["Quiz"]) {
  created.add(quiz);
  return markQuizReceived(quiz);
}
export function isFreshQuizCreation(quiz: Schema["Quiz"] | undefined) {
  return (
    !!quiz &&
    created.has(quiz) &&
    quiz.status === "in_progress" &&
    quiz.questions.every(
      (q) => !q.answered && !q.served_at && q.time_remaining_s == null,
    )
  );
}
export function quizReceiptTime(quiz: Schema["Quiz"] | undefined) {
  return quiz ? (receipts.get(quiz) ?? 0) : 0;
}

export function currentQuestion(quiz: Schema["Quiz"]) {
  return [...quiz.questions]
    .sort((a, b) => a.order - b.order)
    .find((q) => !q.answered);
}
// The server provides remaining time. Only elapsed monotonic time is subtracted.
export function secondsLeft(
  remaining: number,
  receivedAt: number,
  now: number,
) {
  return Math.max(
    0,
    Math.ceil(remaining - Math.max(0, now - receivedAt) / 1000),
  );
}
export function answerPayload(
  question: Schema["QuizQuestion"],
  mode: Schema["QuizMode"],
  choice: string | null,
  text: string,
  elapsed: number,
  focusLosses: number,
): Schema["QuizAnswer"] {
  return {
    question_id: question.id,
    choice_id:
      question.type === "mcq" && question.options?.some((o) => o.id === choice)
        ? choice
        : null,
    text: question.type === "short_answer" ? text.slice(0, 2000) : null,
    time_taken_ms: Math.max(0, Math.round(elapsed)),
    focus_lost_count: mode === "verify" ? Math.max(0, focusLosses) : 0,
  };
}
export function cooldownSeconds(
  timestamp: string | null | undefined,
  now: number,
) {
  const time = Date.parse(timestamp || "");
  return Number.isFinite(time)
    ? Math.max(0, Math.ceil((time - now) / 1000))
    : null;
}
export function duration(seconds: number) {
  const value = Math.max(0, Math.ceil(seconds));
  const hours = Math.floor(value / 3600);
  return `${hours ? `${hours}:` : ""}${String(Math.floor((value % 3600) / 60)).padStart(hours ? 2 : 1, "0")}:${String(value % 60).padStart(2, "0")}`;
}
