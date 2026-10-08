import assert from "node:assert/strict";
import { createServer, type IncomingMessage } from "node:http";
import { after, afterEach, test } from "node:test";
import { once } from "node:events";
import { createApiClient } from "@careerlens/api-client";
import { authMiddleware } from "../lib/api/client";
import { getAccessToken, handleUnauthorized, setSupabaseSource } from "../lib/auth/session";
import { displayName } from "../lib/auth/user";

type Stub = { auth: { getSession: () => Promise<unknown>; signOut: () => Promise<unknown> } };

function stub(tokens: (string | null)[]) {
  const calls = { signOut: 0, getSession: 0 };
  const supabase: Stub = {
    auth: {
      getSession: async () => {
        const token = tokens[Math.min(calls.getSession++, tokens.length - 1)];
        return { data: { session: token ? { access_token: token } : null } };
      },
      signOut: async () => {
        calls.signOut++;
      },
    },
  };
  setSupabaseSource(() => supabase as never);
  return calls;
}

afterEach(() => setSupabaseSource(null));

const seen: IncomingMessage["headers"][] = [];
let status = 200;
const server = createServer((request, response) => {
  seen.push(request.headers);
  response.writeHead(status, { "Content-Type": "application/json" });
  response.end(status === 401 ? JSON.stringify({ code: "unauthorized", message: "Invalid or expired sign-in.", details: null }) : "[]");
});
server.listen(0, "127.0.0.1");
await once(server, "listening");
const address = server.address();
if (!address || typeof address === "string") throw new Error("No test server address");
const client = createApiClient(`http://127.0.0.1:${address.port}`);
client.use(authMiddleware);
after(async () => {
  server.close();
  server.closeAllConnections();
  await once(server, "close");
});

test("without a Supabase client the session helpers do nothing", async () => {
  setSupabaseSource(() => null);
  assert.equal(await getAccessToken(), null);
  await handleUnauthorized(() => assert.fail("must not navigate when sign-in is off"));
});

test("every API request carries the current access token instead of the dev token", async () => {
  status = 200;
  stub(["token-one", "token-two"]);
  seen.length = 0;
  await client.GET("/v1/roles");
  await client.GET("/v1/roles");
  assert.deepEqual(seen.map((h) => h.authorization), ["Bearer token-one", "Bearer token-two"]);
});

test("a signed-out request keeps the wrapper token and the server decides", async () => {
  status = 200;
  stub([null]);
  seen.length = 0;
  await client.GET("/v1/roles");
  assert.equal(seen[0].authorization, "Bearer dev");
});

test("a 401 signs the user out once and sends them to the sign-in page", async () => {
  status = 401;
  const calls = stub(["expired"]);
  const moves: string[] = [];
  await handleUnauthorized((to) => moves.push(to)); // the first 401
  await handleUnauthorized((to) => moves.push(to)); // concurrent requests fail too: no second sign-out
  assert.deepEqual(moves, ["/login"]);
  assert.equal(calls.signOut, 1);
  const res = await client.GET("/v1/roles"); // through the middleware: still exactly one navigation attempt
  assert.equal(res.response.status, 401);
});

test("the Google name is used for pre-filling and labels, trimmed, and ignored when absent", () => {
  assert.equal(displayName({ user_metadata: { full_name: "  Priya Raman " } } as never), "Priya Raman");
  assert.equal(displayName({ user_metadata: { name: "Priya" } } as never), "Priya");
  assert.equal(displayName({ user_metadata: { full_name: "   " } } as never), undefined);
  assert.equal(displayName({ user_metadata: {} } as never), undefined);
  assert.equal(displayName(null), undefined);
});
