"use client";
import { useId } from "react";
import {
  ArrowUpRight,
  Clock3,
  LoaderCircle,
  Check,
  CircleAlert,
} from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { CardFrame, safeUrl, signed, type Schema } from "./shared";
export function MilestoneCard({
  milestone,
  onDoneChange,
  saving = false,
  error,
  disabled = false,
  onRetry,
}: {
  milestone: Schema["RoadmapMilestone"];
  onDoneChange?: (done: boolean) => void;
  saving?: boolean;
  error?: string;
  disabled?: boolean;
  onRetry?: () => void;
}) {
  const id = useId();
  const messageId = `${id}-status`;
  return (
    <CardFrame data-component="MilestoneCard" aria-busy={saving}>
      <div className="flex items-start justify-between gap-3">
        <span className="icon-chip text-sm font-semibold text-primary-text">
          {milestone.order}
        </span>
        <span className="status-pill tone-success">
          {signed(milestone.estimated_gain)} pts
        </span>
      </div>
      <h2>{milestone.title}</h2>
      <p className="text-sm leading-relaxed text-muted-readable">
        {milestone.deliverable}
      </p>
      <ul className="space-y-1">
        {milestone.resources.map((resource) => {
          const href = safeUrl(resource.url);
          return (
            <li key={resource.id}>
              {href ? (
                <a
                  className="inline-flex min-h-11 max-w-full items-center gap-2 text-xs text-primary-text underline underline-offset-4"
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <ArrowUpRight size={14} aria-hidden="true" />
                  <span className="truncate">{resource.title}</span>
                  <span className="sr-only"> (opens in new tab)</span>
                </a>
              ) : (
                <span className="text-xs text-muted-readable">
                  {resource.title}
                </span>
              )}
            </li>
          );
        })}
      </ul>
      <p className="inline-flex items-center gap-2 text-xs text-muted-readable">
        <Clock3 size={14} aria-hidden="true" />
        {milestone.effort_hours} hours estimated effort
      </p>
      <div className="border-t border-border pt-2">
        <label
          htmlFor={id}
          className="flex min-h-11 cursor-pointer items-center gap-3 text-sm font-medium"
        >
          <Checkbox
            id={id}
            checked={milestone.done ?? false}
            disabled={disabled || saving || !onDoneChange}
            aria-invalid={!!error}
            aria-describedby={messageId}
            className="size-5 hover:border-primary active:scale-95"
            onCheckedChange={(checked) => onDoneChange?.(checked === true)}
          />
          {milestone.done ? "Completed" : "Mark as done"}
        </label>
        <div id={messageId} className="min-h-6 text-xs" aria-live="polite">
          {saving ? (
            <span className="inline-flex items-center gap-2 text-muted-readable">
              <LoaderCircle
                size={14}
                className="animate-spin"
                aria-hidden="true"
              />
              Saving milestone…
            </span>
          ) : error ? (
            <span
              role="alert"
              className="inline-flex items-start gap-2 text-danger-readable"
            >
              <CircleAlert size={14} aria-hidden="true" />
              {error}
            </span>
          ) : milestone.done ? (
            <span className="inline-flex items-center gap-2 text-success-readable">
              <Check size={14} aria-hidden="true" />
              Milestone completed
            </span>
          ) : (
            <span className="text-muted-readable">
              Complete the deliverable before checking it off.
            </span>
          )}
        </div>
        {error && onRetry && (
          <Button variant="outline" className="mt-2 min-h-11" onClick={onRetry}>
            Try again
          </Button>
        )}
      </div>
    </CardFrame>
  );
}
