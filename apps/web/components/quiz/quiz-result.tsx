"use client";
/* Hallmark · pre-emit critique: P4 H4 E4 S5 R5 V3 — returned grading and evidence. */
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import { useCreateQuiz, useGetAnalysis } from "@/lib/api/hooks";
import { ApiError, errorMessage } from "@/lib/api/transport";
import { cooldownSeconds, duration } from "@/lib/quiz";
import {
  FlagCard,
  ScoreRing,
  UnderstandingBadge,
  WhyPopover,
} from "@/components/career";
import { signed, type Schema } from "@/components/career/shared";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { QuizFeedback, SourceLink } from "./quiz-feedback";
export function QuizResult({
  quiz,
  result,
}: {
  quiz: Schema["Quiz"];
  result: Schema["QuizResult"];
}) {
  const router = useRouter();
  const create = useCreateQuiz();
  const lock = useRef(false);
  const [mode, setMode] = useState<Schema["QuizMode"]>();
  const [now, setNow] = useState(0);
  const [retakeAt, setRetakeAt] = useState(result.retake_available_at);
  const reduced = useReducedMotion();
  const analysis = useGetAnalysis(
    { analysis_id: quiz.analysis_id },
    { enabled: Boolean(result.score_update) },
  );
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const remaining = cooldownSeconds(retakeAt, now);
  const cooling =
    Boolean(retakeAt) && (now === 0 || remaining == null || remaining > 0);
  async function retake(next: Schema["QuizMode"]) {
    if (lock.current) return;
    lock.current = true;
    setMode(next);
    try {
      const created = await create.mutateAsync({
        analysis_id: quiz.analysis_id,
        body: { project_id: quiz.project_id, mode: next },
      });
      router.push(`/quiz/${encodeURIComponent(created.id)}`);
    } catch (e) {
      if (
        e instanceof ApiError &&
        typeof e.details?.details?.retake_available_at === "string"
      )
        setRetakeAt(e.details.details.retake_available_at);
      lock.current = false;
      setMode(undefined);
    }
  }
  return (
    <section
      className="mx-auto max-w-4xl space-y-6"
      data-component="QuizResult"
    >
      <header className="space-y-3">
        <p className="text-xs font-semibold text-primary-text">
          {result.mode === "practice" ? "Practice complete" : "Verify complete"}
        </p>
        <h1 className="text-2xl font-semibold">Your quiz result</h1>
        <p className="break-anywhere text-sm text-muted-readable">
          {quiz.project_title}
        </p>
      </header>
      <Card className="space-y-5 p-6">
        <div className="flex flex-wrap items-center justify-center gap-6">
          <ScoreRing
            label="Quiz score"
            value={result.score}
            explanation={
              <WhyPopover
                label="Quiz score"
                definition="This score is returned by the grading service. Review the question-by-question feedback, key points and source references below to see how your understanding was assessed."
              />
            }
          />
          <div className="max-w-md space-y-3">
            {result.mode === "verify" && result.understanding ? (
              <UnderstandingBadge understanding={result.understanding} />
            ) : (
              <span className="status-pill tone-muted">
                {result.mode === "practice"
                  ? "Practice: no evidence change"
                  : "Understanding result unavailable"}
              </span>
            )}
            <p className="text-sm leading-relaxed text-muted-readable">
              {result.mode === "practice"
                ? "Practice helps you prepare and never changes your evidence or readiness score."
                : result.understanding === "not_demonstrated"
                  ? "Understanding not demonstrated yet. Review the topics below and try again when ready. This result does not make a claim about who built your project."
                  : "This result reflects your latest verify attempt. Review the returned feedback to see what was demonstrated and what to revisit."}
            </p>
            {result.mode === "verify" && result.focus_lost_total != null && (
              <p className="text-xs text-muted-readable">
                You left the tab {result.focus_lost_total}{" "}
                {result.focus_lost_total === 1 ? "time" : "times"}. This is for
                your review only and is not used in your score.
              </p>
            )}
          </div>
        </div>
      </Card>
      {result.score_update && (
        <Card className="space-y-4 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold">Readiness score update</h2>
            <motion.p
              initial={reduced ? false : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: reduced ? 0 : 0.3 }}
              className={`text-2xl font-bold tabular-nums ${result.score_update.delta < 0 ? "text-danger-readable" : "text-success-readable"}`}
              aria-label={`Readiness change: ${signed(result.score_update.delta)} points`}
            >
              {signed(result.score_update.delta)} pts
            </motion.p>
          </div>
          <div className="grid gap-5 sm:grid-cols-2">
            <ScoreRing
              label="Before check"
              value={result.score_update.before.total}
              band={result.score_update.before.band}
              explanation={
                <WhyPopover
                  label="Before check"
                  components={result.score_update.before.components}
                  evidence={analysis.data?.report?.evidence}
                />
              }
            />
            <ScoreRing
              label="After check"
              value={result.score_update.after.total}
              band={result.score_update.after.band}
              explanation={
                <WhyPopover
                  label="After check"
                  components={result.score_update.after.components}
                  evidence={analysis.data?.report?.evidence}
                />
              }
            />
          </div>
          <p className="text-xs text-muted-readable">
            Before, after and change come from the scoring service. Open each
            explanation to review the contributions.
          </p>
          {analysis.isError && (
            <p className="text-xs text-muted-readable">
              Evidence links could not be refreshed; the returned scoring
              explanations remain available.
            </p>
          )}
        </Card>
      )}
      {result.flag && <FlagCard flag={result.flag} />}
      <div className="grid items-start gap-4 md:grid-cols-2">
        <Card className="space-y-4 p-6">
          <h2 className="text-lg font-semibold">Strengths</h2>
          {result.strengths.length ? (
            <ul className="space-y-3 text-sm leading-relaxed">
              {result.strengths.map((text, i) => (
                <li key={i}>{text}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-readable">
              No strengths were returned for this attempt.
            </p>
          )}
        </Card>
        <Card className="space-y-4 p-6">
          <h2 className="text-lg font-semibold">Topics to review</h2>
          {result.review_topics.length ? (
            <ul className="space-y-4">
              {result.review_topics.map((item, i) => (
                <li key={i} className="space-y-2">
                  <p className="text-sm">{item.topic}</p>
                  <SourceLink source={item.source_ref} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-readable">
              No review topics were returned.
            </p>
          )}
        </Card>
      </div>
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Question-by-question review</h2>
        {result.per_question.length ? (
          result.per_question.map((item, i) => (
            <Card key={item.question_id} className="space-y-4 p-6">
              <h3 className="text-sm font-semibold">
                Question{" "}
                {quiz.questions.find((q) => q.id === item.question_id)?.order ||
                  i + 1}
              </h3>
              {quiz.questions.find((q) => q.id === item.question_id)
                ?.prompt && (
                <p className="text-sm text-muted-readable">
                  {
                    quiz.questions.find((q) => q.id === item.question_id)
                      ?.prompt
                  }
                </p>
              )}
              <QuizFeedback feedback={item} />
            </Card>
          ))
        ) : (
          <p className="rounded-card bg-surface p-6 text-sm text-muted-readable">
            No per-question feedback was returned.
          </p>
        )}
      </section>
      <Card className="space-y-4 p-6">
        <h2 className="text-lg font-semibold">Keep practising</h2>
        {retakeAt && (
          <div className="space-y-2 text-xs text-muted-readable">
            <p className="break-anywhere">
              Verify retake available at: {retakeAt}
            </p>
            <p role="status">
              {now === 0
                ? "Checking retake time…"
                : remaining == null
                  ? "Retake timing could not be read; the service must confirm availability."
                  : remaining > 0
                    ? `Verify available in ${duration(remaining)}`
                    : "Verify retake is available."}
            </p>
          </div>
        )}
        <div className="flex flex-wrap gap-3">
          <Button
            variant="outline"
            className="min-h-11"
            disabled={Boolean(mode)}
            onClick={() => void retake("practice")}
          >
            {mode === "practice" ? "Preparing practice…" : "Practise again"}
          </Button>
          <Button
            className="min-h-11"
            disabled={Boolean(mode) || cooling}
            onClick={() => void retake("verify")}
          >
            {mode === "verify" ? "Preparing verify…" : "Retake verify"}
          </Button>
          <Button asChild variant="outline" className="min-h-11">
            <Link href={`/report/${encodeURIComponent(quiz.analysis_id)}`}>
              Return to your report
            </Link>
          </Button>
        </div>
        {create.isError && (
          <p role="alert" className="text-sm text-danger-readable">
            {errorMessage(create.error)}
          </p>
        )}
      </Card>
    </section>
  );
}
