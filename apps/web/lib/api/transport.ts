import type { components } from "@careerlens/api-client";
export class ApiError extends Error {
  constructor(public readonly status: number, public readonly details?: components["schemas"]["Error"], message = "The request could not be completed.") {
    super(details?.message || message); this.name = "ApiError";
  }
}
function contractError(value: unknown): components["schemas"]["Error"] | undefined {
  if (typeof value === "string") { try { value = JSON.parse(value); } catch { return undefined; } }
  if (typeof value === "object" && value !== null && "message" in value && typeof value.message === "string" && "code" in value && typeof value.code === "string") {
    return value as components["schemas"]["Error"];
  }
  return undefined;
}
export async function unwrap<T>(request: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
  const { data, error, response } = await request;
  if (!response.ok) throw new ApiError(response.status, contractError(error), `Request failed (${response.status}). Please try again.`);
  return data as T; // openapi-fetch's successful response is already inferred from generated paths, including 204.
}
export function shouldRetryQuery(failureCount: number, error: Error): boolean {
  return failureCount < 2 && !(error instanceof ApiError && error.status < 500);
}
export function errorMessage(error: Error): string {
  return error instanceof ApiError ? error.message : "We couldn't reach the API. Check your connection and try again.";
}
export function analysisPollInterval(analysis?: Pick<components["schemas"]["Analysis"], "status">): number | false {
  return analysis?.status === "done" || analysis?.status === "failed" ? false : 2000;
}
