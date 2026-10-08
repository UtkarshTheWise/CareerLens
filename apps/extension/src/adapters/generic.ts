import { domPosting } from "./shared";
export function generic(doc: Document, url: string) {
  return domPosting(doc, url, {
    title: ['[itemprop="title"]', "h1"],
    description: [
      '[itemprop="description"]',
      "[data-job-description]",
      ".job-description",
      "#job-description",
    ],
    company: ['[itemprop="hiringOrganization"]', "[data-job-company]"],
    location: ['[itemprop="jobLocation"]'],
  });
}
