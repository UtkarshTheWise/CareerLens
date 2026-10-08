"use client";
import { CircleHelp, ArrowUpRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover";
import { number, signed, safeUrl, type Schema } from "./shared";
export function WhyPopover({
  label,
  reasons,
  evidence = [],
  definition,
  components,
}: {
  label: string;
  reasons?: Schema["ScoreComponent"]["reasons"];
  evidence?: Schema["Evidence"][];
  definition?: string;
  components?: Schema["ScoreComponent"][];
}) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          data-component="WhyPopover"
          variant="ghost"
          className="min-h-11 gap-2 rounded-control px-3 text-xs text-muted-readable active:translate-y-px"
          aria-label={`Why ${label}?`}
        >
          <CircleHelp size={16} aria-hidden="true" />
          Why?
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        sideOffset={8}
        className="max-h-[min(70vh,480px)] w-[min(380px,calc(100vw-32px))] overflow-y-auto rounded-card border-border bg-surface p-5 text-text shadow-card"
        aria-label={`${label} explanation`}
      >
        <h3 className="text-sm font-semibold">{label}</h3>
        {definition && (
          <p className="mt-3 text-sm leading-relaxed text-muted-readable">
            {definition}
          </p>
        )}
        {reasons && (
          <>
            <p className="mt-2 text-xs text-muted-readable">
              Points shown belong to this component, as returned by the
              analysis.
            </p>
            <ul className="mt-4 space-y-4">
              {reasons.map((reason, index) => (
                <li key={index} className="border-t border-border pt-3">
                  <div className="flex items-start gap-3">
                    <p className="min-w-0 flex-1 text-sm leading-relaxed">
                      {reason.text}
                    </p>
                    <span
                      className={`shrink-0 text-xs font-semibold tabular-nums ${reason.delta < 0 ? "text-danger-readable" : "text-success-readable"}`}
                    >
                      {signed(reason.delta)} pts
                    </span>
                  </div>
                  {!!reason.evidence_ids?.length && (
                    <ul className="mt-2 space-y-1">
                      {reason.evidence_ids.map((id) => {
                        const item = evidence.find((e) => e.id === id);
                        const href = safeUrl(item?.url);
                        return (
                          <li key={id} className="text-xs text-muted-readable">
                            {href ? (
                              <a
                                href={href}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex min-h-11 items-center gap-1 text-primary-text underline underline-offset-4"
                              >
                                {item?.label}
                                <ArrowUpRight size={12} aria-hidden="true" />
                                <span className="sr-only">
                                  {" "}
                                  (opens in new tab)
                                </span>
                              </a>
                            ) : (
                              item?.label || `Evidence reference: ${id}`
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
            {reasons.length === 0 && (
              <p className="mt-3 text-sm text-muted-readable">
                No reasons were supplied for this component.
              </p>
            )}
          </>
        )}
        {components && (
          <div className="mt-4 space-y-4">
            {components.map((component) => (
              <details
                key={component.key}
                className="border-t border-border pt-2"
              >
                <summary className="min-h-11 cursor-pointer py-3 text-sm font-semibold">
                  {component.label}
                  <span className="ml-2 text-xs font-normal tabular-nums text-muted-readable">
                    {number(component.contribution)} readiness pts
                  </span>
                </summary>
                <p className="mb-3 text-xs text-muted-readable">
                  Component score:{" "}
                  {component.score === null
                    ? "no data"
                    : number(component.score)}{" "}
                  / 100 · effective weight: {number(component.weight * 100)}%
                </p>
                <ul className="space-y-3">
                  {component.reasons.map((reason, index) => (
                    <li key={index}>
                      <p className="text-sm leading-relaxed">{reason.text}</p>
                      <p
                        className={`mt-1 text-xs tabular-nums ${reason.delta < 0 ? "text-danger-readable" : "text-success-readable"}`}
                      >
                        {signed(reason.delta)} component pts
                      </p>
                      <ul className="mt-1 space-y-1">
                        {reason.evidence_ids?.map((id) => {
                          const item = evidence.find((e) => e.id === id);
                          const href = safeUrl(item?.url);
                          return (
                            <li
                              key={id}
                              className="text-xs text-muted-readable"
                            >
                              {href ? (
                                <a
                                  href={href}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex min-h-11 items-center text-primary-text underline underline-offset-4"
                                >
                                  {item?.label}
                                  <span className="sr-only">
                                    {" "}
                                    (opens in new tab)
                                  </span>
                                </a>
                              ) : (
                                item?.label || `Evidence reference: ${id}`
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    </li>
                  ))}
                </ul>
                {component.reasons.length === 0 && (
                  <p className="text-xs text-muted-readable">
                    No reasons supplied.
                  </p>
                )}
              </details>
            ))}
          </div>
        )}
        {!definition && !reasons && !components && (
          <p className="mt-3 text-sm text-muted-readable">
            An explanation is not available yet.
          </p>
        )}
        <span className="sr-only">
          {reasons ? `${number(reasons.length)} reasons` : "Definition"}
        </span>
      </PopoverContent>
    </Popover>
  );
}
