# F3 — Onboarding and analysis progress

## Scope and coordination
User resumed F3 after published F2 implementation 82828dc and checkpoint d31554b. Public GitHub refs match local frontend and main e762cb4 (B1–B6). Native fetch is blocked by existing Windows deny ACLs on shared Git metadata; no newer remote changes need merging. Work only in frontend/codex. Do not start F4 or later prompts.

## Implementation
1. Build /onboarding with three labelled steps: name and resume PDF/DOCX (5 MB); optional LinkedIn PDF OR pasted text; optional GitHub username and web portfolio URLs; target role loaded from the typed listRoles hook.
2. Validate on blur and step submission, preserve input across Back/Next, associate errors with fields and focus the first invalid field. Show catalogue loading/error/empty states with retry.
3. Use generated API input types and existing createProfile, updateProfile, uploadDocument/documentBody and startAnalysis hooks. Run sequentially, block duplicate submissions, retain the created profile and successful file uploads for retry within this mounted session. Do not persist personal data or files in browser storage.
4. Navigate to /report/[analysisId]. Use getAnalysis with its existing 2-second polling and terminal stop. Render StageProgress, loading skeletons, request errors/retry, server failure and restart. Done confirms completion; completed evidence report belongs to F4. Do not show unexplained scores.
5. Preserve DESIGN tokens, typography and reusable F2 components. Verify keyboard, reduced motion, both themes and 320/375/390/414/768/1440px with no overflow. Check workflow requests, multipart uploads, failures/retry and terminal polling using synthetic browser fixtures; smoke against Prism.

## Completion
Run web lint/typecheck/build and existing transport tests; record browser/accessibility evidence in chat outputs. Update frontend progress and append own handoff. Commit/publish implementation, then record its verified SHA in a final checkpoint. Pause before F4. Backend, data, contract and generated client remain read-only.
