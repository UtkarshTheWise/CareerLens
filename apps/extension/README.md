# CareerLens Chrome extension

F8: Manifest V3 companion side panel, built with Vite, React, TypeScript and Tailwind. Uses the same DESIGN tokens and Plus Jakarta Sans as the web app.

## Build and load

From the workspace root, with Node 24 and pnpm installed:

```powershell
pnpm install --frozen-lockfile
pnpm --filter extension typecheck
pnpm --filter extension test
pnpm --filter extension build
```

Open chrome://extensions, enable Developer mode, choose **Load unpacked**, and select **apps/extension/dist**. Chrome 116 or newer is required. After rebuilding, click Reload for the extension, close the old panel and reopen it; extension service workers can retain an older build.

1. Open extension Options. Set the API base URL (default http://localhost:8000; use http://localhost:4010 for Prism). Click **Fetch my profile**, or enter your profile UUID, then save settings. System/light/dark themes are available.
2. Open an individual job posting. Click the CareerLens toolbar icon to grant temporary active-tab access and open the side panel. Opening a panel from Chrome's side-panel menu alone does not grant access; click the toolbar icon on the job tab.
3. Click **Analyse this job**. Match displays the API's two scores, summary and skill evidence levels; Gaps displays missing and unverified claims.
4. Save stores both returned match scores and the description in an application. Enter a company/title if the page omitted them. Navigation or a profile/API change invalidates the current match.

## Access and data

The toolbar handler opens the panel without injecting or reading page content. Only Analyse injects the classic, isolated-world extractor into the current tab. Order: JSON-LD JobPosting (arrays/@graph), site-specific selectors, then visible main text capped at 20,000 characters. The last path sends source llm for backend interpretation. No client scoring or inferred skills/company. LinkedIn profiles and job listings without an individual selected job are rejected before DOM access.

Permissions: activeTab, scripting, storage and sidePanel. Persistent host permissions cover only localhost/127.0.0.1 development APIs, never general job-site hosts. Remote APIs must allow the extension origin through CORS. Development/local API requests send Bearer dev; production authentication is not configured by F8. No LLM keys are accepted or stored. Only API URL, profile ID and theme persist in chrome.storage.local; extracted text/results remain in panel memory.

Saving is explicit and uses the generated createApiClient application endpoint. A pending request locks duplicate submissions; a successful save is acknowledged and locked. Network errors can be retried. Exactly-once delivery after a lost server acknowledgement needs backend idempotency, which the current contract does not provide.

## Verification scope

Saved synthetic HTML fixtures cover JSON-LD and Greenhouse/Lever/LinkedIn job layouts; tests also cover Workday, Naukri, generic, hidden-text/size/date handling and profile/listing guards. Unpacked Chromium checks exercise the real toolbar action, side panel, activeTab grants, script injection, local storage, generated-client requests, retry/stale states and responsive themes. The stateful test API is synthetic; backend matching, authentication and persistence are Phase 3 integration work. Public job pages can expire, redirect, require login or change selectors.
