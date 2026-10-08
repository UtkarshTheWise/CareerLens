import type { components } from "@careerlens/api-client";
export type Posting = components["schemas"]["JobPosting"];
export function pageEligibility(raw: string) {
  try {
    const u = new URL(raw);
    if (!["http:", "https:"].includes(u.protocol) || u.username || u.password)
      return "Open a public HTTP or HTTPS job page.";
    if (
      (u.hostname === "linkedin.com" || u.hostname.endsWith(".linkedin.com")) &&
      (!u.pathname.startsWith("/jobs/") ||
        (!u.pathname.startsWith("/jobs/view/") &&
          !/^\d+$/.test(u.searchParams.get("currentJobId") ?? "")))
    )
      return "Open an individual LinkedIn job posting to analyse it. Profile pages are never read.";
    return null;
  } catch {
    return "Open a job page, then click the toolbar icon to grant access.";
  }
}
export function visible(el: Element) {
  for (let e: Element | null = el; e; e = e.parentElement) {
    if (e.hasAttribute("hidden") || e.getAttribute("aria-hidden") === "true")
      return false;
    const style = e.ownerDocument.defaultView?.getComputedStyle(e);
    if (
      style?.display === "none" ||
      style?.visibility === "hidden" ||
      style?.visibility === "collapse" ||
      style?.opacity === "0"
    )
      return false;
  }
  return true;
}
export function visibleText(el: Element) {
  const doc = el.ownerDocument,
    walker = doc.createTreeWalker(el, 4),
    parts: string[] = [];
  let node: Node | null;
  while ((node = walker.nextNode())) {
    const parent = node.parentElement;
    if (
      !parent ||
      parent.closest(
        "script,style,noscript,nav,header,footer,aside,form,button,input,select,textarea",
      ) ||
      !visible(parent)
    )
      continue;
    const value = node.textContent?.trim();
    if (value) parts.push(value);
  }
  return parts.join("\n").slice(0, 20000);
}
export function read(doc: Document, selectors: string[]) {
  for (const selector of selectors) {
    const el = doc.querySelector(selector);
    if (el && visible(el)) {
      const value = el.getAttribute("content") || el.textContent?.trim();
      if (value) return value;
    }
  }
  return "";
}
export function htmlText(doc: Document, html: unknown) {
  if (typeof html !== "string") return "";
  const parsed = new doc.defaultView!.DOMParser().parseFromString(
    html,
    "text/html",
  );
  parsed.querySelectorAll("script,style,noscript").forEach((e) => e.remove());
  parsed
    .querySelectorAll("br")
    .forEach((e) => e.replaceWith(parsed.createTextNode("\n")));
  parsed
    .querySelectorAll(
      "p,div,li,h1,h2,h3,h4,h5,h6,section,article,blockquote,tr",
    )
    .forEach((e) => e.append(parsed.createTextNode("\n")));
  return (parsed.body.textContent || "")
    .replace(/[ \t\r]+/g, " ")
    .replace(/ *\n */g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim()
    .slice(0, 20000);
}
export function dateOnly(value: unknown) {
  if (typeof value !== "string") return null;
  const date = value.slice(0, 10);
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
    !Number.isFinite(Date.parse(date)) ||
    new Date(date).toISOString().slice(0, 10) !== date
  )
    return null;
  return date;
}
export function domPosting(
  doc: Document,
  url: string,
  selectors: {
    title: string[];
    description: string[];
    company?: string[];
    location?: string[];
  },
): Posting | null {
  const title = read(doc, selectors.title);
  let description = "";
  for (const selector of selectors.description) {
    const el = doc.querySelector(selector);
    if (el && visible(el)) {
      description = visibleText(el);
      if (description) break;
    }
  }
  if (!title || !description) return null;
  return {
    title,
    description,
    company: read(doc, selectors.company || []) || null,
    location: read(doc, selectors.location || []) || null,
    url,
    source: "dom",
  };
}
