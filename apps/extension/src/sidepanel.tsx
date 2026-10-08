import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { createRoot } from "react-dom/client";
import {
  BriefcaseBusiness,
  Settings as SettingsIcon,
  Sparkles,
} from "lucide-react";
import type { components } from "@careerlens/api-client";
import "@fontsource/plus-jakarta-sans/400.css";
import "@fontsource/plus-jakarta-sans/500.css";
import "@fontsource/plus-jakarta-sans/600.css";
import "@fontsource/plus-jakarta-sans/700.css";
import "./styles.css";
import { useSettings, type Settings } from "./settings";
import { dateOnly } from "./adapters/shared";
import { activeTab, extractActive } from "./browser";
import { matchJob, createApplication, message } from "./api";
import { Card, Ring, LevelPill, Status } from "./components";
type Result = {
  match: components["schemas"]["JobMatch"];
  posting: components["schemas"]["JobPosting"];
  tab: { id: number; url: string };
  settings: Settings;
};
const tabs = ["Match", "Gaps", "Save"] as const;
function Panel() {
  const { settings, error: settingsError } = useSettings(),
    [tab, setTab] = useState(0),
    [result, setResult] = useState<Result>(),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [saved, setSaved] = useState(""),
    [company, setCompany] = useState(""),
    [title, setTitle] = useState(""),
    [deadline, setDeadline] = useState(""),
    [notes, setNotes] = useState("");
  const request = useRef<AbortController | null>(null),
    target = useRef<{ id: number; url: string } | null>(null),
    tabButtons = useRef<(HTMLButtonElement | null)[]>([]);
  const invalidate = (text: string) => {
    request.current?.abort();
    request.current = null;
    target.current = null;
    setBusy(false);
    setResult(undefined);
    setSaved("");
    setError("");
    setNotice(text);
  };
  useEffect(() => {
    invalidate("");
  }, [settings?.apiUrl, settings?.profileId]);
  useEffect(() => {
    const activated = ({ tabId }: { tabId: number }) => {
      if (target.current && target.current.id !== tabId)
        invalidate("The active tab changed. Analyse the current job again.");
    };
    const updated = (id: number, change: chrome.tabs.OnUpdatedInfo) => {
      if (
        target.current?.id === id &&
        (change.status === "loading" ||
          (change.url && change.url !== target.current.url))
      )
        invalidate("The job page changed. Analyse it again before saving.");
    };
    const removed = (id: number) => {
      if (target.current?.id === id) invalidate("The job tab was closed.");
    };
    chrome.tabs.onActivated.addListener(activated);
    chrome.tabs.onUpdated.addListener(updated);
    chrome.tabs.onRemoved.addListener(removed);
    return () => {
      request.current?.abort();
      chrome.tabs.onActivated.removeListener(activated);
      chrome.tabs.onUpdated.removeListener(updated);
      chrome.tabs.onRemoved.removeListener(removed);
    };
  }, []);
  async function analyse() {
    if (!settings || request.current) return;
    if (!settings.profileId) {
      setError("Choose your profile in Options before analysing a job.");
      return;
    }
    const ctrl = new AbortController();
    request.current = ctrl;
    setBusy(true);
    setResult(undefined);
    setSaved("");
    setError("");
    setNotice("Reading the active job page…");
    setTab(0);
    try {
      target.current = await activeTab();
      if (ctrl.signal.aborted) return;
      const extracted = await extractActive();
      if (ctrl.signal.aborted) return;
      setNotice("Matching this job against your profile…");
      const match = await matchJob(settings, extracted.posting, ctrl.signal);
      const current = await activeTab();
      if (ctrl.signal.aborted) return;
      if (current.id !== extracted.tab.id || current.url !== extracted.tab.url)
        throw new Error(
          "The active page changed. Analyse the current job again.",
        );
      const posting = match.normalized_posting ?? extracted.posting;
      setResult({
        match,
        posting: { ...posting, url: posting.url ?? extracted.tab.url },
        tab: extracted.tab,
        settings,
      });
      setCompany(posting.company ?? "");
      setTitle(posting.title);
      setDeadline(posting.deadline ?? "");
      setNotes("");
      setNotice("");
    } catch (e) {
      if (!ctrl.signal.aborted) {
        setError(message(e));
        setNotice("");
      }
    } finally {
      if (request.current === ctrl) {
        request.current = null;
        setBusy(false);
      }
    }
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (!result || !settings || request.current || saved) return;
    if (!company.trim() || !title.trim()) {
      setError("Enter the company and job title before saving.");
      return;
    }
    if (deadline && dateOnly(deadline) !== deadline) {
      setError("Choose a valid calendar deadline.");
      return;
    }
    const ctrl = new AbortController();
    request.current = ctrl;
    setBusy(true);
    setError("");
    try {
      const current = await activeTab();
      if (ctrl.signal.aborted) return;
      if (
        current.id !== result.tab.id ||
        current.url !== result.tab.url ||
        settings.apiUrl !== result.settings.apiUrl ||
        settings.profileId !== result.settings.profileId
      ) {
        invalidate(
          "This match belongs to an earlier page or profile. Analyse the job again.",
        );
        return;
      }
      const application = await createApplication(
        settings,
        {
          profile_id: settings.profileId,
          company: company.trim(),
          title: title.trim(),
          url: result.posting.url,
          status: "saved",
          deadline: deadline || null,
          keyword_match: result.match.keyword_match,
          evidence_match: result.match.evidence_match,
          description: result.posting.description,
          notes: notes.trim() || null,
        },
        ctrl.signal,
      );
      if (!ctrl.signal.aborted) setSaved(application.id);
    } catch (e) {
      if (!ctrl.signal.aborted) setError(message(e));
    } finally {
      if (request.current === ctrl) {
        request.current = null;
        setBusy(false);
      }
    }
  }
  function tabKey(event: KeyboardEvent, index: number) {
    let next = index;
    if (event.key === "ArrowRight") next = (index + 1) % 3;
    else if (event.key === "ArrowLeft") next = (index + 2) % 3;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = 2;
    else return;
    event.preventDefault();
    setTab(next);
    tabButtons.current[next]?.focus();
  }
  return (
    <main>
      <header className="header">
        <div className="brand">
          <span className="icon">
            <BriefcaseBusiness size={22} aria-hidden="true" />
          </span>
          <h1 style={{ fontSize: 18 }}>CareerLens</h1>
        </div>
        <button
          className="button ghost"
          aria-label="Open Options"
          onClick={() => void chrome.runtime.openOptionsPage()}
        >
          <SettingsIcon size={20} />
        </button>
      </header>
      <Card>
        <span className="caption">JOB MATCH</span>
        {!result && (
          <>
            <h2 className="posting-title">See where your evidence fits.</h2>
            <p className="muted">
              Open a job page, then analyse it against your CareerLens profile.
              Page text is sent to your configured API only when you click
              below.
            </p>
          </>
        )}
        <button
          className="button primary"
          disabled={busy || !settings}
          onClick={() => void analyse()}
        >
          <Sparkles size={16} aria-hidden="true" />
          {busy && !result ? "Analysing…" : "Analyse this job"}
        </button>
        {!settings && !settingsError && <Status>Loading settings…</Status>}
        {settings && !settings.profileId && (
          <>
            <Status>Set your profile in Options to get started.</Status>
            <button
              className="button ghost"
              onClick={() => void chrome.runtime.openOptionsPage()}
            >
              Set up profile
            </button>
          </>
        )}
        {settingsError && <Status error>{settingsError}</Status>}
        {notice && <Status>{notice}</Status>}
        {error && <Status error>{error}</Status>}
      </Card>
      <div className="tabs" role="tablist" aria-label="Job match views">
        {tabs.map((name, index) => (
          <button
            key={name}
            ref={(el) => {
              tabButtons.current[index] = el;
            }}
            role="tab"
            id={"tab-" + index}
            aria-controls={"panel-" + index}
            aria-selected={tab === index}
            tabIndex={tab === index ? 0 : -1}
            onClick={() => {
              setTab(index);
              setError("");
            }}
            onKeyDown={(event) => tabKey(event, index)}
          >
            {name}
          </button>
        ))}
      </div>
      <div
        className="tab-panel"
        role="tabpanel"
        id={"panel-" + tab}
        aria-labelledby={"tab-" + tab}
        tabIndex={0}
      >
        {!result ? (
          <Card>
            <h2 className="posting-title">
              {busy
                ? "Your match is on its way"
                : "Start with a job you’re considering"}
            </h2>
            <p className="muted">
              {busy
                ? "We’ll show the API’s keyword and evidence-backed results here."
                : "Analyse a job to view matches, gaps and save it to your tracker."}
            </p>
            {busy && <div className="skeleton" aria-hidden="true" />}
          </Card>
        ) : (
          <>
            <Card>
              <h2 className="posting-title">{result.posting.title}</h2>
              <p className="muted">
                {[result.posting.company, result.posting.location]
                  .filter(Boolean)
                  .join(" · ") || "Company and location were not provided."}
              </p>
              <a
                className="url"
                href={result.tab.url}
                target="_blank"
                rel="noreferrer"
              >
                View original job
              </a>
              <p className="muted">
                Extraction:{" "}
                {result.posting.source === "jsonld"
                  ? "structured job data"
                  : result.posting.source === "dom"
                    ? "page selectors"
                    : result.posting.source === "llm"
                      ? "visible text, interpreted by the API"
                      : "manual posting"}
              </p>
              <details className="posting-preview">
                <summary>Review extracted description</summary>
                <p className="description-preview">
                  {result.posting.description}
                </p>
              </details>
            </Card>
            {tab === 0 ? (
              <>
                <Card>
                  <div className="ring-grid">
                    <Ring
                      key={result.tab.url + "keyword"}
                      value={result.match.keyword_match}
                      label="Keyword match"
                      why={
                        "The API compares the job’s required skills with your profile claims. " +
                        result.match.summary
                      }
                    />
                    <Ring
                      key={result.tab.url + "evidence"}
                      value={result.match.evidence_match}
                      label="Evidence-backed match"
                      why={
                        "The API weights matched skills by their evidence level. " +
                        result.match.summary
                      }
                    />
                  </div>
                  <p style={{ fontSize: 13, lineHeight: 1.7 }}>
                    {result.match.summary}
                  </p>
                </Card>
                <Card>
                  <h2 className="posting-title">
                    Matched skills{" "}
                    <span className="muted">
                      ({result.match.matched.length})
                    </span>
                  </h2>
                  {result.match.matched.length ? (
                    <ul className="rows">
                      {result.match.matched.map((skill, index) => (
                        <li key={skill.skill_id + index}>
                          <span>{skill.skill_name}</span>
                          <LevelPill level={skill.level} />
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="muted">No matched skills were returned.</p>
                  )}
                </Card>
              </>
            ) : tab === 1 ? (
              <>
                {(["missing", "unverified"] as const).map((kind) => (
                  <Card key={kind}>
                    <h2 className="posting-title">
                      {kind === "missing"
                        ? "Missing skills"
                        : "Unverified claims"}{" "}
                      <span className="muted">
                        ({result.match[kind].length})
                      </span>
                    </h2>
                    <p className="muted">
                      {kind === "missing"
                        ? "Required by this job, with no claim or evidence in your profile."
                        : "Claims supported by weak or unverified evidence. Add evidence to demonstrate them."}
                    </p>
                    {result.match[kind].length ? (
                      <ul className="rows">
                        {result.match[kind].map((skill, index) => (
                          <li key={skill + index}>
                            <span>{skill}</span>
                            <LevelPill level={kind} />
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="muted">
                        {kind === "missing"
                          ? "No missing skills were returned."
                          : "No unverified claims were returned."}
                      </p>
                    )}
                  </Card>
                ))}
              </>
            ) : (
              <Card>
                <h2 className="posting-title">Save to your tracker</h2>
                <p className="muted">
                  Both match scores and the job description are saved with this
                  application. Enter any details the page omitted.
                </p>
                <form className="form" onSubmit={(event) => void save(event)}>
                  <label>
                    Company
                    <input
                      className="input"
                      required
                      maxLength={2000}
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      disabled={busy || !!saved}
                    />
                  </label>
                  <label>
                    Job title
                    <input
                      className="input"
                      required
                      maxLength={2000}
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      disabled={busy || !!saved}
                    />
                  </label>
                  <label>
                    Deadline (optional)
                    <input
                      className="input"
                      type="date"
                      value={deadline}
                      onChange={(e) => setDeadline(e.target.value)}
                      disabled={busy || !!saved}
                    />
                  </label>
                  <label>
                    Notes (optional)
                    <textarea
                      className="input"
                      rows={3}
                      maxLength={4000}
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      disabled={busy || !!saved}
                    />
                  </label>
                  <button className="button primary" disabled={busy || !!saved}>
                    {saved
                      ? "Saved to tracker"
                      : busy
                        ? "Saving…"
                        : "Save to tracker"}
                  </button>
                  {saved && (
                    <Status>
                      Saved successfully. You can find this application in your
                      CareerLens tracker.
                    </Status>
                  )}
                </form>
              </Card>
            )}
          </>
        )}
      </div>
      <footer className="muted">
        Evidence supports a match; it doesn’t guarantee an offer. Settings stay
        on this device.
      </footer>
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<Panel />);
