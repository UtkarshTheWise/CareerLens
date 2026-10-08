"use client";
import { useState, type ReactNode } from "react";
import { Check, Copy, Download } from "lucide-react";
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
      <button type="button" onClick={() => void copy()} className="shrink-0 text-primary-text" aria-label={`Copy ${text}`}>
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
    <li className="flex gap-4">
      <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary-soft text-sm font-semibold text-chip-text" aria-hidden="true">
        {n}
      </span>
      <div className="min-w-0 space-y-2">
        <h3 className="text-base font-semibold">
          <span className="sr-only">Step {n}: </span>
          {title}
        </h3>
        <div className="space-y-2 text-sm text-muted-readable">{children}</div>
      </div>
    </li>
  );
}

const card = "rounded-card border border-border bg-surface p-6 shadow-card sm:p-8";

export function InstallGuide() {
  return (
    <section className="space-y-8">
      <div>
        <p className="mb-2 text-xs font-medium text-muted-readable">Your workspace</p>
        <h1>Chrome extension</h1>
        <p className="mt-2 max-w-xl text-sm text-muted-readable">
          Open a job posting, click the CareerLens icon, and see how your evidence matches what the job asks for. Then save it to your tracker in one
          click. It takes about two minutes to set up.
        </p>
      </div>

      <div className={`${card} max-w-3xl space-y-6`}>
        <p className="text-sm text-muted-readable">
          You need Chrome (or Edge, Brave) version 116 or newer, and a CareerLens profile with at least one finished report. The extension is not in
          the Chrome Web Store yet, so you add it by hand. Chrome will show a &ldquo;developer mode&rdquo; notice afterwards; that is expected.
        </p>
        <ol className="space-y-6">
          <Step n={1} title="Download the extension">
            <Button asChild>
              <a href={EXTENSION_ZIP} download>
                <Download size={16} aria-hidden="true" />
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
      </div>

      <div className={`${card} max-w-3xl space-y-4`}>
        <h2>If something doesn&apos;t work</h2>
        <dl className="space-y-4 text-sm">
          <div>
            <dt className="font-semibold">Sign-in says the redirect isn&apos;t allowed</dt>
            <dd className="text-muted-readable">
              The extension ID in Chrome must be exactly <code className="break-all">{EXTENSION_ID}</code>. If it differs, you loaded a different build;
              download the zip above again and remove the old copy.
            </dd>
          </div>
          <div>
            <dt className="font-semibold">&ldquo;Signed out&rdquo; or &ldquo;Unauthorized&rdquo; later on</dt>
            <dd className="text-muted-readable">Open Options and sign in again; sessions expire after a while.</dd>
          </div>
          <div>
            <dt className="font-semibold">It says there is no analysis</dt>
            <dd className="text-muted-readable">Run a report on this site first; the extension compares jobs against your latest finished report.</dd>
          </div>
          <div>
            <dt className="font-semibold">The first request is slow or fails</dt>
            <dd className="text-muted-readable">
              The free server sleeps when idle and takes up to a minute to wake. Wait, then try again.
            </dd>
          </div>
          <div>
            <dt className="font-semibold">&ldquo;The AI service is busy&rdquo;</dt>
            <dd className="text-muted-readable">
              The shared free allowance is used up. Reading a page that lists no skills is the only thing the extension asks the AI for. Try again in a
              minute.
            </dd>
          </div>
        </dl>
        <p className="border-t border-border pt-4 text-xs text-muted-readable">
          Privacy: the extension reads only the page you ask it to analyse, when you click. It sends the job&apos;s text to CareerLens, and nothing else
          from your browser.
        </p>
      </div>
    </section>
  );
}
