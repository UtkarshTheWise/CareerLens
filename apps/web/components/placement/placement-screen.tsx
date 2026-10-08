"use client";
/* Hallmark · pre-emit critique: P4 H4 E4 S5 R5 V4 — cohort overview, actionable table. */
import { useRef, useState } from "react";
import Link from "next/link";
import { Users, ScanLine, Gauge, CircleAlert, ShieldCheck } from "lucide-react";
import {
  useListCohorts,
  useListRoles,
  useGetCohortInsights,
  useListCohortStudents,
  useExportCohort,
} from "@/lib/api/hooks";
import { errorMessage } from "@/lib/api/transport";
import {
  KpiCard,
  StackedBars,
  ScoreRing,
  BandBadge,
  UnderstandingBadge,
  WhyPopover,
} from "@/components/career";
import { number, type Schema } from "@/components/career/shared";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
const control =
  "min-h-11 w-full min-w-0 rounded-control border border-border bg-surface-2 px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary";
function Failure({ error, retry }: { error: Error; retry: () => void }) {
  return (
    <div role="alert" className="space-y-3">
      <p className="text-sm text-danger-readable">{errorMessage(error)}</p>
      <Button variant="outline" onClick={retry}>
        Retry data
      </Button>
    </div>
  );
}
function Loading() {
  return (
    <Skeleton
      role="status"
      aria-label="Loading placement data"
      className="h-64 rounded-card"
    />
  );
}
export function PlacementScreen() {
  const cohorts = useListCohorts(),
    roles = useListRoles(),
    [selectedCohort, setCohort] = useState(""),
    [selectedRole, setRole] = useState("");
  const cohort =
      cohorts.data?.find((c) => c.id === selectedCohort) || cohorts.data?.[0],
    role = roles.data?.find((r) => r.id === selectedRole) || roles.data?.[0];
  return (
    <section className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold text-primary-text">
          Placement workspace
        </p>
        <h1 className="text-2xl font-semibold">Cohort readiness</h1>
        <p className="max-w-2xl text-sm text-muted-readable">
          See the evidence gaps to address together, then find students who need
          support.
        </p>
      </header>
      <Card className="space-y-4 p-6">
        {cohorts.isPending || roles.isPending ? (
          <Loading />
        ) : cohorts.isError ? (
          <Failure error={cohorts.error} retry={() => void cohorts.refetch()} />
        ) : roles.isError ? (
          <Failure error={roles.error} retry={() => void roles.refetch()} />
        ) : !cohort || !role ? (
          <p className="text-sm text-muted-readable">
            {!cohort ? "No cohorts available yet." : "No roles available yet."}
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-2 text-xs font-semibold">
              Cohort
              <select
                aria-label="Cohort"
                className={control}
                value={cohort.id}
                onChange={(e) => setCohort(e.target.value)}
              >
                {cohorts.data?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2 text-xs font-semibold">
              Target role
              <select
                aria-label="Target role"
                className={control}
                value={role.id}
                onChange={(e) => setRole(e.target.value)}
              >
                {roles.data?.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
      </Card>
      {cohort && role && (
        <CohortView
          key={cohort.id + role.id}
          cohortId={cohort.id}
          roleId={role.id}
        />
      )}
    </section>
  );
}
function Counts({
  title,
  rows,
}: {
  title: string;
  rows: { label: string; count: number }[];
}) {
  const maximum = Math.max(1, ...rows.map((r) => r.count));
  return (
    <Card className="space-y-4 p-6">
      <h2 className="text-lg font-semibold">{title}</h2>
      {rows.length ? (
        <ul className="space-y-4" aria-label={title}>
          {rows.map((r, i) => (
            <li key={i} className="space-y-2">
              <div className="flex justify-between gap-3 text-sm">
                <span className="break-anywhere">{r.label}</span>
                <span className="tabular-nums">{r.count}</span>
              </div>
              <div
                aria-hidden="true"
                className="h-3 overflow-hidden rounded-full bg-surface-2"
              >
                <div
                  className="h-full rounded-full bg-data-2"
                  style={{ width: (r.count / maximum) * 100 + "%" }}
                />
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-readable">No data returned.</p>
      )}
    </Card>
  );
}
function Rates({
  title,
  rows,
  kind,
}: {
  title: string;
  rows: {
    skill_id: string;
    skill_name: string;
    claimed_by: number;
    rate: number;
  }[];
  kind: string;
}) {
  return (
    <Card className="min-w-0 space-y-4 p-6">
      <h2 className="text-lg font-semibold">{title}</h2>
      {rows.length ? (
        <div
          role="region"
          aria-label={title}
          tabIndex={0}
          className="overflow-x-auto focus-visible:ring-2 focus-visible:ring-primary"
        >
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{title}</caption>
            <thead className="bg-surface-2 text-xs">
              <tr>
                <th scope="col" className="p-3">
                  Skill
                </th>
                <th scope="col" className="p-3">
                  Claimed by
                </th>
                <th scope="col" className="p-3">
                  {kind}
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.skill_id} className="border-t border-border">
                  <th scope="row" className="p-3 font-medium">
                    {r.skill_name}
                  </th>
                  <td className="p-3 tabular-nums">{r.claimed_by}</td>
                  <td className="p-3 tabular-nums">{number(r.rate)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-muted-readable">No skill rates returned.</p>
      )}
    </Card>
  );
}
function CohortView({
  cohortId,
  roleId,
}: {
  cohortId: string;
  roleId: string;
}) {
  const input = { cohort_id: cohortId, query: { role_id: roleId } },
    insights = useGetCohortInsights(input),
    [risk, setRisk] = useState(false),
    [search, setSearch] = useState(""),
    students = useListCohortStudents({
      ...input,
      query: { ...input.query, at_risk_only: risk },
    }),
    csv = useExportCohort(input),
    lock = useRef(false),
    [exporting, setExporting] = useState(false),
    [exportError, setExportError] = useState(""),
    [exported, setExported] = useState(false);
  const data = insights.data,
    rows = (students.data || []).filter(
      (s) =>
        (!risk || s.at_risk) &&
        (s.name + " " + (s.department || ""))
          .toLowerCase()
          .includes(search.trim().toLowerCase()),
    );
  async function download() {
    if (lock.current) return;
    lock.current = true;
    setExporting(true);
    setExportError("");
    setExported(false);
    try {
      const response = await csv.refetch();
      if (response.error) throw response.error;
      if (response.data == null) throw new Error("No CSV was returned.");
      const url = URL.createObjectURL(
          new Blob([response.data], { type: "text/csv;charset=utf-8" }),
        ),
        link = document.createElement("a");
      link.href = url;
      link.download = "careerlens-" + cohortId + "-" + roleId + ".csv";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setExported(true);
    } catch (e) {
      setExportError(errorMessage(e as Error));
    } finally {
      lock.current = false;
      setExporting(false);
    }
  }
  return (
    <>
      {insights.isPending ? (
        <Loading />
      ) : insights.isError ? (
        <Card className="p-6">
          <Failure
            error={insights.error}
            retry={() => void insights.refetch()}
          />
        </Card>
      ) : data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <KpiCard label="Students" value={data.student_count} icon={Users} />
            <KpiCard
              label="Analysed"
              value={data.analysed_count}
              icon={ScanLine}
            />
            <KpiCard
              label="Median readiness"
              value={
                data.median_score == null ? "—" : number(data.median_score)
              }
              icon={Gauge}
              explanation={
                <WhyPopover
                  label="Median readiness"
                  definition="The service returns the cohort median for this role. Individual score reasons are available from each student's report below."
                />
              }
            />
            <KpiCard
              label="At risk"
              value={data.at_risk_count}
              icon={CircleAlert}
              explanation={
                <WhyPopover
                  label="At risk"
                  definition="At-risk status is supplied by the service; no cutoff is inferred in this view."
                />
              }
            />
            <KpiCard
              label="Median coverage"
              value={
                data.median_coverage == null
                  ? "—"
                  : number(data.median_coverage) + "%"
              }
              icon={ShieldCheck}
              explanation={
                <WhyPopover
                  label="Median coverage"
                  definition="Evidence Coverage is the percentage of claimed skills with strong or moderate evidence. This is the service's cohort median."
                />
              }
            />
          </div>
          <div className="grid items-start gap-4 lg:grid-cols-2">
            <StackedBars
              title="Readiness bands"
              description="Analysed students, grouped by the service's readiness band."
              series={["Not ready", "Developing", "Ready"]}
              data={[
                {
                  label: "Students",
                  first: data.bands.not_ready,
                  second: data.bands.developing,
                  third: data.bands.ready,
                },
              ]}
            />
            <Counts
              title="Score distribution"
              rows={data.histogram.map((r) => ({
                label: r.bucket,
                count: r.count,
              }))}
            />
            <Counts
              title="Most common missing skills"
              rows={data.top_missing_skills.map((r) => ({
                label: r.skill_name,
                count: r.students,
              }))}
            />
            <Rates
              title="Unverified claim rates"
              kind="Unverified"
              rows={[...data.unverified_rate_by_skill]
                .sort((a, b) => b.unverified_rate - a.unverified_rate)
                .map((r) => ({ ...r, rate: r.unverified_rate }))}
            />
          </div>
          <Card className="space-y-4 p-6">
            <h2 className="text-lg font-semibold">Project understanding</h2>
            <p className="text-xs text-muted-readable">
              Latest verify status on each student&apos;s top project.
              Individual quiz answers and focus data stay private.
            </p>
            {data.understanding ? (
              <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
                {[
                  ["Quizzed", data.understanding.quizzed],
                  ["Demonstrated", data.understanding.demonstrated],
                  ["Partial", data.understanding.partial],
                  ["Not demonstrated yet", data.understanding.not_demonstrated],
                ].map(([label, value]) => (
                  <div key={label}>
                    <dt className="text-xs text-muted-readable">{label}</dt>
                    <dd className="mt-2 text-3xl font-bold tabular-nums">
                      {value}
                    </dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="text-sm text-muted-readable">
                Understanding statistics were not returned.
              </p>
            )}
          </Card>
          <Rates
            title="Built and explained"
            kind="Built + explained"
            rows={(data.understanding?.by_skill || []).map((r) => ({
              ...r,
              rate: r.built_and_explained_rate,
            }))}
          />
        </>
      ) : (
        <Card className="p-6">No cohort insights returned.</Card>
      )}
      <Card className="min-w-0 space-y-5 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">Students</h2>
          <Button
            variant="outline"
            disabled={exporting}
            onClick={() => void download()}
          >
            {exporting ? "Exporting…" : "Export CSV"}
          </Button>
        </div>
        {exportError && (
          <p role="alert" className="text-sm text-danger-readable">
            {exportError}
          </p>
        )}
        {exported && (
          <p role="status" className="text-xs text-success-readable">
            CSV download prepared for the selected cohort and role.
          </p>
        )}
        <div className="flex flex-wrap items-center gap-4">
          <label className="min-w-0 flex-1 space-y-2 text-xs font-semibold">
            Search students
            <input
              type="search"
              aria-label="Search students"
              placeholder="Name or department"
              className={control}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
          <label className="flex min-h-11 items-center gap-3 text-sm">
            <input
              type="checkbox"
              checked={risk}
              onChange={(e) => setRisk(e.target.checked)}
              className="size-5 accent-primary"
            />
            At risk only
          </label>
        </div>
        {students.isPending ? (
          <Loading />
        ) : students.isError ? (
          <Failure
            error={students.error}
            retry={() => void students.refetch()}
          />
        ) : !rows.length ? (
          <p className="text-sm text-muted-readable">
            {search || risk
              ? "No students match these filters."
              : "No students returned for this cohort and role."}
          </p>
        ) : (
          <div
            role="region"
            aria-label="Cohort students table"
            tabIndex={0}
            className="overflow-x-auto focus-visible:ring-2 focus-visible:ring-primary"
          >
            <table className="w-full min-w-[860px] text-left text-sm">
              <caption className="sr-only">
                Students for the selected cohort and target role
              </caption>
              <thead className="bg-surface-2 text-xs">
                <tr>
                  {[
                    "Student",
                    "Department",
                    "Readiness",
                    "Band",
                    "Coverage",
                    "Top gap",
                    "Understanding",
                    "Support",
                  ].map((h) => (
                    <th key={h} scope="col" className="p-3">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => (
                  <StudentRow key={s.profile_id} student={s} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
function StudentRow({ student: s }: { student: Schema["CohortStudent"] }) {
  return (
    <tr className="border-t border-border">
      <th scope="row" className="p-3 font-medium">
        <div className="flex items-center gap-3">
          <span className="icon-chip shrink-0" aria-hidden="true">
            {s.name.slice(0, 1)}
          </span>
          <div>
            {s.name}
            {s.analysis_id && (
              <Link
                href={"/report/" + encodeURIComponent(s.analysis_id)}
                className="mt-2 flex min-h-11 items-center text-xs text-primary-text underline"
              >
                View reasons
              </Link>
            )}
          </div>
        </div>
      </th>
      <td className="p-3">{s.department || "—"}</td>
      <td className="p-3">
        <ScoreRing size={72} value={s.score} band={s.band} label="Readiness" />
      </td>
      <td className="p-3">
        <BandBadge band={s.band} />
      </td>
      <td className="p-3 tabular-nums">{number(s.coverage)}%</td>
      <td className="p-3">{s.top_gap || "—"}</td>
      <td className="p-3">
        {s.understanding ? (
          <UnderstandingBadge understanding={s.understanding} />
        ) : (
          <span className="text-xs text-muted-readable">Not returned</span>
        )}
      </td>
      <td className="p-3">
        <span
          className={
            "status-pill " + (s.at_risk ? "tone-warning" : "tone-muted")
          }
        >
          {s.at_risk ? "At risk" : "No risk flag"}
        </span>
      </td>
    </tr>
  );
}
