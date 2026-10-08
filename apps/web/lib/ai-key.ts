// A student's own Gemini or Groq key. It lives only in this browser (localStorage) and is sent, as two
// headers, only with the requests that call a model. The API never stores it (see apps/api/README.md).
export type AiProvider = "gemini" | "groq";
export type AiKey = { provider: AiProvider; key: string };

const STORAGE_KEY = "careerlens.ai-key";
// Operations that call a model: startAnalysis, createQuiz, answerQuizQuestion, submitQuiz, matchJob, tailorResume,
// plus getQuiz and getQuizResult, which grade a quiz whose time ran out.
const LLM_ROUTES: Array<{ method: string; path: RegExp }> = [
  { method: "POST", path: /^\/v1\/profiles\/[^/]+\/analyses$/ },
  { method: "POST", path: /^\/v1\/analyses\/[^/]+\/quizzes$/ },
  { method: "GET", path: /^\/v1\/quizzes\/[^/]+$/ },
  { method: "POST", path: /^\/v1\/quizzes\/[^/]+\/answers$/ },
  { method: "POST", path: /^\/v1\/quizzes\/[^/]+\/submit$/ },
  { method: "GET", path: /^\/v1\/quizzes\/[^/]+\/result$/ },
  { method: "POST", path: /^\/v1\/jobs\/match$/ },
  { method: "POST", path: /^\/v1\/applications\/[^/]+\/tailored-resume$/ },
];

function storage(): Storage | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
}

export function isValidKey(key: string): boolean {
  return /^[\x21-\x7e]{20,200}$/.test(key);
}

export function readAiKey(): AiKey | null {
  try {
    const raw = storage()?.getItem(STORAGE_KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<AiKey>;
    if ((value.provider === "gemini" || value.provider === "groq") && typeof value.key === "string" && isValidKey(value.key)) {
      return { provider: value.provider, key: value.key };
    }
  } catch {
    // unreadable or tampered value: treat as no key
  }
  return null;
}

/** Returns false when the browser would not store it (private window, blocked storage) or the key is malformed. */
export function saveAiKey(provider: AiProvider, key: string): boolean {
  const trimmed = key.trim();
  if (!isValidKey(trimmed)) return false;
  try {
    const store = storage();
    if (!store) return false;
    store.setItem(STORAGE_KEY, JSON.stringify({ provider, key: trimmed }));
    return readAiKey() !== null;
  } catch {
    return false;
  }
}

export function clearAiKey(): void {
  try {
    storage()?.removeItem(STORAGE_KEY);
  } catch {
    // nothing to remove
  }
}

/** "…wxyz": enough to recognise the key, never enough to use it. */
export function maskKey(key: string): string {
  return key.length > 8 ? `…${key.slice(-4)}` : "…";
}

export function providerLabel(provider: AiProvider): string {
  return provider === "gemini" ? "Gemini" : "Groq";
}

/** The headers for one request: only for the model-calling operations, and only when a key is saved. */
export function aiKeyHeaders(path: string, method: string, saved: AiKey | null = readAiKey()): Record<string, string> {
  if (!saved) return {};
  const upper = method.toUpperCase();
  if (!LLM_ROUTES.some((route) => route.method === upper && route.path.test(path))) return {};
  return { "X-LLM-Provider": saved.provider, "X-LLM-Key": saved.key };
}
