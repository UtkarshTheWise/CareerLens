"use client";
/* Hallmark · pre-emit critique: P4 H4 E4 S4 R5 V3 — DESIGN-locked student dashboard. */
import Link from "next/link";
import { useGetMe, useGetAnalysis, useListAnalyses } from "@/lib/api/hooks";
import { ApiError, errorMessage } from "@/lib/api/transport";
import { consistencyDatasets } from "@/lib/report-presentation";
import { ReportOverview } from "@/components/report/report-overview";
import { AnalysisProgress } from "@/components/analysis/analysis-progress";
import { LevelPill, MilestoneCard, TrendCard } from "@/components/career";
import { signed } from "@/components/career/shared";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader, Section, TextLink } from "@/components/layout/page";
import { useReveal } from "@/lib/use-reveal";
function EmptyDashboard() {
  return (
    <div>
      <PageHeader
        eyebrow="Your workspace"
        title="Your work, in focus."
        description="Start an analysis to connect your resume and projects to the role you want."
      />
      <Button asChild className="min-h-12" size="lg" trailingArrow>
        <Link href="/onboarding">Analyse a profile</Link>
      </Button>
    </div>
  );
}
export function StudentDashboard() {
  const me = useGetMe();
  const id = me.data?.latest_analysis_id;
  const analysis = useGetAnalysis(id ? { analysis_id: id } : undefined);
  const summaries = useListAnalyses(
    me.data && analysis.data?.status === "done"
      ? { profile_id: me.data.id }
      : undefined,
    { staleTime: 0 },
  );
  const lowerRef = useReveal<HTMLDivElement>();
  if (me.isPending || (id && analysis.isPending))
    return (
      <section className="space-y-5">
        <PageHeader eyebrow="Your workspace" title="Dashboard" />
        <div
          role="status"
          aria-label="Loading dashboard"
          className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
        >
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-60 rounded-card" />
          ))}
        </div>
        <Skeleton className="h-72 rounded-card" />
      </section>
    );
  if (me.isError) {
    if (me.error instanceof ApiError && me.error.status === 404)
      return <EmptyDashboard />;
    return (
      <section className="space-y-4">
        <PageHeader eyebrow="Your workspace" title="Dashboard unavailable" />
        <p role="alert" className="text-sm text-danger-readable">
          {errorMessage(me.error)}
        </p>
        <Button
          className="min-h-11"
          onClick={() => me.refetch()}
          disabled={me.isFetching}
        >
          Retry profile
        </Button>
      </section>
    );
  }
  if (!id) return <EmptyDashboard />;
  if (
    !analysis.data ||
    analysis.data.status !== "done" ||
    !analysis.data.report
  )
    return <AnalysisProgress analysisId={id} query={analysis} />;
  const report = analysis.data.report;
  const verified = summaries.data?.find(
    (item) => item.id === id,
  )?.verified_skills;
  const next = [...report.roadmap]
    .sort((a, b) => a.order - b.order)
    .find((milestone) => !milestone.done);
  return (
    <section>
      <PageHeader
        eyebrow="Your latest analysis"
        title="Your work, in focus."
        description="A clearer picture of your skills, backed by the work you’ve done."
        actions={
          <Button asChild variant="outline" className="min-h-11" trailingArrow>
            <Link href={`/report/${encodeURIComponent(id)}`}>
              Open evidence report
            </Link>
          </Button>
        }
      />
      {analysis.isError && (
        <div
          role="alert"
          className="mb-6 space-y-3 rounded-control border border-danger p-4 text-sm"
        >
          <p className="text-danger-readable">{errorMessage(analysis.error)}</p>
          <Button
            variant="outline"
            className="min-h-11"
            onClick={() => analysis.refetch()}
            disabled={analysis.isFetching}
          >
            Retry analysis
          </Button>
        </div>
      )}
      <ReportOverview
        report={report}
        verifiedSkills={verified}
        analysisId={id}
        verifiedState={
          summaries.isPending
            ? "loading"
            : summaries.isError
              ? "error"
              : verified == null
                ? "empty"
                : "ready"
        }
        verifiedMessage={
          summaries.isError
            ? errorMessage(summaries.error)
            : "No verified-skill count was returned."
        }
      />
      {summaries.isError && (
        <div
          role="alert"
          className="mt-6 space-y-3 rounded-control border border-danger p-4 text-sm"
        >
          <p className="text-danger-readable">
            {errorMessage(summaries.error)}
          </p>
          <Button
            variant="outline"
            className="min-h-11"
            onClick={() => summaries.refetch()}
            disabled={summaries.isFetching}
          >
            Retry summary
          </Button>
        </div>
      )}
      <div
        ref={lowerRef}
        className="reveal mt-2 grid items-start gap-x-12 gap-y-0 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]"
      >
        <div className="min-w-0">
          <Section className="xl:pt-8">
            <TrendCard
              title="Consistency over time"
              description={
                report.consistency
                  ? `${report.consistency.active_weeks} active weeks. Monthly/yearly totals group weeks by their start date.`
                  : "No contribution timeline was returned."
              }
              series={["Commits"]}
              datasets={consistencyDatasets(report.consistency?.weeks || [])}
              state={report.consistency?.weeks.length ? "ready" : "empty"}
              message="No contribution history is available for this analysis."
            />
          </Section>
          <Section eyebrow="Next" title="Top gaps to work on">
            <div className="hairline-list">
              {report.gaps.slice(0, 3).map((gap) => (
                <div
                  key={gap.gap_id}
                  className="hue-clay hue-rule my-3 space-y-1 py-1"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-medium">{gap.skill_name}</h3>
                    <LevelPill level={gap.level} variant="text" />
                  </div>
                  <p className="text-xs text-muted-readable">
                    {gap.claimed
                      ? "Claimed skill needs stronger evidence."
                      : "Not claimed for this target role."}
                  </p>
                  <p className="hue-sage hue-text text-xs font-medium tabular-nums">
                    Estimated gain: {signed(gap.estimated_gain)} pts
                  </p>
                </div>
              ))}
              {!report.gaps.length && (
                <p className="text-sm text-muted-readable">
                  No skill gaps were returned.
                </p>
              )}
            </div>
          </Section>
        </div>
        <Section
          className="min-w-0 xl:border-t-0 xl:pt-8"
          eyebrow="Roadmap"
          title="Your next milestone"
          actions={<TextLink href="/roadmap">Full roadmap</TextLink>}
        >
          {next ? (
            <div className="hue-citron space-y-3">
              <MilestoneCard milestone={next} disabled />
              <p className="text-xs text-muted-readable">
                Suggested next step from this analysis.
              </p>
            </div>
          ) : (
            <p className="inset-note">
              {report.roadmap.length
                ? "All supplied milestones are marked complete."
                : "No roadmap milestones were returned."}
            </p>
          )}
        </Section>
      </div>
    </section>
  );
}
