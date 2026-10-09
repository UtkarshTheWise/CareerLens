"use client";
import { useState } from "react";
import { Activity, FileCheck2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Disclosure,
  Metric,
  PageHeader,
  Panel,
  Section,
  SelectRowGroup,
  StatusText,
  TextLink,
  type Tone,
} from "@/components/layout/page";
import {
  KpiCard,
  ScoreRing,
  SegmentedGauge,
  TrendCard,
  StackedBars,
  LevelPill,
  BandBadge,
  EvidenceRow,
  FlagCard,
  MilestoneCard,
  StageProgress,
  WhyPopover,
} from "@/components/career";
import {
  CardFrame,
  number,
  type Schema,
  type ViewState,
} from "@/components/career/shared";
import type { TrendPeriod, TrendPoint } from "@/components/career/trend-card";
import json from "./fixture.json";
const fixture = json as Pick<
  Schema["AnalysisReport"],
  "score" | "coverage" | "claims" | "evidence"
> & {
  flag: Schema["ProjectFlag"];
  milestone: Schema["RoadmapMilestone"];
  cohort: Schema["CohortInsights"];
};
const history: Record<TrendPeriod, TrendPoint[]> = {
  weekly: [
    { label: "Sep 07", primary: 48, secondary: 40 },
    { label: "Sep 14", primary: 55, secondary: 45 },
    { label: "Sep 21", primary: 58, secondary: 55 },
    { label: "Sep 28", primary: 65.1, secondary: 62.5 },
  ],
  monthly: [
    { label: "Jul", primary: 38, secondary: 28 },
    { label: "Aug", primary: 48, secondary: 40 },
    { label: "Sep", primary: 65.1, secondary: 62.5 },
  ],
  yearly: [
    { label: "2024", primary: 22, secondary: 18 },
    { label: "2025", primary: 38, secondary: 28 },
    { label: "2026", primary: 65.1, secondary: 62.5 },
  ],
};
const levels = ["strong", "moderate", "weak", "unverified", "missing"] as const;
const bands = ["not_ready", "developing", "ready"] as const;
const stages = [
  "queued",
  "ingesting",
  "extracting",
  "collecting",
  "detecting",
  "judging",
  "scoring",
  "planning",
  "done",
  "failed",
] as const;
const stagePercent = [0, 10, 25, 40, 55, 70, 85, 92, 100, 70];
function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="mb-5">
      <p className="mb-2 text-xs text-muted-readable">{eyebrow}</p>
      <h2 className="text-xl!">{title}</h2>
      <p className="mt-2 text-sm text-muted-readable">{description}</p>
    </div>
  );
}
const tones: Tone[] = ["success", "warning", "danger", "muted", "primary"];
const sampleSkills = [
  { id: "python", title: "Python", secondary: "campus-api, 41 commits", status: <StatusText tone="success">Strong</StatusText> },
  { id: "docker", title: "Docker", secondary: "Dockerfile in 2 repositories", status: <StatusText tone="primary">Moderate</StatusText> },
  { id: "kubernetes", title: "Kubernetes", secondary: "Listed on the resume only", status: <StatusText tone="muted">Unverified claim</StatusText> },
];
const sampleDetail: Record<string, string> = {
  python: "Strong: a project that uses Python has recent commits and tests. This is sample text for the gallery.",
  docker: "Moderate: a Dockerfile is present, but there is no sign it was run in CI. Sample text.",
  kubernetes: "Unverified claim: listed on the resume with no matching project yet. Sample text.",
};

/** The homepage language for signed-in screens: see docs/DESIGN.md "App screens". */
function AppPrimitives() {
  const [single, setSingle] = useState<string>("python");
  const [multi, setMulti] = useState<string[]>(["python"]);
  return (
    <section aria-labelledby="app-primitives" className="space-y-2">
      <h2 id="app-primitives" className="section-title">App screen primitives</h2>
      <p className="lede">Eyebrow, page and section headers, panels, status text, selectable rows, disclosures and fields. Gallery text is sample content.</p>

      <PageHeader eyebrow="Your workspace" title="Page header" description="One h1 per screen, with an optional lede and actions." actions={<Button variant="outline">Secondary action</Button>} />

      <Section eyebrow="Section" title="Section with a hairline above" description="Sections are separated by rules, not nested cards.">
        <div className="grid gap-6 md:grid-cols-2">
          <Panel label="Panel with a label" footer={<><span>Coverage</span><span data-value>62.5%</span></>}>
            <Metric value="65" unit="/ 100" label="Readiness 65 out of 100" />
            <p className="lede mt-3">A panel is a flat surface with a rule under its label and a footer line.</p>
          </Panel>
          <Panel title="Panel with a title" actions={<TextLink href="/dashboard">Open</TextLink>}>
            <div className="flex flex-wrap gap-4">
              {tones.map((tone) => (
                <StatusText key={tone} tone={tone}>{tone}</StatusText>
              ))}
            </div>
            <p className="inset-note mt-4">An inset note holds explanations and sources.</p>
            <p className="mt-4 flex gap-6">
              <TextLink href="/dashboard">Internal link</TextLink>
              <TextLink href="https://example.com" external>External link</TextLink>
            </p>
          </Panel>
        </div>
      </Section>

      <Section title="Selectable rows">
        <div className="grid gap-8 md:grid-cols-2">
          <SelectRowGroup
            label="Skills, one selected"
            items={sampleSkills}
            selectedId={single}
            onSelect={setSingle}
            detail={sampleDetail[single]}
          />
          <SelectRowGroup
            label="Skills, several selected"
            multiple
            items={sampleSkills.map((s) => ({ ...s, secondary: undefined }))}
            selectedIds={multi}
            onSelect={(id) => setMulti((v) => (v.includes(id) ? v.filter((x) => x !== id) : [...v, id]))}
          />
        </div>
      </Section>

      <Section title="Disclosure and FAQ">
        <div className="grid gap-8 md:grid-cols-2">
          <div>
            <Disclosure summary="Look at the deliverable">
              <p className="inset-note">The thing a student produces to finish a milestone.</p>
            </Disclosure>
            <div className="border-t border-border" />
          </div>
          <div className="faq">
            <details>
              <summary>Native details row</summary>
              <p>Used for troubleshooting and questions.</p>
            </details>
            <details>
              <summary>Another row</summary>
              <p>The marker is a plus that turns into a cross when open.</p>
            </details>
          </div>
        </div>
      </Section>

      <Section title="Fields and chips">
        <div className="grid max-w-3xl gap-5 sm:grid-cols-2">
          <div>
            <label htmlFor="g-field" className="field-label">Text field</label>
            <input id="g-field" className="field" placeholder="Placeholder" />
            <p className="field-hint">Hint text sits under the field.</p>
          </div>
          <div>
            <label htmlFor="g-error" className="field-label">Field with an error</label>
            <input id="g-error" className="field" aria-invalid="true" defaultValue="Wrong value" aria-describedby="g-error-text" />
            <p id="g-error-text" className="field-error">Say what is wrong and how to fix it.</p>
          </div>
          <div className="sm:col-span-2 flex flex-wrap gap-2">
            {["Python", "SQL", "FastAPI"].map((skill) => (
              <span key={skill} className="chip">
                {skill}
                <button type="button" aria-label={"Remove " + skill}>×</button>
              </span>
            ))}
          </div>
          <div className="sm:col-span-2">
            <Button size="lg" trailingArrow>Primary action</Button>
          </div>
        </div>
      </Section>
    </section>
  );
}

export default function ComponentsPage() {
  const [state, setState] = useState<ViewState>("ready");
  const [milestone, setMilestone] = useState(fixture.milestone);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "error">(
    "idle",
  );
  const [stage, setStage] = useState<Schema["AnalysisStage"]>("judging");
  const [milestoneDisabled, setMilestoneDisabled] = useState(false);
  const score = fixture.score;
  const component = score.components[0];
  return (
    <div className="space-y-10">
      <header>
        <p className="mb-3 text-xs font-medium text-primary-text">
          Design preview · F2
        </p>
        <h1>Evidence, made clear.</h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-readable">
          Reusable views for readiness, evidence and next steps. This page uses
          synthetic preview data; it does not change a student profile.
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          <span className="status-pill tone-muted">12 components</span>
          <span className="status-pill tone-primary">Light + dark</span>
          <span className="status-pill tone-muted">
            Frozen contract fixtures
          </span>
        </div>
      </header>
      <section aria-labelledby="metrics-title">
        <SectionHeading
          eyebrow="01 / Numbers"
          title="A clear view of readiness"
          description="Scores and gains stay traceable to the analysis. Charts include a text alternative."
        />
        <div className="grid gap-4 md:grid-cols-3">
          <KpiCard
            label="Job readiness"
            value={number(score.total)}
            icon={Activity}
            explanation={
              <WhyPopover
                label="Job readiness"
                components={score.components}
                evidence={fixture.evidence}
              />
            }
          />
          <KpiCard
            label="Evidence Coverage"
            value={`${fixture.coverage}%`}
            icon={FileCheck2}
            explanation={
              <WhyPopover
                label="Evidence Coverage"
                definition="Evidence Coverage is the percentage of claimed catalogue skills supported at strong or moderate level. Claims outside the catalogue are reported separately."
              />
            }
          />
          <KpiCard
            label="Verified skills"
            value={5}
            icon={ShieldCheck}
            delta={{
              value: "+2",
              direction: "up",
              sentiment: "positive",
              period: "illustrative change",
            }}
          />
        </div>
        <div className="mt-4 grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)]">
          <CardFrame>
            <h2 id="metrics-title">ScoreRing + SegmentedGauge</h2>
            <div className="flex flex-wrap items-start justify-center gap-6">
              <ScoreRing
                value={score.total}
                label="Readiness"
                band={score.band}
                explanation={
                  <>
                    <BandBadge band={score.band} />
                    <WhyPopover
                      label="Readiness"
                      components={score.components}
                      evidence={fixture.evidence}
                    />
                  </>
                }
              />
              <ScoreRing
                value={fixture.coverage}
                label="Coverage"
                explanation={
                  <WhyPopover
                    label="Coverage"
                    definition="Claimed catalogue skills at strong or moderate level ÷ all claimed catalogue skills × 100."
                  />
                }
              />
            </div>
            <div className="border-t border-border pt-4">
              <h3 className="mb-4 text-sm font-semibold">
                Effective component weights
              </h3>
              <SegmentedGauge
                label="Effective score weights"
                segments={score.components.map((c) => ({
                  label: c.label,
                  value: c.weight * 100,
                }))}
              />
            </div>
          </CardFrame>
          <div className="space-y-4">
            <TrendCard
              title="Readiness over time"
              description="Illustrative history for the component preview."
              series={["Readiness", "Coverage"]}
              datasets={history}
            />
            <StackedBars
              title="Cohort readiness bands"
              description="Supplied synthetic cohort example · students analysed."
              series={["Not ready", "Developing", "Ready"]}
              data={[
                {
                  label: "Demo cohort",
                  first: fixture.cohort.bands.not_ready,
                  second: fixture.cohort.bands.developing,
                  third: fixture.cohort.bands.ready,
                },
              ]}
            />
          </div>
        </div>
      </section>
      <section>
        <SectionHeading
          eyebrow="02 / Evidence"
          title="Show the work behind the number"
          description="Levels, reasons and links give each claim context."
        />
        <CardFrame>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2>LevelPill + BandBadge</h2>
            <WhyPopover
              label={component.label}
              reasons={component.reasons}
              evidence={fixture.evidence}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {levels.map((level) => (
              <LevelPill key={level} level={level} />
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {bands.map((band) => (
              <BandBadge key={band} band={band} />
            ))}
          </div>
          <div className="mt-2">
            <h3 className="mb-3 text-sm font-semibold">EvidenceRow</h3>
            {fixture.claims.slice(0, 3).map((claim) => (
              <EvidenceRow
                key={claim.skill_id}
                claim={claim}
                evidence={fixture.evidence}
              />
            ))}
          </div>
        </CardFrame>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <FlagCard flag={fixture.flag} />
          <CardFrame>
            <h2>WhyPopover</h2>
            <p className="text-sm text-muted-readable">
              Each component keeps its supplied reasons, positive and withheld
              points, and evidence references.
            </p>
            <div className="flex flex-wrap gap-2">
              {score.components.map((c) => (
                <div
                  key={c.key}
                  className="flex min-w-0 items-center gap-2 rounded-control border border-border p-2"
                >
                  <span className="text-xs">{c.label}</span>
                  <WhyPopover
                    label={c.label}
                    reasons={c.reasons}
                    evidence={fixture.evidence}
                  />
                </div>
              ))}
            </div>
          </CardFrame>
        </div>
      </section>
      <section>
        <SectionHeading
          eyebrow="03 / Next steps"
          title="Make progress visible"
          description="Controlled milestone and analysis states, ready for their later screen integrations."
        />
        <div className="grid items-start gap-4 md:grid-cols-2">
          <div className="space-y-4">
            <MilestoneCard
              milestone={milestone}
              saving={saveState === "saving"}
              disabled={milestoneDisabled}
              error={
                saveState === "error"
                  ? "Couldn’t save this milestone. Please try again."
                  : undefined
              }
              onDoneChange={(done) => {
                setMilestone({ ...milestone, done });
                setSaveState("idle");
              }}
              onRetry={() => setSaveState("idle")}
            />
            <CardFrame>
              <h2>Milestone state controls</h2>
              <p className="text-xs text-muted-readable">
                Preview only; no API writes or persistence.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  className="min-h-11"
                  onClick={() => setSaveState("saving")}
                >
                  Preview saving
                </Button>
                <Button
                  variant="outline"
                  className="min-h-11"
                  onClick={() => setSaveState("error")}
                >
                  Preview save error
                </Button>
                <Button
                  variant="outline"
                  className="min-h-11"
                  aria-pressed={milestoneDisabled}
                  onClick={() => setMilestoneDisabled(!milestoneDisabled)}
                >
                  Toggle disabled
                </Button>
                <Button
                  variant="outline"
                  className="min-h-11"
                  onClick={() => {
                    setSaveState("idle");
                    setMilestoneDisabled(false);
                    setMilestone(fixture.milestone);
                  }}
                >
                  Reset milestone
                </Button>
              </div>
            </CardFrame>
          </div>
          <CardFrame>
            <h2>StageProgress</h2>
            <label
              className="text-xs font-medium text-muted-readable"
              htmlFor="preview-stage"
            >
              Preview analysis stage
            </label>
            <select
              id="preview-stage"
              value={stage}
              className="h-11 w-full rounded-control border border-border bg-surface-2 px-3 text-sm"
              onChange={(e) =>
                setStage(e.target.value as Schema["AnalysisStage"])
              }
            >
              {stages.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <StageProgress
              status={stage}
              progress={stagePercent[stages.indexOf(stage)]}
              lastStage={stage === "failed" ? "judging" : undefined}
              error={
                stage === "failed"
                  ? "Project review is unavailable. Please try the analysis again."
                  : null
              }
            />
          </CardFrame>
        </div>
      </section>
      <section>
        <SectionHeading
          eyebrow="04 / States"
          title="Useful even when data is missing"
          description="Loading, empty and contract-error patterns share the same geometry."
        />
        <CardFrame>
          <label className="text-xs font-medium" htmlFor="preview-state">
            Preview data state
          </label>
          <select
            id="preview-state"
            value={state}
            onChange={(e) => setState(e.target.value as ViewState)}
            className="h-11 w-full rounded-control border border-border bg-surface-2 px-3 text-sm"
          >
            {["ready", "loading", "empty", "error"].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </CardFrame>
        <div className="mt-4 grid items-start gap-4 md:grid-cols-2">
          <KpiCard
            label="Preview metric"
            value={score.total}
            icon={Activity}
            state={state}
            message={
              state === "error"
                ? "The analysis could not be loaded. Please try again."
                : "Complete an analysis to see this metric."
            }
          />
          <TrendCard
            title="Preview trend states"
            series={["Readiness", "Coverage"]}
            datasets={history}
            state={state}
            message={
              state === "error"
                ? "The score history could not be loaded. Please try again."
                : "History appears after more than one analysis."
            }
          />
        </div>
      </section>
      <AppPrimitives />
    </div>
  );
}
