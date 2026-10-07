"use client";
import Link from "next/link";
import { BadgeCheck, Target } from "lucide-react";
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
import { Card, CardContent } from "@/components/ui/card";
export const coverageDefinition =
  "Evidence Coverage is the percentage of claimed skills with strong or moderate evidence.";
export function RoleReasons({ role }: { role: Schema["RoleFit"] }) {
  return (
    <details className="w-full text-xs">
      <summary className="min-h-11 cursor-pointer py-3 text-primary-text">
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
  return (
    <div className="space-y-4">
      <div className="grid items-stretch gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="py-0">
          <CardContent className="space-y-3 p-6">
            <h2 className="text-xs font-medium text-muted-readable">
              Job Readiness
            </h2>
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
              <BandBadge band={report.score.band} />
              <span className="status-pill tone-muted">
                {report.score.confidence} confidence
              </span>
            </div>
            {report.score.capped && (
              <p className="text-xs leading-relaxed text-muted-readable">
                A score cap was applied. Review the analysis notes below.
              </p>
            )}
          </CardContent>
        </Card>
        <Card className="py-0">
          <CardContent className="p-6">
            <h2 className="mb-3 text-xs font-medium text-muted-readable">
              Evidence Coverage
            </h2>
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
          </CardContent>
        </Card>
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
              <Link
                href={`/report/${encodeURIComponent(analysisId)}#claims`}
                className="inline-flex min-h-11 items-center text-primary-text underline underline-offset-4"
              >
                View evidence
              </Link>
            </div>
          }
        />
        <Card className="py-0">
          <CardContent className="space-y-3 p-6">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-xs font-medium text-muted-readable">
                Top role fit
              </h2>
              <span className="icon-chip text-primary-text">
                <Target size={20} strokeWidth={1.75} aria-hidden="true" />
              </span>
            </div>
            {role ? (
              <>
                <p className="text-sm font-semibold">{role.role_name}</p>
                <ScoreRing value={role.score} label="Role fit" size={144} />
                <RoleReasons role={role} />
              </>
            ) : (
              <p className="py-8 text-sm text-muted-readable">
                No role-fit results were returned.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
      <Card className="py-0">
        <CardContent className="p-6">
          <div className="mb-6">
            <h2 className="text-base font-semibold">Why this score</h2>
            <p className="mt-2 text-xs text-muted-readable">
              Effective weights and contributions from this analysis. Open each
              explanation to see its evidence.
            </p>
          </div>
          <div className="grid items-start gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
            <SegmentedGauge
              label="Effective score weights"
              segments={report.score.components.map((component) => ({
                label: component.label,
                value: component.weight * 100,
              }))}
            />
            <div className="min-w-0 space-y-3">
              {report.score.components.map((component) => (
                <div
                  key={component.key}
                  className="rounded-control border border-border p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-semibold">{component.label}</h3>
                    <WhyPopover
                      label={component.label}
                      reasons={component.reasons}
                      evidence={report.evidence}
                    />
                  </div>
                  <dl className="mt-2 grid grid-cols-3 gap-2 text-xs">
                    <div>
                      <dt className="text-muted-readable">Score</dt>
                      <dd className="mt-1 font-semibold tabular-nums">
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
        </CardContent>
      </Card>
      {report.notes.length > 0 && (
        <section
          aria-label="Analysis notes"
          className="rounded-card border border-border bg-surface-2 p-6"
        >
          <h2 className="text-sm font-semibold">
            What this analysis could see
          </h2>
          <ul className="mt-3 space-y-2 text-sm leading-relaxed text-muted-readable">
            {report.notes.map((note, i) => (
              <li key={i}>{note}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
