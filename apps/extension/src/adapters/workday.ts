import { domPosting } from "./shared";
export function workday(doc: Document, url: string) {
  return domPosting(doc, url, {
    title: ['[data-automation-id="jobPostingHeader"]'],
    description: ['[data-automation-id="jobPostingDescription"]'],
    location: ['[data-automation-id="locations"]'],
  });
}
