"use client";
/* Hallmark · pre-emit critique: P4 H4 E4 S4 R5 V3 — ordered deliverables, honest history. */
import { useRef, useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/query-keys";
import type { Schema } from "@/components/career/shared";
import {
  useGetMe,
  useGetAnalysis,
  useListAnalyses,
  useUpdateMilestone,
  useListRoles,
} from "@/lib/api/hooks";
import { ApiError, errorMessage } from "@/lib/api/transport";
import { scoreHistory } from "@/lib/score-history";
import { AnalysisProgress } from "@/components/analysis/analysis-progress";
import { MilestoneCard, TrendCard } from "@/components/career";
import { PageHeader, Panel, Section, TextLink } from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
export function RoadmapScreen() {
  const [selectedRole, setSelectedRole] = useState(""),
    roles = useListRoles(),
    me = useGetMe(),
    id = me.data?.latest_analysis_id,
    analysis = useGetAnalysis(id ? { analysis_id: id } : undefined),
    history = useListAnalyses(
      me.data ? { profile_id: me.data.id } : undefined,
      { staleTime: 0 },
    );
  if (me.isPending)
    return (
      <Skeleton
        role="status"
        aria-label="Loading roadmap"
        className="h-96 rounded-card"
      />
    );
  if (me.isError && !(me.error instanceof ApiError && me.error.status === 404))
    return (
      <div className="panel space-y-4">
        <h1 className="page-title">Roadmap unavailable</h1>
        <p role="alert" className="text-sm text-danger-readable">
          {errorMessage(me.error)}
        </p>
        <Button className="min-h-11" onClick={() => me.refetch()}>
          Retry profile
        </Button>
      </div>
    );
  if (!id)
    return (
      <div>
        <PageHeader
          eyebrow="Your roadmap"
          title="Your next steps"
          description="Run an analysis to build a roadmap from your evidence gaps."
        />
        <Button asChild size="lg" trailingArrow>
          <Link href="/onboarding">Analyse a profile</Link>
        </Button>
      </div>
    );
  if (!analysis.data?.report || analysis.data.status !== "done")
    return <AnalysisProgress analysisId={id} query={analysis} />;
  const historyRole = selectedRole || analysis.data.role_id;
  const completedScans = (history.data || [])
    .filter((r) => r.status === "done" && r.role_id === historyRole)
    .sort((a, b) => b.created_at.localeCompare(a.created_at));
  const roleIds = Array.from(
    new Set([
      analysis.data.role_id,
      ...(history.data || []).map((r) => r.role_id),
    ]),
  );
  return (
    <section>
      <PageHeader
        eyebrow="Your roadmap"
        title="Your next steps"
        description="Small deliverables to strengthen the evidence behind your skills."
      />
      <RoadmapTasks
        key={id}
        analysisId={id}
        milestones={analysis.data.report.roadmap}
      />
      <Section
        eyebrow="History"
        title="Readiness over time"
        actions={
          <div>
            <label htmlFor="history-role" className="field-label">
              History target role
            </label>
            <select
              id="history-role"
              aria-label="History target role"
              value={historyRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              className="field w-full min-w-48"
            >
              {roleIds.map((roleId) => (
                <option key={roleId} value={roleId}>
                  {roles.data?.find((r) => r.id === roleId)?.name || roleId}
                </option>
              ))}
            </select>
          </div>
        }
      >
        <div className="min-w-0 overflow-clip rounded-card">
          <TrendCard
            key={historyRole}
            title="Readiness over time"
            description="Completed scans for the selected role only. Periods end at its latest scan; values are not averaged. Open a scan below to review its reasons."
            series={["Readiness"]}
            datasets={scoreHistory(history.data || [], historyRole)}
            state={
              history.isPending
                ? "loading"
                : history.isError
                  ? "error"
                  : "ready"
            }
            message={
              history.error
                ? errorMessage(history.error)
                : "No completed scans yet. Re-scan your profile to start a history."
            }
          />
        </div>
        {history.isError && (
          <Button
            className="mt-4 min-h-11"
            variant="outline"
            onClick={() => history.refetch()}
          >
            Retry history
          </Button>
        )}
      </Section>
      <Section eyebrow="History" title="Scan history">
        <ul className="hairline-list">
          {completedScans.map((r) => (
            <li
              key={r.id}
              className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm first:pt-0"
            >
              <span className="tabular-nums">
                {r.created_at.slice(0, 10)} ·{" "}
                {roles.data?.find((role) => role.id === r.role_id)?.name ||
                  r.role_id}{" "}
                · {r.score ?? "—"} points
              </span>
              <span className="inline-flex min-h-11 items-center">
                <TextLink href={"/report/" + encodeURIComponent(r.id)}>
                  View reasons
                </TextLink>
              </span>
            </li>
          ))}
        </ul>
        {!history.isPending && !history.isError && !completedScans.length && (
          <p className="text-sm text-muted-readable">
            No completed scans to review.
          </p>
        )}
        <Button asChild variant="outline" className="mt-5 min-h-11" trailingArrow>
          <Link href="/onboarding">Re-scan profile</Link>
        </Button>
      </Section>
    </section>
  );
}
function RoadmapTasks({
  analysisId,
  milestones,
}: {
  analysisId: string;
  milestones: import("@careerlens/api-client").components["schemas"]["RoadmapMilestone"][];
}) {
  const cache = useQueryClient();
  const mutation = useUpdateMilestone(),
    locks = useRef(new Set<string>()),
    [overrides, setOverrides] = useState<Record<string, boolean>>({}),
    [pending, setPending] = useState<Record<string, boolean>>({}),
    [errors, setErrors] = useState<Record<string, string>>({}),
    [attempts, setAttempts] = useState<Record<string, boolean>>({}),
    [filter, setFilter] = useState<"all" | "todo" | "done">("all");
  const tasks = [...milestones]
    .sort((a, b) => a.order - b.order)
    .map((m) => ({ ...m, done: overrides[m.id] ?? m.done ?? false }));
  const done = tasks.filter((m) => m.done).length;
  const next = tasks.find((m) => !m.done);
  const visible = tasks.filter(
    (m) => filter === "all" || (filter === "done" ? m.done : !m.done),
  );
  async function change(id: string, value: boolean) {
    if (locks.current.has(id)) return;
    locks.current.add(id);
    setOverrides((v) => ({ ...v, [id]: value }));
    setPending((v) => ({ ...v, [id]: true }));
    setErrors((v) => ({ ...v, [id]: "" }));
    setAttempts((v) => ({ ...v, [id]: value }));
    try {
      const saved = await mutation.mutateAsync({
        analysis_id: analysisId,
        milestone_id: id,
        body: { done: value },
      });
      cache.setQueryData<Schema["Analysis"]>(
        queryKeys.getAnalysis({ analysis_id: analysisId }),
        (data) =>
          data?.report
            ? {
                ...data,
                report: {
                  ...data.report,
                  roadmap: data.report.roadmap.map((m) =>
                    m.id === id ? { ...saved, done: saved.done ?? value } : m,
                  ),
                },
              }
            : data,
      );
      setOverrides((v) => {
        const next = { ...v };
        delete next[id];
        return next;
      });
    } catch (e) {
      setOverrides((v) => {
        const next = { ...v };
        delete next[id];
        return next;
      });
      setErrors((v) => ({ ...v, [id]: errorMessage(e as Error) }));
    } finally {
      locks.current.delete(id);
      setPending((v) => ({ ...v, [id]: false }));
    }
  }
  return (
    <>
      <Panel label="Roadmap progress">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-[17px] font-medium tracking-[-.02em]">
            Deliverables completed
          </h2>
          <span className="text-sm tabular-nums">
            {done} / {tasks.length} complete
          </span>
        </div>
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={tasks.length || 1}
          aria-valuenow={done}
          aria-label="Completed roadmap deliverables"
          className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-2"
        >
          <div
            className="h-full rounded-full bg-primary"
            style={{
              width: tasks.length ? (done / tasks.length) * 100 + "%" : "0%",
            }}
          />
        </div>
        <p className="mt-3 text-xs text-muted-readable">
          Checking off work records completion. Re-scan to measure any change in
          readiness.
        </p>
      </Panel>
      <Section
        eyebrow="Deliverables"
        title="What to build next"
        description={
          tasks.length
            ? next
              ? `Next deliverable: ${next.title}`
              : "All deliverables complete. Re-scan with your new evidence when ready."
            : undefined
        }
        actions={
          !!tasks.length && (
            <div>
              <label htmlFor="roadmap-filter" className="field-label">
                Show
              </label>
              <select
                id="roadmap-filter"
                aria-label="Roadmap filters"
                value={filter}
                onChange={(e) =>
                  setFilter(e.target.value as "all" | "todo" | "done")
                }
                className="field min-w-44"
              >
                <option value="all">All ({tasks.length})</option>
                <option value="todo">To do ({tasks.length - done})</option>
                <option value="done">Done ({done})</option>
              </select>
            </div>
          )
        }
      >
        {tasks.length ? (
          <div className="grid items-start gap-4 md:grid-cols-2 xl:grid-cols-3">
            {visible.map((m) => (
              <MilestoneCard
                key={m.id}
                milestone={m}
                onDoneChange={(value) => void change(m.id, value)}
                saving={pending[m.id]}
                error={errors[m.id]}
                onRetry={() => void change(m.id, attempts[m.id])}
              />
            ))}
            {!visible.length && (
              <p role="status" className="text-sm text-muted-readable">
                No deliverables in this view. Choose another filter.
              </p>
            )}
          </div>
        ) : (
          <div className="panel space-y-4">
            <h2 className="text-[17px] font-medium tracking-[-.02em]">
              No milestones returned
            </h2>
            <p className="text-sm text-muted-readable">
              Re-scan when you have new evidence to review.
            </p>
            <Button asChild className="min-h-11">
              <Link href="/onboarding">Re-scan profile</Link>
            </Button>
          </div>
        )}
      </Section>
    </>
  );
}
