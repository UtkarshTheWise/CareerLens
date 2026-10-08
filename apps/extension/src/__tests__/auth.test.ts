import assert from "node:assert/strict";
import { test } from "node:test";
import { bearerFor, codeFromRedirect } from "../auth-helpers";

const base = "https://bchilaidlnimfdagenlcpoannjomfkil.chromiumapp.org/";

test("the authorization code is read from the redirect back to the extension", () => {
  assert.equal(codeFromRedirect(`${base}?code=abc-123`), "abc-123");
  assert.equal(codeFromRedirect(`${base}?foo=1&code=xyz&state=s`), "xyz");
});

test("a refused or cancelled sign-in is a plain message, never the provider text", () => {
  for (const url of [
    `${base}?error=access_denied&error_description=User+denied+access`,
    `${base}#error=access_denied&error_description=Something+secret`,
    `${base}?error=server_error`,
  ]) {
    assert.throws(() => codeFromRedirect(url), (e: Error) => e.message === "Google sign-in was not completed. Try again.");
  }
});

test("a redirect without a code, or that is not a URL, fails clearly", () => {
  assert.throws(() => codeFromRedirect(base), /did not finish/);
  assert.throws(() => codeFromRedirect(""), /did not return to the extension/);
  assert.throws(() => codeFromRedirect("not a url"), /did not return to the extension/);
});

test("signed out means an empty bearer, so the API answers 401 and the panel says to sign in", () => {
  assert.equal(bearerFor("token-1"), "token-1");
  assert.equal(bearerFor(null), "");
});
