import assert from "node:assert/strict";
import { createServer, type IncomingMessage } from "node:http";
import { after, test } from "node:test";
import { once } from "node:events";
import { createApiClient } from "@careerlens/api-client";
import { createOperations } from "../lib/api/operations";
import { documentBody } from "../lib/api/upload";
import { ApiError, analysisPollInterval, shouldRetryQuery } from "../lib/api/transport";

const seen: { method?: string; url?: string; headers: IncomingMessage["headers"]; body: string }[] = [];
const profile = { id: "profile-1", name: "Synthetic Student", portfolio_urls: [], has_resume: true, has_linkedin: false, created_at: "2026-10-07T00:00:00Z" };
const server = createServer(async (request, response) => {
  const chunks: Buffer[] = [];
  for await (const chunk of request) chunks.push(Buffer.from(chunk));
  seen.push({ method: request.method, url: request.url, headers: request.headers, body: Buffer.concat(chunks).toString() });
  if (request.method === "DELETE") { response.writeHead(204).end(); return; }
  if (request.url?.includes("/export")) { response.writeHead(200, { "Content-Type": "text/csv" }).end('name,score\n"Synthetic, Student",65.1\n'); return; }
  response.setHeader("Content-Type", "application/json");
  if (request.url === "/v1/profiles/bad") { response.writeHead(422).end(JSON.stringify({ code: "validation_error", message: "Choose a valid profile.", details: { field: "profile_id" } })); return; }
  response.end(JSON.stringify(request.url === "/v1/roles" ? [] : profile));
});
server.listen(0, "127.0.0.1");
await once(server, "listening");
const address = server.address();
if (!address || typeof address === "string") throw new Error("No test server address");
const operations = createOperations(createApiClient(`http://127.0.0.1:${address.port}`));
after(async () => { server.close(); server.closeAllConnections(); await once(server, "close"); });

test("generated client sends dev bearer and preserves JSON body", async () => {
  const result = await operations.createProfile({ body: { name: profile.name, portfolio_urls: [] } });
  assert.equal(result.name, profile.name);
  const request = seen.at(-1)!;
  assert.equal(request.headers.authorization, "Bearer dev");
  assert.match(request.headers["content-type"]!, /application\/json/);
  assert.deepEqual(JSON.parse(request.body), { name: profile.name, portfolio_urls: [] });
});
test("document upload keeps the file and browser multipart boundary", async () => {
  const file = new File(["fixture PDF bytes"], "resume.pdf", { type: "application/pdf" });
  await operations.uploadDocument({ profile_id: "profile-1", body: documentBody(file, "resume") });
  const request = seen.at(-1)!;
  assert.match(request.headers["content-type"]!, /^multipart\/form-data; boundary=/);
  assert.match(request.body, /filename="resume.pdf"/);
  assert.match(request.body, /fixture PDF bytes/);
  assert.match(request.body, /name="kind"/);
  assert.doesNotMatch(request.body, /\[object File\]/);
});
test("CSV export parses text and serializes role query", async () => {
  const csv = await operations.exportCohort({ cohort_id: "cohort-1", query: { role_id: "sde-backend" } });
  assert.equal(csv, 'name,score\n"Synthetic, Student",65.1\n');
  assert.equal(seen.at(-1)!.url, "/v1/cohorts/cohort-1/export?role_id=sde-backend");
});
test("DELETE accepts empty 204 responses", async () => {
  assert.equal(await operations.deleteProfile({ profile_id: "profile-1" }), undefined);
});
test("contract error message and details survive HTTP failure", async () => {
  await assert.rejects(operations.getProfile({ profile_id: "bad" }), (error: unknown) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 422); assert.equal(error.message, "Choose a valid profile.");
    assert.deepEqual(error.details?.details, { field: "profile_id" }); return true;
  });
});
test("cancellation reaches fetch instead of issuing a request", async () => {
  const count = seen.length; const controller = new AbortController(); controller.abort();
  await assert.rejects(operations.listRoles(controller.signal), { name: "AbortError" });
  assert.equal(seen.length, count);
});
test("analysis polling stops at both terminal statuses", () => {
  for (const status of ["queued", "ingesting", "extracting", "collecting", "detecting", "judging", "scoring", "planning"] as const) assert.equal(analysisPollInterval({ status }), 2000);
  assert.equal(analysisPollInterval({ status: "done" }), false);
  assert.equal(analysisPollInterval({ status: "failed" }), false);
});
test("query retries exclude client/rate-limit errors and have a bound", () => {
  for (const status of [401, 403, 404, 409, 422, 429]) assert.equal(shouldRetryQuery(0, new ApiError(status)), false);
  assert.equal(shouldRetryQuery(0, new ApiError(503)), true);
  assert.equal(shouldRetryQuery(0, new TypeError("Failed to fetch")), true);
  assert.equal(shouldRetryQuery(2, new ApiError(503)), false);
});
