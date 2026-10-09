"use client";
import { useRef, useState } from "react";
import {
  useListCohorts,
  useListRoles,
  useGetCohortInsights,
  useListCohortStudents,
  useExportCohort,
} from "@/lib/api/hooks";
import { studentDirectory } from "@/lib/student-directory";
import {
  BAND_LABELS,
  DEFAULT_FILTERS,
  LEVEL_LABELS,
  LIMIT_CHOICES,
  SCORE_CHOICES,
  SORT_LABELS,
  cohortQuery,
  filterSummary,
  hasActiveFilters,
  skillOptions,
  type CohortFilters,
  type CohortSort,
  type MinLevel,
} from "@/lib/cohort-filters";
import { errorMessage } from "@/lib/api/transport";
import {
  ScoreRing,
  BandBadge,
  UnderstandingBadge,
  WhyPopover,
} from "@/components/career";
import { number, type Schema } from "@/components/career/shared";
import {
  Metric,
  PageHeader,
  Panel,
  Section,
  SelectRowGroup,
  StatusText,
  TextLink,
  type Tone,
} from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

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
    <div>
      <PageHeader
        eyebrow="Placement workspace"
        title="Cohort readiness"
        description="See the evidence gaps to address together, then find the students who fit a role or need support."
      />
      <Section>
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
            <label>
              <span className="field-label">Cohort</span>
              <select
                aria-label="Cohort"
                className="field"
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
            <label>
              <span className="field-label">Target role</span>
              <select
                aria-label="Target role"
                className="field"
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
      </Section>
      {cohort && role && (
        <CohortView
          key={cohort.id + role.id}
          cohortId={cohort.id}
          role={role}
        />
      )}
    </div>
  );
}
function Counts({
  title,
  rows,
  histogram = false,
}: {
  title: string;
  histogram?: boolean;
  rows: { label: string; count: number }[];
}) {
  const maximum = Math.max(1, ...rows.map((r) => r.count));
  return (
    <Panel title={title}>
      {rows.length && histogram ? (
        <div
          role="region"
          aria-label={title}
          tabIndex={0}
          className="overflow-x-auto focus-visible:ring-2 focus-visible:ring-primary"
        >
          <ul
            className="flex h-56 min-w-[480px] items-end gap-2"
            aria-label="Students by readiness score bucket"
          >
            {rows.map((r, i) => (
              <li
                key={i}
                className="flex h-full min-w-0 flex-1 flex-col justify-end gap-2 text-center text-xs"
              >
                <span className="tabular-nums">{r.count}</span>
                <div
                  aria-hidden="true"
                  className="mx-1 min-h-0 rounded-t-control bg-primary"
                  style={{ height: (r.count / maximum) * 150 }}
                />
                <span className="min-h-8 text-muted-readable">{r.label}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : rows.length ? (
        <ul className="space-y-4" aria-label={title}>
          {rows.map((r, i) => (
            <li key={i} className="space-y-2">
              <div className="flex justify-between gap-3 text-sm">
                <span className="break-anywhere">{r.label}</span>
                <span className="tabular-nums">{r.count}</span>
              </div>
              <div
                aria-hidden="true"
                className="h-2 overflow-hidden rounded-full bg-surface-2"
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
    </Panel>
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
  const [expanded, setExpanded] = useState(false);
  const visible = expanded ? rows : rows.slice(0, 6);
  return (
    <Panel title={title}>
      {rows.length ? (
        <div
          role="region"
          aria-label={title}
          tabIndex={0}
          className="overflow-x-auto focus-visible:ring-2 focus-visible:ring-primary"
        >
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{title}</caption>
            <thead className="border-b border-border text-xs text-muted-readable">
              <tr>
                <th scope="col" className="py-3 pr-3 font-medium">
                  Skill
                </th>
                <th scope="col" className="p-3 font-medium">
                  Claimed by
                </th>
                <th scope="col" className="p-3 font-medium">
                  {kind}
                </th>
              </tr>
            </thead>
            <tbody>
              {visible.map((r) => (
                <tr key={r.skill_id} className="border-t border-border first:border-t-0">
                  <th scope="row" className="py-3 pr-3 font-medium">
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
      {rows.length > 6 && (
        <Button
          variant="outline"
          className="mt-4"
          aria-expanded={expanded}
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "Show fewer skills" : `Show all ${rows.length} skills`}
        </Button>
      )}
    </Panel>
  );
}
function MetricCell({
  label,
  value,
  unit,
  definition,
}: {
  label: string;
  value: string | number;
  unit?: string;
  definition?: string;
}) {
  return (
    <div className="min-w-0 py-4 sm:px-6 sm:first:pl-0">
      <h3 className="eyebrow">{label}</h3>
      <div className="mt-2">
        <Metric value={value} unit={unit} />
      </div>
      {definition ? (
        <div className="-ml-3 mt-1">
          <WhyPopover label={label} definition={definition} />
        </div>
      ) : null}
    </div>
  );
}
const LEVEL_TEXT: Record<Schema["EvidenceLevel"], { label: string; tone: Tone }> = {
  strong: { label: "Strong", tone: "success" },
  moderate: { label: "Moderate", tone: "primary" },
  weak: { label: "Weak", tone: "warning" },
  unverified: { label: "Unverified claim", tone: "muted" },
  missing: { label: "Missing", tone: "danger" },
};
const BAND_KEYS = ["not_ready", "developing", "ready"] as const;

function FindStudents({
  filters,
  change,
  options,
}: {
  filters: CohortFilters;
  change: (next: Partial<CohortFilters>) => void;
  options: { id: string; name: string }[];
}) {
  const noSkills = filters.skills.length === 0;
  const toggleSkill = (id: string) =>
    change({
      skills: filters.skills.includes(id)
        ? filters.skills.filter((s) => s !== id)
        : [...filters.skills, id],
    });
  return (
    <Panel label="Filters combine: every one you set must match">
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="min-w-0">
          <h3 className="field-label">Skills</h3>
          <p className="field-hint mb-3">
            Choose up to 10. Students need evidence for the skill, not only a mention on a resume.
          </p>
          {options.length ? (
            <div className="max-h-72 overflow-y-auto rounded-control border border-border px-2">
              <SelectRowGroup
                label="Skills to find"
                multiple
                selectedIds={filters.skills}
                onSelect={toggleSkill}
                items={options.map((o) => ({ id: o.id, title: o.name }))}
              />
            </div>
          ) : (
            <p className="text-sm text-muted-readable">No skills to choose from for this role yet.</p>
          )}
          <fieldset className="mt-5" disabled={filters.skills.length < 2}>
            <legend className="field-label">A student must have</legend>
            <div className="flex flex-wrap gap-x-6">
              {(
                [
                  ["all", "All selected skills"],
                  ["any", "Any selected skill"],
                ] as const
              ).map(([value, label]) => (
                <label key={value} className="flex min-h-11 items-center gap-3 text-sm">
                  <input
                    type="radio"
                    name="skill-match"
                    value={value}
                    checked={filters.skillMatch === value}
                    onChange={() => change({ skillMatch: value })}
                    className="size-5 accent-primary"
                  />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>
        </div>
        <div className="grid min-w-0 content-start gap-4 sm:grid-cols-2">
          <label>
            <span className="field-label">Evidence for the skill</span>
            <select
              className="field"
              disabled={noSkills}
              value={filters.minLevel}
              onChange={(e) => change({ minLevel: e.target.value as MinLevel })}
            >
              {(Object.keys(LEVEL_LABELS) as MinLevel[]).map((k) => (
                <option key={k} value={k}>
                  {LEVEL_LABELS[k]}
                </option>
              ))}
            </select>
            {noSkills ? <p className="field-hint">Choose a skill first.</p> : null}
          </label>
          <label>
            <span className="field-label">Minimum readiness score</span>
            <select
              className="field"
              value={filters.minScore ?? ""}
              onChange={(e) =>
                change({ minScore: e.target.value === "" ? null : Number(e.target.value) })
              }
            >
              <option value="">Any</option>
              {SCORE_CHOICES.map((n) => (
                <option key={n} value={n}>
                  {n}+
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="field-label">Order</span>
            <select
              className="field"
              value={filters.sort}
              onChange={(e) => change({ sort: e.target.value as CohortSort })}
            >
              {(Object.keys(SORT_LABELS) as CohortSort[]).map((k) => (
                <option key={k} value={k}>
                  {SORT_LABELS[k]}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="field-label">Show</span>
            <select
              className="field"
              value={filters.limit ?? ""}
              onChange={(e) =>
                change({ limit: e.target.value === "" ? null : Number(e.target.value) })
              }
            >
              <option value="">All</option>
              {LIMIT_CHOICES.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <fieldset className="sm:col-span-2">
            <legend className="field-label">Readiness band</legend>
            <div className="flex flex-wrap gap-x-6">
              {BAND_KEYS.map((band) => (
                <label key={band} className="flex min-h-11 items-center gap-3 text-sm">
                  <input
                    type="checkbox"
                    checked={filters.bands.includes(band)}
                    onChange={(e) =>
                      change({
                        bands: e.target.checked
                          ? [...filters.bands, band]
                          : filters.bands.filter((b) => b !== band),
                      })
                    }
                    className="size-5 accent-primary"
                  />
                  {BAND_LABELS[band]}
                </label>
              ))}
            </div>
          </fieldset>
          <label className="flex min-h-11 items-center gap-3 text-sm sm:col-span-2">
            <input
              type="checkbox"
              checked={filters.atRiskOnly}
              onChange={(e) => change({ atRiskOnly: e.target.checked })}
              className="size-5 accent-primary"
            />
            At risk only
          </label>
        </div>
      </div>
    </Panel>
  );
}
function CohortView({
  cohortId,
  role,
}: {
  cohortId: string;
  role: Schema["Role"];
}) {
  const roleId = role.id,
    insights = useGetCohortInsights({
      cohort_id: cohortId,
      query: { role_id: roleId },
    }),
    [filters, setFilters] = useState<CohortFilters>(DEFAULT_FILTERS),
    [search, setSearch] = useState(""),
    [page, setPage] = useState(0),
    input = { cohort_id: cohortId, query: cohortQuery(roleId, filters) },
    students = useListCohortStudents(input),
    csv = useExportCohort(input),
    lock = useRef(false),
    [exporting, setExporting] = useState(false),
    [exportError, setExportError] = useState(""),
    [exported, setExported] = useState(false);
  const data = insights.data,
    options = skillOptions(role, data),
    names = Object.fromEntries(options.map((o) => [o.id, o.name])),
    active = hasActiveFilters(filters) || search.trim() !== "",
    rows = studentDirectory(students.data || [], search);
  const showMatches = filters.skills.length > 0;
  const pageCount = Math.max(1, Math.ceil(rows.length / 20));
  const currentPage = Math.min(page, pageCount - 1);
  const visibleRows = rows.slice(currentPage * 20, currentPage * 20 + 20);
  function change(next: Partial<CohortFilters>) {
    setFilters((f) => ({ ...f, ...next }));
    setPage(0);
  }
  function clear() {
    setFilters(DEFAULT_FILTERS);
    setSearch("");
    setPage(0);
  }
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
      <Section title="Cohort at a glance">
        {insights.isPending ? (
          <Loading />
        ) : insights.isError ? (
          <Failure
            error={insights.error}
            retry={() => void insights.refetch()}
          />
        ) : data ? (
          <Panel>
            <div className="grid divide-y divide-border sm:grid-cols-2 sm:divide-y-0 sm:divide-x lg:grid-cols-5">
              <MetricCell label="Students" value={data.student_count} />
              <MetricCell label="Analysed" value={data.analysed_count} />
              <MetricCell
                label="Median readiness"
                value={data.median_score == null ? "—" : number(data.median_score)}
                unit={data.median_score == null ? undefined : "/ 100"}
                definition="The service returns the cohort median for this role. Individual score reasons are available from each student's report below."
              />
              <MetricCell
                label="At risk"
                value={data.at_risk_count}
                definition="At-risk status is supplied by the service; no cutoff is inferred in this view."
              />
              <MetricCell
                label="Median coverage"
                value={data.median_coverage == null ? "—" : number(data.median_coverage) + "%"}
                definition="Evidence Coverage is the percentage of claimed skills with strong or moderate evidence. This is the service's cohort median."
              />
            </div>
          </Panel>
        ) : (
          <p className="text-sm text-muted-readable">No cohort insights returned.</p>
        )}
      </Section>
      <Section
        title="Find students"
        description="For example, two students with a good score and verified Docker. Results update as you choose, and the CSV export uses the same filters."
        actions={
          active ? (
            <Button variant="outline" onClick={clear}>
              Clear filters
            </Button>
          ) : null
        }
      >
        <FindStudents filters={filters} change={change} options={options} />
      </Section>
      <Section
        title="Students"
        actions={
          <Button
            variant="outline"
            disabled={exporting}
            onClick={() => void download()}
          >
            {exporting ? "Exporting…" : "Export CSV"}
          </Button>
        }
      >
        {exportError && (
          <p role="alert" className="mb-4 text-sm text-danger-readable">
            {exportError}
          </p>
        )}
        {exported && (
          <p role="status" className="mb-4 text-xs text-success-readable">
            CSV download prepared with the current filters.
          </p>
        )}
        <label className="mb-4 block max-w-md">
          <span className="field-label">Search students</span>
          <input
            type="search"
            aria-label="Search students"
            placeholder="Name or department"
            className="field"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
          />
        </label>
        {!students.isPending && !students.isError && (
          <div aria-live="polite" className="mb-4 text-sm">
            <p className="font-medium">
              {rows.length} {rows.length === 1 ? "student" : "students"} found
              {rows.length
                ? ` · showing ${currentPage * 20 + 1}–${Math.min((currentPage + 1) * 20, rows.length)}`
                : ""}
            </p>
            {hasActiveFilters(filters) ? (
              <p className="text-muted-readable">{filterSummary(filters, names)}</p>
            ) : null}
          </div>
        )}
        {students.isPending ? (
          <Loading />
        ) : students.isError ? (
          <Failure
            error={students.error}
            retry={() => void students.refetch()}
          />
        ) : !rows.length ? (
          <p className="inset-note">
            {active
              ? "No students match these filters. Try a lower evidence level or fewer skills."
              : "No students returned for this cohort and role."}
          </p>
        ) : (
          <Panel className="p-0">
            <div
              role="region"
              aria-label="Cohort students table"
              tabIndex={0}
              className="overflow-x-auto rounded-card focus-visible:ring-2 focus-visible:ring-primary"
            >
              <table className={"w-full text-left text-sm " + (showMatches ? "min-w-[1060px]" : "min-w-[860px]")}>
                <caption className="sr-only">
                  Students for the selected cohort and target role
                </caption>
                <thead className="border-b border-border text-xs text-muted-readable">
                  <tr>
                    {[
                      "Student",
                      "Department",
                      "Readiness",
                      "Band",
                      "Coverage",
                      ...(showMatches ? ["Matched evidence"] : []),
                      "Top gap",
                      "Understanding",
                      "Support",
                    ].map((h) => (
                      <th key={h} scope="col" className="p-4 font-medium">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {visibleRows.map((s) => (
                    <StudentRow key={s.profile_id} student={s} showMatches={showMatches} />
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        )}
        {pageCount > 1 && (
          <nav
            aria-label="Student pages"
            className="mt-4 flex flex-wrap items-center justify-between gap-3"
          >
            <Button
              variant="outline"
              disabled={currentPage === 0}
              onClick={() => setPage(currentPage - 1)}
            >
              Previous page
            </Button>
            <span className="text-xs text-muted-readable">
              Page {currentPage + 1} of {pageCount}
            </span>
            <Button
              variant="outline"
              disabled={currentPage + 1 >= pageCount}
              onClick={() => setPage(currentPage + 1)}
            >
              Next page
            </Button>
          </nav>
        )}
      </Section>
      {data && (
        <Section title="Cohort insights">
          <div className="grid min-w-0 grid-cols-1 items-start gap-4 lg:grid-cols-2">
            <Panel
              title="Readiness bands"
              footer={<span>Analysed students, grouped by the service&apos;s readiness band.</span>}
            >
              <ul className="space-y-4" aria-label="Readiness bands">
                {BAND_KEYS.map((key) => (
                  <li key={key} className="space-y-2">
                    <div className="flex items-center justify-between gap-3">
                      <BandBadge band={key} />
                      <span className="tabular-nums text-sm">
                        {data.bands[key]} students
                      </span>
                    </div>
                    <div
                      aria-hidden="true"
                      className="h-2 overflow-hidden rounded-full bg-surface-2"
                    >
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{
                          width:
                            (data.bands[key] /
                              Math.max(
                                1,
                                data.bands.not_ready +
                                  data.bands.developing +
                                  data.bands.ready,
                              )) *
                              100 +
                            "%",
                        }}
                      />
                    </div>
                    <span className="sr-only">
                      {BAND_LABELS[key]}: {data.bands[key]}
                    </span>
                  </li>
                ))}
              </ul>
            </Panel>
            <Counts
              title="Score distribution"
              histogram
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
          <div className="mt-4 space-y-4">
            <Panel
              title="Project understanding"
              footer={
                <span>
                  Latest verify status on each student&apos;s top project. Individual quiz
                  answers and focus data stay private.
                </span>
              }
            >
              {data.understanding ? (
                <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
                  {[
                    ["Quizzed", data.understanding.quizzed],
                    ["Demonstrated", data.understanding.demonstrated],
                    ["Partial", data.understanding.partial],
                    ["Not demonstrated yet", data.understanding.not_demonstrated],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <dt className="eyebrow">{label}</dt>
                      <dd className="mt-2">
                        <Metric value={value} />
                      </dd>
                    </div>
                  ))}
                </dl>
              ) : (
                <p className="text-sm text-muted-readable">
                  Understanding statistics were not returned.
                </p>
              )}
            </Panel>
            <Rates
              title="Built and explained"
              kind="Built + explained"
              rows={(data.understanding?.by_skill || []).map((r) => ({
                ...r,
                rate: r.built_and_explained_rate,
              }))}
            />
          </div>
        </Section>
      )}
    </>
  );
}
function StudentRow({
  student: s,
  showMatches,
}: {
  student: Schema["CohortStudent"];
  showMatches: boolean;
}) {
  return (
    <tr className="border-t border-border first:border-t-0">
      <th scope="row" className="p-4 font-medium">
        <div className="min-w-0">
          <span className="break-anywhere">{s.name}</span>
          {s.analysis_id && (
            <div className="mt-1 flex min-h-11 items-center">
              <TextLink href={"/report/" + encodeURIComponent(s.analysis_id)}>
                View reasons
              </TextLink>
            </div>
          )}
        </div>
      </th>
      <td className="p-4">{s.department || "—"}</td>
      <td className="p-4">
        <ScoreRing size={72} value={s.score} band={s.band} label="Readiness" />
      </td>
      <td className="p-4">
        <BandBadge band={s.band} />
      </td>
      <td className="p-4 tabular-nums">{number(s.coverage)}%</td>
      {showMatches && (
        <td className="p-4">
          {s.matched_skills?.length ? (
            <ul className="space-y-1" aria-label={"Evidence matched for " + s.name}>
              {s.matched_skills.map((m) => (
                <li key={m.skill_id}>
                  <StatusText tone={LEVEL_TEXT[m.level].tone}>
                    {m.skill_name}: {LEVEL_TEXT[m.level].label}
                  </StatusText>
                </li>
              ))}
            </ul>
          ) : (
            <span className="text-xs text-muted-readable">—</span>
          )}
        </td>
      )}
      <td className="p-4">{s.top_gap || "—"}</td>
      <td className="p-4">
        {s.understanding ? (
          <UnderstandingBadge understanding={s.understanding} />
        ) : (
          <span className="text-xs text-muted-readable">Not returned</span>
        )}
      </td>
      <td className="p-4">
        <StatusText tone={s.at_risk ? "warning" : "muted"}>
          {s.at_risk ? "At risk" : "No risk flag"}
        </StatusText>
      </td>
    </tr>
  );
}
