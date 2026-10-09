"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { BrandMark } from "@/components/layout/brand-mark";
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
      <section className="panel w-full max-w-md space-y-6 sm:p-8" aria-labelledby="login-title">
        <div className="flex items-center gap-3 text-lg font-bold tracking-tight">
          <BrandMark />
          CareerLens
        </div>
        <div className="space-y-3">
          <p className="eyebrow">Student sign-in</p>
          <h1 id="login-title" className="page-title">Sign in to see your evidence</h1>
          <p className="lede">
            Use your Google account. We use it only to know who you are, so your analyses and quiz results stay
            yours. Your resume and repositories are never sent to Google.
          </p>
        </div>
        {auth.error && (
          <p role="alert" className="field-error">{auth.error}</p>
        )}
        <Button size="lg" trailingArrow className="w-full" onClick={() => void start()} disabled={busy || auth.status === "loading"}>
          {busy ? "Opening Google…" : "Continue with Google"}
        </Button>
        <p className="text-xs leading-relaxed text-muted-readable">
          Bring your resume and project links. Your work is the starting point. <Link href="/" className="text-link">Back to home</Link>
        </p>
      </section>
    </main>
  );
}
