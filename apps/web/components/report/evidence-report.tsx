"use client";
/* Hallmark · pre-emit critique: P4 H4 E4 S4 R5 V3 — DESIGN-locked evidence report. */
import { useState } from "react";
import Link from "next/link";
import { useListAnalyses } from "@/lib/api/hooks";
import { errorMessage } from "@/lib/api/transport";
import { EvidenceRow, ScoreRing } from "@/components/career";
import type { Schema } from "@/components/career/shared";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ReportOverview, RoleReasons } from "./report-overview";
import { ProjectCard } from "./project-card";
import { WhatIfPanel } from "./what-if-panel";
const levels = ["strong", "moderate", "weak", "unverified", "missing"] as const;
export function EvidenceReport({
  analysis,
  report,
  onRefresh,
  refreshing,
  error,
}: {
  analysis: Schema["Analysis"];
  report: Schema["AnalysisReport"];
  onRefresh: () => void;
  refreshing: boolean;
  error?: string;
}) {
  const summaries = useListAnalyses(
    { profile_id: analysis.profile_id },
    { staleTime: 0 },
  );
  const verified = summaries.data?.find(
    (item) => item.id === analysis.id,
  )?.verified_skills;
  const [level, setLevel] = useState<"all" | Schema["EvidenceLevel"]>("all");
  const claims = report.claims.filter(
    (claim) => level === "all" || claim.level === level,
  );
  return (
    <section className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="mb-2 text-xs font-semibold text-primary-text">
            Your analysis, explained
          </p>
          <h1 className="text-2xl font-semibold">Evidence report</h1>
          <p className="mt-3 text-sm text-muted-readable">
            Claims, projects and the evidence behind this assessment.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            className="min-h-11"
            onClick={onRefresh}
            disabled={refreshing}
          >
            {refreshing ? "Refreshing…" : "Refresh report"}
          </Button>
          <Button asChild className="min-h-11">
            <Link href="/onboarding">New analysis</Link>
          </Button>
        </div>
      </div>
      {error && (
        <p
          role="alert"
          className="rounded-control border border-danger bg-surface p-4 text-sm text-danger-readable"
        >
          {error}
        </p>
      )}
      <ReportOverview
        report={report}
        verifiedSkills={verified}
        analysisId={analysis.id}
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
          className="flex flex-wrap items-center gap-3 rounded-control border border-danger p-4 text-xs"
        >
          <p>{errorMessage(summaries.error)}</p>
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
      <section id="claims" className="space-y-4">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">Claims and evidence</h2>
            <p className="mt-2 text-xs text-muted-readable">
              {claims.length} of {report.claims.length} claims shown. Levels
              come from the analysis.
            </p>
          </div>
          <div>
            <label
              htmlFor="claim-level"
              className="mb-2 block text-xs font-medium"
            >
              Evidence level
            </label>
            <select
              id="claim-level"
              className="min-h-11 max-w-full rounded-control border border-border bg-surface px-3 text-sm"
              value={level}
              onChange={(e) => setLevel(e.target.value as typeof level)}
            >
              <option value="all">All levels</option>
              {levels.map((value) => (
                <option key={value} value={value}>
                  {value.charAt(0).toUpperCase() + value.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="space-y-3">
          {claims.map((claim) => (
            <EvidenceRow
              key={claim.skill_id}
              claim={claim}
              evidence={report.evidence}
            />
          ))}
          {!claims.length && (
            <p className="rounded-card border border-border bg-surface p-6 text-sm text-muted-readable">
              {report.claims.length
                ? "No claims match this evidence level."
                : "No skill claims were returned."}
            </p>
          )}
        </div>
      </section>
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Project review</h2>
        <div className="grid items-start gap-4 xl:grid-cols-2">
          {report.projects.map((project) => (
            <ProjectCard
              key={project.project_id}
              project={project}
              analysisId={analysis.id}
            />
          ))}
        </div>
        {!report.projects.length && (
          <p className="rounded-card bg-surface p-6 text-sm text-muted-readable">
            No projects were available for review.
          </p>
        )}
      </section>
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Role fit</h2>
        <div className="grid items-start gap-4 md:grid-cols-2 xl:grid-cols-3">
          {report.role_fits.map((role) => (
            <Card key={role.role_id} className="py-0">
              <CardContent className="space-y-3 p-6">
                <h3 className="text-sm font-semibold">{role.role_name}</h3>
                <ScoreRing
                  value={role.score}
                  label={`${role.role_name} fit`}
                  size={144}
                />
                <RoleReasons role={role} />
              </CardContent>
            </Card>
          ))}
        </div>
        {!report.role_fits.length && (
          <p className="text-sm text-muted-readable">
            No role-fit results were returned.
          </p>
        )}
      </section>
      <WhatIfPanel
        key={`${analysis.id}-${JSON.stringify(report.score)}`}
        analysisId={analysis.id}
        report={report}
      />
    </section>
  );
}
