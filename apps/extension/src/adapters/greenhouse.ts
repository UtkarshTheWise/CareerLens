import { domPosting } from "./shared";
export function greenhouse(doc: Document, url: string) {
  return domPosting(doc, url, {
    title: ["h1.app-title", "h1.section-header", "h1"],
    description: ["#content", ".job__description", ".job-description"],
    company: [".company-name", ".company_name"],
    location: [".location", ".job__location"],
  });
}
