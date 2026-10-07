"use client";
/* Hallmark · pre-emit critique: P4 H4 E4 S4 R5 V3 — DESIGN-locked onboarding flow. */
import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  FileText,
  FolderGit2,
  LoaderCircle,
  Target,
  Upload,
} from "lucide-react";
import {
  useCreateProfile,
  useUpdateProfile,
  useUploadDocument,
  useStartAnalysis,
  useListRoles,
} from "@/lib/api/hooks";
import type { OperationInputs } from "@/lib/api/operations";
import { documentBody } from "@/lib/api/upload";
import { errorMessage } from "@/lib/api/transport";
import {
  portfolioUrls,
  validateStep,
  type Field,
  type FieldErrors,
  type WizardValues,
} from "@/lib/onboarding";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
const steps = [
  { label: "Your documents", icon: FileText },
  { label: "Your work", icon: FolderGit2 },
  { label: "Target role", icon: Target },
];
const control =
  "w-full min-w-0 rounded-control border border-border bg-surface-2 px-3 py-3 text-sm outline-none transition-colors hover:border-primary focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-danger active:border-primary";
function FieldBlock({
  id,
  label,
  required,
  error,
  hint,
  children,
}: {
  id: string;
  label: string;
  required?: boolean;
  error?: string;
  hint: string;
  children: ReactNode;
}) {
  return (
    <div className="min-w-0 space-y-2">
      <label htmlFor={id} className="block text-sm font-semibold">
        {label}
        {required && (
          <span className="ml-1 text-xs font-normal text-muted-readable">
            (required)
          </span>
        )}
      </label>
      {children}
      <p
        id={`${id}-help`}
        className={`text-xs leading-relaxed ${error ? "text-danger-readable" : "text-muted-readable"}`}
      >
        {error || hint}
      </p>
    </div>
  );
}
export function OnboardingWizard() {
  const router = useRouter();
  const roles = useListRoles();
  const createProfile = useCreateProfile();
  const updateProfile = useUpdateProfile();
  const upload = useUploadDocument();
  const analyse = useStartAnalysis();
  const [step, setStep] = useState(0);
  const [values, setValues] = useState<WizardValues>({
    name: "",
    resume: null,
    linkedinMode: "none",
    linkedinFile: null,
    linkedinText: "",
    github: "",
    portfolios: "",
    role: "",
  });
  const [errors, setErrors] = useState<FieldErrors>({});
  const [touched, setTouched] = useState<Partial<Record<Field, boolean>>>({});
  const [busy, setBusy] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);
  const [linkedinSaved, setLinkedinSaved] = useState(false);
  const [phase, setPhase] = useState("");
  const [failure, setFailure] = useState<string>();
  const locked = useRef(false);
  const savedProfile = useRef<string | undefined>(undefined);
  const savedBody = useRef<string | undefined>(undefined);
  const uploaded = useRef<{ resume?: File; linkedin?: File }>({});
  const form = useRef<HTMLFormElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const roleIds = roles.data?.map((role) => role.id) || [];
  function change<K extends Field>(field: K, value: WizardValues[K]) {
    const next = { ...values, [field]: value };
    setValues(next);
    if (touched[field])
      setErrors((old) => ({
        ...old,
        [field]: validateStep(next, step, roleIds)[field],
      }));
    setFailure(undefined);
  }
  function blur(field: Field) {
    setTouched((old) => ({ ...old, [field]: true }));
    setErrors((old) => ({
      ...old,
      [field]: validateStep(values, step, roleIds)[field],
    }));
  }
  function fieldProps(field: Field) {
    return {
      id: field,
      "aria-invalid": Boolean(errors[field]),
      "aria-describedby": `${field}-help`,
      onBlur: () => blur(field),
    };
  }
  function goTo(next: number) {
    setStep(next);
    setErrors({});
    setTouched({});
    requestAnimationFrame(() => {
      heading.current?.focus();
      heading.current?.scrollIntoView({ block: "nearest" });
    });
  }
  function showErrors(found: FieldErrors, atStep = step) {
    setStep(atStep);
    setErrors(found);
    setTouched(
      Object.fromEntries(Object.keys(found).map((field) => [field, true])),
    );
    requestAnimationFrame(() =>
      form.current?.querySelector<HTMLElement>("[aria-invalid=true]")?.focus(),
    );
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (locked.current) return;
    const found = validateStep(values, step, roleIds);
    if (Object.keys(found).length) {
      showErrors(found);
      return;
    }
    if (step < 2) {
      goTo(step + 1);
      return;
    }
    for (let i = 0; i < 3; i++) {
      const all = validateStep(values, i, roleIds);
      if (Object.keys(all).length) {
        showErrors(all, i);
        return;
      }
    }
    locked.current = true;
    setBusy(true);
    setFailure(undefined);
    const body: OperationInputs["createProfile"]["body"] = {
      name: values.name.trim(),
      github_username: values.github.trim() || null,
      portfolio_urls: portfolioUrls(values.portfolios),
      linkedin_text:
        values.linkedinMode === "text" ? values.linkedinText.trim() : null,
      target_role_id: values.role,
    };
    try {
      if (!savedProfile.current) {
        setPhase("Creating your profile…");
        const profile = await createProfile.mutateAsync({ body });
        savedProfile.current = profile.id;
        setProfileSaved(true);
        savedBody.current = JSON.stringify(body);
      } else if (savedBody.current !== JSON.stringify(body)) {
        setPhase("Updating your profile…");
        await updateProfile.mutateAsync({
          profile_id: savedProfile.current,
          body,
        });
        savedBody.current = JSON.stringify(body);
      }
      const profile_id = savedProfile.current;
      if (values.resume && uploaded.current.resume !== values.resume) {
        setPhase("Uploading your resume…");
        await upload.mutateAsync({
          profile_id,
          body: documentBody(values.resume, "resume"),
        });
        uploaded.current.resume = values.resume;
      }
      if (
        values.linkedinMode === "pdf" &&
        values.linkedinFile &&
        uploaded.current.linkedin !== values.linkedinFile
      ) {
        setPhase("Uploading your LinkedIn export…");
        await upload.mutateAsync({
          profile_id,
          body: documentBody(values.linkedinFile, "linkedin"),
        });
        uploaded.current.linkedin = values.linkedinFile;
        setLinkedinSaved(true);
      }
      setPhase("Starting your analysis…");
      const analysis = await analyse.mutateAsync({
        profile_id,
        body: { role_id: values.role },
      });
      setPhase("Analysis started. Opening progress…");
      router.push(`/report/${encodeURIComponent(analysis.id)}`);
    } catch (error) {
      setFailure(errorMessage(error instanceof Error ? error : new Error()));
      setPhase("");
      setBusy(false);
      locked.current = false;
    }
  }
  return (
    <section className="mx-auto max-w-5xl space-y-7">
      <div className="max-w-2xl">
        <p className="mb-2 text-xs font-semibold text-primary-text">
          Your first analysis
        </p>
        <h1 className="text-2xl font-semibold tracking-tight">
          Start with the work you’ve done.
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-muted-readable">
          Bring your resume, public work and a target role. CareerLens connects
          your claims to evidence and shows where to grow next.
        </p>
      </div>
      <ol
        aria-label="Onboarding steps"
        className="grid grid-cols-3 gap-2 sm:gap-4"
      >
        {steps.map(({ label, icon: Icon }, index) => (
          <li
            key={label}
            aria-current={step === index ? "step" : undefined}
            className={`min-w-0 rounded-control border p-3 sm:p-4 ${step === index ? "border-primary bg-primary-soft text-chip-text" : "border-border bg-surface text-muted-readable"}`}
          >
            <div className="mb-2 flex items-center gap-2">
              <span className="text-xs font-semibold">{index + 1}</span>
              {index < step ? (
                <Check size={18} aria-label="Completed" />
              ) : (
                <Icon size={18} strokeWidth={1.75} aria-hidden="true" />
              )}
            </div>
            <p className="text-xs font-semibold sm:text-sm">{label}</p>
          </li>
        ))}
      </ol>
      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_260px]">
        <Card>
          <CardContent className="p-5 sm:p-6">
            <form ref={form} onSubmit={submit} noValidate aria-busy={busy}>
              <div className="mb-6">
                <p className="mb-1 text-xs text-muted-readable">
                  Step {step + 1} of 3
                </p>
                <h2
                  ref={heading}
                  tabIndex={-1}
                  className="text-lg font-semibold outline-none"
                >
                  {steps[step].label}
                </h2>
              </div>
              <fieldset disabled={busy} className="min-w-0 space-y-6">
                {step === 0 && (
                  <>
                    <FieldBlock
                      id="name"
                      label="Your name"
                      required
                      error={errors.name}
                      hint="Use the name you want on your profile."
                    >
                      <input
                        {...fieldProps("name")}
                        className={control}
                        autoComplete="name"
                        required
                        aria-required="true"
                        value={values.name}
                        onChange={(e) => change("name", e.target.value)}
                      />
                    </FieldBlock>
                    <FieldBlock
                      id="resume"
                      label="Resume"
                      required
                      error={errors.resume}
                      hint="PDF or DOCX, up to 5 MB. Choose a document with selectable text."
                    >
                      <div className="rounded-control border border-dashed border-border bg-surface-2 p-4">
                        <Upload
                          size={20}
                          strokeWidth={1.75}
                          className="mb-3 text-primary-text"
                          aria-hidden="true"
                        />
                        <input
                          {...fieldProps("resume")}
                          className={`${control} bg-surface file:mr-3 file:rounded-control file:border-0 file:bg-primary-soft file:px-3 file:py-2 file:text-xs file:font-semibold file:text-chip-text`}
                          type="file"
                          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                          required
                          aria-required="true"
                          onChange={(e) => {
                            change("resume", e.target.files?.[0] || null);
                            setTouched((old) => ({ ...old, resume: true }));
                            setErrors((old) => ({
                              ...old,
                              resume: validateStep(
                                {
                                  ...values,
                                  resume: e.target.files?.[0] || null,
                                },
                                0,
                              ).resume,
                            }));
                          }}
                        />
                        {values.resume && (
                          <p className="mt-2 break-all text-xs text-muted-readable">
                            Selected: {values.resume.name}
                          </p>
                        )}
                      </div>
                    </FieldBlock>
                    <fieldset className="space-y-3">
                      <legend className="mb-3 text-sm font-semibold">
                        LinkedIn profile{" "}
                        <span className="text-xs font-normal text-muted-readable">
                          (optional)
                        </span>
                      </legend>
                      <div className="flex flex-wrap gap-2">
                        {(
                          [
                            ["none", "Skip for now"],
                            ["pdf", "Upload PDF"],
                            ["text", "Paste text"],
                          ] as const
                        ).map(([mode, label]) => (
                          <label
                            key={mode}
                            className={`flex min-h-11 cursor-pointer items-center gap-2 whitespace-nowrap rounded-control border px-3 text-xs font-medium transition-colors hover:border-primary active:bg-surface-2 ${values.linkedinMode === mode ? "border-primary bg-primary-soft text-chip-text" : "border-border"}`}
                          >
                            <input
                              type="radio"
                              name="linkedin-mode"
                              disabled={busy || linkedinSaved}
                              value={mode}
                              checked={values.linkedinMode === mode}
                              onChange={() => {
                                change("linkedinMode", mode);
                                setErrors((old) => ({
                                  ...old,
                                  linkedinFile: undefined,
                                  linkedinText: undefined,
                                }));
                              }}
                              className="size-4 accent-primary"
                            />
                            {label}
                          </label>
                        ))}
                      </div>
                      {linkedinSaved && (
                        <p className="text-xs text-muted-readable">
                          Your LinkedIn PDF is already saved. You can replace it
                          with another PDF below.
                        </p>
                      )}
                      {values.linkedinMode === "pdf" && (
                        <FieldBlock
                          id="linkedinFile"
                          label="LinkedIn PDF export"
                          required
                          error={errors.linkedinFile}
                          hint="Export your own LinkedIn profile as a PDF, up to 5 MB."
                        >
                          <input
                            {...fieldProps("linkedinFile")}
                            className={control}
                            type="file"
                            accept=".pdf,application/pdf"
                            required
                            aria-required="true"
                            onChange={(e) =>
                              change(
                                "linkedinFile",
                                e.target.files?.[0] || null,
                              )
                            }
                          />
                        </FieldBlock>
                      )}
                      {values.linkedinMode === "text" && (
                        <FieldBlock
                          id="linkedinText"
                          label="LinkedIn profile text"
                          required
                          error={errors.linkedinText}
                          hint="Paste text from your own profile. Do not include contact details you don’t want to share."
                        >
                          <textarea
                            {...fieldProps("linkedinText")}
                            className={`${control} min-h-36 resize-y`}
                            required
                            aria-required="true"
                            value={values.linkedinText}
                            onChange={(e) =>
                              change("linkedinText", e.target.value)
                            }
                          />
                        </FieldBlock>
                      )}
                    </fieldset>
                  </>
                )}
                {step === 1 && (
                  <>
                    <FieldBlock
                      id="github"
                      label="GitHub username (optional)"
                      error={errors.github}
                      hint="Username only. CareerLens reviews public repositories; GitHub is optional for design roles."
                    >
                      <input
                        {...fieldProps("github")}
                        className={control}
                        value={values.github}
                        onChange={(e) => change("github", e.target.value)}
                        placeholder="your-username"
                        autoCapitalize="none"
                        spellCheck={false}
                      />
                    </FieldBlock>
                    <FieldBlock
                      id="portfolios"
                      label="Portfolio links (optional)"
                      error={errors.portfolios}
                      hint="One complete web URL per line. Include your portfolio, Behance or Figma work."
                    >
                      <textarea
                        {...fieldProps("portfolios")}
                        className={`${control} min-h-36 resize-y`}
                        value={values.portfolios}
                        onChange={(e) => change("portfolios", e.target.value)}
                        placeholder="https://example.com/portfolio"
                        autoCapitalize="none"
                        spellCheck={false}
                      />
                    </FieldBlock>
                    <p className="rounded-control bg-surface-2 p-4 text-xs leading-relaxed text-muted-readable">
                      You can continue without links. Your analysis will explain
                      where evidence is unavailable.
                    </p>
                  </>
                )}
                {step === 2 && (
                  <>
                    {roles.isPending ? (
                      <div role="status" aria-label="Loading target roles">
                        <Skeleton className="h-12 w-full" />
                        <p className="mt-2 text-xs text-muted-readable">
                          Loading target roles…
                        </p>
                      </div>
                    ) : roles.isError ? (
                      <div
                        role="alert"
                        className="space-y-3 rounded-control border border-danger p-4"
                      >
                        <p className="text-sm text-danger-readable">
                          {errorMessage(roles.error)}
                        </p>
                        <Button
                          type="button"
                          variant="outline"
                          className="min-h-11"
                          onClick={() => roles.refetch()}
                          disabled={roles.isFetching}
                        >
                          Retry roles
                        </Button>
                      </div>
                    ) : !roles.data?.length ? (
                      <div className="space-y-3 rounded-control bg-surface-2 p-4">
                        <p className="text-sm">
                          No target roles are available yet.
                        </p>
                        <Button
                          type="button"
                          variant="outline"
                          className="min-h-11"
                          onClick={() => roles.refetch()}
                          disabled={roles.isFetching}
                        >
                          Refresh roles
                        </Button>
                      </div>
                    ) : (
                      <FieldBlock
                        id="role"
                        label="Target role"
                        required
                        error={errors.role}
                        hint="Choose the role you want this analysis to assess."
                      >
                        <select
                          {...fieldProps("role")}
                          className={`${control} min-h-12`}
                          value={values.role}
                          onChange={(e) => change("role", e.target.value)}
                          required
                          aria-required="true"
                        >
                          <option value="">Choose a role</option>
                          {roles.data.map((role) => (
                            <option key={role.id} value={role.id}>
                              {role.name}
                            </option>
                          ))}
                        </select>
                      </FieldBlock>
                    )}
                    {roles.data?.find((role) => role.id === values.role) && (
                      <div className="rounded-control bg-surface-2 p-4">
                        <p className="mb-2 text-xs font-semibold">
                          Skills considered for this role
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {roles.data
                            .find((role) => role.id === values.role)!
                            .skills.map((skill) => (
                              <span
                                key={skill.skill_id}
                                className="rounded-full border border-border px-2.5 py-1 text-xs"
                              >
                                {skill.skill_name}
                              </span>
                            ))}
                        </div>
                      </div>
                    )}
                    <dl className="space-y-3 border-t border-border pt-4 text-sm">
                      <div>
                        <dt className="text-xs text-muted-readable">Profile</dt>
                        <dd className="mt-1 break-words font-medium">
                          {values.name.trim()}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted-readable">Resume</dt>
                        <dd className="mt-1 break-all">
                          {values.resume?.name}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-xs text-muted-readable">
                          Additional evidence
                        </dt>
                        <dd className="mt-1 break-words">
                          {[
                            values.github.trim() &&
                              `GitHub: ${values.github.trim()}`,
                            portfolioUrls(values.portfolios).length > 0 &&
                              `${portfolioUrls(values.portfolios).length} portfolio link(s)`,
                            values.linkedinMode !== "none" &&
                              "LinkedIn profile",
                          ]
                            .filter(Boolean)
                            .join(" · ") || "No additional evidence selected"}
                        </dd>
                      </div>
                    </dl>
                  </>
                )}
              </fieldset>
              {failure && (
                <div
                  role="alert"
                  className="mt-6 rounded-control border border-danger bg-surface-2 p-4"
                >
                  <p className="text-sm text-danger-readable">{failure}</p>
                  <p className="mt-2 text-xs text-muted-readable">
                    Your entries are still here. Retry Analyse, or go back to
                    review them.
                    {profileSaved ? " The created profile will be reused." : ""}
                  </p>
                </div>
              )}
              <p
                role="status"
                aria-live="polite"
                className="mt-5 min-h-5 text-xs text-muted-readable"
              >
                {phase}
              </p>
              <div className="mt-3 flex flex-wrap justify-between gap-3 border-t border-border pt-5">
                <Button
                  type="button"
                  variant="ghost"
                  className="min-h-11 rounded-control"
                  onClick={() => goTo(step - 1)}
                  disabled={step === 0 || busy}
                >
                  <ArrowLeft aria-hidden="true" />
                  Back
                </Button>
                <Button
                  type="submit"
                  className="min-h-11 rounded-control active:translate-y-px"
                  disabled={
                    busy ||
                    (step === 2 &&
                      (roles.isPending || roles.isError || !roles.data?.length))
                  }
                >
                  {busy ? (
                    <>
                      <LoaderCircle
                        className="animate-spin"
                        aria-hidden="true"
                      />
                      Working…
                    </>
                  ) : step === 2 ? (
                    <>
                      Analyse
                      <ArrowRight aria-hidden="true" />
                    </>
                  ) : (
                    <>
                      Continue
                      <ArrowRight aria-hidden="true" />
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
        <aside className="rounded-card border border-border bg-surface p-6 text-sm">
          <span className="icon-chip mb-4">
            <FileText
              size={20}
              strokeWidth={1.75}
              className="text-primary-text"
              aria-hidden="true"
            />
          </span>
          <h2 className="font-semibold">Evidence, in context.</h2>
          <p className="mt-3 leading-relaxed text-muted-readable">
            Your resume supplies the claims. Your projects and experience help
            show the work behind them.
          </p>
          <p className="mt-4 text-xs leading-relaxed text-muted-readable">
            Use your own documents and public links. Processing begins only when
            you choose Analyse.
          </p>
        </aside>
      </div>
    </section>
  );
}
