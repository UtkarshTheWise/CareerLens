import type { Schema } from "./shared";
const states = {
  demonstrated: { label: "Verified understanding", tone: "tone-success" },
  partial: { label: "Partial", tone: "tone-warning" },
  not_demonstrated: { label: "Review needed", tone: "tone-danger-outline" },
  not_taken: { label: "Not taken", tone: "tone-muted" },
} satisfies Record<Schema["Understanding"], { label: string; tone: string }>;
export function UnderstandingBadge({
  understanding = "not_taken",
}: {
  understanding?: Schema["Understanding"];
}) {
  const state = states[understanding];
  return (
    <span
      data-component="UnderstandingBadge"
      className={`status-pill ${state.tone}`}
      aria-label={`Project understanding: ${state.label}`}
    >
      {state.label}
    </span>
  );
}
