import { createClient, type SupabaseClient } from "@supabase/supabase-js";

// Sign-in is on only when both public values are set (the anon key is public by design; never put the
// service-role key anywhere in this app). Without them the app keeps its development behaviour.
const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const isAuthConfigured = Boolean(url && anonKey);

let client: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient | null {
  if (!isAuthConfigured) return null;
  client ??= createClient(url as string, anonKey as string, {
    auth: { flowType: "pkce", persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
  });
  return client;
}
