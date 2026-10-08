import { createClient, type SupabaseClient, type SupportedStorage } from "@supabase/supabase-js";
import { codeFromRedirect } from "./auth-helpers";

// Public values baked in at build time (apps/extension/.env.local). The anon key is public by design; the
// service-role key must never go in the extension.
const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const authConfigured = Boolean(url && anonKey);

// The session lives in chrome.storage.local (this extension only), not in page storage.
const storage: SupportedStorage = {
  async getItem(key) {
    const stored = await chrome.storage.local.get(key);
    return typeof stored[key] === "string" ? stored[key] : null;
  },
  async setItem(key, value) {
    await chrome.storage.local.set({ [key]: value });
  },
  async removeItem(key) {
    await chrome.storage.local.remove(key);
  },
};

let client: SupabaseClient | null = null;

function supabase(): SupabaseClient {
  if (!authConfigured) throw new Error("Sign-in is not configured in this build.");
  client ??= createClient(url as string, anonKey as string, {
    auth: {
      flowType: "pkce",
      storage,
      storageKey: "careerlens-auth",
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: false,
    },
  });
  return client;
}

/** The current access token (refreshed when due), or null when signed out or sign-in is not configured. */
export async function accessToken(): Promise<string | null> {
  if (!authConfigured) return null;
  const { data } = await supabase().auth.getSession();
  return data.session?.access_token ?? null;
}

export type Account = { email?: string; name?: string };

export async function currentAccount(): Promise<Account | null> {
  if (!authConfigured) return null;
  const { data } = await supabase().auth.getSession();
  const user = data.session?.user;
  if (!user) return null;
  const meta = user.user_metadata as { full_name?: unknown; name?: unknown };
  const name = meta.full_name ?? meta.name;
  return { email: user.email, name: typeof name === "string" ? name : undefined };
}

/** Google sign-in through the browser's own identity window; the redirect lands on this extension's
 * chromiumapp.org address, which must be allow-listed in Supabase (docs/AUTH_SETUP.md). */
export async function signInWithGoogle(): Promise<void> {
  const redirectTo = chrome.identity.getRedirectURL();
  const { data, error } = await supabase().auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo, skipBrowserRedirect: true },
  });
  if (error || !data.url) throw new Error("Google sign-in could not start. Try again in a moment.");
  const responseUrl = await chrome.identity.launchWebAuthFlow({ url: data.url, interactive: true });
  if (!responseUrl) throw new Error("Sign-in was closed before it finished.");
  const { error: exchange } = await supabase().auth.exchangeCodeForSession(codeFromRedirect(responseUrl));
  if (exchange) throw new Error("Sign-in could not be completed. Try again.");
}

export async function signOut(): Promise<void> {
  if (authConfigured) await supabase().auth.signOut();
}
