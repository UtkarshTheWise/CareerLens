"use client";
/* Hallmark · pre-emit critique: P4 H4 E4 S4 R5 V3 — server-authoritative simulator. */
import { useEffect, useId, useMemo, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { useSimulateAnalysis } from "@/lib/api/hooks";
import { errorMessage } from "@/lib/api/transport";
import {
  signalOptions,
  simulationChanges,
  type SimulationSignal,
} from "@/lib/report-presentation";
import { ScoreRing, WhyPopover } from "@/components/career";
import { signed, type Schema } from "@/components/career/shared";
import { Button } from "@/components/ui/button";
import { Panel, Section } from "@/components/layout/page";
export function WhatIfPanel({
  analysisId,
  report,
}: {
  analysisId: string;
  report: Schema["AnalysisReport"];
}) {
  const { mutateAsync } = useSimulateAnalysis();
  const id = useId();
  const reduced = useReducedMotion();
  const generation = useRef(0);
  const [selected, setSelected] = useState<Record<string, SimulationSignal[]>>(
    {},
  );
  const [retry, setRetry] = useState(0);
  const [state, setState] = useState<{
    status: "idle" | "loading" | "ready" | "error";
    result?: Schema["SimulationResult"];
    error?: string;
  }>({ status: "idle" });
  const changes = useMemo(
    () => simulationChanges(selected, report.projects),
    [selected, report.projects],
  );
  useEffect(() => {
    if (!changes.length) return;
    let active = true;
    const token = ++generation.current;
    const timer = setTimeout(() => {
      setState({ status: "loading" });
      mutateAsync({ analysis_id: analysisId, body: { changes } })
        .then((result) => {
          if (active && token === generation.current)
            setState({ status: "ready", result });
        })
        .catch((error: Error) => {
          if (active && token === generation.current)
            setState({ status: "error", error: errorMessage(error) });
        });
    }, 350);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [analysisId, changes, retry, mutateAsync]);
  function toggle(project: string, signal: SimulationSignal, checked: boolean) {
    generation.current++;
    setState({ status: "idle" });
    setSelected((old) => ({
      ...old,
      [project]: checked
        ? [...(old[project] || []), signal]
        : (old[project] || []).filter((item) => item !== signal),
    }));
  }
  const projects = report.projects.filter((project) => project.kind === "code");
  return (
    <Section
      id="simulator"
      eyebrow="Preview"
      title="What if you improved the evidence?"
      description="Choose hypothetical changes. The analysis service recomputes the impact; your saved profile and report stay unchanged."
      actions={
        <Button
          variant="outline"
          className="min-h-11"
          disabled={!changes.length}
          onClick={() => {
            generation.current++;
            setSelected({});
            setState({ status: "idle" });
          }}
        >
          Reset preview
        </Button>
      }
    >
      <div className="space-y-4">
        {projects.length ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {projects.map((project) => (
              <fieldset key={project.project_id} className="panel min-w-0">
                <legend className="px-2 text-sm font-medium">
                  {project.title}
                </legend>
                <div className="hairline-list">
                  {signalOptions.map(({ value, label }) => {
                    const present = Boolean(project.signals?.[value]);
                    const inputId = `${id}-${project.project_id}-${value}`;
                    return (
                      <label
                        key={value}
                        htmlFor={inputId}
                        className={`flex min-h-12 items-center justify-between gap-3 py-2 text-[13px] transition-colors ${present ? "cursor-not-allowed text-muted-readable" : "cursor-pointer"}`}
                      >
                        <span className="flex items-center gap-3">
                          <input
                            id={inputId}
                            type="checkbox"
                            className="size-4 shrink-0 accent-primary"
                            aria-label={`${label} — ${project.title}`}
                            disabled={present}
                            checked={
                              present ||
                              Boolean(
                                selected[project.project_id]?.includes(value),
                              )
                            }
                            onChange={(e) =>
                              toggle(
                                project.project_id,
                                value,
                                e.target.checked,
                              )
                            }
                          />
                          {label}
                        </span>
                        {present && (
                          <span className="status-text tone-text-success">
                            Already evidenced
                          </span>
                        )}
                      </label>
                    );
                  })}
                </div>
              </fieldset>
            ))}
          </div>
        ) : (
          <p className="inset-note">
            No code projects are available for these signal changes.
          </p>
        )}
        <div
          role="status"
          aria-live="polite"
          className="text-sm text-muted-readable"
        >
          {!changes.length
            ? "Choose a change to preview its impact."
            : state.status === "loading"
              ? "Recomputing the preview…"
              : state.status === "idle"
                ? "Preparing your preview…"
                : state.status === "ready"
                  ? "Preview updated. Saved scores are unchanged."
                  : "Preview could not be updated."}
        </div>
        {state.status === "error" && (
          <div role="alert" className="panel space-y-3 border-danger">
            <p className="text-sm text-danger-readable">{state.error}</p>
            <Button
              variant="outline"
              className="min-h-11"
              onClick={() => {
                generation.current++;
                setState({ status: "idle" });
                setRetry((value) => value + 1);
              }}
            >
              Retry preview
            </Button>
          </div>
        )}
        {state.status === "ready" && state.result && (
          <Panel label="Hypothetical readiness">
            <div className="space-y-5">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <h3 className="text-sm font-medium">Change from this preview</h3>
                <motion.p
                  key={state.result.delta}
                  initial={reduced ? false : { opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: reduced ? 0 : 0.3 }}
                  className={`metric text-[32px]! ${state.result.delta < 0 ? "text-danger-readable" : "text-success-readable"}`}
                  aria-label={`Simulated score change: ${signed(state.result.delta)} points`}
                >
                  {signed(state.result.delta)}
                  <span className="metric-unit">pts</span>
                </motion.p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <ScoreRing
                  label="Before preview"
                  value={state.result.before.total}
                  band={state.result.before.band}
                  explanation={
                    <WhyPopover
                      label="Before preview"
                      components={state.result.before.components}
                      evidence={report.evidence}
                    />
                  }
                />
                <ScoreRing
                  label="After preview"
                  value={state.result.after.total}
                  band={state.result.after.band}
                  explanation={
                    <WhyPopover
                      label="After preview"
                      components={state.result.after.components}
                      evidence={report.evidence}
                    />
                  }
                />
              </div>
              <p className="inset-note">
                This is a hypothetical recomputation, not newly verified work.
                The supplied explanations show how its contributions changed.
              </p>
            </div>
          </Panel>
        )}
      </div>
    </Section>
  );
}
