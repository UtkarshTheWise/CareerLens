// Hand-written once in Phase 0. schema.d.ts is generated: run `pnpm gen:client`, never edit it.
import createClient from "openapi-fetch";
import type { components, paths } from "./schema";

export type { components, paths };

export function createApiClient(baseUrl: string, token = "dev") {
  return createClient<paths>({
    baseUrl,
    headers: { Authorization: `Bearer ${token}` },
  });
}

export type ApiClient = ReturnType<typeof createApiClient>;
