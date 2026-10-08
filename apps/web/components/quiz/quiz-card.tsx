"use client";
/* Hallmark · pre-emit critique: P4 H4 E4 S5 R5 V3 — focused, server-timed quiz. */
import { useEffect, useRef, useState } from "react";
import { answerPayload, duration, secondsLeft } from "@/lib/quiz";
import { errorMessage } from "@/lib/api/transport";
import type { Schema } from "@/components/career/shared";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CodeSnippet } from "./code-snippet";

export function QuizCard({
  question,
  mode,
  total,
  receivedAt,
  onSend,
  onRefresh,
}: {
  question: Schema["QuizQuestion"];
  mode: Schema["QuizMode"];
  total: number;
  receivedAt: number;
  onSend: (answer: Schema["QuizAnswer"], retry: boolean) => Promise<void>;
  onRefresh: () => void;
}) {
  const verify = mode === "verify";
  const [choice, setChoice] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [hint, setHint] = useState(false);
  const [pasteNotice, setPasteNotice] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string>();
  const timing = question.time_remaining_s;
  const [remaining, setRemaining] = useState(() =>
    timing == null ? null : secondsLeft(timing, receivedAt, performance.now()),
  );
  const [start] = useState(() => performance.now());
  const focusLosses = useRef(0);
  const lost = useRef(false);
  const locked = useRef(false);
  const attempt = useRef<Schema["QuizAnswer"] | null>(null);
  const values = useRef({ choice, text });
  const sender = useRef(onSend);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    values.current = { choice, text };
    sender.current = onSend;
  }, [choice, text, onSend]);
  useEffect(() => {
    heading.current?.focus();
  }, []);
  async function send(retry = false) {
    if (locked.current) return;
    locked.current = true;
    setPending(true);
    setError(undefined);
    const payload =
      attempt.current ||
      answerPayload(
        question,
        mode,
        values.current.choice,
        values.current.text,
        performance.now() - start,
        focusLosses.current,
      );
    attempt.current = payload;
    try {
      await sender.current(payload, retry);
    } catch (e) {
      locked.current = false;
      setPending(false);
      setError(
        errorMessage(
          e instanceof Error
            ? e
            : new Error("The answer could not be recorded."),
        ),
      );
    }
  }
  const sendRef = useRef(send);
  useEffect(() => {
    sendRef.current = send;
  });
  useEffect(() => {
    if (!verify || timing == null) return;
    function tick() {
      const value = secondsLeft(timing!, receivedAt, performance.now());
      setRemaining(value);
      if (value === 0 && !attempt.current) void sendRef.current();
    }
    tick();
    const interval = setInterval(tick, 200);
    return () => clearInterval(interval);
  }, [verify, timing, receivedAt]);
  useEffect(() => {
    if (!verify) return;
    function markLoss() {
      if (!lost.current && !attempt.current) {
        lost.current = true;
        focusLosses.current++;
      }
    }
    function regain() {
      if (document.visibilityState === "visible" && document.hasFocus())
        lost.current = false;
    }
    function visibility() {
      if (document.hidden) markLoss();
      else regain();
    }
    window.addEventListener("blur", markLoss);
    window.addEventListener("focus", regain);
    document.addEventListener("visibilitychange", visibility);
    return () => {
      window.removeEventListener("blur", markLoss);
      window.removeEventListener("focus", regain);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, [verify]);
  const unavailable = verify && timing == null;
  const disabled = pending || Boolean(error) || unavailable;
  const circumference = 2 * Math.PI * 42;
  const fraction =
    question.time_limit_s && remaining != null
      ? Math.min(1, remaining / question.time_limit_s)
      : 0;
  return (
    <Card className="min-w-0 space-y-5 p-6" data-component="QuizCard">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold text-primary-text">
            Question {question.order} of {total}
          </p>
          <p className="mt-2 text-xs text-muted-readable">
            {question.category.replaceAll("_", " ")} ·{" "}
            {question.type === "mcq"
              ? "Choose one answer"
              : "Explain in your own words"}
          </p>
        </div>
        {verify && (
          <div
            role="timer"
            aria-label={
              remaining == null
                ? "Remaining time unavailable"
                : `${remaining} seconds remaining`
            }
            className="relative size-24 shrink-0"
          >
            <svg
              viewBox="0 0 100 100"
              aria-hidden="true"
              className="size-full -rotate-90"
            >
              <circle
                cx="50"
                cy="50"
                r="42"
                fill="none"
                stroke="var(--surface-2)"
                strokeWidth="8"
              />
              <circle
                cx="50"
                cy="50"
                r="42"
                fill="none"
                stroke="var(--primary)"
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={`${fraction * circumference} ${circumference}`}
              />
            </svg>
            <span
              aria-hidden="true"
              className="absolute inset-0 flex items-center justify-center text-lg font-semibold tabular-nums"
            >
              {remaining == null ? "?" : duration(remaining)}
            </span>
          </div>
        )}
      </div>
      <ol aria-label="Question progress" className="flex flex-wrap gap-2">
        {Array.from({ length: Math.min(total, 10) }, (_, i) => (
          <li
            key={i}
            aria-current={i + 1 === question.order ? "step" : undefined}
            className={`size-2.5 rounded-full ${i + 1 <= question.order ? "bg-primary" : "bg-border"}`}
          >
            <span className="sr-only">
              Question {i + 1}
              {i + 1 === question.order ? ", current" : ""}
            </span>
          </li>
        ))}
      </ol>
      <h2
        ref={heading}
        tabIndex={-1}
        className="break-anywhere text-lg font-semibold leading-relaxed outline-none"
      >
        {question.prompt}
      </h2>
      {question.code_snippet && <CodeSnippet snippet={question.code_snippet} />}

      {unavailable && (
        <div role="alert" className="space-y-3 text-sm">
          <p className="text-warning-readable">
            The service did not return remaining time. Refresh to continue with
            the server timer.
          </p>
          <Button variant="outline" onClick={onRefresh}>
            Refresh timing
          </Button>
        </div>
      )}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
        className="space-y-4"
      >
        {question.type === "mcq" ? (
          <fieldset disabled={disabled} className="space-y-3">
            <legend className="mb-3 text-xs font-semibold">Your answer</legend>
            {question.options?.length ? (
              question.options.map((option) => (
                <label
                  key={option.id}
                  className={`flex min-h-14 cursor-pointer items-start gap-3 rounded-control border p-4 text-sm leading-relaxed transition-colors focus-within:ring-2 focus-within:ring-primary ${choice === option.id ? "border-primary bg-primary/5" : "border-border bg-surface-2 hover:border-primary"} ${disabled ? "cursor-not-allowed opacity-70" : ""}`}
                >
                  <input
                    type="radio"
                    name={`answer-${question.id}`}
                    value={option.id}
                    checked={choice === option.id}
                    onChange={() => setChoice(option.id)}
                    className="mt-1 size-4 shrink-0 accent-primary"
                  />
                  <span className="break-anywhere">{option.text}</span>
                </label>
              ))
            ) : (
              <p role="alert" className="text-sm text-warning-readable">
                No answer options were returned. Refresh the question.
              </p>
            )}
          </fieldset>
        ) : (
          <div>
            <label
              htmlFor={`answer-${question.id}`}
              className="mb-3 block text-xs font-semibold"
            >
              Your answer
            </label>
            <textarea
              id={`answer-${question.id}`}
              value={text}
              onChange={(e) => setText(e.target.value)}
              maxLength={2000}
              rows={7}
              disabled={disabled}
              onPaste={(e) => {
                if (verify) {
                  e.preventDefault();
                  setPasteNotice(true);
                }
              }}
              className="w-full resize-y rounded-control border border-border bg-surface-2 p-4 text-sm leading-relaxed outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-70"
              aria-describedby={`answer-help-${question.id}`}
            />
            <p
              id={`answer-help-${question.id}`}
              className="mt-2 text-xs text-muted-readable"
            >
              {text.length}/2000 characters. Graded on understanding, not
              English.
            </p>
          </div>
        )}
        {pasteNotice && (
          <p role="status" className="text-xs text-warning-readable">
            Paste is disabled in verify mode. Write your answer in your own
            words.
          </p>
        )}
        {!verify && question.hint && (
          <div>
            <Button
              type="button"
              variant="ghost"
              className="min-h-11"
              onClick={() => setHint((v) => !v)}
              aria-expanded={hint}
            >
              {hint ? "Hide hint" : "Show hint"}
            </Button>
            {hint && (
              <p className="mt-2 rounded-control bg-surface-2 p-4 text-sm text-muted-readable">
                {question.hint}
              </p>
            )}
          </div>
        )}
        {verify && (
          <p className="text-xs leading-relaxed text-muted-readable">
            One question at a time, with no going back. Leaving the tab is
            recorded for your review and does not affect your score.
          </p>
        )}
        {error ? (
          <div role="alert" className="space-y-3">
            <p className="text-sm text-danger-readable">{error}</p>
            <p className="text-xs text-muted-readable">
              Your answer is held while we check whether it was already
              recorded.
            </p>
            <Button
              type="button"
              variant="outline"
              className="min-h-11"
              onClick={() => void send(true)}
            >
              Retry answer
            </Button>
          </div>
        ) : (
          <Button
            type="submit"
            className="min-h-11"
            disabled={
              disabled ||
              (question.type === "mcq" && !choice) ||
              (question.type === "short_answer" && !text.trim())
            }
          >
            {pending ? "Recording answer…" : "Record answer"}
          </Button>
        )}
        {pending && (
          <p role="status" className="text-xs text-muted-readable">
            Recording your answer…
          </p>
        )}
      </form>
    </Card>
  );
}
