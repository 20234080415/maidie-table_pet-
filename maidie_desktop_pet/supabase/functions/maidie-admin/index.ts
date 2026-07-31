import { createClient } from "@supabase/supabase-js";

import { secretSupabaseKey, sha256Hex } from "../_shared/http.ts";
import {
  clearSessionHeaders,
  createSessionHeaders,
  hasValidSession,
  hostedProductionRuntime,
  newPasswordSalt,
  newSessionSecret,
  ownerFingerprint,
  passwordDigest,
  safePasswordMatch,
  safeSecretMatch,
} from "./admin_auth.ts";

type JsonRecord = Record<string, unknown>;

const jsonHeaders = {
  "Cache-Control": "no-store",
  "Content-Type": "application/json; charset=utf-8",
  "X-Content-Type-Options": "nosniff",
};

function json(body: JsonRecord, status = 200, headers: HeadersInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...jsonHeaders, ...headers },
  });
}

function routePath(request: Request): string {
  const pathname = new URL(request.url).pathname;
  const marker = "/maidie-admin";
  const index = pathname.indexOf(marker);
  return index < 0 ? "/" : pathname.slice(index + marker.length) || "/";
}

function adminClient() {
  const url = Deno.env.get("SUPABASE_URL") ?? "";
  const key = secretSupabaseKey();
  return url && key
    ? createClient(url, key, {
      auth: { persistSession: false, autoRefreshToken: false },
    })
    : null;
}

type AdminClient = NonNullable<ReturnType<typeof adminClient>>;

async function trustedProductionRequest(
  request: Request,
  admin: AdminClient,
): Promise<boolean> {
  if (!hostedProductionRuntime()) return false;
  const { data, error } = await admin
    .from("maidie_admin_runtime")
    .select("environment,enabled,proxy_secret_hash")
    .eq("id", true)
    .maybeSingle();
  if (error || !data || data.environment !== "production" || !data.enabled) {
    return false;
  }
  const provided = request.headers.get("x-maidie-admin-proxy") ?? "";
  if (provided.length < 32) return false;
  return safeSecretMatch(
    await sha256Hex(provided),
    String(data.proxy_secret_hash),
  );
}

async function sessionSecret(admin: AdminClient): Promise<string> {
  const { data } = await admin
    .from("maidie_admin_config")
    .select("session_secret")
    .eq("id", true)
    .maybeSingle();
  return String(data?.session_secret ?? "");
}

async function requestBody(request: Request): Promise<JsonRecord | null> {
  const contentType = request.headers.get("content-type") ?? "";
  const length = Number(request.headers.get("content-length") ?? "0");
  if (!contentType.toLowerCase().includes("application/json") || length > 16_384) {
    return null;
  }
  try {
    const value = await request.json();
    return value && typeof value === "object" ? value as JsonRecord : null;
  } catch {
    return null;
  }
}

async function audit(
  admin: AdminClient,
  action: string,
  targetType = "",
  targetId = "",
  detail: JsonRecord = {},
): Promise<void> {
  await admin.from("maidie_admin_audit_log").insert({
    action,
    target_type: targetType,
    target_id: targetId,
    detail,
  });
}

async function loginFingerprint(request: Request): Promise<string> {
  const address = request.headers.get("cf-connecting-ip") ||
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    "unknown";
  const agent = (request.headers.get("user-agent") ?? "").slice(0, 256);
  const secret = Deno.env.get("MAIDIE_ADMIN_SESSION_SECRET") ?? "";
  return sha256Hex(`${address}|${agent}|${secret}`);
}

async function loginBlocked(
  admin: AdminClient,
  fingerprint: string,
): Promise<boolean> {
  const { data } = await admin
    .from("maidie_admin_login_limits")
    .select("blocked_until")
    .eq("fingerprint", fingerprint)
    .maybeSingle();
  return Boolean(
    data?.blocked_until &&
      new Date(String(data.blocked_until)).getTime() > Date.now(),
  );
}

async function recordLoginFailure(
  admin: AdminClient,
  fingerprint: string,
): Promise<void> {
  const now = new Date();
  const { data } = await admin
    .from("maidie_admin_login_limits")
    .select("failure_count,window_started_at")
    .eq("fingerprint", fingerprint)
    .maybeSingle();
  const windowStarted = data?.window_started_at
    ? new Date(String(data.window_started_at))
    : now;
  const expired = now.getTime() - windowStarted.getTime() > 15 * 60 * 1000;
  const failureCount = expired ? 1 : Number(data?.failure_count ?? 0) + 1;
  await admin.from("maidie_admin_login_limits").upsert({
    fingerprint,
    window_started_at: expired ? now.toISOString() : windowStarted.toISOString(),
    failure_count: failureCount,
    blocked_until: failureCount >= 5
      ? new Date(now.getTime() + 15 * 60 * 1000).toISOString()
      : null,
    updated_at: now.toISOString(),
  });
}

function randomInviteCode(prefix: string): string {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  const bytes = crypto.getRandomValues(new Uint8Array(12));
  let suffix = "";
  for (const byte of bytes) suffix += alphabet[byte % alphabet.length];
  return `${prefix}-${suffix.slice(0, 4)}-${suffix.slice(4, 8)}-${suffix.slice(8)}`;
}

async function bootstrap(admin: AdminClient): Promise<Response> {
  const { data, error } = await admin
    .from("maidie_admin_config")
    .select("configured_at,session_secret")
    .eq("id", true)
    .maybeSingle();
  if (error) return json({ success: false, error: "database_error" }, 503);
  return json({
    success: true,
    configured: Boolean(data),
    authenticated: false,
  });
}

async function setup(
  request: Request,
  admin: AdminClient,
): Promise<Response> {
  const owner = (request.headers.get("x-maidie-admin-owner") ?? "").trim();
  const body = await requestBody(request);
  const password = String(body?.password ?? "");
  if (!owner || password.length < 12 || password.length > 128) {
    return json({ success: false, error: "invalid_setup" }, 400);
  }
  const { data: existing } = await admin
    .from("maidie_admin_config")
    .select("id")
    .eq("id", true)
    .maybeSingle();
  if (existing) return json({ success: false, error: "already_configured" }, 409);

  const salt = newPasswordSalt();
  const generatedSessionSecret = newSessionSecret();
  const { error } = await admin.from("maidie_admin_config").insert({
    id: true,
    password_hash: await passwordDigest(password, salt),
    password_salt: salt,
    owner_fingerprint: await ownerFingerprint(owner),
    session_secret: generatedSessionSecret,
  });
  if (error) return json({ success: false, error: "setup_failed" }, 409);
  await audit(admin, "admin_configured");
  return json(
    { success: true },
    201,
    await createSessionHeaders(generatedSessionSecret),
  );
}

async function login(
  request: Request,
  admin: AdminClient,
): Promise<Response> {
  const body = await requestBody(request);
  const password = String(body?.password ?? "");
  const fingerprint = await loginFingerprint(request);
  if (await loginBlocked(admin, fingerprint)) {
    return json({ success: false, error: "too_many_attempts" }, 429);
  }
  const { data } = await admin
    .from("maidie_admin_config")
    .select("password_hash,password_salt,session_secret")
    .eq("id", true)
    .maybeSingle();
  if (!data || !password || password.length > 128) {
    await recordLoginFailure(admin, fingerprint);
    return json({ success: false, error: "invalid_credentials" }, 401);
  }
  const digest = await passwordDigest(password, String(data.password_salt));
  if (!safePasswordMatch(digest, String(data.password_hash))) {
    await recordLoginFailure(admin, fingerprint);
    await audit(admin, "login_failed");
    return json({ success: false, error: "invalid_credentials" }, 401);
  }
  await admin.from("maidie_admin_login_limits")
    .delete()
    .eq("fingerprint", fingerprint);
  await audit(admin, "login_succeeded");
  return json(
    { success: true },
    200,
    await createSessionHeaders(String(data.session_secret)),
  );
}

async function overview(admin: AdminClient): Promise<Response> {
  const [inviteResult, userResult, auditResult] = await Promise.all([
    admin.from("maidie_invite_codes")
      .select("id,code,status,note,created_at,used_at")
      .order("created_at", { ascending: false })
      .limit(200),
    admin.from("maidie_users")
      .select("id,device_id,invite_code_id,status,created_at,revoked_at")
      .order("created_at", { ascending: false })
      .limit(200),
    admin.from("maidie_admin_audit_log")
      .select("id,action,target_type,target_id,detail,created_at")
      .order("created_at", { ascending: false })
      .limit(50),
  ]);
  if (inviteResult.error || userResult.error || auditResult.error) {
    return json({ success: false, error: "database_error" }, 503);
  }
  const invites = inviteResult.data ?? [];
  const users = userResult.data ?? [];
  return json({
    success: true,
    invites,
    users,
    audit: auditResult.data ?? [],
    stats: {
      invite_total: invites.length,
      invite_unused: invites.filter((item) => item.status === "unused").length,
      invite_used: invites.filter((item) => item.status === "used").length,
      invite_disabled: invites.filter((item) => item.status === "disabled").length,
      user_active: users.filter((item) => item.status === "active").length,
      user_revoked: users.filter((item) => item.status === "revoked").length,
    },
  });
}

async function createInvites(
  request: Request,
  admin: AdminClient,
): Promise<Response> {
  const body = await requestBody(request);
  const count = Math.max(1, Math.min(50, Math.trunc(Number(body?.count ?? 1))));
  const prefix = String(body?.prefix ?? "MAIDIE")
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "")
    .slice(0, 12) || "MAIDIE";
  const note = String(body?.note ?? "").trim().slice(0, 200);
  const rows = Array.from({ length: count }, () => ({
    code: randomInviteCode(prefix),
    note,
  }));
  const { data, error } = await admin
    .from("maidie_invite_codes")
    .insert(rows)
    .select("id,code,status,note,created_at,used_at");
  if (error) return json({ success: false, error: "create_failed" }, 409);
  await audit(admin, "invites_created", "invite", "", { count, prefix });
  return json({ success: true, invites: data ?? [] }, 201);
}

async function disableInvite(
  admin: AdminClient,
  id: string,
): Promise<Response> {
  const { data, error } = await admin
    .from("maidie_invite_codes")
    .update({ status: "disabled" })
    .eq("id", id)
    .eq("status", "unused")
    .select("id")
    .maybeSingle();
  if (error || !data) {
    return json({ success: false, error: "invite_not_unused" }, 409);
  }
  await audit(admin, "invite_disabled", "invite", id);
  return json({ success: true });
}

async function setUserStatus(
  admin: AdminClient,
  id: string,
  status: "active" | "revoked",
): Promise<Response> {
  const { data, error } = await admin
    .from("maidie_users")
    .update({
      status,
      revoked_at: status === "revoked" ? new Date().toISOString() : null,
    })
    .eq("id", id)
    .select("id")
    .maybeSingle();
  if (error || !data) return json({ success: false, error: "user_not_found" }, 404);
  await audit(
    admin,
    status === "revoked" ? "user_revoked" : "user_restored",
    "user",
    id,
  );
  return json({ success: true });
}

Deno.serve(async (request: Request) => {
  const admin = adminClient();
  if (!admin) return json({ success: false, error: "service_unavailable" }, 503);
  if (!await trustedProductionRequest(request, admin)) {
    return new Response("Not found", { status: 404 });
  }

  const path = routePath(request);
  if (request.method === "GET" && path === "/bootstrap") {
    const response = await bootstrap(admin);
    if (response.status !== 200) return response;
    const payload = await response.json() as JsonRecord;
    const secret = await sessionSecret(admin);
    return json({
      ...payload,
      authenticated: Boolean(
        secret && await hasValidSession(request, secret)
      ),
    });
  }
  if (request.method === "POST" && path === "/setup") {
    return setup(request, admin);
  }
  if (request.method === "POST" && path === "/login") {
    return login(request, admin);
  }
  if (request.method === "POST" && path === "/logout") {
    return json(
      { success: true },
      200,
      clearSessionHeaders(),
    );
  }
  const secret = await sessionSecret(admin);
  if (!secret || !await hasValidSession(request, secret)) {
    return json({ success: false, error: "unauthorized" }, 401);
  }
  if (request.method === "GET" && path === "/overview") {
    return overview(admin);
  }
  if (request.method === "POST" && path === "/invites") {
    return createInvites(request, admin);
  }
  const disableMatch = path.match(/^\/invites\/(\d+)\/disable$/);
  if (request.method === "POST" && disableMatch) {
    return disableInvite(admin, disableMatch[1]);
  }
  const userMatch = path.match(
    /^\/users\/([0-9a-f-]{36})\/(revoke|restore)$/,
  );
  if (request.method === "POST" && userMatch) {
    return setUserStatus(
      admin,
      userMatch[1],
      userMatch[2] === "revoke" ? "revoked" : "active",
    );
  }
  return json({ success: false, error: "not_found" }, 404);
});
