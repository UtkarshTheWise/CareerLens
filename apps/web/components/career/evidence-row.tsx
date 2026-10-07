import { ArrowUpRight, FileCheck } from "lucide-react";
import { LevelPill } from "./badges";
import { safeUrl, type Schema } from "./shared";
export function EvidenceRow({
  claim,
  evidence,
}: {
  claim: Schema["SkillClaim"];
  evidence: Schema["Evidence"][];
}) {
  return (
    <div
      data-component="EvidenceRow"
      className="grid min-w-0 gap-3 border-t border-border py-4 first:border-t-0 sm:grid-cols-[minmax(120px,1fr)_minmax(0,2fr)]"
    >
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="text-sm font-semibold">{claim.skill_name}</h3>
        <LevelPill level={claim.level} />
      </div>
      <div className="min-w-0">
        <p className="text-sm leading-relaxed text-muted-readable">
          {claim.reason}
        </p>
        <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
          {claim.evidence_ids.map((id) => {
            const item = evidence.find((e) => e.id === id);
            const href = safeUrl(item?.url);
            return (
              <li key={id} className="min-w-0 text-xs">
                {href ? (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex min-h-11 max-w-full items-center gap-2 text-primary-text underline underline-offset-4"
                  >
                    <ArrowUpRight size={16} aria-hidden="true" />
                    <span className="truncate">{item?.label}</span>
                    <span className="sr-only"> (opens in new tab)</span>
                  </a>
                ) : (
                  <span className="inline-flex items-center gap-2 text-muted-readable">
                    <FileCheck size={14} aria-hidden="true" />
                    {item?.label || `Evidence reference: ${id}`}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
