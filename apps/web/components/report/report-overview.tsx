"use client";
import { BadgeCheck } from "lucide-react";
import {
  BandBadge,
  KpiCard,
  ScoreRing,
  SegmentedGauge,
  WhyPopover,
} from "@/components/career";
import {
  number,
  type Schema,
  type ViewState,
} from "@/components/career/shared";
import { Panel, TextLink } from "@/components/layout/page";
import { useReveal } from "@/lib/use-reveal";
export const coverageDefinition =
  "Evidence Coverage is the percentage of claimed skills with strong or moderate evidence.";
export function RoleReasons({ role }: { role: Schema["RoleFit"] }) {
  return (
    <details className="w-full text-xs">
      <summary className="text-link min-h-11 cursor-pointer py-3">
        Why this role?
      </summary>
      {role.reasons.length ? (
        <ul className="space-y-2 text-sm leading-relaxed text-muted-readable">
          {role.reasons.map((reason, i) => (
            <li key={i}>{reason}</li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-readable">
          No role-fit explanation was returned.
        </p>
      )}
      {role.top_missing.length > 0 && (
        <p className="mt-3 text-xs text-muted-readable">
          Missing skills: {role.top_missing.join(", ")}
        </p>
      )}
    </details>
  );
}
export function ReportOverview({
  report,
  verifiedSkills,
  analysisId,
  verifiedState = "ready",
  verifiedMessage,
}: {
  report: Schema["AnalysisReport"];
  verifiedSkills?: number | null;
  analysisId: string;
  verifiedState?: ViewState;
  verifiedMessage?: string;
}) {
  const role = [...report.role_fits].sort((a, b) => b.score - a.score)[0];
  const topRef = useReveal<HTMLDivElement>();
  const whyRef = useReveal<HTMLElement>();
  return (
    <div className="space-y-8">
      <div
        ref={topRef}
        className="reveal grid items-stretch gap-4 sm:grid-cols-2 xl:grid-cols-4"
      >
        <Panel
          label="Job Readiness"
          footer={
            <>
              <span>Confidence</span>
              <span data-value>{report.score.confidence}</span>
            </>
          }
        >
          <div className="space-y-3">
            <ScoreRing
              value={report.score.total}
              label="Readiness"
              band={report.score.band}
              explanation={
                <WhyPopover
                  label="Readiness"
                  components={report.score.components}
                  evidence={report.evidence}
                />
              }
            />
            <div className="flex flex-wrap justify-center gap-2">
              <BandBadge band={report.score.band} variant="text" />
            </div>
            {report.score.capped && (
              <p className="text-xs leading-relaxed text-muted-readable">
                A score cap was applied. Review the analysis notes below.
              </p>
            )}
          </div>
        </Panel>
        <Panel label="Evidence Coverage">
          <ScoreRing
            value={report.coverage}
            label="Coverage"
            explanation={
              <WhyPopover
                label="Evidence Coverage"
                definition={coverageDefinition}
              />
            }
          />
          <p className="mt-3 text-xs leading-relaxed text-muted-readable">
            Claimed skills backed by strong or moderate evidence.
          </p>
        </Panel>
        <KpiCard
          label="Verified skills"
          state={verifiedState}
          message={verifiedMessage}
          value={
            verifiedSkills === undefined || verifiedSkills === null
              ? "—"
              : number(verifiedSkills)
          }
          icon={BadgeCheck}
          explanation={
            <div className="space-y-3 text-xs text-muted-readable">
              <p>
                {verifiedSkills === undefined || verifiedSkills === null
                  ? "The analysis summary did not supply a verified-skill count."
                  : "Claimed skills marked strong or moderate in the analysis summary."}
              </p>
              <span className="inline-flex min-h-11 items-center">
                <TextLink
                  href={`/report/${encodeURIComponent(analysisId)}#claims`}
                >
                  View evidence
                </TextLink>
              </span>
            </div>
          }
        />
        <Panel label="Top role fit">
          {role ? (
            <div className="space-y-3">
              <p className="text-sm font-medium">{role.role_name}</p>
              <ScoreRing value={role.score} label="Role fit" size={144} />
              <RoleReasons role={role} />
            </div>
          ) : (
            <p className="py-8 text-sm text-muted-readable">
              No role-fit results were returned.
            </p>
          )}
        </Panel>
      </div>
      <section ref={whyRef} className="reveal app-section" aria-labelledby="why-score">
        <div className="mb-6">
          <p className="eyebrow mb-2">Explained</p>
          <h2 id="why-score" className="section-title">
            Why this score
          </h2>
          <p className="lede mt-2">
            Effective weights and contributions from this analysis. Open each
            explanation to see its evidence.
          </p>
        </div>
        <div className="grid items-start gap-8 lg:grid-cols-[240px_minmax(0,1fr)]">
          <SegmentedGauge
            label="Effective score weights"
            segments={report.score.components.map((component) => ({
              label: component.label,
              value: component.weight * 100,
            }))}
          />
          <div className="hairline-list min-w-0">
            {report.score.components.map((component) => (
              <div key={component.key} className="py-4 first:pt-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-sm font-medium">{component.label}</h3>
                  <WhyPopover
                    label={component.label}
                    reasons={component.reasons}
                    evidence={report.evidence}
                  />
                </div>
                <dl className="mt-2 grid grid-cols-3 gap-2 text-xs">
                  <div>
                    <dt className="text-muted-readable">Score</dt>
                    <dd className="mt-1 font-medium tabular-nums">
                      {component.score === null
                        ? "Unavailable"
                        : `${number(component.score)} / 100`}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-readable">Weight</dt>
                    <dd className="mt-1 tabular-nums">
                      {number(component.weight * 100)}%
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-readable">Contribution</dt>
                    <dd className="mt-1 tabular-nums">
                      {number(component.contribution)} pts
                    </dd>
                  </div>
                </dl>
              </div>
            ))}
            {!report.score.components.length && (
              <p className="text-sm text-muted-readable">
                No score breakdown was returned.
              </p>
            )}
          </div>
        </div>
      </section>
      {report.notes.length > 0 && (
        <section aria-label="Analysis notes" className="inset-note">
          <h2 className="text-sm font-medium text-text">
            What this analysis could see
          </h2>
          <ul className="mt-3 space-y-2 text-sm leading-relaxed">
            {report.notes.map((note, i) => (
              <li key={i}>{note}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
