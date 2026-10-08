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
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
function EmptyDashboard() {
  return (
    <div className="space-y-5 rounded-card border border-border bg-surface p-6">
      <h1 className="text-2xl font-semibold">Your work, in focus.</h1>
      <p className="max-w-xl text-sm leading-relaxed text-muted-readable">
        Start an analysis to connect your resume and projects to the role you
        want.
      </p>
      <Button asChild className="min-h-11">
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
  if (me.isPending || (id && analysis.isPending))
    return (
      <section className="space-y-5">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
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
        <h1 className="text-2xl font-semibold">Dashboard unavailable</h1>
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
    <section className="space-y-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="mb-2 text-xs font-semibold text-primary-text">
            Your latest analysis
          </p>
          <h1 className="text-2xl font-semibold">Your work, in focus.</h1>
          <p className="mt-3 text-sm text-muted-readable">
            A clearer picture of your skills, backed by the work you’ve done.
          </p>
        </div>
        <Button asChild variant="outline" className="min-h-11">
          <Link href={`/report/${encodeURIComponent(id)}`}>
            Open evidence report
          </Link>
        </Button>
      </div>
      {analysis.isError && (
        <div
          role="alert"
          className="space-y-3 rounded-control border border-danger p-4 text-sm"
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
          className="space-y-3 rounded-control border border-danger p-4 text-sm"
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
      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <div className="space-y-4">
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
          <Card className="py-0">
            <CardContent className="p-6">
              <h2 className="text-base font-semibold">Top gaps to work on</h2>
              <div className="mt-4 space-y-3">
                {report.gaps.slice(0, 3).map((gap) => (
                  <div
                    key={gap.gap_id}
                    className="space-y-2 rounded-control border border-border p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="text-sm font-semibold">
                        {gap.skill_name}
                      </h3>
                      <LevelPill level={gap.level} />
                    </div>
                    <p className="text-xs text-muted-readable">
                      {gap.claimed
                        ? "Claimed skill needs stronger evidence."
                        : "Not claimed for this target role."}
                    </p>
                    <p className="text-xs font-medium text-success-readable">
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
            </CardContent>
          </Card>
        </div>
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold">Your next milestone</h2>
            <Link
              href="/roadmap"
              className="inline-flex min-h-11 items-center whitespace-nowrap text-xs text-primary-text underline underline-offset-4"
            >
              Full roadmap
            </Link>
          </div>
          {next ? (
            <>
              <MilestoneCard milestone={next} disabled />
              <p className="text-xs text-muted-readable">
                Suggested next step from this analysis.
              </p>
            </>
          ) : (
            <p className="rounded-card bg-surface p-6 text-sm text-muted-readable">
              {report.roadmap.length
                ? "All supplied milestones are marked complete."
                : "No roadmap milestones were returned."}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
