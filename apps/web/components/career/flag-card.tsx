import { Flag } from "lucide-react";
import { CardFrame, signed, type Schema } from "./shared";
const names: Record<Schema["ProjectFlag"]["code"], string> = {
  single_dump: "Commit history",
  unmodified_fork: "Unmodified fork",
  default_readme: "Starter README",
  tutorial_pattern: "Project depth",
  thin_wrapper: "Project scope",
  claim_mismatch: "Claim evidence",
  vague_description: "Project description",
  understanding_gap: "Understanding not demonstrated yet",
};
export function FlagCard({ flag }: { flag: Schema["ProjectFlag"] }) {
  return (
    <CardFrame data-component="FlagCard">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="icon-chip text-warning-readable">
          <Flag size={20} strokeWidth={1.75} aria-hidden="true" />
        </span>
        <span
          className={`status-pill ${flag.severity === "high" ? "tone-danger-outline" : flag.severity === "medium" ? "tone-warning" : "tone-muted"}`}
        >
          {flag.severity} severity
        </span>
      </div>
      <h2>{names[flag.code]}</h2>
      <p className="text-sm leading-relaxed text-muted-readable">
        {flag.reason}
      </p>
      <div className="rounded-control bg-surface-2 p-4">
        <h3 className="text-xs font-semibold">How to fix</h3>
        <p className="mt-2 text-sm leading-relaxed">{flag.fix}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span className="status-pill tone-success">
          {signed(flag.estimated_gain)} pts
        </span>
        <span className="text-xs text-muted-readable">
          Estimated gain if resolved
        </span>
      </div>
    </CardFrame>
  );
}
