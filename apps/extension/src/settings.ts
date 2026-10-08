import { useEffect, useState } from "react";
export type Settings = {
  apiUrl: string;
  profileId: string;
  theme: "system" | "light" | "dark";
};
export const defaults: Settings = {
  // A production build bakes in its API with VITE_API_URL (optional chaining: Node tests have no import.meta.env).
  apiUrl: (import.meta.env?.VITE_API_URL as string | undefined) || "http://localhost:8000",
  profileId: "",
  theme: "system",
};
export function validateSettings(value: Settings): Settings {
  let url: URL;
  try {
    url = new URL(value.apiUrl.trim());
  } catch {
    throw new Error("Enter a full HTTP or HTTPS API URL.");
  }
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash
  )
    throw new Error(
      "Use an HTTP or HTTPS API base URL without login details, query or fragment.",
    );
  const profileId = value.profileId.trim();
  if (
    profileId &&
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      profileId,
    )
  )
    throw new Error("Enter a valid profile UUID, or use Fetch my profile.");
  if (!["system", "light", "dark"].includes(value.theme))
    throw new Error("Choose system, light or dark theme.");
  return { apiUrl: url.href.replace(/\/$/, ""), profileId, theme: value.theme };
}
export async function loadSettings(): Promise<Settings> {
  const { settings } = await chrome.storage.local.get("settings");
  return settings ? validateSettings({ ...defaults, ...settings }) : defaults;
}
export async function saveSettings(value: Settings) {
  const settings = validateSettings(value);
  await chrome.storage.local.set({ settings });
  return settings;
}
export function useSettings() {
  const [settings, setSettings] = useState<Settings>(),
    [error, setError] = useState("");
  useEffect(() => {
    let alive = true;
    const load = () =>
      loadSettings()
        .then((v) => {
          if (alive) {
            setSettings(v);
            setError("");
          }
        })
        .catch(() => {
          if (alive)
            setError(
              "Extension settings could not be read. Open Options to configure them.",
            );
        });
    void load();
    const changed = (
      _changes: Record<string, chrome.storage.StorageChange>,
      area: string,
    ) => {
      if (area === "local") void load();
    };
    chrome.storage.onChanged.addListener(changed);
    return () => {
      alive = false;
      chrome.storage.onChanged.removeListener(changed);
    };
  }, []);
  useEffect(() => {
    if (!settings) return;
    const media = matchMedia("(prefers-color-scheme: dark)"),
      apply = () => {
        document.documentElement.dataset.theme =
          settings.theme === "system"
            ? media.matches
              ? "dark"
              : "light"
            : settings.theme;
      };
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [settings]);
  return { settings, error };
}
