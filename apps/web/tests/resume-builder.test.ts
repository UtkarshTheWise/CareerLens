import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import {
  DRAFT_KEY,
  MAX_SKILLS,
  addSkill,
  clearDraft,
  draftErrors,
  draftHints,
  emptyDraft,
  emptyEducation,
  emptyExperience,
  emptyProject,
  loadDraft,
  parseDraft,
  resumeFile,
  resumeText,
  saveDraft,
  suggestSkills,
  type ResumeDraft,
} from "../lib/resume-builder";

const roles = [
  {
    id: "sde-backend",
    name: "Backend Developer",
    category: "engineering" as const,
    skills: [
      { skill_id: "python", skill_name: "Python", importance: 3 },
      { skill_id: "sql", skill_name: "SQL", importance: 3 },
      { skill_id: "docker", skill_name: "Docker", importance: 2 },
      { skill_id: "git", skill_name: "Git", importance: 1 },
    ],
  },
  {
    id: "data-analyst",
    name: "Data Analyst",
    category: "data" as const,
    skills: [
      { skill_id: "sql", skill_name: "SQL", importance: 3 },
      { skill_id: "python", skill_name: "Python", importance: 2 },
      { skill_id: "tableau", skill_name: "Tableau", importance: 2 },
      { skill_id: "git", skill_name: "Git", importance: 1 },
    ],
  },
];

const draft: ResumeDraft = {
  ...emptyDraft(),
  email: "asha@example.com",
  phone: "+91 98765 43210",
  links: "https://github.com/ashav",
  skills: ["Python", "SQL"],
  projects: [
    {
      title: "Campus API",
      description: "A REST API for hostel requests.\nBuilt with FastAPI.",
      link: "https://github.com/ashav/campus-api",
      technologies: "FastAPI, SQLite",
    },
    emptyProject(),
  ],
  experience: [
    {
      org: "Northwind Labs",
      role: "Backend intern",
      start: "Jun 2025",
      end: "Aug 2025",
      bullets: "Wrote tests for the billing service\n- Fixed two slow queries",
    },
  ],
  education: [
    { institution: "VIT Chennai", degree: "B.Tech CSE", start: "2023", end: "2027", details: "" },
  ],
  certifications: "AWS Cloud Practitioner",
};

test("resume text: name first, contact second, headed sections in a fixed order, blanks omitted", () => {
  const text = resumeText(draft, "Asha Verma");
  const lines = text.split("\n");
  assert.equal(lines[0], "Asha Verma");
  assert.equal(lines[1], "asha@example.com | +91 98765 43210");
  assert.equal(lines[2], "https://github.com/ashav");
  const headings = ["SKILLS", "PROJECTS", "EXPERIENCE", "EDUCATION", "CERTIFICATIONS"];
  const at = headings.map((heading) => lines.indexOf(heading));
  assert.ok(at.every((i) => i > 2), "every heading present");
  assert.deepEqual([...at].sort((a, b) => a - b), at, "headings are in order");
  assert.ok(text.includes("SKILLS\nPython, SQL\n\nPROJECTS\nCampus API\n"));
  assert.ok(text.includes("Northwind Labs, Backend intern\nJun 2025 - Aug 2025\n- Wrote tests for the billing service\n- Fixed two slow queries"));
  assert.ok(text.includes("VIT Chennai, B.Tech CSE\n2023 - 2027"));
  assert.ok(text.endsWith("AWS Cloud Practitioner\n"));
  assert.equal(text.includes("\n\n\n"), false);
});

test("empty sections are left out", () => {
  const text = resumeText({ ...emptyDraft(), email: "a@b.co", skills: ["Python"] }, "Asha");
  assert.equal(text, "Asha\na@b.co\n\nSKILLS\nPython\n");
});

test("nothing is invented: every digit and every skill comes from the student's input", () => {
  const text = resumeText(draft, "Asha Verma");
  const typed = JSON.stringify(draft) + "Asha Verma";
  for (const digit of text.match(/[0-9]+/g) ?? []) assert.ok(typed.includes(digit), `digit run ${digit}`);
  const withoutDigits = resumeText({ ...emptyDraft(), email: "a@b.co", skills: ["Python"], projects: [{ ...emptyProject(), title: "Tool" }] }, "Asha");
  assert.equal(/[0-9]/.test(withoutDigits), false);
  assert.equal(withoutDigits.includes("SQL"), false);
});

test("resume file is a plain text resume.txt", async () => {
  const file = resumeFile(draft, "Asha Verma");
  assert.equal(file.name, "resume.txt");
  assert.match(file.type, /^text\/plain/);
  assert.equal(await file.text(), resumeText(draft, "Asha Verma"));
});

test("draftErrors: name, contact, a skill and one entry are required", () => {
  assert.deepEqual(Object.keys(draftErrors(emptyDraft(), "")).sort(), ["contact", "entries", "name", "skills"]);
  assert.deepEqual(draftErrors(draft, "Asha Verma"), {});
  assert.ok(draftErrors({ ...draft, email: "not-an-email" }, "Asha").email);
  assert.equal(draftErrors({ ...draft, email: "" }, "Asha").contact, undefined, "a phone is enough");
  assert.ok(draftErrors({ ...draft, email: "", phone: "" }, "Asha").contact);
  assert.ok(draftErrors({ ...draft, projects: [{ ...emptyProject(), description: "x" }] }, "Asha")["projects.0.title"]);
  assert.ok(draftErrors({ ...draft, experience: [{ ...emptyExperience(), bullets: "x" }] }, "Asha")["experience.0.org"]);
  assert.ok(draftErrors({ ...draft, education: [{ ...emptyEducation(), degree: "x" }] }, "Asha")["education.0.institution"]);
  assert.ok(draftErrors({ ...draft, certifications: "x".repeat(2001) }, "Asha").length);
});

test("hints never block: long skill list, no numbers, no link", () => {
  assert.deepEqual(draftHints(draft).length, 1, "the sample has no numbers in its descriptions");
  const measured = { ...draft, projects: [{ ...emptyProject(), title: "T", description: "Cut load time by 20%" }] };
  assert.deepEqual(draftHints(measured), []);
  const many = { ...draft, skills: Array.from({ length: 26 }, (_, i) => `Skill ${String.fromCharCode(97 + i)}`) };
  assert.ok(draftHints(many).some((hint) => /26 skills/.test(hint)));
  const noNumbers = { ...draft, projects: [{ ...emptyProject(), title: "T", description: "Built a tool" }], experience: [] };
  assert.ok(draftHints(noNumbers).some((hint) => /only if you measured/.test(hint)));
  assert.ok(draftHints({ ...draft, links: "" }).some((hint) => /GitHub/.test(hint)));
});

test("suggestions: selected role by importance, else union; chosen skills excluded; query filters", () => {
  assert.deepEqual(suggestSkills(roles, "sde-backend", [], "").map((s) => s.name), ["Python", "SQL", "Docker", "Git"]);
  // no role chosen: highest importance across roles first, then how many roles want it, then name
  assert.deepEqual(
    suggestSkills(roles, undefined, [], "").map((s) => s.name),
    ["Python", "SQL", "Docker", "Tableau", "Git"],
  );
  assert.deepEqual(suggestSkills(roles, "sde-backend", ["python", " SQL "], "").map((s) => s.name), ["Docker", "Git"]);
  assert.deepEqual(suggestSkills(roles, undefined, [], "ta").map((s) => s.name), ["Tableau"]);
  assert.deepEqual(suggestSkills(roles, undefined, [], "", 2).map((s) => s.name), ["Python", "SQL"]);
  assert.deepEqual(suggestSkills(roles, "unknown-role", [], "").length, 5);
});

test("addSkill trims, de-duplicates ignoring case, and caps length and count", () => {
  assert.deepEqual(addSkill([], "  Machine   Learning "), ["Machine Learning"]);
  assert.deepEqual(addSkill(["Python"], "python"), ["Python"]);
  assert.deepEqual(addSkill(["Python"], "   "), ["Python"]);
  assert.deepEqual(addSkill([], "x".repeat(41)), []);
  assert.equal(addSkill([], "x".repeat(40)).length, 1);
  const full = Array.from({ length: MAX_SKILLS }, (_, i) => `S${i}`);
  assert.equal(addSkill(full, "New").length, MAX_SKILLS);
});

test("parseDraft rejects malformed JSON and wrong shapes, and keeps good drafts", () => {
  assert.equal(parseDraft(null), null);
  assert.equal(parseDraft("{not json"), null);
  assert.equal(parseDraft("[]"), null);
  assert.equal(parseDraft(JSON.stringify({ ...draft, skills: "Python" })), null);
  assert.equal(parseDraft(JSON.stringify({ ...draft, projects: [{ title: 1 }] })), null);
  assert.deepEqual(parseDraft(JSON.stringify(draft)), draft);
});

const store = new Map<string, string>();
const original = Object.getOwnPropertyDescriptor(globalThis, "window");
function installStorage(broken = false) {
  Object.defineProperty(globalThis, "window", {
    configurable: true,
    value: {
      localStorage: {
        getItem: (key: string) => {
          if (broken) throw new Error("blocked");
          return store.get(key) ?? null;
        },
        setItem: (key: string, value: string) => {
          if (broken) throw new Error("blocked");
          store.set(key, value);
        },
        removeItem: (key: string) => {
          if (broken) throw new Error("blocked");
          store.delete(key);
        },
      },
    },
  });
}
afterEach(() => {
  store.clear();
  if (original) Object.defineProperty(globalThis, "window", original);
  else delete (globalThis as { window?: unknown }).window;
});

test("draft saves, loads and clears through localStorage", () => {
  installStorage();
  saveDraft(draft);
  assert.ok(store.has(DRAFT_KEY));
  assert.deepEqual(loadDraft(), draft);
  clearDraft();
  assert.equal(loadDraft(), null);
});

test("a corrupt stored draft is ignored", () => {
  installStorage();
  store.set(DRAFT_KEY, "{broken");
  assert.equal(loadDraft(), null);
});

test("blocked storage never throws", () => {
  installStorage(true);
  assert.doesNotThrow(() => saveDraft(draft));
  assert.doesNotThrow(() => clearDraft());
  assert.equal(loadDraft(), null);
});
