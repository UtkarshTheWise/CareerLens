import { domPosting } from "./shared";
export function naukri(doc: Document, url: string) {
  return domPosting(doc, url, {
    title: [".jd-header-title", "header h1"],
    description: [".job-desc", ".job-desc-container"],
    company: [".jd-header-comp-name"],
    location: [".loc-wrap"],
  });
}
