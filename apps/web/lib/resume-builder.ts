import type { components } from "@careerlens/api-client";

/* Build a first resume in the app. Pure functions, no React and no scoring.
   The generated text only contains what the student typed (plus section headings): it never adds a skill,
   a number or a sentence of its own. The backend reads it as a plain-text resume (docs/PIPELINE.md stage 1). */

type Role = components["schemas"]["Role"];

export type ProjectEntry = { title: string; description: string; link: string; technologies: string };
export type ExperienceEntry = { org: string; role: string; start: string; end: string; bullets: string };
export type EducationEntry = { institution: string; degree: string; start: string; end: string; details: string };
export type ResumeDraft = {
  email: string;
  phone: string;
  links: string;
  headline: string;
  skills: string[];
  projects: ProjectEntry[];
  experience: ExperienceEntry[];
  education: EducationEntry[];
  certifications: string;
};

export const DRAFT_KEY = "careerlens.resume-draft.v1";
export const MAX_SKILLS = 30;
export const MAX_SKILL_LENGTH = 40;
export const MAX_ENTRIES = 12;
export const MAX_FIELD_LENGTH = 2000;
export const RECOMMENDED_SKILLS = 25;

export const emptyProject = (): ProjectEntry => ({ title: "", description: "", link: "", technologies: "" });
export const emptyExperience = (): ExperienceEntry => ({ org: "", role: "", start: "", end: "", bullets: "" });
export const emptyEducation = (): EducationEntry => ({ institution: "", degree: "", start: "", end: "", details: "" });

export function emptyDraft(): ResumeDraft {
  return {
    email: "",
    phone: "",
    links: "",
    headline: "",
    skills: [],
    projects: [],
    experience: [],
    education: [],
    certifications: "",
  };
}

const clean = (value: string) => value.trim();
const filled = (...values: string[]) => values.some((value) => clean(value));
const EMAIL = /^[^\s@]+@[^\s@]+[.][^\s@]+$/;

export function isBlankProject(entry: ProjectEntry) {
  return !filled(entry.title, entry.description, entry.link, entry.technologies);
}
export function isBlankExperience(entry: ExperienceEntry) {
  return !filled(entry.org, entry.role, entry.start, entry.end, entry.bullets);
}
export function isBlankEducation(entry: EducationEntry) {
  return !filled(entry.institution, entry.degree, entry.start, entry.end, entry.details);
}

/** Keys are field names the builder can show next to the field. Empty object = ready to send. */
export function draftErrors(draft: ResumeDraft, name: string): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!clean(name)) errors.name = "Enter your name to continue.";
  const email = clean(draft.email);
  const phone = clean(draft.phone);
  if (!email && !phone) errors.contact = "Add an email address or a phone number.";
  if (email && !EMAIL.test(email)) errors.email = "Enter a valid email address.";
  if (draft.skills.length < 1) errors.skills = "Add at least one skill.";
  const hasEntry =
    draft.projects.some((entry) => !isBlankProject(entry)) ||
    draft.experience.some((entry) => !isBlankExperience(entry)) ||
    draft.education.some((entry) => !isBlankEducation(entry));
  if (!hasEntry) errors.entries = "Add at least one project, experience or education entry.";
  draft.projects.forEach((entry, i) => {
    if (!isBlankProject(entry) && !clean(entry.title)) errors[`projects.${i}.title`] = "Give this project a title.";
  });
  draft.experience.forEach((entry, i) => {
    if (!isBlankExperience(entry) && !clean(entry.org) && !clean(entry.role))
      errors[`experience.${i}.org`] = "Add the organisation or your role.";
  });
  draft.education.forEach((entry, i) => {
    if (!isBlankEducation(entry) && !clean(entry.institution))
      errors[`education.${i}.institution`] = "Add the institution.";
  });
  const tooLong = [
    draft.links,
    draft.headline,
    draft.certifications,
    ...draft.projects.flatMap((entry) => [entry.title, entry.description, entry.link, entry.technologies]),
    ...draft.experience.flatMap((entry) => [entry.org, entry.role, entry.start, entry.end, entry.bullets]),
    ...draft.education.flatMap((entry) => [entry.institution, entry.degree, entry.start, entry.end, entry.details]),
  ].some((value) => value.length > MAX_FIELD_LENGTH);
  if (tooLong) errors.length = "One of your entries is too long. Keep each field under 2,000 characters.";
  if (draft.projects.length > MAX_ENTRIES || draft.experience.length > MAX_ENTRIES || draft.education.length > MAX_ENTRIES)
    errors.length = `Keep each section to ${MAX_ENTRIES} entries or fewer.`;
  return errors;
}

/** Suggestions only, never blocking. */
export function draftHints(draft: ResumeDraft): string[] {
  const hints: string[] = [];
  if (draft.skills.length > RECOMMENDED_SKILLS)
    hints.push(`You listed ${draft.skills.length} skills. A shorter list of skills you can point to reads more clearly.`);
  const writing = [
    ...draft.projects.map((entry) => entry.description),
    ...draft.experience.map((entry) => entry.bullets),
  ].join(" ");
  if (clean(writing) && !/[0-9]/.test(writing))
    hints.push("No numbers in your descriptions yet. Add them only if you measured them.");
  if (!clean(draft.links)) hints.push("A GitHub link on a project lets CareerLens look at the code behind it.");
  return hints;
}

function lines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function dates(start: string, end: string): string {
  return [clean(start), clean(end)].filter(Boolean).join(" - ");
}

export function resumeText(draft: ResumeDraft, name: string): string {
  const head = [clean(name), [clean(draft.email), clean(draft.phone)].filter(Boolean).join(" | ")];
  const links = lines(draft.links).join(" | ");
  if (links) head.push(links);
  if (clean(draft.headline)) head.push(clean(draft.headline));
  const blocks: string[] = [head.filter(Boolean).join("\n")];

  if (draft.skills.length) blocks.push(["SKILLS", draft.skills.join(", ")].join("\n"));

  const projects = draft.projects
    .filter((entry) => !isBlankProject(entry))
    .map((entry) =>
      [
        clean(entry.title),
        ...lines(entry.description),
        clean(entry.technologies) ? `Technologies: ${clean(entry.technologies)}` : "",
        clean(entry.link),
      ]
        .filter(Boolean)
        .join("\n"),
    );
  if (projects.length) blocks.push(["PROJECTS", projects.join("\n\n")].join("\n"));

  const experience = draft.experience
    .filter((entry) => !isBlankExperience(entry))
    .map((entry) =>
      [
        [clean(entry.org), clean(entry.role)].filter(Boolean).join(", "),
        dates(entry.start, entry.end),
        ...lines(entry.bullets).map((line) => (line.startsWith("-") ? line : `- ${line}`)),
      ]
        .filter(Boolean)
        .join("\n"),
    );
  if (experience.length) blocks.push(["EXPERIENCE", experience.join("\n\n")].join("\n"));

  const education = draft.education
    .filter((entry) => !isBlankEducation(entry))
    .map((entry) =>
      [
        [clean(entry.institution), clean(entry.degree)].filter(Boolean).join(", "),
        dates(entry.start, entry.end),
        ...lines(entry.details),
      ]
        .filter(Boolean)
        .join("\n"),
    );
  if (education.length) blocks.push(["EDUCATION", education.join("\n\n")].join("\n"));

  const certifications = lines(draft.certifications);
  if (certifications.length) blocks.push(["CERTIFICATIONS", ...certifications].join("\n"));

  return blocks.join("\n\n") + "\n";
}

export function resumeFile(draft: ResumeDraft, name: string): File {
  return new File([resumeText(draft, name)], "resume.txt", { type: "text/plain;charset=utf-8" });
}

/** Skills to suggest while typing. Comes only from the catalogue the API returns for GET /v1/roles. */
export function suggestSkills(
  roles: readonly Role[],
  roleId: string | undefined,
  chosen: readonly string[],
  query: string,
  limit = 12,
): { id: string; name: string }[] {
  const taken = new Set(chosen.map((skill) => skill.trim().toLowerCase()));
  const needle = query.trim().toLowerCase();
  const scored = new Map<string, { name: string; importance: number; roles: number }>();
  const selected = roleId ? roles.find((role) => role.id === roleId) : undefined;
  const pool = selected ? [selected] : roles;
  for (const role of pool) {
    for (const skill of role.skills) {
      const found = scored.get(skill.skill_id);
      if (found) {
        found.importance = Math.max(found.importance, skill.importance);
        found.roles += 1;
      } else scored.set(skill.skill_id, { name: skill.skill_name, importance: skill.importance, roles: 1 });
    }
  }
  return [...scored.entries()]
    .filter(([, skill]) => !taken.has(skill.name.toLowerCase()))
    .filter(([, skill]) => !needle || skill.name.toLowerCase().includes(needle))
    .sort(
      (a, b) =>
        b[1].importance - a[1].importance || b[1].roles - a[1].roles || a[1].name.localeCompare(b[1].name),
    )
    .slice(0, limit)
    .map(([id, skill]) => ({ id, name: skill.name }));
}

/** Returns the same array when nothing changes (empty, duplicate, too long or list full). */
export function addSkill(list: readonly string[], text: string): string[] {
  const skill = text.trim().replace(/\s+/g, " ");
  if (!skill || skill.length > MAX_SKILL_LENGTH || list.length >= MAX_SKILLS) return [...list];
  if (list.some((item) => item.toLowerCase() === skill.toLowerCase())) return [...list];
  return [...list, skill];
}

export function removeSkill(list: readonly string[], skill: string): string[] {
  return list.filter((item) => item !== skill);
}

/* ---- the draft lives in this browser only, so a student can come back to it ---- */

function isStrings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}
function entries<T extends Record<string, string>>(value: unknown, template: T): T[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const keys = Object.keys(template);
  const out: T[] = [];
  for (const item of value) {
    if (!item || typeof item !== "object") return undefined;
    const record = item as Record<string, unknown>;
    if (!keys.every((key) => typeof record[key] === "string")) return undefined;
    out.push(Object.fromEntries(keys.map((key) => [key, record[key] as string])) as T);
  }
  return out;
}

export function parseDraft(raw: string | null): ResumeDraft | null {
  if (!raw) return null;
  try {
    const data = JSON.parse(raw) as Record<string, unknown>;
    if (!data || typeof data !== "object") return null;
    const projects = entries(data.projects, emptyProject());
    const experience = entries(data.experience, emptyExperience());
    const education = entries(data.education, emptyEducation());
    const text = ["email", "phone", "links", "headline", "certifications"] as const;
    if (!projects || !experience || !education || !isStrings(data.skills)) return null;
    if (!text.every((key) => typeof data[key] === "string")) return null;
    return {
      email: data.email as string,
      phone: data.phone as string,
      links: data.links as string,
      headline: data.headline as string,
      certifications: data.certifications as string,
      skills: (data.skills as string[]).slice(0, MAX_SKILLS),
      projects: projects.slice(0, MAX_ENTRIES),
      experience: experience.slice(0, MAX_ENTRIES),
      education: education.slice(0, MAX_ENTRIES),
    };
  } catch {
    return null;
  }
}

export function loadDraft(): ResumeDraft | null {
  try {
    return parseDraft(window.localStorage.getItem(DRAFT_KEY));
  } catch {
    return null;
  }
}

export function saveDraft(draft: ResumeDraft) {
  try {
    window.localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  } catch {
    // Private windows and blocked storage: the form still works without a saved draft.
  }
}

export function clearDraft() {
  try {
    window.localStorage.removeItem(DRAFT_KEY);
  } catch {
    // Nothing to clear when storage is unavailable.
  }
}

export function hasDraftContent(draft: ResumeDraft): boolean {
  return (
    filled(draft.email, draft.phone, draft.links, draft.headline, draft.certifications) ||
    draft.skills.length > 0 ||
    draft.projects.some((entry) => !isBlankProject(entry)) ||
    draft.experience.some((entry) => !isBlankExperience(entry)) ||
    draft.education.some((entry) => !isBlankEducation(entry))
  );
}
