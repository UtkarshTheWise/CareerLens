"use client";
import { useState } from "react";
import Link from "next/link";
import { ArrowUpRight, KeyRound, LogOut, Puzzle, ShieldCheck } from "lucide-react";
import { displayName, useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { clearAiKey, isValidKey, maskKey, providerLabel, readAiKey, saveAiKey, type AiKey, type AiProvider } from "@/lib/ai-key";

const control =
  "w-full min-w-0 rounded-control border border-border bg-surface-2 px-3 py-3 text-sm outline-none transition-colors hover:border-primary focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface";
const providers: Array<{ id: AiProvider; name: string; url: string; where: string }> = [
  { id: "gemini", name: "Google Gemini", url: "https://aistudio.google.com/apikey", where: "Google AI Studio" },
  { id: "groq", name: "Groq", url: "https://console.groq.com/keys", where: "the Groq console" },
];

function AccountCard() {
  const { status, user, signOut } = useAuth();
  const name = displayName(user);
  return (
    <section aria-labelledby="account-title" className="rounded-card border border-border bg-surface p-6 shadow-card sm:p-8">
      <h2 id="account-title">Account</h2>
      {status === "signed-in" ? (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-4">
          <p className="min-w-0 text-sm">
            <span className="block font-semibold">{name || "Signed in with Google"}</span>
            <span className="block truncate text-muted-readable">{user?.email}</span>
          </p>
          <Button variant="outline" onClick={() => void signOut()}>
            <LogOut size={16} aria-hidden="true" />
            Sign out
          </Button>
        </div>
      ) : (
        <p className="mt-2 text-sm text-muted-readable">Sign-in is not switched on in this environment.</p>
      )}
    </section>
  );
}

function AiKeyCard() {
  const [saved, setSaved] = useState<AiKey | null>(() => readAiKey());
  const [provider, setProvider] = useState<AiProvider>(saved?.provider ?? "gemini");
  const [draft, setDraft] = useState("");
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string }>();
  const chosen = providers.find((p) => p.id === provider)!;

  function save() {
    if (!isValidKey(draft.trim())) {
      setMessage({ kind: "error", text: "That doesn't look like an API key. Copy it again from the provider, with no spaces." });
      return;
    }
    if (!saveAiKey(provider, draft)) {
      setMessage({ kind: "error", text: "This browser wouldn't store the key (a private window or blocked site data). Nothing was saved." });
      return;
    }
    setSaved(readAiKey());
    setDraft("");
    setMessage({ kind: "ok", text: `Saved. Reports and quizzes now use your ${providerLabel(provider)} key.` });
  }
  function remove() {
    clearAiKey();
    setSaved(null);
    setDraft("");
    setMessage({ kind: "ok", text: "Removed from this browser. CareerLens' shared allowance is used again." });
  }

  return (
    <section aria-labelledby="ai-key-title" className="rounded-card border border-border bg-surface p-6 shadow-card sm:p-8">
      <div className="flex items-start gap-4">
        <div className="icon-chip shrink-0">
          <KeyRound aria-hidden="true" size={20} strokeWidth={1.75} />
        </div>
        <div className="min-w-0">
          <h2 id="ai-key-title">Your own AI key (optional)</h2>
          <p className="mt-2 max-w-xl text-sm text-muted-readable">
            CareerLens uses a small shared free allowance for the AI that reads your work and writes your quizzes. It can run out. Add a free key
            of your own and your reports, quizzes and job matches use your allowance instead.
          </p>
        </div>
      </div>

      <p role="status" className="mt-5 rounded-control bg-surface-2 px-4 py-3 text-sm">
        {saved ? (
          <>
            <strong>Using your {providerLabel(saved.provider)} key</strong> (ends {maskKey(saved.key)}).
          </>
        ) : (
          <>
            <strong>Using CareerLens&apos; shared allowance.</strong> You may see &ldquo;the AI service is busy&rdquo; when it is used up.
          </>
        )}
      </p>

      <form
        className="mt-5 space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          save();
        }}
      >
        <fieldset className="space-y-2">
          <legend className="text-sm font-semibold">Provider</legend>
          <div className="flex flex-wrap gap-3">
            {providers.map((p) => (
              <label key={p.id} className="flex cursor-pointer items-center gap-2 rounded-control border border-border bg-surface-2 px-4 py-3 text-sm has-[:checked]:border-primary">
                <input type="radio" name="provider" value={p.id} checked={provider === p.id} onChange={() => setProvider(p.id)} />
                {p.name}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="space-y-2">
          <label htmlFor="ai-key" className="block text-sm font-semibold">
            {chosen.name} API key
          </label>
          <input
            id="ai-key"
            type="password"
            className={control}
            autoComplete="off"
            spellCheck={false}
            placeholder={saved ? "Paste a new key to replace the saved one" : "Paste your key"}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            aria-describedby="ai-key-help"
          />
          <p id="ai-key-help" className="text-xs text-muted-readable">
            Create a free key in{" "}
            <a href={chosen.url} target="_blank" rel="noreferrer noopener" className="font-semibold text-primary-text underline">
              {chosen.where}
            </a>
            , then paste it here.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={!draft.trim()}>
            Save key
          </Button>
          {saved && (
            <Button type="button" variant="outline" onClick={remove}>
              Remove key
            </Button>
          )}
        </div>
        {message && (
          <p role={message.kind === "error" ? "alert" : "status"} className={`text-sm ${message.kind === "error" ? "text-danger-readable" : "text-muted-readable"}`}>
            {message.text}
          </p>
        )}
      </form>

      <div className="mt-6 flex items-start gap-3 border-t border-border pt-5 text-xs leading-relaxed text-muted-readable">
        <ShieldCheck size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
        <p>
          Your key is kept only in this browser. When you start a report, take a quiz or match a job, it travels over HTTPS through the CareerLens
          server to {chosen.name} for that request, and is not stored or logged by us. Use a key you can revoke, and remove it on a shared computer.
          The Chrome extension still uses the shared allowance.
        </p>
      </div>
    </section>
  );
}

export function SettingsScreen() {
  return (
    <section className="space-y-8">
      <div>
        <p className="mb-2 text-xs font-medium text-muted-readable">Your workspace</p>
        <h1>Settings</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-readable">Your account and how CareerLens reaches the AI.</p>
      </div>
      <div className="grid max-w-3xl gap-6">
        <AccountCard />
        <AiKeyCard />
        <Link
          href="/extension"
          className="flex items-center gap-3 rounded-card border border-border bg-surface p-5 text-sm font-semibold text-primary-text shadow-card"
        >
          <Puzzle size={20} aria-hidden="true" />
          Install the Chrome extension
          <ArrowUpRight className="ml-auto" size={16} aria-hidden="true" />
        </Link>
      </div>
    </section>
  );
}
