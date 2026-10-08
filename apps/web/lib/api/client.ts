import { createApiClient } from "@careerlens/api-client";
export const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:4010";
export const apiClient = createApiClient(apiBaseUrl);
