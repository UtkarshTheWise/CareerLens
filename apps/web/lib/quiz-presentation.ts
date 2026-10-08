import type { components } from "@careerlens/api-client";
export function choiceText(
  question: components["schemas"]["QuizQuestion"] | undefined,
  id: string,
) {
  return question?.options?.find((option) => option.id === id)?.text || id;
}
export function timerNotice(remaining: number | null) {
  if (remaining == null || remaining > 30) return "";
  if (remaining === 0) return "Time is up. Your answer is being recorded.";
  return remaining <= 10
    ? "10 seconds or less remaining. Finish your answer."
    : "30 seconds or less remaining. Finish your answer.";
}
