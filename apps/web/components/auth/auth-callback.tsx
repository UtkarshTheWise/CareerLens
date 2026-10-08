"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getSupabase } from "@/lib/auth/supabase";

/** Landing page after Google: Supabase exchanges the code in the URL for a session on load. */
export function AuthCallback() {
  const router = useRouter();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const supabase = getSupabase();
    if (!supabase) {
      router.replace("/dashboard");
      return;
    }
    let alive = true;
    void supabase.auth.getSession().then(({ data, error }) => {
      if (!alive) return;
      if (data.session) {
        router.replace("/dashboard"); // a first-time user sees the empty dashboard with "Analyse a profile"
      } else {
        console.warn("sign-in did not produce a session", error?.name);
        setFailed(true);
      }
    });
    return () => {
      alive = false;
    };
  }, [router]);

  return (
    <main id="main-content" className="flex min-h-dvh items-center justify-center p-4">
      {failed ? (
        <section role="alert" className="max-w-md space-y-3 rounded-card border border-border bg-surface p-6">
          <h1 className="text-xl font-semibold">Sign-in did not finish</h1>
          <p className="text-sm text-muted-readable">
            The link may have expired or been opened twice. Start again from the sign-in page.
          </p>
          <Link href="/login" className="text-sm font-medium text-primary-text underline">Back to sign in</Link>
        </section>
      ) : (
        <p role="status" className="text-sm text-muted-readable">Finishing sign-in…</p>
      )}
    </main>
  );
}
