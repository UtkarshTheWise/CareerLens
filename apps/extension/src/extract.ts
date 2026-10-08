import { extractPosting } from "./adapters";
try {
  (
    globalThis as typeof globalThis & { __careerLensExtraction?: unknown }
  ).__careerLensExtraction = {
    posting: extractPosting(document, location.href),
    url: location.href,
  };
} catch (e) {
  (
    globalThis as typeof globalThis & { __careerLensExtraction?: unknown }
  ).__careerLensExtraction = {
    error: (e as Error).message,
    url: location.href,
  };
}
