"use client";
/* Hallmark · pre-emit critique: P4 H4 E4 S5 R5 V3 — one question, explicit modes. */
import { useRef, useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import {
  useAnswerQuizQuestion,
  useGetQuiz,
  useGetQuizResult,
  useSubmitQuiz,
} from "@/lib/api/hooks";
import { queryKeys } from "@/lib/api/query-keys";
import { errorMessage } from "@/lib/api/transport";
import {
  currentQuestion,
  isFreshQuizCreation,
  quizReceiptTime,
} from "@/lib/quiz";
import type { Schema } from "@/components/career/shared";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/layout/page";
import { Skeleton } from "@/components/ui/skeleton";
import { QuizCard } from "./quiz-card";
import { QuizFeedback } from "./quiz-feedback";
import { QuizResult } from "./quiz-result";
export function QuizScreen({ quizId }: { quizId: string }) {
  const cache = useQueryClient();
  const [initialQuiz] = useState(() =>
    cache.getQueryData<Schema["Quiz"]>(queryKeys.getQuiz({ quiz_id: quizId })),
  );
  const [initialReceipt] = useState(() => quizReceiptTime(initialQuiz));
  const seed = isFreshQuizCreation(initialQuiz) ? initialQuiz : undefined;
  const [begun, setBegun] = useState(false);
  const query = useGetQuiz({ quiz_id: quizId }, { enabled: begun || !seed });
  const receivedAt = quizReceiptTime(query.data);
  const quiz = query.data;
  const answer = useAnswerQuizQuestion();
  const submit = useSubmitQuiz();
  const submitLock = useRef(false);
  const [result, setResult] = useState<Schema["QuizResult"]>();
  const [feedback, setFeedback] = useState<{
    question: Schema["QuizQuestion"];
    answer: Schema["QuizAnswerFeedback"];
  }>();
  const [lastRecorded, setLastRecorded] = useState<Schema["QuizQuestion"]>();
  const [notice, setNotice] = useState<string>();
  const [sendingQuestion, setSendingQuestion] = useState<{
    question: Schema["QuizQuestion"];
    receivedAt: number;
  }>();
  const fetchedResult = useGetQuizResult(
    { quiz_id: quizId },
    { enabled: quiz?.status === "submitted" && !result && !submit.isPending },
  );
  async function finish() {
    if (submitLock.current) return;
    submitLock.current = true;
    try {
      setResult(await submit.mutateAsync({ quiz_id: quizId }));
    } catch {
      submitLock.current = false;
    }
  }
  async function send(payload: Schema["QuizAnswer"], retry: boolean) {
    if (!quiz) throw new Error("Refresh the quiz to continue.");
    const question = quiz.questions.find((q) => q.id === payload.question_id);
    if (!question)
      throw new Error("The current question changed. Refresh the quiz.");
    setSendingQuestion({ question, receivedAt });
    if (retry) {
      const refreshed = await query.refetch();
      if (refreshed.error) throw refreshed.error;
      if (refreshed.data?.status === "submitted") return;
      const recorded = refreshed.data?.questions.find(
        (q) => q.id === question.id,
      )?.answered;
      // Acknowledgment may have arrived on the server even if the response was lost.
      if (recorded) {
        setLastRecorded(question);
        setNotice(
          "Your earlier answer was recorded. Any feedback will be available in the final result.",
        );
        if (question.order >= quiz.total_questions && quiz.mode === "verify")
          await finish();
        return;
      }
      if (refreshed.data && currentQuestion(refreshed.data)?.id !== question.id)
        throw new Error(
          "The server returned a different current question. Refresh to resume it.",
        );
    }
    const recorded = await answer.mutateAsync({
      quiz_id: quizId,
      body: payload,
    });
    if (!recorded.recorded)
      throw new Error(
        "The service did not confirm your answer. Retry to check its status.",
      );
    setLastRecorded(question);
    if (quiz.mode === "practice") setFeedback({ question, answer: recorded });
    else if (question.order >= quiz.total_questions) await finish();
  }
  function retryQuiz() {
    setBegun(true);
    void query.refetch();
  }
  if (
    (query.isPending && !quiz) ||
    (!seed && receivedAt === initialReceipt && !query.isError) ||
    (begun && query.isFetching && quiz === seed)
  )
    return (
      <div
        role="status"
        aria-label="Loading quiz"
        className="mx-auto max-w-3xl space-y-4"
      >
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-80 w-full rounded-card" />
        <span className="sr-only">Loading project check</span>
      </div>
    );
  if (!quiz)
    return (
      <div className="panel mx-auto max-w-3xl space-y-4">
        <h1 className="page-title">Project check unavailable</h1>
        <p role="alert" className="field-error">
          {query.error ? errorMessage(query.error) : "No quiz was returned."}
        </p>
        <Button
          variant="outline"
          className="min-h-11"
          disabled={query.isFetching}
          onClick={retryQuiz}
        >
          Retry quiz
        </Button>
      </div>
    );
  if (result || quiz.status === "submitted") {
    const final = result || fetchedResult.data;
    if (final) return <QuizResult quiz={quiz} result={final} />;
    return (
      <div className="panel mx-auto max-w-3xl space-y-4">
        <h1 className="page-title">Your quiz result</h1>
        {fetchedResult.isError ? (
          <>
            <p role="alert" className="field-error">
              {errorMessage(fetchedResult.error)}
            </p>
            <Button variant="outline" onClick={() => fetchedResult.refetch()}>
              Retry result
            </Button>
          </>
        ) : (
          <p role="status" className="text-sm text-muted-readable">
            Loading your submitted result…
          </p>
        )}
      </div>
    );
  }
  const question =
    answer.isPending && sendingQuestion
      ? sendingQuestion.question
      : currentQuestion(quiz);
  const questionReceivedAt =
    answer.isPending && sendingQuestion
      ? sendingQuestion.receivedAt
      : receivedAt;
  const active =
    begun || (quiz.mode === "verify" && question?.time_remaining_s != null);
  return (
    <section className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        eyebrow={quiz.mode === "practice" ? "Practice" : "Verify understanding"}
        title="Project understanding check"
        description={<span className="break-anywhere">{quiz.project_title}</span>}
        className="pb-2"
      />
      {!active ? (
        <div className="panel space-y-5" data-component="QuizIntro">
          <h2 className="section-title">Explain the work you know.</h2>
          <p className="text-sm leading-relaxed text-muted-readable">
            {quiz.total_questions} questions about your project. Answers are
            graded on understanding, not English. You can answer in any
            language.
          </p>
          <div className="inset-note text-text">
            {quiz.mode === "practice"
              ? "Practice is untimed. Hints and feedback help you prepare; it does not change your evidence or score."
              : "Verify is timed, one question at a time, with no going back. Paste is disabled. Feedback appears after final submission; the latest verify result can update your evidence."}
          </div>
          {quiz.mode === "verify" && (
            <div>
              <h3 className="eyebrow">Time per question</h3>
              {quiz.questions.length ? (
                <ul className="mt-2 space-y-2 text-xs text-muted-readable">
                  {quiz.questions.map((q) => (
                    <li key={q.id}>
                      Question {q.order}:{" "}
                      {q.time_limit_s != null
                        ? `${q.time_limit_s} seconds`
                        : "The service has not returned a time limit."}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-xs text-muted-readable">
                  Time limits appear when the service serves each question.
                </p>
              )}
              <p className="mt-3 text-xs text-muted-readable">
                Leaving the tab is recorded for your review. It does not affect
                your score. Skipping a quiz never lowers your score.
              </p>
            </div>
          )}
          <Button
            className="min-h-11"
            disabled={query.isFetching}
            onClick={() => setBegun(true)}
          >
            {query.isFetching ? "Loading question…" : "Begin check"}
          </Button>
        </div>
      ) : submit.isPending ? (
        <div className="panel">
          <p role="status" className="text-sm text-muted-readable">
            {submit.isPending
              ? "Submitting your quiz…"
              : "Recording your answer…"}
          </p>
        </div>
      ) : feedback ? (
        <div className="panel space-y-5">
          <h2
            className="section-title"
            tabIndex={-1}
            ref={(el) => {
              if (el) el.focus();
            }}
          >
            Practice feedback
          </h2>
          <p className="text-sm text-muted-readable">
            {feedback.question.prompt}
          </p>
          <QuizFeedback
            feedback={feedback.answer}
            question={feedback.question}
          />
          <Button
            className="min-h-11"
            onClick={() => {
              if (feedback.question.order >= quiz.total_questions)
                void finish();
              else {
                setFeedback(undefined);
                void query.refetch();
              }
            }}
          >
            {feedback.question.order >= quiz.total_questions
              ? "Finish practice"
              : "Next question"}
          </Button>
        </div>
      ) : question && question.id !== lastRecorded?.id ? (
        <QuizCard
          key={question.id}
          question={question}
          mode={quiz.mode}
          total={quiz.total_questions}
          receivedAt={questionReceivedAt}
          onSend={send}
          onRefresh={retryQuiz}
        />
      ) : (
        <div className="panel space-y-4">
          <h2 className="section-title">
            {lastRecorded && lastRecorded.order >= quiz.total_questions
              ? "Ready to submit"
              : "Waiting for the next question"}
          </h2>
          <p className="text-sm text-muted-readable">
            {lastRecorded
              ? "Your answer was recorded."
              : quiz.questions.length
                ? "No unanswered question was returned."
                : "No questions were returned. Refresh to check whether your quiz is ready."}
          </p>
          {(lastRecorded && lastRecorded.order >= quiz.total_questions) ||
          (quiz.questions.length > 0 &&
            quiz.questions.every((q) => q.answered) &&
            Math.max(...quiz.questions.map((q) => q.order)) >=
              quiz.total_questions) ? (
            <Button className="min-h-11" onClick={() => void finish()}>
              Submit quiz
            </Button>
          ) : (
            <Button
              variant="outline"
              className="min-h-11"
              disabled={query.isFetching}
              onClick={() => query.refetch()}
            >
              Refresh quiz
            </Button>
          )}
        </div>
      )}
      {submit.isError && (
        <div
          role="alert"
          className="space-y-3 rounded-control border border-danger-readable bg-danger-tint p-4"
        >
          <p className="text-sm text-danger-readable">
            {errorMessage(submit.error)}
          </p>
          <Button
            variant="outline"
            className="min-h-11"
            onClick={() => void finish()}
          >
            Retry submission
          </Button>
        </div>
      )}
      {query.isError && (
        <p role="alert" className="text-sm text-danger-readable">
          {errorMessage(query.error)}
        </p>
      )}
      {notice && (
        <p role="status" className="text-xs text-muted-readable">
          {notice}
        </p>
      )}
      <Button asChild variant="outline" className="min-h-11">
        <Link href={`/report/${encodeURIComponent(quiz.analysis_id)}`}>
          Return to your report
        </Link>
      </Button>
    </section>
  );
}
