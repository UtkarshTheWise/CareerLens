import { CardFrame, signed, type Schema } from "./shared";
import { StatusText } from "@/components/layout/page";
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
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
        <span className="eyebrow">Low-evidence signal</span>
        <StatusText
          tone={
            flag.severity === "high"
              ? "danger"
              : flag.severity === "medium"
                ? "warning"
                : "muted"
          }
        >
          {flag.severity} severity
        </StatusText>
      </div>
      <h2 className="text-[17px]! font-medium! tracking-[-.02em]!">
        {names[flag.code]}
      </h2>
      <p className="text-sm leading-relaxed text-muted-readable">
        {flag.reason}
      </p>
      <div className="inset-note">
        <h3 className="text-xs font-medium text-text">How to fix</h3>
        <p className="mt-2 text-sm leading-relaxed text-text">{flag.fix}</p>
      </div>
      <p className="flex flex-wrap items-baseline gap-x-2 text-xs text-muted-readable">
        <span className="text-[13px] font-medium tabular-nums text-success-readable">
          {signed(flag.estimated_gain)} pts
        </span>
        Estimated gain if resolved
      </p>
    </CardFrame>
  );
}
