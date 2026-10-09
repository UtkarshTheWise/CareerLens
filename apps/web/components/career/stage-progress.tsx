import { Check, Circle, CircleAlert, LoaderCircle } from "lucide-react";
import type { Schema } from "./shared";
const stages = [
  "queued",
  "ingesting",
  "extracting",
  "collecting",
  "detecting",
  "judging",
  "scoring",
  "planning",
] as const satisfies readonly Schema["AnalysisStage"][];
const labels: Record<Schema["AnalysisStage"], string> = {
  queued: "Queued",
  ingesting: "Reading documents",
  extracting: "Extracting claims",
  collecting: "Collecting evidence",
  detecting: "Checking skills",
  judging: "Reviewing projects",
  scoring: "Calculating readiness",
  planning: "Building your roadmap",
  done: "Analysis complete",
  failed: "Analysis stopped",
};
export function StageProgress({
  status,
  progress,
  error,
  lastStage,
}: Pick<Schema["AnalysisStatus"], "status" | "progress" | "error"> & {
  lastStage?: (typeof stages)[number];
}) {
  const index = stages.findIndex(
    (stage) => stage === (status === "failed" ? lastStage : status),
  );
  return (
    <div data-component="StageProgress">
      <div className="mb-5 flex items-center justify-between gap-3">
        <h3 className="text-[17px] font-medium tracking-[-.02em]" aria-live="polite">
          {labels[status]}
        </h3>
        <span className="text-xs font-medium tabular-nums text-muted-readable">
          {progress}%
        </span>
      </div>
      <div
        role="progressbar"
        aria-label="Analysis progress"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        className="mb-6 h-1.5 overflow-hidden rounded-full bg-surface-2"
      >
        <div
          className="h-full rounded-full bg-primary"
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>
      <ol className="space-y-4">
        {stages.map((stage, step) => {
          const complete = status === "done" || (index >= 0 && step < index);
          const active = step === index && status !== "done";
          const failed = active && status === "failed";
          const Icon = complete
            ? Check
            : failed
              ? CircleAlert
              : active
                ? LoaderCircle
                : Circle;
          return (
            <li
              key={stage}
              className="flex items-center gap-3 text-sm"
              aria-current={active ? "step" : undefined}
            >
              <span
                className={`flex size-7 shrink-0 items-center justify-center rounded-full ${complete ? "tone-success" : failed ? "tone-danger-outline" : active ? "tone-primary" : "tone-muted"}`}
              >
                <Icon
                  size={14}
                  className={active && !failed ? "animate-spin" : ""}
                  aria-hidden="true"
                />
              </span>
              <span
                className={
                  active || complete ? "text-text" : "text-muted-readable"
                }
              >
                {labels[stage]}
              </span>
              <span className="sr-only">
                {" "}
                —{" "}
                {complete
                  ? "complete"
                  : failed
                    ? "failed"
                    : active
                      ? "in progress"
                      : "pending"}
              </span>
            </li>
          );
        })}
      </ol>
      {status === "failed" && (
        <p
          role="alert"
          className="mt-5 rounded-control border border-danger p-3 text-sm text-danger-readable"
        >
          {error || "The analysis could not finish. Please try again."}
        </p>
      )}
    </div>
  );
}
