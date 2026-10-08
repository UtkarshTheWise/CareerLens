import type { ReactNode } from "react";
import { ArrowDown, ArrowUp, Minus, type LucideIcon } from "lucide-react";
import { CardFrame, CardState, type ViewState } from "./shared";
export function KpiCard({
  label,
  value,
  icon: Icon,
  delta,
  explanation,
  state = "ready",
  message,
}: {
  label: string;
  value: ReactNode;
  icon: LucideIcon;
  delta?: {
    value: string;
    direction: "up" | "down" | "flat";
    sentiment: "positive" | "negative" | "neutral";
    period: string;
  };
  explanation?: ReactNode;
  state?: ViewState;
  message?: string;
}) {
  const DeltaIcon =
    delta?.direction === "down"
      ? ArrowDown
      : delta?.direction === "up"
        ? ArrowUp
        : Minus;
  return (
    <CardFrame data-component="KpiCard">
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-xs! font-medium! text-muted-readable">{label}</h2>
        <span className="icon-chip shrink-0 text-primary-text">
          <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
        </span>
      </div>
      <CardState state={state} message={message}>
        <div className="text-4xl font-semibold tracking-tight tabular-nums">
          {value ?? "—"}
        </div>
        {delta && (
          <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
            <span
              className={`inline-flex items-center gap-1 font-medium ${delta.sentiment === "positive" ? "text-success-readable" : delta.sentiment === "negative" ? "text-danger-readable" : "text-muted-readable"}`}
            >
              <DeltaIcon size={14} aria-hidden="true" />
              {delta.value}
              <span className="sr-only"> {delta.direction}</span>
            </span>
            <span className="text-muted-readable">{delta.period}</span>
          </p>
        )}
        {explanation && <div className="-ml-3">{explanation}</div>}
      </CardState>
    </CardFrame>
  );
}
