# Sign-in setup: Supabase with Google

CareerLens signs students in with their Google account through Supabase Auth. The web app and the Chrome
extension each get the user's Supabase access token and send it to the API, which verifies it
(`apps/api/app/services/auth.py`). Nothing here needs the Supabase service-role key. Do not put it anywhere.

Until these steps are done the apps keep their development behaviour (a "dev" token against a `DEV_AUTH=1`
backend or the mock), so nothing breaks while you set things up.

## 1. Google Cloud (about 5 minutes)

1. console.cloud.google.com → create or pick a project → **APIs & Services → OAuth consent screen**: External, app name "CareerLens", your support email. Add yourself and any teammates as test users while the app is in Testing.
2. **Credentials → Create credentials → OAuth client ID → Web application.**
3. Under **Authorized redirect URIs** add: `https://<your-project-ref>.supabase.co/auth/v1/callback`
4. Copy the **Client ID** and **Client secret**.

## 2. Supabase dashboard

1. **Authentication → Providers → Google**: enable, paste the Client ID and secret, save.
2. **Authentication → URL Configuration**:
   - **Site URL**: your deployed web app (for example `https://careerlens.vercel.app`).
   - **Redirect URLs** (allow-list), add all of:
     - `http://localhost:3000/**`
     - `https://<your-web-app>/**`
     - `https://bchilaidlnimfdagenlcpoannjomfkil.chromiumapp.org/` ← the extension (its id is fixed by the `key` in `apps/extension/public/manifest.json`)
3. **Project Settings → API**: note the **Project URL** and the **anon public** key (public by design).
4. **Project Settings → API → JWT Settings** (or **JWT Keys**): note whether the project signs tokens with the legacy **JWT secret** (HS256) or with **signing keys** (ES256/RS256).

## 3. Configure the three places

| Where | Values |
|---|---|
| **API** (Render dashboard, or `apps/api/.env`) | `ENVIRONMENT=production`, `DEV_AUTH=0`, and **either** `SUPABASE_JWT_SECRET=<legacy JWT secret>` (HS256) **or** `SUPABASE_URL=https://<ref>.supabase.co` (signing keys, checked through JWKS; also pins the issuer). `PLACEMENT_STAFF=<comma-separated staff emails>`. `CORS_ORIGINS=https://<your-web-app>` (the extension is allowed by pattern). |
| **Web app** (`apps/web/.env.local`, and Vercel project settings) | `NEXT_PUBLIC_API_URL=https://<your-api>`, `NEXT_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co`, `NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon public key>` |
| **Extension** (`apps/extension/.env.local`, then rebuild) | `VITE_API_URL=https://<your-api>`, `VITE_SUPABASE_URL=https://<ref>.supabase.co`, `VITE_SUPABASE_ANON_KEY=<anon public key>` |

For local work against a local API, use `NEXT_PUBLIC_API_URL=http://localhost:8000` and a backend with
`DEV_AUTH=1`; leave the Supabase values empty to skip sign-in entirely.

## 4. Who is placement staff

Cohort data is staff-only. An account counts as staff if its **email or user id is in `PLACEMENT_STAFF`**, or its
Supabase `app_metadata.role` is `placement` (set by an admin in the dashboard under Authentication → Users; the
user cannot edit `app_metadata`). Everyone else gets a "staff only" message on the placement screen.

## 5. Check it by hand (these need your real project)

- [ ] Web: open the app → redirected to **Sign in** → Continue with Google → land on the dashboard; the header shows your name; **Sign out** returns to the sign-in page.
- [ ] First sign-in has no profile: the dashboard offers "Analyse a profile"; the onboarding name field is pre-filled with your Google name.
- [ ] A second Google account cannot open the first account's report or quiz URLs (404).
- [ ] A non-staff account sees "staff only" on the placement screen; a staff account sees the cohort.
- [ ] Extension: load `apps/extension/dist` unpacked → the extension id on `chrome://extensions` is `bchilaidlnimfdagenlcpoannjomfkil` → Options → **Sign in with Google** → **Fetch my profile** → save → open a job page and Analyse.
- [ ] If the extension's Google window fails with a redirect error, the Supabase **Redirect URLs** entry above is missing or has a typo (it must match exactly, including the trailing slash).

## Notes

- The extension's key pair: only the **public** key is committed (`key` in the manifest) so the id is stable. The private key was never saved and is not needed to load the extension unpacked. If you publish to the Chrome Web Store later, Google assigns its own id; add that redirect URL too.
- Access tokens are short-lived; Supabase refreshes them in the browser. The API rejects an expired token with 401, and the web app then signs the user out and shows the sign-in page.
- Google only supplies the account name and email. The resume, repositories and quiz answers are never sent to Google.
