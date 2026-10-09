"use client";
import { useState, type ReactNode } from "react";
import { Check, Copy } from "lucide-react";
import { PageHeader, Section } from "@/components/layout/page";
import { Button } from "@/components/ui/button";

export const EXTENSION_ZIP = "/downloads/careerlens-extension.zip";
const EXTENSION_ID = "bchilaidlnimfdagenlcpoannjomfkil";

function CopyText({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false); // the text is selectable right there
    }
  }
  return (
    <span className="inline-flex max-w-full items-center gap-2 rounded-control bg-surface-2 px-3 py-1.5 align-middle">
      <code className="min-w-0 break-all text-xs">{text}</code>
      <button type="button" onClick={() => void copy()} className="inline-flex size-8 shrink-0 items-center justify-center text-primary-text" aria-label={`Copy ${text}`}>
        {copied ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
      </button>
      <span role="status" className="sr-only">
        {copied ? "Copied" : ""}
      </span>
    </span>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <li className="grid grid-cols-[40px_minmax(0,1fr)] gap-x-4 border-t border-border py-6 first:border-t-0 first:pt-0">
      <span className="font-medium text-muted-readable [font-variant-numeric:tabular-nums]" aria-hidden="true">
        {String(n).padStart(2, "0")}
      </span>
      <div className="min-w-0 space-y-2">
        <h3 className="text-[17px] font-medium tracking-[-.02em]">
          <span className="sr-only">Step {n}: </span>
          {title}
        </h3>
        <div className="space-y-2 text-sm leading-relaxed text-muted-readable">{children}</div>
      </div>
    </li>
  );
}

const troubleshooting: Array<{ q: ReactNode; a: ReactNode }> = [
  {
    q: "Sign-in says the redirect isn't allowed",
    a: (
      <>
        The extension ID in Chrome must be exactly <code className="break-all">{EXTENSION_ID}</code>. If it differs, you loaded a different build;
        download the zip above again and remove the old copy.
      </>
    ),
  },
  { q: <>&ldquo;Signed out&rdquo; or &ldquo;Unauthorized&rdquo; later on</>, a: "Open Options and sign in again; sessions expire after a while." },
  { q: "It says there is no analysis", a: "Run a report on this site first; the extension compares jobs against your latest finished report." },
  { q: "The first request is slow or fails", a: "The free server sleeps when idle and takes up to a minute to wake. Wait, then try again." },
  {
    q: <>&ldquo;The AI service is busy&rdquo;</>,
    a: "The shared free allowance is used up. Reading a page that lists no skills is the only thing the extension asks the AI for. Try again in a minute.",
  },
];

export function InstallGuide() {
  return (
    <section>
      <PageHeader
        eyebrow="Your workspace"
        title="Chrome extension"
        description="Open a job posting, click the CareerLens icon, and see how your evidence matches what the job asks for. Then save it to your tracker in one click. It takes about two minutes to set up."
      />

      <Section title="Set it up" className="max-w-3xl">
        <p className="lede mb-8">
          You need Chrome (or Edge, Brave) version 116 or newer, and a CareerLens profile with at least one finished report. The extension is not in
          the Chrome Web Store yet, so you add it by hand. Chrome will show a &ldquo;developer mode&rdquo; notice afterwards; that is expected.
        </p>
        <ol>
          <Step n={1} title="Download the extension">
            <Button asChild trailingArrow>
              <a href={EXTENSION_ZIP} download>
                Download careerlens-extension.zip
              </a>
            </Button>
          </Step>
          <Step n={2} title="Unzip it">
            <p>
              Right-click the file and choose <strong>Extract all</strong> (Windows) or double-click it (Mac). Keep the unzipped folder somewhere
              permanent, such as Documents; Chrome reads it from there every time it starts.
            </p>
          </Step>
          <Step n={3} title="Open Chrome's extensions page">
            <p>
              Paste this into a new tab&apos;s address bar (links to it are blocked by the browser): <CopyText text="chrome://extensions" />
            </p>
          </Step>
          <Step n={4} title="Turn on Developer mode">
            <p>
              Use the <strong>Developer mode</strong> switch at the top right of that page.
            </p>
          </Step>
          <Step n={5} title="Load the folder">
            <p>
              Click <strong>Load unpacked</strong> and choose the unzipped folder: the one that contains <code>manifest.json</code>. CareerLens appears in
              the list{" "}
              <span>
                with the ID <CopyText text={EXTENSION_ID} />.
              </span>
            </p>
            <p>Click the puzzle-piece icon in Chrome&apos;s toolbar and pin CareerLens so it is always one click away.</p>
          </Step>
          <Step n={6} title="Sign in and connect your profile">
            <p>
              Right-click the CareerLens icon and choose <strong>Options</strong>. Press <strong>Sign in with Google</strong> and use the same account as
              this site. Then press <strong>Fetch my profile</strong> and <strong>Save settings</strong>.
            </p>
          </Step>
          <Step n={7} title="Try it on a job">
            <p>
              Open a job posting on Greenhouse, Lever, Workday, Naukri, LinkedIn, or any page with standard job data. Click the CareerLens icon, then{" "}
              <strong>Analyse this job</strong>. You&apos;ll see which required skills your work already shows evidence for, and which are gaps.
            </p>
          </Step>
        </ol>
      </Section>

      <Section title="If something doesn't work" className="max-w-3xl">
        <div className="faq">
          {troubleshooting.map((item, i) => (
            <details key={i}>
              <summary>{item.q}</summary>
              <p>{item.a}</p>
            </details>
          ))}
        </div>
        <p className="mt-8 max-w-prose text-xs leading-relaxed text-muted-readable">
          Privacy: the extension reads only the page you ask it to analyse, when you click. It sends the job&apos;s text to CareerLens, and nothing else
          from your browser.
        </p>
      </Section>
    </section>
  );
}
