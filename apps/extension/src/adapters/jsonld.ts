import { htmlText, dateOnly, type Posting } from "./shared";
export function jsonld(doc: Document, url: string): Posting | null {
  const found: Record<string, unknown>[] = [];
  function walk(value: unknown, depth = 0) {
    if (depth > 20 || !value || typeof value !== "object") return;
    if (Array.isArray(value)) {
      for (const item of value) walk(item, depth + 1);
      return;
    }
    const node = value as Record<string, unknown>;
    const types = Array.isArray(node["@type"])
      ? node["@type"]
      : [node["@type"]];
    if (
      types.some(
        (t) =>
          typeof t === "string" &&
          (t === "JobPosting" || /[/#]JobPosting$/.test(t)),
      )
    )
      found.push(node);
    for (const [key, item] of Object.entries(node)) {
      if (key !== "@context") walk(item, depth + 1);
    }
  }
  for (const script of doc.querySelectorAll(
    'script[type="application/ld+json"]',
  )) {
    if ((script.textContent?.length || 0) > 1000000) continue;
    try {
      walk(JSON.parse(script.textContent || ""));
    } catch {
      /* Invalid blocks do not prevent later valid JSON-LD. */
    }
  }
  const jobs = found.filter(
    (j) => typeof j.title === "string" && htmlText(doc, j.description),
  );
  const job =
    jobs.find(
      (j) =>
        typeof j.url === "string" && j.url.split("#")[0] === url.split("#")[0],
    ) || jobs[0];
  if (!job) return null;
  const org = job.hiringOrganization;
  const company =
    typeof org === "string"
      ? org
      : org &&
          typeof org === "object" &&
          "name" in org &&
          typeof org.name === "string"
        ? org.name
        : null;
  const locations = (
    Array.isArray(job.jobLocation) ? job.jobLocation : [job.jobLocation]
  ).flatMap((place) => {
    if (!place || typeof place !== "object") return [];
    const address = "address" in place ? place.address : null;
    if (!address || typeof address !== "object") return [];
    const parts = [
      "addressLocality",
      "addressRegion",
      "addressCountry",
    ].flatMap((key) => {
      const v = (address as Record<string, unknown>)[key];
      return typeof v === "string"
        ? [v]
        : v &&
            typeof v === "object" &&
            "name" in v &&
            typeof v.name === "string"
          ? [v.name]
          : [];
    });
    return parts.length ? [parts.join(", ")] : [];
  });
  return {
    title: job.title as string,
    company,
    location: locations.join("; ") || null,
    description: htmlText(doc, job.description),
    deadline: dateOnly(job.validThrough),
    url,
    source: "jsonld",
  };
}
