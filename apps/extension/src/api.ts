import { createApiClient, type components } from "@careerlens/api-client";
import type { Settings } from "./settings";
export class RequestError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
const client = (settings: Settings) => {
  const u = new URL(settings.apiUrl),
    dev =
      import.meta.env.DEV || ["localhost", "127.0.0.1"].includes(u.hostname);
  const api = createApiClient(settings.apiUrl, dev ? "dev" : "");
  if (!dev)
    api.use({
      onRequest: ({ request }) => {
        request.headers.delete("Authorization");
        return request;
      },
    });
  return api;
};
async function unwrap<T>({
  data,
  error,
  response,
}: {
  data?: T;
  error?: unknown;
  response: Response;
}) {
  if (!response.ok) {
    const message =
      error &&
      typeof error === "object" &&
      "message" in error &&
      typeof error.message === "string"
        ? error.message
        : "The API request failed (" + response.status + "). Try again.";
    throw new RequestError(response.status, message);
  }
  if (data == null) throw new Error("The API returned no data.");
  return data;
}
export async function getMe(settings: Settings, signal?: AbortSignal) {
  return unwrap(await client(settings).GET("/v1/me", { signal }));
}
export async function matchJob(
  settings: Settings,
  posting: components["schemas"]["JobPosting"],
  signal?: AbortSignal,
) {
  return unwrap(
    await client(settings).POST("/v1/jobs/match", {
      signal,
      body: { profile_id: settings.profileId, posting },
    }),
  );
}
export async function createApplication(
  settings: Settings,
  body: components["schemas"]["ApplicationCreate"],
  signal?: AbortSignal,
) {
  return unwrap(
    await client(settings).POST("/v1/applications", { signal, body }),
  );
}
export function message(error: unknown) {
  return error instanceof RequestError
    ? error.message
    : error instanceof Error && error.name !== "TypeError"
      ? error.message
      : "Could not reach the API. Check its URL, server availability and extension CORS access in Options.";
}
