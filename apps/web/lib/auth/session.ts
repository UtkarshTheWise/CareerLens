import type { SupabaseClient } from "@supabase/supabase-js";
import { getSupabase } from "./supabase";

type Source = () => SupabaseClient | null;
let source: Source = getSupabase;

/** Tests swap the Supabase client for a stub. */
export function setSupabaseSource(next: Source | null) {
  source = next ?? getSupabase;
  leaving = false;
}

/** The current access token, refreshed by Supabase when it is about to expire; null when signed out or when
 * sign-in is not configured (the app then uses its development token). */
export async function getAccessToken(): Promise<string | null> {
  const supabase = source();
  if (!supabase) return null;
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

let leaving = false;

function onLoginPage(): boolean {
  return typeof window !== "undefined" && window.location.pathname.startsWith("/login");
}

/** The API rejected our token: end the session and go to the sign-in page, once. */
export async function handleUnauthorized(
  navigate: (to: string) => void = (to) => {
    if (typeof window !== "undefined") window.location.assign(to);
  },
) {
  const supabase = source();
  if (!supabase || leaving || onLoginPage()) return;
  leaving = true;
  try {
    await supabase.auth.signOut();
  } finally {
    navigate("/login");
  }
}
