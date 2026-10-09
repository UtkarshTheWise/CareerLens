"use client";
import { useState } from "react";
import { LogOut } from "lucide-react";
import { displayName, useAuth } from "@/components/auth/auth-provider";
import { PageHeader, Panel, Section, TextLink } from "@/components/layout/page";
import { Button } from "@/components/ui/button";
import { clearAiKey, isValidKey, maskKey, providerLabel, readAiKey, saveAiKey, type AiKey, type AiProvider } from "@/lib/ai-key";

const providers: Array<{ id: AiProvider; name: string; url: string; where: string }> = [
  { id: "gemini", name: "Google Gemini", url: "https://aistudio.google.com/apikey", where: "Google AI Studio" },
  { id: "groq", name: "Groq", url: "https://console.groq.com/keys", where: "the Groq console" },
];

function AccountCard() {
  const { status, user, signOut } = useAuth();
  const name = displayName(user);
  return (
    <Section title="Account" className="max-w-3xl">
      {status === "signed-in" ? (
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="min-w-0 text-sm">
            <span className="block font-medium">{name || "Signed in with Google"}</span>
            <span className="block truncate text-muted-readable">{user?.email}</span>
          </p>
          <Button variant="outline" onClick={() => void signOut()}>
            <LogOut size={16} aria-hidden="true" />
            Sign out
          </Button>
        </div>
      ) : (
        <p className="lede">Sign-in is not switched on in this environment.</p>
      )}
    </Section>
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
    <Section
      eyebrow="Optional"
      title="Your own AI key"
      description="CareerLens uses a small shared free allowance for the AI that reads your work and writes your quizzes. It can run out. Add a free key of your own and your reports, quizzes and job matches use your allowance instead."
      className="max-w-3xl"
    >
      <p role="status" className="inset-note text-text">
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
        className="mt-6 space-y-5"
        onSubmit={(event) => {
          event.preventDefault();
          save();
        }}
      >
        <fieldset className="space-y-2">
          <legend className="field-label">Provider</legend>
          <div className="flex flex-wrap gap-3">
            {providers.map((p) => (
              <label key={p.id} className="flex min-h-11 cursor-pointer items-center gap-2 rounded-control border border-input bg-surface px-4 py-2 text-sm has-[:checked]:border-primary has-[:checked]:bg-surface-3">
                <input type="radio" name="provider" value={p.id} checked={provider === p.id} onChange={() => setProvider(p.id)} />
                {p.name}
              </label>
            ))}
          </div>
        </fieldset>
        <div>
          <label htmlFor="ai-key" className="field-label">
            {chosen.name} API key
          </label>
          <input
            id="ai-key"
            type="password"
            className="field"
            autoComplete="off"
            spellCheck={false}
            placeholder={saved ? "Paste a new key to replace the saved one" : "Paste your key"}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            aria-describedby="ai-key-help"
          />
          <p id="ai-key-help" className="field-hint">
            Create a free key in <TextLink href={chosen.url} external>{chosen.where}</TextLink>, then paste it here.
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
          <p role={message.kind === "error" ? "alert" : "status"} className={message.kind === "error" ? "field-error" : "field-hint"}>
            {message.text}
          </p>
        )}
      </form>

      <p className="mt-8 max-w-prose border-t border-border pt-5 text-xs leading-relaxed text-muted-readable">
        Your key is kept only in this browser. When you start a report, take a quiz or match a job, it travels over HTTPS through the CareerLens
        server to {chosen.name} for that request, and is not stored or logged by us. Use a key you can revoke, and remove it on a shared computer.
        The Chrome extension still uses the shared allowance.
      </p>
    </Section>
  );
}

export function SettingsScreen() {
  return (
    <section>
      <PageHeader eyebrow="Your workspace" title="Settings" description="Your account and how CareerLens reaches the AI." />
      <AccountCard />
      <AiKeyCard />
      <Section className="max-w-3xl">
        <Panel>
          <p className="text-sm">
            Want job matches while you browse? <TextLink href="/extension">Install the Chrome extension</TextLink>
          </p>
        </Panel>
      </Section>
    </section>
  );
}
