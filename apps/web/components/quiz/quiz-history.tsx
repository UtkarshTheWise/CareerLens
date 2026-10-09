"use client";
import Link from "next/link";
import { useListQuizzes } from "@/lib/api/hooks";
import { errorMessage } from "@/lib/api/transport";
import { UnderstandingBadge } from "@/components/career";
import { number } from "@/components/career/shared";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
export function QuizHistory({ profileId }: { profileId: string }) {
  const query = useListQuizzes({ profile_id: profileId });
  return (
    <section className="space-y-4" data-component="QuizHistory">
      <h2 className="section-title">Project check history</h2>
      <p className="lede">
        Your project checks for this profile. Open a submitted result to review
        its feedback.
      </p>
      {query.isPending ? (
        <div role="status" aria-label="Loading quiz history">
          <Skeleton className="h-24 w-full rounded-card" />
        </div>
      ) : query.isError ? (
        <div
          role="alert"
          className="panel space-y-3 border-danger-readable"
        >
          <p className="field-error">
            {errorMessage(query.error)}
          </p>
          <Button
            variant="outline"
            className="min-h-11"
            disabled={query.isFetching}
            onClick={() => query.refetch()}
          >
            Retry history
          </Button>
        </div>
      ) : query.data?.length ? (
        <ul className="hairline-list border-y border-border">
          {[...query.data]
            .sort((a, b) => b.created_at.localeCompare(a.created_at))
            .map((quiz) => (
              <li
                key={quiz.id}
                className="flex flex-wrap items-center justify-between gap-4 py-5"
              >
                <div className="min-w-0 space-y-2">
                  <h3 className="break-anywhere text-[15px] font-medium">
                    {quiz.project_title}
                  </h3>
                  <p className="break-anywhere text-xs text-muted-readable">
                    {quiz.mode === "practice" ? "Practice" : "Verify"} ·{" "}
                    {quiz.status === "submitted" ? "Submitted" : "In progress"}{" "}
                    · {quiz.created_at}
                  </p>
                  <div className="flex flex-wrap items-center gap-2">
                    {quiz.score != null && quiz.status === "submitted" && (
                      <span className="text-xs">
                        Quiz score: {number(quiz.score)}/100
                      </span>
                    )}
                    {quiz.mode === "verify" && quiz.understanding && (
                      <UnderstandingBadge understanding={quiz.understanding} />
                    )}
                  </div>
                </div>
                <Button asChild variant="outline" className="min-h-11">
                  <Link href={`/quiz/${encodeURIComponent(quiz.id)}`}>
                    {quiz.status === "submitted"
                      ? "View result"
                      : "Resume check"}
                  </Link>
                </Button>
              </li>
            ))}
        </ul>
      ) : (
        <p className="inset-note">
          No project checks yet. Choose Practice or Verify on a project above.
        </p>
      )}
    </section>
  );
}
