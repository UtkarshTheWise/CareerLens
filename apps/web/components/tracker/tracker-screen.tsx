"use client";
/* Hallmark · pre-emit critique: P4 H4 E4 S5 R5 V4 — editable application pipeline. */
import { useRef, useState } from "react";
import Link from "next/link";
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
import { Card } from "@/components/ui/card";
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
const control =
  "min-h-11 w-full min-w-0 rounded-control border border-border bg-surface-2 px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary";
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
      <Card className="space-y-4 p-6">
        <h1>Tracker unavailable</h1>
        <p role="alert">{errorMessage(me.error)}</p>
        <Button onClick={() => me.refetch()}>Retry profile</Button>
      </Card>
    );
  if (!me.data)
    return (
      <Card className="space-y-4 p-6">
        <h1 className="text-2xl font-semibold">Your application tracker</h1>
        <p className="text-sm text-muted-readable">
          Create a profile to save and organise applications.
        </p>
        <Button asChild>
          <Link href="/onboarding">Create profile</Link>
        </Button>
      </Card>
    );
  return <ApplicationBoard key={me.data.id} profileId={me.data.id} />;
}
function ApplicationBoard({ profileId }: { profileId: string }) {
  const query = useListApplications({ query: { profile_id: profileId } }),
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
    [message, setMessage] = useState("");
  const source = [
      ...(query.data || []),
      ...created.filter((a) => !query.data?.some((q) => q.id === a.id)),
    ],
    applications = source.map((a) => ({
      ...a,
      status: overrides[a.id] ?? a.status,
    }));
  async function move(id: string, status: Schema["ApplicationStatus"]) {
    const previous = applications.find((a) => a.id === id)?.status;
    if (!previous || previous === status || locks.current.has(id)) return;
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
      if (!saved.status) throw new Error("The service did not confirm the application status.");
      setOverrides((v) => ({ ...v, [id]: saved.status! }));
      setMessage("Application moved to " + labels[saved.status] + ".");
    } catch (e) {
      setOverrides((v) => ({ ...v, [id]: previous }));
      setErrors((v) => ({ ...v, [id]: errorMessage(e as Error) }));
    } finally {
      locks.current.delete(id);
      setPending((v) => ({ ...v, [id]: false }));
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
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="text-xs font-semibold text-primary-text">
            Application workspace
          </p>
          <h1 className="text-2xl font-semibold">Your application tracker</h1>
          <p className="max-w-xl text-sm text-muted-readable">
            Move each opportunity as it progresses. Drag a card or use its
            status menu.
          </p>
        </div>
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
            <Button className="min-h-11">
              <Plus size={16} aria-hidden="true" />
              Add manually
            </Button>
          </Dialog.Trigger>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 z-50 bg-[var(--overlay)]" />
            <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[90dvh] w-[calc(100%_-_32px)] max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-card border border-border bg-surface p-6 shadow-card">
              <Dialog.Title className="text-lg font-semibold">
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
                      className="block space-y-2 text-xs font-semibold"
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
                  <label className="block space-y-2 text-xs font-semibold">
                    Notes
                    <textarea
                      name="notes"
                      aria-label="Notes"
                      maxLength={4000}
                      rows={3}
                      className={control + " py-3"}
                    />
                  </label>
                </fieldset>
                {addError && (
                  <p role="alert" className="text-sm text-danger-readable">
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
      </header>
      {message && (
        <p role="status" className="text-xs text-success-readable">
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
        <Card className="space-y-3 p-6">
          <p role="alert" className="text-sm text-danger-readable">
            {errorMessage(query.error)}
          </p>
          <Button variant="outline" onClick={() => query.refetch()}>
            Retry applications
          </Button>
        </Card>
      ) : (
        <>
          <p className="text-xs text-muted-readable">
            {applications.length} applications ·{" "}
            {applications.length
              ? "Match percentages are returned by the service."
              : "Save your first opportunity with Add manually."}
          </p>
          <div className="grid items-start gap-4 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5">
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
                className="min-w-0 rounded-card border border-border bg-surface-2 p-3"
              >
                <header className="mb-4 flex items-center justify-between gap-3 p-2">
                  <h2 className="text-sm font-semibold">{labels[status]}</h2>
                  <span className="status-pill tone-muted">
                    {applications.filter((a) => a.status === status).length}
                  </span>
                </header>
                <div className="space-y-3">
                  {applications
                    .filter((a) => a.status === status)
                    .map((a) => (
                      <Card
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
                        className="min-w-0 space-y-4 p-4"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="break-anywhere text-xs text-muted-readable">
                              {a.company}
                            </p>
                            <h3 className="mt-2 break-anywhere text-sm font-semibold">
                              {a.title}
                            </h3>
                          </div>
                          <GripVertical
                            size={16}
                            aria-hidden="true"
                            className="shrink-0 text-muted-readable"
                          />
                        </div>
                        <div className="flex flex-wrap justify-center gap-3">
                          <ScoreRing
                            size={88}
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
                            size={88}
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
                        {a.deadline && (
                          <p className="flex items-center gap-2 text-xs text-muted-readable">
                            <CalendarDays size={14} aria-hidden="true" />
                            Deadline: {a.deadline}
                          </p>
                        )}
                        {safeUrl(a.url) && (
                          <a
                            href={safeUrl(a.url)!}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex min-h-11 items-center text-xs text-primary-text underline"
                          >
                            View posting
                          </a>
                        )}
                        <label className="block space-y-2 text-xs font-semibold">
                          Status
                          <select
                            aria-label={
                              "Status for " + a.company + " " + a.title
                            }
                            className={control}
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
                            <p className="text-xs text-danger-readable">
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
                      </Card>
                    ))}
                  {!applications.some((a) => a.status === status) && (
                    <p className="px-2 py-6 text-xs text-muted-readable">
                      No applications here yet.
                    </p>
                  )}
                </div>
              </section>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
