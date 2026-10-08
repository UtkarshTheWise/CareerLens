"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ScanLine } from "lucide-react";
import { useAuth } from "./auth-provider";
import { Button } from "@/components/ui/button";

export function LoginScreen() {
  const auth = useAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (auth.status === "signed-in" || auth.status === "disabled") router.replace("/dashboard");
  }, [auth.status, router]);

  async function start() {
    setBusy(true);
    await auth.signIn(); // on success the browser leaves for Google
    setBusy(false);
  }

  return (
    <main id="main-content" className="flex min-h-dvh items-center justify-center p-4">
      <section className="w-full max-w-md space-y-6 rounded-card border border-border bg-surface p-6 sm:p-8" aria-labelledby="login-title">
        <div className="flex items-center gap-3 text-lg font-bold tracking-tight">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-control bg-primary text-primary-foreground">
            <ScanLine size={24} strokeWidth={1.75} aria-hidden="true" />
          </span>
          CareerLens
        </div>
        <div className="space-y-2">
          <h1 id="login-title" className="text-2xl font-semibold">Sign in to see your evidence</h1>
          <p className="text-sm leading-relaxed text-muted-readable">
            Use your Google account. We use it only to know who you are, so your analyses and quiz results stay
            yours. Your resume and repositories are never sent to Google.
          </p>
        </div>
        {auth.error && (
          <p role="alert" className="text-sm text-danger-readable">{auth.error}</p>
        )}
        <Button className="min-h-11 w-full" onClick={() => void start()} disabled={busy || auth.status === "loading"}>
          {busy ? "Opening Google…" : "Continue with Google"}
        </Button>
        <p className="text-xs leading-relaxed text-muted-readable">
          Placement staff use the same button; access to cohort data depends on your account being on the staff
          list. <Link href="/dashboard" className="text-primary-text underline">Back to the app</Link>
        </p>
      </section>
    </main>
  );
}
