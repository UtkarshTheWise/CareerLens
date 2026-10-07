"use client";
/* Hallmark · pre-emit critique: P4 H4 E4 S4 R5 V3 — ordered deliverables, honest history. */
import { useRef, useState } from "react";
import Link from "next/link";
import {
  useGetMe,
  useGetAnalysis,
  useListAnalyses,
  useUpdateMilestone,
} from "@/lib/api/hooks";
import { ApiError, errorMessage } from "@/lib/api/transport";
import { scoreHistory } from "@/lib/score-history";
import { AnalysisProgress } from "@/components/analysis/analysis-progress";
import { MilestoneCard, TrendCard } from "@/components/career";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
export function RoadmapScreen() {
  const me = useGetMe(),
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
      <Card className="space-y-4 p-6">
        <h1>Roadmap unavailable</h1>
        <p role="alert">{errorMessage(me.error)}</p>
        <Button onClick={() => me.refetch()}>Retry profile</Button>
      </Card>
    );
  if (!id)
    return (
      <Card className="space-y-4 p-6">
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
      <TrendCard
        title="Readiness over time"
        description="Completed scans only. Periods end at your latest scan; values are not averaged. Open a scan below to review its reasons."
        series={["Readiness"]}
        datasets={scoreHistory(history.data || [])}
        state={
          history.isPending ? "loading" : history.isError ? "error" : "ready"
        }
        message={
          history.error
            ? errorMessage(history.error)
            : "No completed scans yet. Re-scan your profile to start a history."
        }
      />
      {history.isError && (
        <Button variant="outline" onClick={() => history.refetch()}>
          Retry history
        </Button>
      )}
      <Card className="space-y-4 p-6">
        <h2 className="text-lg font-semibold">Scan history</h2>
        <ul className="space-y-3">
          {(history.data || [])
            .filter((r) => r.status === "done")
            .sort((a, b) => b.created_at.localeCompare(a.created_at))
            .map((r) => (
              <li
                key={r.id}
                className="flex flex-wrap items-center justify-between gap-3 text-sm"
              >
                <span>
                  {r.created_at.slice(0, 10)} · {r.role_id} · {r.score ?? "—"}{" "}
                  points
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
        {!history.isPending &&
          !history.isError &&
          !history.data?.some((r) => r.status === "done") && (
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
  const mutation = useUpdateMilestone(),
    locks = useRef(new Set<string>()),
    [overrides, setOverrides] = useState<Record<string, boolean>>({}),
    [pending, setPending] = useState<Record<string, boolean>>({}),
    [errors, setErrors] = useState<Record<string, string>>({}),
    [attempts, setAttempts] = useState<Record<string, boolean>>({});
  const tasks = [...milestones]
    .sort((a, b) => a.order - b.order)
    .map((m) => ({ ...m, done: overrides[m.id] ?? m.done ?? false }));
  const done = tasks.filter((m) => m.done).length;
  async function change(id: string, value: boolean) {
    if (locks.current.has(id)) return;
    locks.current.add(id);
    const previous = tasks.find((m) => m.id === id)?.done ?? false;
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
      setOverrides((v) => ({ ...v, [id]: saved.done ?? value }));
    } catch (e) {
      setOverrides((v) => ({ ...v, [id]: previous }));
      setErrors((v) => ({ ...v, [id]: errorMessage(e as Error) }));
    } finally {
      locks.current.delete(id);
      setPending((v) => ({ ...v, [id]: false }));
    }
  }
  return (
    <>
      <Card className="space-y-3 p-6">
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
      {tasks.length ? (
        <div className="grid items-start gap-4 md:grid-cols-2 xl:grid-cols-3">
          {tasks.map((m) => (
            <MilestoneCard
              key={m.id}
              milestone={m}
              onDoneChange={(value) => void change(m.id, value)}
              saving={pending[m.id]}
              error={errors[m.id]}
              onRetry={() => void change(m.id, attempts[m.id])}
            />
          ))}
        </div>
      ) : (
        <Card className="space-y-4 p-6">
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
