import {
  clearSessionHeaders,
  createSessionCookie,
  createSessionHeaders,
  hasValidSession,
  hostedProductionRuntime,
  passwordDigest,
} from "./admin_auth.ts";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

Deno.test("password digest is salted and deterministic", async () => {
  const first = await passwordDigest("a-strong-admin-password", "salt-one");
  const repeated = await passwordDigest("a-strong-admin-password", "salt-one");
  const different = await passwordDigest("a-strong-admin-password", "salt-two");
  assert(first === repeated, "same password and salt should match");
  assert(first !== different, "different salt should change the digest");
});

Deno.test("hosted runtime gate requires a deployment id", () => {
  Deno.env.delete("DENO_DEPLOYMENT_ID");
  assert(!hostedProductionRuntime(), "local runtime must stay disabled");
  Deno.env.set("DENO_DEPLOYMENT_ID", "production-deployment");
  assert(hostedProductionRuntime(), "hosted deployment should pass");
});

Deno.test("signed session cookie rejects tampering", async () => {
  const secret = "s".repeat(48);
  const cookie = await createSessionCookie(secret);
  const token = cookie.split(";")[0];
  const validRequest = new Request("https://example.test", {
    headers: { cookie: token },
  });
  assert(await hasValidSession(validRequest, secret), "new session should be valid");
  const tampered = `${token.slice(0, -1)}x`;
  const invalidRequest = new Request("https://example.test", {
    headers: { cookie: tampered },
  });
  assert(
    !await hasValidSession(invalidRequest, secret),
    "tampered session must fail",
  );
});

Deno.test("session headers provide a proxy-safe cookie fallback", async () => {
  const headers = await createSessionHeaders("s".repeat(48));
  assert(headers["Set-Cookie"], "standard cookie header should be present");
  assert(
    headers["X-Maidie-Admin-Set-Cookie"] === headers["Set-Cookie"],
    "proxy fallback must preserve the exact cookie",
  );
  const cleared = clearSessionHeaders();
  assert(
    cleared["X-Maidie-Admin-Set-Cookie"]?.includes("Max-Age=0"),
    "logout fallback should expire the cookie",
  );
});
