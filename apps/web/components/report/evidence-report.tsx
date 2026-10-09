"use client";
/* Hallmark · pre-emit critique: P4 H4 E4 S4 R5 V3 — DESIGN-locked evidence report. */
import { useState } from "react";
import Link from "next/link";
import { useListAnalyses } from "@/lib/api/hooks";
import { errorMessage } from "@/lib/api/transport";
import { LevelPill, ScoreRing } from "@/components/career";
import { safeUrl, type Schema } from "@/components/career/shared";
import { Button } from "@/components/ui/button";
import {
  PageHeader,
  Panel,
  Section,
  SelectRowGroup,
  TextLink,
} from "@/components/layout/page";
import { ReportOverview, RoleReasons } from "./report-overview";
import { ProjectCard } from "./project-card";
import { WhatIfPanel } from "./what-if-panel";
import { QuizHistory } from "@/components/quiz/quiz-history";
const levels = ["strong", "moderate", "weak", "unverified", "missing"] as const;

function ClaimDetail({
  claim,
  evidence,
}: {
  claim: Schema["SkillClaim"];
  evidence: Schema["Evidence"][];
}) {
  return (
    <div data-component="EvidenceRow">
      <p className="text-xs font-medium text-text">
        {claim.skill_name}
        {claim.claimed ? "" : " (not claimed on the resume)"}
      </p>
      <p className="mt-2 text-sm leading-relaxed text-muted-readable">
        {claim.reason}
      </p>
      {claim.evidence_ids.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1">
          {claim.evidence_ids.map((id) => {
            const item = evidence.find((e) => e.id === id);
            const href = safeUrl(item?.url);
            return (
              <li key={id} className="min-w-0 text-xs">
                {href ? (
                  <span className="inline-flex min-h-11 max-w-full items-center">
                    <TextLink href={href} external>
                      <span className="break-anywhere">{item?.label}</span>
                    </TextLink>
                  </span>
                ) : (
                  <span className="text-muted-readable">
                    {item?.label || `Evidence reference: ${id}`}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

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
  const [picked, setPicked] = useState<string | null>(null);
  const claims = report.claims.filter(
    (claim) => level === "all" || claim.level === level,
  );
  const selected = claims.find((c) => c.skill_id === picked) ?? claims[0];
  return (
    <div>
      <PageHeader
        eyebrow="Your analysis, explained"
        title="Evidence report"
        description="Claims, projects and the evidence behind this assessment."
        actions={
          <>
            <Button
              variant="outline"
              className="min-h-11"
              onClick={onRefresh}
              disabled={refreshing}
            >
              {refreshing ? "Refreshing…" : "Refresh report"}
            </Button>
            <Button asChild className="min-h-11" trailingArrow>
              <Link href="/onboarding">New analysis</Link>
            </Button>
          </>
        }
      />
      {error && (
        <p
          role="alert"
          className="mb-6 rounded-control border border-danger bg-surface p-4 text-sm text-danger-readable"
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
          className="mt-6 flex flex-wrap items-center gap-3 rounded-control border border-danger p-4 text-xs"
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
      <Section
        id="claims"
        className="mt-8"
        eyebrow="Skills"
        title="Claims and evidence"
        description={`${claims.length} of ${report.claims.length} claims shown. Select a skill to see the reason and its sources. Levels come from the analysis.`}
        actions={
          <div>
            <label htmlFor="claim-level" className="field-label">
              Evidence level
            </label>
            <select
              id="claim-level"
              className="field max-w-full"
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
        }
      >
        {claims.length > 0 ? (
          <SelectRowGroup
            label="Skill claims"
            items={claims.map((claim) => ({
              id: claim.skill_id,
              title: claim.skill_name,
              secondary: claim.claimed
                ? `${claim.evidence_ids.length} evidence item${claim.evidence_ids.length === 1 ? "" : "s"}`
                : "Not claimed on the resume",
              status: <LevelPill level={claim.level} variant="text" />,
            }))}
            selectedId={selected?.skill_id}
            onSelect={setPicked}
            detail={
              selected ? (
                <ClaimDetail claim={selected} evidence={report.evidence} />
              ) : null
            }
          />
        ) : (
          <p className="inset-note">
            {report.claims.length
              ? "No claims match this evidence level."
              : "No skill claims were returned."}
          </p>
        )}
      </Section>
      <Section
        eyebrow="Work"
        title="Project review"
        description="Each project is reviewed on what the code and its history show. A low-evidence project is one the analysis could not back up yet."
      >
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
          <p className="inset-note">No projects were available for review.</p>
        )}
      </Section>
      <div className="app-section">
        <QuizHistory profileId={analysis.profile_id} />
      </div>
      <Section eyebrow="Roles" title="Role fit">
        <div className="grid items-start gap-4 md:grid-cols-2 xl:grid-cols-3">
          {report.role_fits.map((role) => (
            <Panel key={role.role_id} title={role.role_name}>
              <div className="space-y-3">
                <ScoreRing
                  value={role.score}
                  label={`${role.role_name} fit`}
                  size={144}
                />
                <RoleReasons role={role} />
              </div>
            </Panel>
          ))}
        </div>
        {!report.role_fits.length && (
          <p className="text-sm text-muted-readable">
            No role-fit results were returned.
          </p>
        )}
      </Section>
      <WhatIfPanel
        key={`${analysis.id}-${JSON.stringify(report.score)}`}
        analysisId={analysis.id}
        report={report}
      />
    </div>
  );
}
