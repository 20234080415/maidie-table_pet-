const encoder = new TextEncoder();

const SESSION_COOKIE = "maidie_admin_session";
const SESSION_FORWARD_HEADER = "X-Maidie-Admin-Set-Cookie";
const SESSION_SECONDS = 8 * 60 * 60;
const PASSWORD_ITERATIONS = 210_000;

function base64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary)
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replaceAll("=", "");
}

function base64UrlText(value: string): string {
  return base64Url(encoder.encode(value));
}

function randomBytes(length: number): Uint8Array {
  return crypto.getRandomValues(new Uint8Array(length));
}

async function hmac(value: string, secret: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  return base64Url(
    new Uint8Array(
      await crypto.subtle.sign("HMAC", key, encoder.encode(value)),
    ),
  );
}

function constantTimeEqual(left: string, right: string): boolean {
  const a = encoder.encode(left);
  const b = encoder.encode(right);
  let difference = a.length ^ b.length;
  const length = Math.max(a.length, b.length);
  for (let index = 0; index < length; index += 1) {
    difference |= (a[index % a.length] ?? 0) ^ (b[index % b.length] ?? 0);
  }
  return difference === 0;
}

export function hostedProductionRuntime(): boolean {
  return Boolean(Deno.env.get("DENO_DEPLOYMENT_ID"));
}

export function safeSecretMatch(provided: string, expected: string): boolean {
  return constantTimeEqual(provided, expected);
}

export async function passwordDigest(
  password: string,
  salt: string,
): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(password),
    "PBKDF2",
    false,
    ["deriveBits"],
  );
  const bits = await crypto.subtle.deriveBits(
    {
      name: "PBKDF2",
      hash: "SHA-256",
      salt: encoder.encode(salt),
      iterations: PASSWORD_ITERATIONS,
    },
    key,
    256,
  );
  return base64Url(new Uint8Array(bits));
}

export function newPasswordSalt(): string {
  return base64Url(randomBytes(18));
}

export function newSessionSecret(): string {
  return base64Url(randomBytes(48));
}

export function safePasswordMatch(provided: string, expected: string): boolean {
  return constantTimeEqual(provided, expected);
}

export async function ownerFingerprint(owner: string): Promise<string> {
  const digest = await crypto.subtle.digest(
    "SHA-256",
    encoder.encode(owner.trim().toLowerCase()),
  );
  return base64Url(new Uint8Array(digest));
}

export async function createSessionCookie(sessionSecret: string): Promise<string> {
  const expiresAt = Math.floor(Date.now() / 1000) + SESSION_SECONDS;
  const nonce = base64Url(randomBytes(18));
  const payload = base64UrlText(JSON.stringify({ exp: expiresAt, nonce }));
  const signature = await hmac(
    payload,
    sessionSecret,
  );
  return `${SESSION_COOKIE}=${payload}.${signature}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=${SESSION_SECONDS}`;
}

export async function createSessionHeaders(
  sessionSecret: string,
): Promise<Record<string, string>> {
  const cookie = await createSessionCookie(sessionSecret);
  return {
    "Set-Cookie": cookie,
    [SESSION_FORWARD_HEADER]: cookie,
  };
}

function cookieValue(request: Request, name: string): string {
  const cookies = request.headers.get("cookie") ?? "";
  for (const item of cookies.split(";")) {
    const [key, ...parts] = item.trim().split("=");
    if (key === name) return parts.join("=");
  }
  return "";
}

export async function hasValidSession(
  request: Request,
  sessionSecret: string,
): Promise<boolean> {
  const token = cookieValue(request, SESSION_COOKIE);
  const [payload, signature, extra] = token.split(".");
  if (!payload || !signature || extra) return false;
  const expected = await hmac(
    payload,
    sessionSecret,
  );
  if (!constantTimeEqual(signature, expected)) return false;
  try {
    const normalized = payload.replaceAll("-", "+").replaceAll("_", "/")
      .padEnd(Math.ceil(payload.length / 4) * 4, "=");
    const decoded = JSON.parse(atob(normalized)) as { exp?: number };
    return Number(decoded.exp ?? 0) > Math.floor(Date.now() / 1000);
  } catch {
    return false;
  }
}

export function clearSessionCookie(): string {
  return `${SESSION_COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0`;
}

export function clearSessionHeaders(): Record<string, string> {
  const cookie = clearSessionCookie();
  return {
    "Set-Cookie": cookie,
    [SESSION_FORWARD_HEADER]: cookie,
  };
}
