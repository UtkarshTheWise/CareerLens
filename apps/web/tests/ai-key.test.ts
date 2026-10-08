import test from "node:test";
import assert from "node:assert/strict";
import { aiKeyHeaders, clearAiKey, isValidKey, maskKey, readAiKey, saveAiKey } from "../lib/ai-key";

const KEY = "AIzaSy-0123456789-abcdefghijklmnop";

function fakeStorage(fail = false) {
  const data = new Map<string, string>();
  return {
    getItem: (k: string) => {
      if (fail) throw new Error("blocked");
      return data.get(k) ?? null;
    },
    setItem: (k: string, v: string) => {
      if (fail) throw new Error("blocked");
      data.set(k, v);
    },
    removeItem: (k: string) => {
      if (fail) throw new Error("blocked");
      data.delete(k);
    },
    data,
  };
}
function withStorage<T>(storage: unknown, run: () => T): T {
  Object.defineProperty(globalThis, "localStorage", { value: storage, configurable: true });
  try {
    return run();
  } finally {
    Reflect.deleteProperty(globalThis, "localStorage");
  }
}

test("a key is validated, saved, read back and removed", () => {
  withStorage(fakeStorage(), () => {
    assert.equal(readAiKey(), null);
    assert.equal(saveAiKey("gemini", "too short"), false);
    assert.equal(saveAiKey("groq", "has spaces inside the key value"), false);
    assert.equal(saveAiKey("gemini", `  ${KEY}  `), true);
    assert.deepEqual(readAiKey(), { provider: "gemini", key: KEY });
    clearAiKey();
    assert.equal(readAiKey(), null);
  });
});

test("blocked or missing storage never throws and never reports a saved key", () => {
  withStorage(fakeStorage(true), () => {
    assert.equal(saveAiKey("gemini", KEY), false);
    assert.equal(readAiKey(), null);
    assert.doesNotThrow(clearAiKey);
  });
  assert.equal(readAiKey(), null); // no localStorage at all
  assert.equal(saveAiKey("gemini", KEY), false);
});

test("a tampered stored value is ignored", () => {
  const store = fakeStorage();
  store.data.set("careerlens.ai-key", JSON.stringify({ provider: "openai", key: KEY }));
  withStorage(store, () => assert.equal(readAiKey(), null));
  store.data.set("careerlens.ai-key", "{not json");
  withStorage(store, () => assert.equal(readAiKey(), null));
});

test("the key is masked to its last four characters", () => {
  assert.equal(maskKey(KEY), "…mnop");
  assert.equal(maskKey("short"), "…");
  assert.equal(isValidKey(KEY), true);
  assert.equal(isValidKey("ключ-0123456789-0123456789"), false);
});

test("headers go only on the model-calling operations, and only when a key is saved", () => {
  const saved = { provider: "groq" as const, key: KEY };
  const expected = { "X-LLM-Provider": "groq", "X-LLM-Key": KEY };
  const calls: Array<[string, string]> = [
    ["/v1/profiles/p1/analyses", "POST"],
    ["/v1/analyses/a1/quizzes", "POST"],
    ["/v1/quizzes/q1", "GET"],
    ["/v1/quizzes/q1/answers", "POST"],
    ["/v1/quizzes/q1/submit", "post"],
    ["/v1/quizzes/q1/result", "GET"],
    ["/v1/jobs/match", "POST"],
    ["/v1/applications/x1/tailored-resume", "POST"],
  ];
  for (const [path, method] of calls) assert.deepEqual(aiKeyHeaders(path, method, saved), expected, path);
  const others: Array<[string, string]> = [
    ["/v1/me", "GET"],
    ["/v1/profiles/p1/analyses", "GET"],
    ["/v1/profiles/p1/documents", "POST"],
    ["/v1/analyses/a1", "GET"],
    ["/v1/cohorts", "GET"],
    ["/v1/applications", "POST"],
    ["/v1/quizzes/q1", "DELETE"],
  ];
  for (const [path, method] of others) assert.deepEqual(aiKeyHeaders(path, method, saved), {}, path);
  assert.deepEqual(aiKeyHeaders("/v1/jobs/match", "POST", null), {});
});
