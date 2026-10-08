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
import { Card } from "@/components/ui/card";
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
      <Card className="gap-4 p-6">
        <h1>Roadmap unavailable</h1>
        <p role="alert">{errorMessage(me.error)}</p>
        <Button onClick={() => me.refetch()}>Retry profile</Button>
      </Card>
    );
  if (!id)
    return (
      <Card className="gap-4 p-6">
        <h1 className="text-2xl font-semibold">Your next steps</h1>
        <p className="text-sm text-muted-readable">
          Run an analysis to build a roadmap from your evidence gaps.
        </p>
        <Button asChild>
          <Link href="/onboarding">Analyse a profile</Link>
        </Button>
      </Card>
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
    <section className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">Your next steps</h1>
        <p className="text-sm text-muted-readable">
          Small deliverables to strengthen the evidence behind your skills.
        </p>
      </header>
      <RoadmapTasks
        key={id}
        analysisId={id}
        milestones={analysis.data.report.roadmap}
      />
      <label className="block max-w-sm space-y-2 text-xs font-semibold">
        History target role
        <select
          aria-label="History target role"
          value={historyRole}
          onChange={(e) => setSelectedRole(e.target.value)}
          className="min-h-11 w-full rounded-control border border-border bg-surface px-3 text-sm focus-visible:ring-2 focus-visible:ring-primary"
        >
          {roleIds.map((roleId) => (
            <option key={roleId} value={roleId}>
              {roles.data?.find((r) => r.id === roleId)?.name || roleId}
            </option>
          ))}
        </select>
      </label>
      <div className="min-w-0 overflow-clip rounded-card">
        <TrendCard
          key={historyRole}
          title="Readiness over time"
          description="Completed scans for the selected role only. Periods end at its latest scan; values are not averaged. Open a scan below to review its reasons."
          series={["Readiness"]}
          datasets={scoreHistory(history.data || [], historyRole)}
          state={
            history.isPending ? "loading" : history.isError ? "error" : "ready"
          }
          message={
            history.error
              ? errorMessage(history.error)
              : "No completed scans yet. Re-scan your profile to start a history."
          }
        />
      </div>
      {history.isError && (
        <Button variant="outline" onClick={() => history.refetch()}>
          Retry history
        </Button>
      )}
      <Card className="gap-4 p-6">
        <h2 className="text-lg font-semibold">Scan history</h2>
        <ul className="space-y-3">
          {completedScans.map((r) => (
            <li
              key={r.id}
              className="flex flex-wrap items-center justify-between gap-3 text-sm"
            >
              <span>
                {r.created_at.slice(0, 10)} ·{" "}
                {roles.data?.find((role) => role.id === r.role_id)?.name ||
                  r.role_id}{" "}
                · {r.score ?? "—"} points
              </span>
              <Link
                className="inline-flex min-h-11 items-center text-primary-text underline"
                href={"/report/" + encodeURIComponent(r.id)}
              >
                View reasons
              </Link>
            </li>
          ))}
        </ul>
        {!history.isPending && !history.isError && !completedScans.length && (
          <p className="text-sm text-muted-readable">
            No completed scans to review.
          </p>
        )}
        <Button asChild variant="outline">
          <Link href="/onboarding">Re-scan profile</Link>
        </Button>
      </Card>
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
      <Card className="gap-3 p-6">
        <div className="flex flex-wrap justify-between gap-2">
          <h2 className="text-lg font-semibold">Roadmap progress</h2>
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
          className="h-3 overflow-hidden rounded-full bg-surface-2"
        >
          <div
            className="h-full rounded-full bg-primary"
            style={{
              width: tasks.length ? (done / tasks.length) * 100 + "%" : "0%",
            }}
          />
        </div>
        <p className="text-xs text-muted-readable">
          Checking off work records completion. Re-scan to measure any change in
          readiness.
        </p>
      </Card>
      {!!tasks.length && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="min-w-0 text-sm text-muted-readable">
            {next ? (
              <>
                Next deliverable:{" "}
                <span className="font-medium text-text">{next.title}</span>
              </>
            ) : (
              "All deliverables complete. Re-scan with your new evidence when ready."
            )}
          </p>
          <div
            role="group"
            aria-label="Roadmap filters"
            className="flex flex-wrap gap-2"
          >
            {(["all", "todo", "done"] as const).map((value) => (
              <Button
                key={value}
                variant={filter === value ? "default" : "outline"}
                className="min-h-11"
                aria-pressed={filter === value}
                onClick={() => setFilter(value)}
              >
                {value === "all"
                  ? `All (${tasks.length})`
                  : value === "todo"
                    ? `To do (${tasks.length - done})`
                    : `Done (${done})`}
              </Button>
            ))}
          </div>
        </div>
      )}
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
        <Card className="gap-4 p-6">
          <h2>No milestones returned</h2>
          <p className="text-sm text-muted-readable">
            Re-scan when you have new evidence to review.
          </p>
          <Button asChild>
            <Link href="/onboarding">Re-scan profile</Link>
          </Button>
        </Card>
      )}
    </>
  );
}
