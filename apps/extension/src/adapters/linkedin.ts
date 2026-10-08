import { domPosting } from "./shared";
export function linkedin(doc: Document, url: string) {
  return domPosting(doc, url, {
    title: [
      ".job-details-jobs-unified-top-card__job-title h1",
      ".top-card-layout__title",
      ".jobs-unified-top-card__job-title",
      "h1",
    ],
    description: [
      ".jobs-description__content",
      ".show-more-less-html__markup",
      "#job-details",
    ],
    company: [
      ".job-details-jobs-unified-top-card__company-name",
      ".topcard__org-name-link",
    ],
    location: [
      ".job-details-jobs-unified-top-card__primary-description-container",
      ".topcard__flavor--bullet",
    ],
  });
}
