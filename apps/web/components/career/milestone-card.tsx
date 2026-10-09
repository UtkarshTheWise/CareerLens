"use client";
import { useId } from "react";
import { LoaderCircle, Check, CircleAlert } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Disclosure, TextLink } from "@/components/layout/page";
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
    <CardFrame data-component="MilestoneCard" aria-busy={saving} className="tint-card hue-violet">
      <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-border pb-3 text-[11px] tracking-[.025em] text-muted-readable">
        <span>Milestone {milestone.order}</span>
        <span className="tabular-nums">{milestone.effort_hours} hours estimated effort</span>
      </div>
      <h2 className="text-[22px]! leading-[30px]! font-medium! tracking-[-.035em]!">
        {milestone.title}
      </h2>
      <p className="flex flex-wrap items-baseline gap-x-2 text-xs text-muted-readable">
        <span className="text-[13px] font-medium tabular-nums text-success-readable">
          Estimated gain {signed(milestone.estimated_gain)} pts
        </span>
        from this analysis
      </p>
      <Disclosure summary="Look at the deliverable">
        <p className="text-sm leading-relaxed text-muted-readable">
          {milestone.deliverable}
        </p>
        {milestone.resources.length > 0 && (
          <ul className="mt-3 space-y-1">
            {milestone.resources.map((resource) => {
              const href = safeUrl(resource.url);
              return (
                <li key={resource.id} className="min-w-0">
                  {href ? (
                    <span className="inline-flex min-h-11 max-w-full items-center">
                      <TextLink href={href} external>
                        <span className="break-anywhere">{resource.title}</span>
                      </TextLink>
                    </span>
                  ) : (
                    <span className="text-xs text-muted-readable">
                      {resource.title}
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </Disclosure>
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
