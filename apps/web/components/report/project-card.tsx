"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { FlagCard, UnderstandingBadge } from "@/components/career";
import { number, safeUrl, type Schema } from "@/components/career/shared";
import { useCreateQuiz } from "@/lib/api/hooks";
import { ApiError, errorMessage } from "@/lib/api/transport";
import { Button } from "@/components/ui/button";
import { Disclosure, Metric, TextLink } from "@/components/layout/page";
const codeParts = [
  { key: "hygiene", label: "Hygiene", max: 20 },
  { key: "engineering", label: "Engineering", max: 30 },
  { key: "authorship", label: "Authorship", max: 30 },
  { key: "depth", label: "Depth", max: 20 },
] as const;
const designParts = [
  { key: "problem_statement", label: "Problem statement", max: 25 },
  { key: "process_evidence", label: "Process evidence", max: 30 },
  { key: "outcome_or_metrics", label: "Outcome or metrics", max: 20 },
  { key: "tool_evidence", label: "Tool evidence", max: 15 },
  { key: "presentation", label: "Presentation", max: 10 },
] as const;
export function ProjectCard({
  project,
  analysisId,
}: {
  project: Schema["ProjectAudit"];
  analysisId: string;
}) {
  const quiz = useCreateQuiz();
  const router = useRouter();
  const lock = useRef(false);
  const [mode, setMode] = useState<Schema["QuizMode"]>();
  const href = safeUrl(project.url);
  const demo = safeUrl(project.demo_url);
  async function start(mode: Schema["QuizMode"]) {
    if (lock.current) return;
    lock.current = true;
    setMode(mode);
    try {
      const next = await quiz.mutateAsync({
        analysis_id: analysisId,
        body: { project_id: project.project_id, mode },
      });
      router.push(
        `/quiz/${encodeURIComponent(next.id)}?analysis=${encodeURIComponent(analysisId)}`,
      );
    } catch {
      lock.current = false;
      setMode(undefined);
    }
  }
  const retryAt =
    quiz.error instanceof ApiError
      ? quiz.error.details?.details?.retake_available_at
      : undefined;
  return (
    <article data-project-id={project.project_id} className="min-w-0 space-y-4">
      <div className="panel space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border pb-3">
          <div className="min-w-0">
            <p className="eyebrow mb-2">
              {project.kind === "design" ? "Design project" : "Code project"}
              {project.self_reported ? " · Link-based evidence" : ""}
            </p>
            <h3 className="break-words text-[17px] font-medium tracking-[-.02em]">
              {project.title}
            </h3>
          </div>
          <UnderstandingBadge understanding={project.understanding} />
        </div>
        {(href || demo) && (
          <div className="flex flex-wrap gap-x-5 gap-y-1">
            {href && (
              <span className="inline-flex min-h-11 items-center">
                <TextLink href={href} external>
                  {project.kind === "design"
                    ? "View portfolio"
                    : "View repository"}
                </TextLink>
              </span>
            )}
            {demo && (
              <span className="inline-flex min-h-11 items-center">
                <TextLink href={demo} external>
                  View demo
                </TextLink>
              </span>
            )}
          </div>
        )}
        <div>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="text-xs font-medium text-muted-readable">
              Project score
            </p>
            <Metric
              value={number(project.score)}
              unit="/ 100"
              className="text-[32px]!"
            />
          </div>
          <p className="mt-2 text-xs text-muted-readable">
            {project.counted_in_score
              ? "Included in the project-quality component."
              : "Not included among the selected projects for project quality."}
          </p>
          <Disclosure summary="How this project was scored" className="mt-2">
            <dl className="space-y-2 text-xs">
              {project.kind === "code" &&
                codeParts.map(({ key, label, max }) => (
                  <div
                    key={key}
                    className="flex flex-wrap justify-between gap-2"
                  >
                    <dt>{label}</dt>
                    <dd className="tabular-nums">
                      {project.subscores?.[key] === undefined
                        ? "Unavailable"
                        : `${number(project.subscores[key]!)} / ${max}`}
                    </dd>
                  </div>
                ))}
              {project.kind === "design" &&
                designParts.map(({ key, label, max }) => (
                  <div
                    key={key}
                    className="flex flex-wrap justify-between gap-2"
                  >
                    <dt>{label}</dt>
                    <dd className="tabular-nums">
                      {project.design_subscores?.[key] === undefined
                        ? "Unavailable"
                        : `${number(project.design_subscores[key]!)} / ${max}`}
                    </dd>
                  </div>
                ))}
            </dl>
            <p className="mt-3 text-xs text-muted-readable">
              Review the supplied project description, issues and flags below
              for the evidence behind this assessment.
            </p>
          </Disclosure>
        </div>
        <div>
          <h4 className="panel-label">What it does</h4>
          <p className="text-sm leading-relaxed text-muted-readable">
            {project.what_it_does || "No project description was returned."}
          </p>
        </div>
        <div>
          <h4 className="panel-label">Evidence-based description</h4>
          <p className="text-sm leading-relaxed text-muted-readable">
            {project.honest_rewrite || "No suggested description was returned."}
          </p>
        </div>
        {project.detected_skills.length > 0 && (
          <div
            className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-readable"
            aria-label="Detected project skills"
          >
            {project.detected_skills.map((skill) => (
              <span key={skill} className="status-text tone-text-muted">
                {skill}
              </span>
            ))}
          </div>
        )}
        {!!project.issues?.length && (
          <div>
            <h4 className="panel-label">Review notes</h4>
            <ul className="hairline-list text-sm">
              {project.issues.map((issue, i) => (
                <li key={i} className="py-3 first:pt-0">
                  <p>{issue.issue}</p>
                  <p className="mt-1 text-xs text-muted-readable">
                    How to fix: {issue.fix}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="border-t border-border pt-4">
          <p className="mb-3 text-xs leading-relaxed text-muted-readable">
            Check your understanding of this project. Practice does not change
            your score; skipping a check never lowers it.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              className="min-h-11 max-w-full px-3 text-xs"
              variant="outline"
              onClick={() => start("practice")}
              disabled={Boolean(mode)}
            >
              {mode === "practice" ? "Preparing…" : "Practice"}
            </Button>
            <Button
              className="min-h-11 max-w-full px-3 text-xs"
              onClick={() => start("verify")}
              disabled={Boolean(mode)}
            >
              {mode === "verify" ? "Preparing…" : "Verify my understanding"}
            </Button>
          </div>
          {quiz.isError && (
            <div
              role="alert"
              className="mt-3 space-y-2 text-xs text-danger-readable"
            >
              <p>{errorMessage(quiz.error)}</p>
              {typeof retryAt === "string" && (
                <p className="break-words">Retake available at: {retryAt}</p>
              )}
            </div>
          )}
        </div>
      </div>
      {project.flags.map((flag) => (
        <FlagCard key={flag.flag_id} flag={flag} />
      ))}
      {project.flags.length === 0 && (
        <p className="px-1 text-xs text-muted-readable">
          No project flags were returned.
        </p>
      )}
    </article>
  );
}
