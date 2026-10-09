"use client";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import type { components } from "@careerlens/api-client";
import { Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Disclosure, SelectRowGroup } from "@/components/layout/page";
import {
  MAX_ENTRIES,
  MAX_SKILLS,
  MAX_SKILL_LENGTH,
  addSkill,
  clearDraft,
  draftHints,
  emptyDraft,
  emptyEducation,
  emptyExperience,
  emptyProject,
  removeSkill,
  resumeText,
  suggestSkills,
  type EducationEntry,
  type ExperienceEntry,
  type ProjectEntry,
  type ResumeDraft,
} from "@/lib/resume-builder";

type Role = components["schemas"]["Role"];

function Field({
  id,
  label,
  hint,
  error,
  optional,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  optional?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="min-w-0">
      <label htmlFor={id} className="field-label">
        {label}
        {optional ? <span className="ml-1 text-xs font-normal text-muted-readable">(optional)</span> : null}
      </label>
      {children}
      {error ? (
        <p id={`${id}-help`} className="field-error">{error}</p>
      ) : hint ? (
        <p id={`${id}-help`} className="field-hint">{hint}</p>
      ) : null}
    </div>
  );
}

function fieldProps(id: string, error?: string, hint?: string) {
  return {
    id,
    "aria-invalid": error ? (true as const) : undefined,
    "aria-describedby": error || hint ? `${id}-help` : undefined,
  };
}

function BuilderSection({
  title,
  description,
  error,
  children,
}: {
  title: string;
  description?: string;
  error?: string;
  children: ReactNode;
}) {
  const titleId = useId();
  return (
    <section aria-labelledby={titleId} className="space-y-4 border-t border-border pt-6 first:border-t-0 first:pt-0">
      <div>
        <h3 id={titleId} className="text-base font-medium tracking-[-.02em]">{title}</h3>
        {description ? <p className="field-hint">{description}</p> : null}
        {error ? <p role="alert" className="field-error">{error}</p> : null}
      </div>
      {children}
    </section>
  );
}

function SkillPicker({
  draft,
  onChange,
  roleId,
  roles,
  error,
}: {
  draft: ResumeDraft;
  onChange: (next: ResumeDraft) => void;
  roleId?: string;
  roles: readonly Role[];
  error?: string;
}) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [note, setNote] = useState("");
  const role = roles.find((item) => item.id === roleId);
  const suggestions = suggestSkills(roles, roleId, draft.skills, query);
  const full = draft.skills.length >= MAX_SKILLS;

  function add(text: string) {
    const next = addSkill(draft.skills, text);
    if (next.length === draft.skills.length) {
      const trimmed = text.trim();
      if (!trimmed) return;
      setNote(
        full
          ? `You can list up to ${MAX_SKILLS} skills.`
          : trimmed.length > MAX_SKILL_LENGTH
            ? `Keep a skill under ${MAX_SKILL_LENGTH} characters.`
            : `${trimmed} is already in your list.`,
      );
      return;
    }
    setNote(`Added ${next[next.length - 1]}.`);
    onChange({ ...draft, skills: next });
    setQuery("");
  }

  return (
    <div className="space-y-4">
      <Field
        id={`${id}-input`}
        label="Add a skill"
        hint="Add skills you can point to in a project, job or course. A skill that appears only in this list shows as an Unverified claim until your work backs it."
        error={error}
      >
        <div className="flex gap-2">
          <input
            ref={input}
            {...fieldProps(`${id}-input`, error, "hint")}
            className="field"
            value={query}
            maxLength={80}
            autoComplete="off"
            placeholder="Type a skill, or pick one below"
            disabled={full}
            onChange={(event) => {
              setQuery(event.target.value);
              setNote("");
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                add(query);
              }
            }}
          />
          <Button type="button" variant="outline" onClick={() => add(query)} disabled={full || !query.trim()}>
            <Plus aria-hidden="true" />
            Add
          </Button>
        </div>
      </Field>
      <p role="status" aria-live="polite" className="min-h-5 text-xs text-muted-readable">{note}</p>

      {draft.skills.length ? (
        <ul aria-label="Your skills" className="flex flex-wrap gap-2">
          {draft.skills.map((skill) => (
            <li key={skill} className="chip">
              <span className="break-anywhere">{skill}</span>
              <button
                type="button"
                aria-label={`Remove ${skill}`}
                onClick={() => {
                  onChange({ ...draft, skills: removeSkill(draft.skills, skill) });
                  setNote(`Removed ${skill}.`);
                  input.current?.focus();
                }}
              >
                <X size={16} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {!full && suggestions.length ? (
        <div>
          <p className="field-label">{role ? `Suggested skills for ${role.name}` : "Common across roles"}</p>
          <SelectRowGroup
            label={role ? `Suggested skills for ${role.name}` : "Common skills across roles"}
            items={suggestions.map((skill) => ({ id: skill.id, title: skill.name }))}
            onSelect={(skillId) => {
              const picked = suggestions.find((skill) => skill.id === skillId);
              if (picked) add(picked.name);
            }}
          />
        </div>
      ) : null}
    </div>
  );
}

function EntryList<T>({
  noun,
  entries,
  make,
  onChange,
  render,
}: {
  noun: string;
  entries: T[];
  make: () => T;
  onChange: (next: T[]) => void;
  render: (entry: T, index: number, set: (patch: Partial<T>) => void) => ReactNode;
}) {
  const list = useRef<HTMLOListElement>(null);
  const addButton = useRef<HTMLButtonElement>(null);
  const [focusAt, setFocusAt] = useState<number | "add" | null>(null);

  useEffect(() => {
    if (focusAt === null) return;
    if (focusAt === "add") addButton.current?.focus();
    else
      list.current
        ?.querySelectorAll<HTMLElement>("[data-entry]")
        [focusAt]?.querySelector<HTMLElement>("input, textarea")
        ?.focus();
    setFocusAt(null);
  }, [focusAt, entries.length]);

  return (
    <div className="space-y-4">
      {entries.length ? (
        <ol ref={list} className="space-y-4">
          {entries.map((entry, index) => (
            <li key={index} data-entry className="rounded-control border border-border p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-sm font-medium">{`${noun} ${index + 1}`}</p>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  aria-label={`Remove ${noun.toLowerCase()} ${index + 1}`}
                  onClick={() => {
                    onChange(entries.filter((_, i) => i !== index));
                    setFocusAt(index > 0 ? index - 1 : entries.length > 1 ? 0 : "add");
                  }}
                >
                  <X aria-hidden="true" />
                  Remove
                </Button>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                {render(entry, index, (patch) =>
                  onChange(entries.map((item, i) => (i === index ? { ...item, ...patch } : item))),
                )}
              </div>
            </li>
          ))}
        </ol>
      ) : null}
      <Button
        ref={addButton}
        type="button"
        variant="outline"
        disabled={entries.length >= MAX_ENTRIES}
        onClick={() => {
          onChange([...entries, make()]);
          setFocusAt(entries.length);
        }}
      >
        <Plus aria-hidden="true" />
        {`Add ${noun.toLowerCase()}`}
      </Button>
    </div>
  );
}

/** Build a first resume without a file. The text sent is shown in the preview, and contains only what is typed here. */
export function ResumeBuilder({
  name,
  draft,
  onChange,
  roleId,
  roles,
  errors,
}: {
  name: string;
  draft: ResumeDraft;
  onChange: (next: ResumeDraft) => void;
  roleId?: string;
  roles: readonly Role[];
  errors: Record<string, string>;
}) {
  const id = useId();
  const hints = draftHints(draft);
  const set = (patch: Partial<ResumeDraft>) => onChange({ ...draft, ...patch });

  return (
    <div className="space-y-8" data-component="ResumeBuilder">
      <BuilderSection title="Contact" error={errors.contact}>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id={`${id}-email`} label="Email" error={errors.email} hint="We use it only to build your resume text.">
            <input
              {...fieldProps(`${id}-email`, errors.email, "hint")}
              className="field"
              type="email"
              autoComplete="email"
              value={draft.email}
              onChange={(event) => set({ email: event.target.value })}
            />
          </Field>
          <Field id={`${id}-phone`} label="Phone" optional>
            <input
              {...fieldProps(`${id}-phone`)}
              className="field"
              type="tel"
              autoComplete="tel"
              value={draft.phone}
              onChange={(event) => set({ phone: event.target.value })}
            />
          </Field>
        </div>
        <Field
          id={`${id}-links`}
          label="Links"
          optional
          hint="One per line, for example your GitHub profile or portfolio."
        >
          <textarea
            {...fieldProps(`${id}-links`, undefined, "hint")}
            className="field"
            autoCapitalize="none"
            spellCheck={false}
            value={draft.links}
            onChange={(event) => set({ links: event.target.value })}
          />
        </Field>
        <Field id={`${id}-headline`} label="Headline" optional hint="One line about what you do, in your own words.">
          <input
            {...fieldProps(`${id}-headline`, undefined, "hint")}
            className="field"
            value={draft.headline}
            onChange={(event) => set({ headline: event.target.value })}
          />
        </Field>
      </BuilderSection>

      <BuilderSection title="Skills">
        <SkillPicker draft={draft} onChange={onChange} roleId={roleId} roles={roles} error={errors.skills} />
      </BuilderSection>

      <BuilderSection
        title="Projects, experience and education"
        description="Add at least one. Say what you did and what changed. Add a number only if you measured it."
        error={errors.entries}
      >
        <div className="space-y-8">
          <div className="space-y-3">
            <h4 className="text-sm font-medium">Projects</h4>
            <EntryList<ProjectEntry>
              noun="Project"
              entries={draft.projects}
              make={emptyProject}
              onChange={(projects) => set({ projects })}
              render={(entry, index, patch) => (
                <>
                  <Field id={`${id}-p${index}-title`} label="Title" error={errors[`projects.${index}.title`]}>
                    <input
                      {...fieldProps(`${id}-p${index}-title`, errors[`projects.${index}.title`])}
                      className="field"
                      value={entry.title}
                      onChange={(event) => patch({ title: event.target.value })}
                    />
                  </Field>
                  <Field
                    id={`${id}-p${index}-link`}
                    label="Link"
                    optional
                    hint="A GitHub link lets CareerLens look at the code."
                  >
                    <input
                      {...fieldProps(`${id}-p${index}-link`, undefined, "hint")}
                      className="field"
                      autoCapitalize="none"
                      spellCheck={false}
                      value={entry.link}
                      onChange={(event) => patch({ link: event.target.value })}
                    />
                  </Field>
                  <div className="sm:col-span-2">
                    <Field
                      id={`${id}-p${index}-description`}
                      label="What it does and what you did"
                      hint="Say what you did and what changed. Add a number only if you measured it."
                    >
                      <textarea
                        {...fieldProps(`${id}-p${index}-description`, undefined, "hint")}
                        className="field"
                        value={entry.description}
                        onChange={(event) => patch({ description: event.target.value })}
                      />
                    </Field>
                  </div>
                  <div className="sm:col-span-2">
                    <Field id={`${id}-p${index}-tech`} label="Technologies" optional>
                      <input
                        {...fieldProps(`${id}-p${index}-tech`)}
                        className="field"
                        value={entry.technologies}
                        onChange={(event) => patch({ technologies: event.target.value })}
                      />
                    </Field>
                  </div>
                </>
              )}
            />
          </div>

          <div className="space-y-3">
            <h4 className="text-sm font-medium">Experience</h4>
            <EntryList<ExperienceEntry>
              noun="Experience"
              entries={draft.experience}
              make={emptyExperience}
              onChange={(experience) => set({ experience })}
              render={(entry, index, patch) => (
                <>
                  <Field id={`${id}-x${index}-org`} label="Organisation" error={errors[`experience.${index}.org`]}>
                    <input
                      {...fieldProps(`${id}-x${index}-org`, errors[`experience.${index}.org`])}
                      className="field"
                      value={entry.org}
                      onChange={(event) => patch({ org: event.target.value })}
                    />
                  </Field>
                  <Field id={`${id}-x${index}-role`} label="Your role">
                    <input
                      {...fieldProps(`${id}-x${index}-role`)}
                      className="field"
                      value={entry.role}
                      onChange={(event) => patch({ role: event.target.value })}
                    />
                  </Field>
                  <Field id={`${id}-x${index}-start`} label="Start" optional>
                    <input
                      {...fieldProps(`${id}-x${index}-start`)}
                      className="field"
                      placeholder="Jun 2025"
                      value={entry.start}
                      onChange={(event) => patch({ start: event.target.value })}
                    />
                  </Field>
                  <Field id={`${id}-x${index}-end`} label="End" optional>
                    <input
                      {...fieldProps(`${id}-x${index}-end`)}
                      className="field"
                      placeholder="Aug 2025 or Present"
                      value={entry.end}
                      onChange={(event) => patch({ end: event.target.value })}
                    />
                  </Field>
                  <div className="sm:col-span-2">
                    <Field
                      id={`${id}-x${index}-bullets`}
                      label="What you did"
                      hint="One point per line. Say what you did and what changed. Add a number only if you measured it."
                    >
                      <textarea
                        {...fieldProps(`${id}-x${index}-bullets`, undefined, "hint")}
                        className="field"
                        value={entry.bullets}
                        onChange={(event) => patch({ bullets: event.target.value })}
                      />
                    </Field>
                  </div>
                </>
              )}
            />
          </div>

          <div className="space-y-3">
            <h4 className="text-sm font-medium">Education</h4>
            <EntryList<EducationEntry>
              noun="Education"
              entries={draft.education}
              make={emptyEducation}
              onChange={(education) => set({ education })}
              render={(entry, index, patch) => (
                <>
                  <Field
                    id={`${id}-e${index}-institution`}
                    label="Institution"
                    error={errors[`education.${index}.institution`]}
                  >
                    <input
                      {...fieldProps(`${id}-e${index}-institution`, errors[`education.${index}.institution`])}
                      className="field"
                      value={entry.institution}
                      onChange={(event) => patch({ institution: event.target.value })}
                    />
                  </Field>
                  <Field id={`${id}-e${index}-degree`} label="Degree or course" optional>
                    <input
                      {...fieldProps(`${id}-e${index}-degree`)}
                      className="field"
                      value={entry.degree}
                      onChange={(event) => patch({ degree: event.target.value })}
                    />
                  </Field>
                  <Field id={`${id}-e${index}-start`} label="Start" optional>
                    <input
                      {...fieldProps(`${id}-e${index}-start`)}
                      className="field"
                      value={entry.start}
                      onChange={(event) => patch({ start: event.target.value })}
                    />
                  </Field>
                  <Field id={`${id}-e${index}-end`} label="End" optional>
                    <input
                      {...fieldProps(`${id}-e${index}-end`)}
                      className="field"
                      value={entry.end}
                      onChange={(event) => patch({ end: event.target.value })}
                    />
                  </Field>
                  <div className="sm:col-span-2">
                    <Field id={`${id}-e${index}-details`} label="Details" optional hint="One per line, such as relevant courses.">
                      <textarea
                        {...fieldProps(`${id}-e${index}-details`, undefined, "hint")}
                        className="field"
                        value={entry.details}
                        onChange={(event) => patch({ details: event.target.value })}
                      />
                    </Field>
                  </div>
                </>
              )}
            />
          </div>
        </div>
      </BuilderSection>

      <BuilderSection title="Certifications" description="Optional. One per line.">
        <Field id={`${id}-certs`} label="Certifications" optional>
          <textarea
            {...fieldProps(`${id}-certs`)}
            className="field"
            value={draft.certifications}
            onChange={(event) => set({ certifications: event.target.value })}
          />
        </Field>
      </BuilderSection>

      {errors.length ? <p role="alert" className="field-error">{errors.length}</p> : null}

      {hints.length ? (
        <div className="inset-note" aria-label="Suggestions">
          <ul className="list-disc space-y-1 pl-5">
            {hints.map((hint) => (
              <li key={hint}>{hint}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div>
        <Disclosure summary="Preview the text we will send">
          <pre className="inset-note max-h-96 overflow-auto whitespace-pre-wrap break-words font-mono text-xs text-text">
            {resumeText(draft, name)}
          </pre>
        </Disclosure>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
          <p className="field-hint max-w-prose">
            This draft is saved in this browser only so you can come back to it. It is cleared after your resume is sent, or with Clear draft.
          </p>
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              clearDraft();
              onChange(emptyDraft());
            }}
          >
            Clear draft
          </Button>
        </div>
      </div>
    </div>
  );
}
