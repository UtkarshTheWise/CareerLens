"use client";
/* Hallmark · pre-emit critique: P4 H4 E4 S5 R5 V4 — editable application pipeline. */
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/lib/api/query-keys";
import {
  trackerView,
  deadlineLabel,
  type ApplicationSort,
} from "@/lib/tracker-view";
import { Dialog } from "radix-ui";
import { X, Plus, GripVertical, CalendarDays } from "lucide-react";
import {
  useGetMe,
  useListApplications,
  useUpdateApplication,
  useCreateApplication,
} from "@/lib/api/hooks";
import { ApiError, errorMessage } from "@/lib/api/transport";
import { applicationDraft } from "@/lib/application-draft";
import { ScoreRing, WhyPopover } from "@/components/career";
import { safeUrl, type Schema } from "@/components/career/shared";
import { PageHeader } from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
const statuses: Schema["ApplicationStatus"][] = [
    "saved",
    "applied",
    "interviewing",
    "offer",
    "rejected",
  ],
  labels = {
    saved: "Saved",
    applied: "Applied",
    interviewing: "Interviewing",
    offer: "Offer",
    rejected: "Rejected",
  };
const control = "field";
export function TrackerScreen() {
  const me = useGetMe();
  if (me.isPending)
    return (
      <Skeleton
        className="h-96 rounded-card"
        role="status"
        aria-label="Loading tracker"
      />
    );
  if (me.isError && !(me.error instanceof ApiError && me.error.status === 404))
    return (
      <div className="panel space-y-4">
        <h1 className="page-title">Tracker unavailable</h1>
        <p role="alert" className="field-error">{errorMessage(me.error)}</p>
        <Button onClick={() => me.refetch()}>Retry profile</Button>
      </div>
    );
  if (!me.data)
    return (
      <div className="panel space-y-4">
        <h1 className="page-title">Your application tracker</h1>
        <p className="lede">
          Create a profile to save and organise applications.
        </p>
        <Button asChild size="lg" trailingArrow>
          <Link href="/onboarding">Create profile</Link>
        </Button>
      </div>
    );
  return <ApplicationBoard key={me.data.id} profileId={me.data.id} />;
}
function ApplicationBoard({ profileId }: { profileId: string }) {
  const input = { query: { profile_id: profileId } };
  const cache = useQueryClient();
  const query = useListApplications(input),
    update = useUpdateApplication(),
    create = useCreateApplication(),
    locks = useRef(new Set<string>()),
    addLock = useRef(false),
    [overrides, setOverrides] = useState<
      Record<string, Schema["ApplicationStatus"]>
    >({}),
    [pending, setPending] = useState<Record<string, boolean>>({}),
    [errors, setErrors] = useState<Record<string, string>>({}),
    [attempts, setAttempts] = useState<
      Record<string, Schema["ApplicationStatus"]>
    >({}),
    [created, setCreated] = useState<Schema["Application"][]>([]),
    [open, setOpen] = useState(false),
    [adding, setAdding] = useState(false),
    [addError, setAddError] = useState(""),
    [message, setMessage] = useState(""),
    [search, setSearch] = useState(""),
    [sort, setSort] = useState<ApplicationSort>("updated"),
    [view, setView] = useState<"board" | "grouped">("board");
  const source = [
      ...(query.data || []),
      ...created.filter((a) => !query.data?.some((q) => q.id === a.id)),
    ],
    applications = source.map((a) => ({
      ...a,
      status: overrides[a.id] ?? a.status ?? "saved",
    }));
  const visible = trackerView(applications, search, sort);
  async function move(id: string, status: Schema["ApplicationStatus"]) {
    const previous = applications.find((a) => a.id === id)?.status;
    if (!previous || previous === status || locks.current.has(id)) return;
    const restoreFocus =
      document.activeElement
        ?.closest("[data-application-id]")
        ?.getAttribute("data-application-id") === id;
    locks.current.add(id);
    setOverrides((v) => ({ ...v, [id]: status }));
    setPending((v) => ({ ...v, [id]: true }));
    setAttempts((v) => ({ ...v, [id]: status }));
    setErrors((v) => ({ ...v, [id]: "" }));
    try {
      const saved = await update.mutateAsync({
        application_id: id,
        body: { status },
      });
      if (!saved.status)
        throw new Error("The service did not confirm the application status.");
      cache.setQueryData<Schema["Application"][]>(
        queryKeys.listApplications(input),
        (rows) => (rows || []).map((a) => (a.id === id ? saved : a)),
      );
      setOverrides((v) => {
        const next = { ...v };
        delete next[id];
        return next;
      });
      setMessage("Application moved to " + labels[saved.status] + ".");
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
      if (restoreFocus)
        requestAnimationFrame(() => {
          const card = Array.from(
            document.querySelectorAll<HTMLElement>("[data-application-id]"),
          ).find((el) => el.dataset.applicationId === id);
          card?.querySelector<HTMLSelectElement>("select")?.focus();
        });
    }
  }
  async function add(form: HTMLFormElement) {
    if (addLock.current) return;
    setAddError("");
    let body: Schema["ApplicationCreate"];
    try {
      body = applicationDraft(new FormData(form), profileId);
    } catch (e) {
      setAddError((e as Error).message);
      return;
    }
    addLock.current = true;
    setAdding(true);
    try {
      const saved = await create.mutateAsync({ body });
      setCreated((v) => [...v, saved]);
      setMessage("Application saved.");
      setOpen(false);
    } catch (e) {
      setAddError(errorMessage(e as Error));
    } finally {
      addLock.current = false;
      setAdding(false);
    }
  }
  return (
    <section className="space-y-6">
      <PageHeader
        className="pb-2"
        eyebrow="Application workspace"
        title="Your application tracker"
        description="Move each opportunity as it progresses. Drag a card or use its status menu."
        actions={
        <>
          {!query.isPending && !query.isError && (
            <Button
              variant="outline"
              className="min-h-11"
              disabled={query.isFetching}
              onClick={() => query.refetch()}
            >
              {query.isFetching ? "Refreshing…" : "Refresh applications"}
            </Button>
          )}
          <Dialog.Root
            open={open}
            onOpenChange={(value) => {
              if (!adding) {
                setOpen(value);
                if (value) setAddError("");
              }
            }}
          >
            <Dialog.Trigger asChild>
              <Button className="min-h-11" trailingArrow>
                <Plus size={16} aria-hidden="true" />
                Add manually
              </Button>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className="fixed inset-0 z-50 bg-[var(--overlay)]" />
              <Dialog.Content className="panel fixed left-1/2 top-1/2 z-50 max-h-[90dvh] w-[calc(100%_-_32px)] max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto">
                <Dialog.Title className="section-title">
                  Add an application
                </Dialog.Title>
                <Dialog.Description className="mt-2 pr-6 text-sm text-muted-readable">
                  Save an opportunity to your tracker. Match scores appear when
                  the service supplies them.
                </Dialog.Description>
                <Dialog.Close asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-3 top-3"
                    disabled={adding}
                    aria-label="Close add application"
                  >
                    <X size={18} />
                  </Button>
                </Dialog.Close>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    void add(e.currentTarget);
                  }}
                  className="mt-5 space-y-4"
                >
                  <fieldset disabled={adding} className="space-y-4">
                    {[
                      ["company", "Company", "text", true],
                      ["title", "Job title", "text", true],
                      ["url", "Job URL", "url", false],
                      ["deadline", "Deadline", "date", false],
                    ].map(([name, label, type, required]) => (
                      <label
                        key={String(name)}
                        className="field-label"
                      >
                        {label}
                        <input
                          name={String(name)}
                          aria-label={String(label)}
                          type={String(type)}
                          required={Boolean(required)}
                          maxLength={type === "date" ? undefined : 2000}
                          className={control}
                        />
                      </label>
                    ))}
                    <label className="field-label">
                      Notes
                      <textarea
                        name="notes"
                        aria-label="Notes"
                        maxLength={4000}
                        rows={3}
                        className={control + " mt-1.5"}
                      />
                    </label>
                  </fieldset>
                  {addError && (
                    <p role="alert" className="field-error">
                      {addError}
                    </p>
                  )}
                  <Button type="submit" className="min-h-11" disabled={adding}>
                    {adding ? "Saving…" : "Save application"}
                  </Button>
                </form>
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>
        </>
        }
      />
      {message && (
        <p role="status" className="status-text tone-text-success">
          {message}
        </p>
      )}
      {query.isPending ? (
        <Skeleton
          className="h-80 rounded-card"
          role="status"
          aria-label="Loading applications"
        />
      ) : query.isError ? (
        <div className="panel space-y-3">
          <p role="alert" className="field-error">
            {errorMessage(query.error)}
          </p>
          <Button variant="outline" onClick={() => query.refetch()}>
            Retry applications
          </Button>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-end gap-4">
            <label className="field-label mb-0 w-full min-w-0 sm:w-auto sm:flex-1">
              Search applications
              <input
                type="search"
                aria-label="Search applications"
                placeholder="Company or job title"
                className={control + " mt-1.5"}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </label>
            <label className="field-label mb-0 w-full min-w-0 sm:w-auto">
              Sort applications
              <select
                aria-label="Sort applications"
                className={control + " mt-1.5"}
                value={sort}
                onChange={(e) => setSort(e.target.value as ApplicationSort)}
              >
                <option value="updated">Recently updated</option>
                <option value="deadline">Deadline: soonest first</option>
                <option value="company">Company A–Z</option>
              </select>
            </label>
            <div role="group" aria-label="Tracker view" className="flex gap-2">
              <Button
                variant={view === "board" ? "default" : "outline"}
                aria-pressed={view === "board"}
                onClick={() => setView("board")}
              >
                Board
              </Button>
              <Button
                variant={view === "grouped" ? "default" : "outline"}
                aria-pressed={view === "grouped"}
                onClick={() => setView("grouped")}
              >
                Grouped
              </Button>
            </div>
          </div>
          {search && (
            <Button
              variant="ghost"
              className="justify-start self-start"
              onClick={() => setSearch("")}
            >
              Clear search
            </Button>
          )}
          <p role="status" className="text-xs text-muted-readable">
            {visible.length} of {applications.length}{" "}
            {applications.length === 1 ? "application" : "applications"} ·{" "}
            {applications.length
              ? "Match percentages are returned by the service."
              : "Save your first opportunity with Add manually."}
          </p>
          {view === "board" && (
            <p className="text-xs text-muted-readable">
              Five stages, left to right. Scroll the board to see later stages;
              use each card’s status menu to move it with a keyboard.
            </p>
          )}
          {!visible.length && !!applications.length && (
            <p className="text-sm text-muted-readable">
              No applications match your search. Clear it to see every
              opportunity.
            </p>
          )}
          <div
            role="region"
            aria-label="Application pipeline"
            tabIndex={view === "board" ? 0 : undefined}
            className={
              view === "board"
                ? "overflow-x-auto rounded-card pb-3 focus-visible:ring-2 focus-visible:ring-primary"
                : "min-w-0"
            }
          >
            <div
              className={
                view === "board"
                  ? "grid grid-flow-col auto-cols-[minmax(250px,1fr)] items-start gap-4"
                  : "space-y-4"
              }
            >
              {statuses.map((status) => (
                <section
                  key={status}
                  aria-label={labels[status] + " applications"}
                  data-status={status}
                  onDragOver={(e) => {
                    e.preventDefault();
                    e.dataTransfer.dropEffect = "move";
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    const id = e.dataTransfer.getData("application/id");
                    if (applications.some((a) => a.id === id))
                      void move(id, status);
                  }}
                  className="min-w-0 rounded-card border border-border bg-surface p-3"
                >
                  <header className="mb-3 flex items-center justify-between gap-3 border-b border-border p-2 pb-3">
                    <h2 className="eyebrow">{labels[status]}</h2>
                    <span className="text-[13px] font-medium text-text [font-variant-numeric:tabular-nums]">
                      {visible.filter((a) => a.status === status).length}
                    </span>
                  </header>
                  <div
                    className={
                      view === "grouped"
                        ? "grid items-start gap-3 md:grid-cols-2 xl:grid-cols-3"
                        : "space-y-3"
                    }
                  >
                    {visible
                      .filter((a) => a.status === status)
                      .map((a) => (
                        <div
                          key={a.id}
                          data-application-id={a.id}
                          draggable={!pending[a.id]}
                          onDragStart={(e) => {
                            if (locks.current.has(a.id)) {
                              e.preventDefault();
                              return;
                            }
                            e.dataTransfer.setData("application/id", a.id);
                            e.dataTransfer.effectAllowed = "move";
                          }}
                          aria-busy={pending[a.id]}
                          className="flex min-w-0 flex-col gap-3 rounded-xl border border-border bg-surface-2 p-4"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <p className="break-anywhere text-xs text-muted-readable">
                                {a.company}
                              </p>
                              <h3 className="mt-2 break-anywhere text-[15px] font-medium">
                                {a.title}
                              </h3>
                            </div>
                            <GripVertical
                              size={16}
                              aria-hidden="true"
                              className="shrink-0 text-muted-readable"
                            />
                          </div>
                          <div className="grid grid-cols-2 items-start gap-3">
                            <ScoreRing
                              size={72}
                              label="Keyword match"
                              value={a.keyword_match ?? null}
                              explanation={
                                <WhyPopover
                                  label="Keyword match"
                                  definition="Keyword match is supplied by the matching service for the posting. Missing scores are shown as unavailable."
                                />
                              }
                            />
                            <ScoreRing
                              size={72}
                              label="Evidence match"
                              value={a.evidence_match ?? null}
                              explanation={
                                <WhyPopover
                                  label="Evidence match"
                                  definition="Evidence match is supplied by the service using evidence-backed skills. No match is calculated by the tracker."
                                />
                              }
                            />
                          </div>
                          {a.deadline && <Deadline value={a.deadline} />}
                          {(a.notes || a.description) && (
                            <details className="border-t border-border text-xs">
                              <summary className="min-h-11 cursor-pointer py-3 font-medium">
                                Notes & job details
                              </summary>
                              <div className="space-y-3 pb-3">
                                {a.notes && (
                                  <p className="whitespace-pre-wrap break-anywhere leading-relaxed">
                                    {a.notes}
                                  </p>
                                )}
                                {a.description && (
                                  <p className="max-h-48 overflow-y-auto whitespace-pre-wrap break-anywhere leading-relaxed text-muted-readable">
                                    {a.description}
                                  </p>
                                )}
                              </div>
                            </details>
                          )}
                          {safeUrl(a.url) && (
                            <a
                              href={safeUrl(a.url)!}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-link inline-flex min-h-11 items-center"
                            >
                              View posting ↗
                            </a>
                          )}
                          <label className="field-label mb-0">
                            Status
                            <select
                              aria-label={
                                "Status for " + a.company + " " + a.title
                              }
                              className={control + " mt-1.5"}
                              value={a.status}
                              disabled={pending[a.id]}
                              onChange={(e) =>
                                void move(
                                  a.id,
                                  e.target.value as Schema["ApplicationStatus"],
                                )
                              }
                            >
                              {statuses.map((s) => (
                                <option key={s} value={s}>
                                  {labels[s]}
                                </option>
                              ))}
                            </select>
                          </label>
                          {pending[a.id] && (
                            <p
                              role="status"
                              className="text-xs text-muted-readable"
                            >
                              Saving status…
                            </p>
                          )}
                          {errors[a.id] && (
                            <div role="alert" className="space-y-3">
                              <p className="field-error">
                                {errors[a.id]}
                              </p>
                              <Button
                                variant="outline"
                                className="min-h-11"
                                onClick={() => void move(a.id, attempts[a.id])}
                              >
                                Retry move
                              </Button>
                            </div>
                          )}
                        </div>
                      ))}
                    {!visible.some((a) => a.status === status) && (
                      <p className="px-2 py-6 text-xs text-muted-readable">
                        No applications here yet.
                      </p>
                    )}
                  </div>
                </section>
              ))}
            </div>
          </div>
        </>
      )}
    </section>
  );
}

function Deadline({ value }: { value: string }) {
  // Render relative wording after hydration so the visitor's calendar day is used.
  const [label, setLabel] = useState<ReturnType<typeof deadlineLabel>>(null);
  useEffect(() => {
    const refresh = () => setLabel(deadlineLabel(value, new Date()));
    refresh();
    const timer = setInterval(refresh, 60000);
    return () => clearInterval(timer);
  }, [value]);
  return (
    <p
      className={
        "flex flex-wrap items-center gap-2 text-xs " +
        (label?.soon ? "text-warning-readable" : "text-muted-readable")
      }
    >
      <CalendarDays size={14} aria-hidden="true" />
      <time dateTime={value}>Deadline: {label?.date || value}</time>
      {label?.note && <span className="font-semibold">· {label.note}</span>}
    </p>
  );
}
