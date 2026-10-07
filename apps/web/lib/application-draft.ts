import type { components } from "@careerlens/api-client";
export function applicationDraft(
  form: FormData,
  profileId: string,
): components["schemas"]["ApplicationCreate"] {
  const company = String(form.get("company") || "").trim(),
    title = String(form.get("title") || "").trim(),
    raw = String(form.get("url") || "").trim(),
    deadline = String(form.get("deadline") || "").trim();
  if (!company || !title)
    throw new Error("Company and job title are required.");
  let url: string | null = null;
  if (raw) {
    try {
      const parsed = new URL(raw);
      if (
        !["https:", "http:"].includes(parsed.protocol) ||
        parsed.username ||
        parsed.password
      )
        throw new Error();
      url = parsed.href;
    } catch {
      throw new Error(
        "Enter a valid HTTP or HTTPS job URL without login details.",
      );
    }
  }
  if (
    deadline &&
    (!/^\d{4}-\d{2}-\d{2}$/.test(deadline) ||
      !Number.isFinite(Date.parse(deadline)) ||
      new Date(deadline).toISOString().slice(0, 10) !== deadline)
  )
    throw new Error("Enter a valid deadline date.");
  return {
    profile_id: profileId,
    company,
    title,
    url,
    deadline: deadline || null,
    status: "saved",
    notes: String(form.get("notes") || "").trim() || null,
  };
}
