import type { ReactNode } from "react";
import type { components } from "@careerlens/api-client";
import { CircleAlert, Search } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
export type Schema = components["schemas"];
export type ViewState = "ready" | "loading" | "empty" | "error";
export const number = (value: number) =>
  new Intl.NumberFormat("en", { maximumFractionDigits: 1 }).format(value);
export const signed = (value: number) =>
  `${value > 0 ? "+" : value < 0 ? "−" : ""}${number(Math.abs(value))}`;
export function safeUrl(value?: string | null) {
  try {
    const url = new URL(value || "");
    return ["http:", "https:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}
export function CardFrame({
  children,
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <Card
      className={cn(
        "min-w-0 gap-4 rounded-card border-border bg-surface p-6 text-text shadow-card",
        className,
      )}
      {...props}
    >
      {children}
    </Card>
  );
}
export function CardState({
  state,
  message,
  children,
}: {
  state: ViewState;
  message?: string;
  children: ReactNode;
}) {
  if (state === "ready") return children;
  if (state === "loading")
    return (
      <div
        role="status"
        aria-label="Loading component"
        className="space-y-4 py-4"
      >
        <Skeleton className="h-8 w-24" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <span className="sr-only">Loading</span>
      </div>
    );
  const Icon = state === "error" ? CircleAlert : Search;
  return (
    <div
      role={state === "error" ? "alert" : undefined}
      className="flex min-h-32 flex-col items-start justify-center gap-3 text-sm"
    >
      <span className="icon-chip">
        <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
      </span>
      <p className="font-medium">
        {state === "error" ? "Couldn’t load this view" : "No data yet"}
      </p>
      <p className="text-muted-readable">
        {message ||
          (state === "error"
            ? "Try again when your connection is restored."
            : "Data will appear after an analysis is available.")}
      </p>
    </div>
  );
}
