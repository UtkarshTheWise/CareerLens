import { createApiClient, type ApiClient } from "@careerlens/api-client";
import { aiKeyHeaders } from "../ai-key";
import { getAccessToken, handleUnauthorized } from "../auth/session";
import { isAuthConfigured } from "../auth/supabase";

export const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:4010";
export const apiClient = createApiClient(apiBaseUrl);

// With sign-in configured, every request carries the signed-in user's access token (the wrapper's "dev"
// token is only for the mock and a DEV_AUTH backend). A 401 means the session is gone: sign out.
export const authMiddleware: Parameters<ApiClient["use"]>[0] = {
  async onRequest({ request }) {
    const token = await getAccessToken();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
  async onResponse({ response }) {
    if (response.status === 401) await handleUnauthorized();
    return response;
  },
};

if (isAuthConfigured) apiClient.use(authMiddleware);

// A student's own AI key (Settings) rides along on the requests that call a model, so those calls spend
// their quota instead of the shared allowance. Independent of sign-in.
export const aiKeyMiddleware: Parameters<ApiClient["use"]>[0] = {
  async onRequest({ request }) {
    const { pathname } = new URL(request.url);
    for (const [name, value] of Object.entries(aiKeyHeaders(pathname, request.method))) request.headers.set(name, value);
    return request;
  },
};

apiClient.use(aiKeyMiddleware);
