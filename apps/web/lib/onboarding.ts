import { draftErrors, type ResumeDraft } from "./resume-builder";
export const MAX_DOCUMENT_BYTES = 5 * 1024 * 1024;
export type ResumeMode = "upload" | "build";
export type WizardValues = {
  name: string;
  resumeMode: ResumeMode;
  resumeDraft: ResumeDraft;
  resume: File | null;
  linkedinMode: "none" | "pdf" | "text";
  linkedinFile: File | null;
  linkedinText: string;
  github: string;
  portfolios: string;
  role: string;
};
export type Field = keyof WizardValues;
export type FieldErrors = Partial<Record<Field, string>>;
export function fileError(file: File | null, kind: "resume" | "linkedin") {
  if (!file)
    return kind === "resume"
      ? "Choose your resume PDF or DOCX to continue."
      : "Choose your LinkedIn profile PDF, or select another option.";
  const extensions = kind === "resume" ? /\.(pdf|docx)$/i : /\.pdf$/i;
  if (!extensions.test(file.name))
    return kind === "resume"
      ? "Use a PDF or DOCX file for your resume."
      : "Use a PDF export for your LinkedIn profile.";
  if (file.size === 0)
    return "This file is empty. Choose a file containing text.";
  if (file.size > MAX_DOCUMENT_BYTES)
    return "This file exceeds 5 MB. Choose a smaller file.";
}
export function portfolioUrls(text: string) {
  return text
    .split(/\r?\n/)
    .map((url) => url.trim())
    .filter(Boolean);
}
export function validateStep(
  values: WizardValues,
  step: number,
  roleIds: readonly string[] = [],
): FieldErrors {
  const errors: FieldErrors = {};
  if (step === 0) {
    if (!values.name.trim()) errors.name = "Enter your name to continue.";
    if (values.resumeMode === "build") {
      // The builder shows its own field-level messages; the wizard only needs to know it is not finished.
      if (Object.keys(draftErrors(values.resumeDraft, values.name)).some((key) => key !== "name"))
        errors.resume = "Finish the required parts of your resume.";
    } else {
      const resumeError = fileError(values.resume, "resume");
      if (resumeError) errors.resume = resumeError;
    }
    if (values.linkedinMode === "pdf") {
      const linkedinError = fileError(values.linkedinFile, "linkedin");
      if (linkedinError) errors.linkedinFile = linkedinError;
    }
    if (values.linkedinMode === "text" && !values.linkedinText.trim())
      errors.linkedinText =
        "Paste your LinkedIn profile text, or select Skip for now.";
  }
  if (step === 1) {
    const github = values.github.trim();
    if (
      github &&
      (!/^[a-z\d](?:[a-z\d-]{0,37}[a-z\d])?$/i.test(github) ||
        github.includes("--"))
    )
      errors.github =
        "Use a GitHub username (up to 39 letters, numbers or single hyphens), not a URL.";
    if (
      portfolioUrls(values.portfolios).some((value) => {
        try {
          const url = new URL(value);
          return (
            !["https:", "http:"].includes(url.protocol) ||
            !url.hostname ||
            Boolean(url.username || url.password)
          );
        } catch {
          return true;
        }
      })
    )
      errors.portfolios =
        "Use a full http:// or https:// URL on each line, without a username or password.";
  }
  if (step === 2 && !roleIds.includes(values.role))
    errors.role = "Choose an available target role to continue.";
  return errors;
}
