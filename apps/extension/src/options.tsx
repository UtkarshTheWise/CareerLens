import { useEffect, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import { BriefcaseBusiness } from "lucide-react";
import "@fontsource/plus-jakarta-sans/400.css";
import "@fontsource/plus-jakarta-sans/500.css";
import "@fontsource/plus-jakarta-sans/600.css";
import "@fontsource/plus-jakarta-sans/700.css";
import "./styles.css";
import {
  defaults,
  loadSettings,
  saveSettings,
  validateSettings,
  useSettings,
  type Settings,
} from "./settings";
import { getMe, message } from "./api";
import { Card, Status } from "./components";
function Options() {
  useSettings();
  const [draft, setDraft] = useState<Settings>(defaults),
    [ready, setReady] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [status, setStatus] = useState("");
  useEffect(() => {
    let alive = true;
    void loadSettings()
      .then((value) => {
        if (alive) setDraft(value);
      })
      .catch(() => {
        if (alive)
          setError(
            "Stored settings could not be loaded. Configure and save them again.",
          );
      })
      .finally(() => {
        if (alive) setReady(true);
      });
    return () => {
      alive = false;
    };
  }, []);
  function update<K extends keyof Settings>(key: K, value: Settings[K]) {
    setDraft((previous) => ({ ...previous, [key]: value }));
    setStatus("");
    setError("");
  }
  async function fetchProfile() {
    if (busy) return;
    setBusy(true);
    setError("");
    setStatus("");
    try {
      const config = validateSettings({ ...draft, profileId: "" }),
        profile = await getMe(config);
      setDraft((previous) => ({ ...previous, profileId: profile.id }));
      setStatus("Profile fetched. Save settings to use it.");
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    setStatus("");
    try {
      const value = await saveSettings(draft);
      setDraft(value);
      setStatus("Settings saved on this device.");
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="options">
      <header className="brand">
        <span className="icon">
          <BriefcaseBusiness size={22} aria-hidden="true" />
        </span>
        <h1 style={{ fontSize: 22 }}>CareerLens options</h1>
      </header>
      <Card>
        <h2 className="posting-title">Connect your profile</h2>
        <p className="muted">
          Use the same API and profile as your CareerLens web app.
        </p>
        <form className="form" onSubmit={(e) => void save(e)}>
          <label>
            API base URL
            <input
              className="input"
              type="url"
              required
              value={draft.apiUrl}
              disabled={!ready || busy}
              onChange={(e) => update("apiUrl", e.target.value)}
              aria-describedby="api-help"
            />
          </label>
          <p className="muted" id="api-help">
            Local development defaults to http://localhost:8000 and sends Bearer
            dev. Custom remote APIs must allow requests from this extension
            through CORS. No production login is configured here.
          </p>
          <label>
            Profile ID
            <input
              className="input"
              value={draft.profileId}
              disabled={!ready || busy}
              onChange={(e) => update("profileId", e.target.value)}
              aria-describedby="profile-help"
              placeholder="Your profile UUID"
            />
          </label>
          <p className="muted" id="profile-help">
            Fetch your current profile from the configured API, or enter its
            UUID.
          </p>
          <button
            type="button"
            className="button"
            disabled={!ready || busy}
            onClick={() => void fetchProfile()}
          >
            {busy ? "Working…" : "Fetch my profile"}
          </button>
          <label>
            Theme
            <select
              className="input"
              value={draft.theme}
              disabled={!ready || busy}
              onChange={(e) =>
                update("theme", e.target.value as Settings["theme"])
              }
            >
              <option value="system">System</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </label>
          <button className="button primary" disabled={!ready || busy}>
            {busy ? "Working…" : "Save settings"}
          </button>
          {error && <Status error>{error}</Status>}
          {status && <Status>{status}</Status>}
          {!ready && <Status>Loading settings…</Status>}
        </form>
      </Card>
      <p className="muted">
        Only the API URL, profile ID and theme are stored locally. Job text and
        match results remain in the current panel session. LLM keys belong on
        the backend.
      </p>
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<Options />);
