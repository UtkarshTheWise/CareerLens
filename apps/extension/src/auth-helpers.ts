// Pure helpers for the Google sign-in flow, kept free of chrome.* and import.meta so they can be tested in Node.

/** The authorization code in the URL Supabase sent the browser back to after Google. */
export function codeFromRedirect(responseUrl: string): string {
  let url: URL;
  try {
    url = new URL(responseUrl);
  } catch {
    throw new Error("Sign-in did not return to the extension. Try again.");
  }
  // Supabase reports a refusal (for example the user pressed Cancel) as error params on the query or hash.
  const params = new URLSearchParams(url.hash.replace(/^#/, ""));
  const error = url.searchParams.get("error_description") || url.searchParams.get("error") || params.get("error_description") || params.get("error");
  if (error) throw new Error("Google sign-in was not completed. Try again.");
  const code = url.searchParams.get("code");
  if (!code) throw new Error("Sign-in did not finish. Try again.");
  return code;
}

/** The value for the Authorization header: the user's token, or an empty bearer so the API answers 401. */
export function bearerFor(token: string | null): string {
  return token ?? "";
}
