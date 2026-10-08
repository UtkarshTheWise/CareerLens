import { jsonld } from "./jsonld";
import { linkedin } from "./linkedin";
import { greenhouse } from "./greenhouse";
import { lever } from "./lever";
import { workday } from "./workday";
import { naukri } from "./naukri";
import { generic } from "./generic";
import { pageEligibility, read, visibleText, type Posting } from "./shared";
export function extractPosting(doc: Document, url: string): Posting {
  const blocked = pageEligibility(url);
  if (blocked) throw new Error(blocked);
  const structured = jsonld(doc, url);
  if (structured) return structured;
  const host = new URL(url).hostname;
  const isHost = (domain: string) =>
    host === domain || host.endsWith("." + domain);
  const adapters = isHost("linkedin.com")
    ? [linkedin]
    : isHost("greenhouse.io") || isHost("greenhouse.com")
      ? [greenhouse]
      : isHost("lever.co")
        ? [lever]
        : isHost("myworkdayjobs.com")
          ? [workday]
          : isHost("naukri.com")
            ? [naukri]
            : [];
  for (const adapter of [...adapters, generic]) {
    const result = adapter(doc, url);
    if (result) return result;
  }
  const main = doc.querySelector("main,[role=main]") || doc.body;
  const description = visibleText(main);
  if (!description)
    throw new Error(
      "No visible job text was found. Open the full posting and try again.",
    );
  return {
    title: read(doc, ["h1"]) || doc.title,
    company: null,
    location: null,
    url,
    description,
    source: "llm",
  };
}
