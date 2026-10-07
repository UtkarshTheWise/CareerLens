"use client";
/* Hallmark · pre-emit critique: P4 H4 E4 S4 R5 V3 — DESIGN-locked analysis progress. */
import Link from "next/link";
import { useRef } from "react";
import { useStartAnalysis, useGetAnalysis } from "@/lib/api/hooks";
import { errorMessage } from "@/lib/api/transport";
import { useRouter } from "next/navigation";
import { StageProgress } from "@/components/career";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
export function AnalysisProgress({ analysisId }: { analysisId: string }) {
  const analysis = useGetAnalysis({ analysis_id: analysisId });
  const restart = useStartAnalysis();
  const router = useRouter();
  const retryLocked = useRef(false);
  async function retryAnalysis() {
    if (!analysis.data || retryLocked.current) return;
    retryLocked.current = true;
    try {
      const next = await restart.mutateAsync({
        profile_id: analysis.data.profile_id,
        body: { role_id: analysis.data.role_id },
      });
      router.push(`/report/${encodeURIComponent(next.id)}`);
    } catch {
      retryLocked.current = false;
      /* The mutation error is rendered below. */
    }
  }
  return (
    <section className="mx-auto max-w-4xl space-y-6">
      <div>
        <p className="mb-2 text-xs font-semibold text-primary-text">
          Your evidence analysis
        </p>
        <h1 className="text-2xl font-semibold">
          {analysis.data?.status === "done"
            ? "Your analysis is complete."
            : analysis.data?.status === "failed"
              ? "Your analysis stopped."
              : "Connecting claims to evidence."}
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-readable">
          {analysis.data?.status === "done"
            ? "Your results have been saved. Keep this report URL to return to them."
            : analysis.data?.status === "failed"
              ? "Your saved profile is still available. Review the error below or start another analysis."
              : "We’ll update this page as your documents and public work are reviewed. You can return to this report URL to check progress."}
        </p>
      </div>
      {analysis.isPending && (
        <Card>
          <CardContent
            className="space-y-4 p-6"
            role="status"
            aria-label="Loading analysis"
          >
            <Skeleton className="h-5 w-44" />
            <Skeleton className="h-2 w-full" />
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
            <p className="text-sm text-muted-readable">Loading analysis…</p>
          </CardContent>
        </Card>
      )}
      {analysis.isError && (
        <div
          role="alert"
          className="space-y-3 rounded-card border border-danger bg-surface p-6"
        >
          <h2 className="font-semibold">Couldn’t refresh this analysis</h2>
          <p className="text-sm text-danger-readable">
            {errorMessage(analysis.error)}
          </p>
          <p className="text-xs text-muted-readable">
            {analysis.data
              ? "The last received progress remains below."
              : "Retry to check its status."}
          </p>
          <Button
            onClick={() => analysis.refetch()}
            disabled={analysis.isFetching}
            variant="outline"
            className="min-h-11"
          >
            {analysis.isFetching ? "Retrying…" : "Retry status"}
          </Button>
        </div>
      )}
      {analysis.data && (
        <div className="grid items-start gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <Card>
            <CardContent className="p-6">
              <StageProgress
                status={analysis.data.status}
                progress={analysis.data.progress}
                error={analysis.data.error}
              />
            </CardContent>
          </Card>
          <div className="space-y-4">
            {analysis.data.status === "done" ? (
              <Card>
                <CardContent className="space-y-3 p-6">
                  <h2 className="font-semibold">Results saved</h2>
                  <p className="text-sm leading-relaxed text-muted-readable">
                    This analysis has finished. Keep this URL to return to it.
                  </p>
                  {/* TODO(progress): F4 renders the completed evidence report and its explanations here. */}
                  <Button asChild variant="outline" className="min-h-11">
                    <Link href="/onboarding">New analysis</Link>
                  </Button>
                </CardContent>
              </Card>
            ) : analysis.data.status === "failed" ? (
              <Card>
                <CardContent className="space-y-4 p-6">
                  <h2 className="font-semibold">Try again when you’re ready</h2>
                  {!analysis.data.error && (
                    <p className="text-sm text-muted-readable">
                      The analysis failed without an error message. Try again or
                      review your inputs.
                    </p>
                  )}
                  <p className="text-xs leading-relaxed text-muted-readable">
                    Retry starts a new analysis using the saved profile and
                    target role.
                  </p>
                  {restart.isError && (
                    <p role="alert" className="text-sm text-danger-readable">
                      {errorMessage(restart.error)}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-3">
                    <Button
                      onClick={retryAnalysis}
                      disabled={restart.isPending}
                      className="min-h-11"
                    >
                      {restart.isPending ? "Starting…" : "Retry analysis"}
                    </Button>
                    <Button asChild variant="outline" className="min-h-11">
                      <Link href="/onboarding">Review inputs</Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <>
                <div
                  role="status"
                  aria-label="Preparing your report"
                  className="space-y-4"
                >
                  <Skeleton className="h-36 rounded-card" />
                  <Skeleton className="h-28 rounded-card" />
                </div>
                <p className="text-xs leading-relaxed text-muted-readable">
                  Results will appear after all stages finish. No score is
                  estimated while analysis is running.
                </p>
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
