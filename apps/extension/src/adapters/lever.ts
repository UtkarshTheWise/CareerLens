import { domPosting } from "./shared";
export function lever(doc: Document, url: string) {
  return domPosting(doc, url, {
    title: [".posting-headline h2", ".posting-headline h1"],
    description: [
      ".posting-page .content",
      ".posting-page",
      ".posting-content",
    ],
    company: [
      ".posting-headline .company-name",
      'meta[property="og:site_name"]',
    ],
    location: [".posting-categories .location"],
  });
}
