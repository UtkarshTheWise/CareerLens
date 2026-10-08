import type { User } from "@supabase/supabase-js";

/** The name Google gave us, for pre-filling forms and labelling the signed-in user. */
export function displayName(user: User | null): string | undefined {
  const meta = user?.user_metadata as { full_name?: unknown; name?: unknown } | undefined;
  const name = meta?.full_name ?? meta?.name;
  return typeof name === "string" && name.trim() ? name.trim() : undefined;
}
