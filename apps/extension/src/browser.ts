import type { components } from "@careerlens/api-client";
import { pageEligibility } from "./adapters/shared";
export async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id || !tab.url)
    throw new Error(
      "Open a job page and click the CareerLens toolbar icon to grant access.",
    );
  const blocked = pageEligibility(tab.url);
  if (blocked) throw new Error(blocked);
  return { id: tab.id, url: tab.url };
}
export async function extractActive() {
  const tab = await activeTab();
  try {
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["extractor.js"],
    });
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const state = globalThis as typeof globalThis & {
          __careerLensExtraction?: {
            posting?: components["schemas"]["JobPosting"];
            url: string;
            error?: string;
          };
        };
        const result = state.__careerLensExtraction;
        delete state.__careerLensExtraction;
        return result;
      },
    });
    const result = results[0]?.result;
    if (!result || result.error || !result.posting)
      throw new Error(result?.error || "The extractor returned no posting.");
    const current = await activeTab();
    if (
      current.id !== tab.id ||
      current.url !== result.url ||
      tab.url !== result.url
    )
      throw new Error(
        "The tab changed during extraction. Analyse the current job again.",
      );
    return { posting: result.posting, tab: current };
  } catch (e) {
    if (
      e instanceof Error &&
      /Cannot access|Missing host permission|Cannot read/i.test(e.message)
    )
      throw new Error(
        "Chrome has not granted access to this tab. Click the toolbar icon on the job page, then try again.",
      );
    throw e;
  }
}
