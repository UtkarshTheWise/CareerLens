import { choiceText } from "@/lib/quiz-presentation";
import { safeUrl, number, type Schema } from "@/components/career/shared";
export function SourceLink({
  source,
}: {
  source?: Schema["SourceRef"] | null;
}) {
  if (!source) return null;
  const href = safeUrl(source.url);
  return (
    <div className="space-y-2 text-xs text-muted-readable">
      <p className="break-anywhere">
        {source.path}
        {source.start_line != null
          ? ` · lines ${source.start_line}${source.end_line != null ? `–${source.end_line}` : ""}`
          : ""}
        {source.section ? ` · ${source.section}` : ""}
      </p>
      {href && (
        <a
          href={href}
          target="_blank"
          rel="noreferrer"
          className="text-link inline-flex min-h-11 items-center"
        >
          {source.start_line != null ? "View lines" : "View source"}
        </a>
      )}
    </div>
  );
}
export function QuizFeedback({
  feedback,
  question,
}: {
  feedback: Schema["QuizAnswerFeedback"];
  question?: Schema["QuizQuestion"];
}) {
  return (
    <div className="space-y-4" data-component="QuizFeedback">
      {feedback.score != null && (
        <p className="text-sm font-semibold">
          Question score: {number(feedback.score * 100)}%
        </p>
      )}
      {feedback.timed_out && (
        <p className="status-text tone-text-warning">
          The server marked this answer as timed out.
        </p>
      )}
      {feedback.choice_id && (
        <p className="text-xs text-muted-readable">
          Your choice: {choiceText(question, feedback.choice_id)}
        </p>
      )}
      {feedback.text != null && (
        <div>
          <h4 className="eyebrow">Your answer</h4>
          <p className="mt-2 whitespace-pre-wrap break-anywhere text-sm text-muted-readable">
            {feedback.text || "No written answer recorded."}
          </p>
        </div>
      )}
      {feedback.correct_choice_id && (
        <p className="text-xs">
          Correct choice returned by the service:{" "}
          {choiceText(question, feedback.correct_choice_id)}
        </p>
      )}
      {!!feedback.key_points?.length && (
        <ul className="space-y-3">
          {feedback.key_points.map((point, i) => (
            <li key={i} className="flex items-start gap-3">
              <span
                className={`status-text shrink-0 ${point.status === "covered" ? "tone-text-success" : point.status === "partial" ? "tone-text-warning" : "tone-text-danger"}`}
              >
                {point.status}
              </span>
              <span className="min-w-0 text-sm leading-relaxed">
                {point.text}
              </span>
            </li>
          ))}
        </ul>
      )}
      {!!feedback.incorrect_statements?.length && (
        <div>
          <h4 className="eyebrow">Points to revisit</h4>
          <ul className="mt-2 space-y-2 text-sm text-muted-readable">
            {feedback.incorrect_statements.map((text, i) => (
              <li key={i}>{text}</li>
            ))}
          </ul>
        </div>
      )}
      {feedback.feedback && (
        <p className="text-sm leading-relaxed">{feedback.feedback}</p>
      )}
      {feedback.model_answer && (
        <div className="inset-note">
          <h4 className="eyebrow">Model answer</h4>
          <p className="mt-2 whitespace-pre-wrap break-anywhere text-sm leading-relaxed text-muted-readable">
            {feedback.model_answer}
          </p>
        </div>
      )}
      {feedback.score == null && !feedback.feedback && (
        <p className="text-sm text-muted-readable">
          Your answer was recorded. Detailed feedback was not returned.
        </p>
      )}
      <SourceLink source={feedback.source_ref} />
    </div>
  );
}
