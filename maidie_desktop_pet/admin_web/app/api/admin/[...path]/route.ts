import { NextRequest } from "next/server";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

async function proxy(request: NextRequest, context: RouteContext) {
  const apiUrl = process.env.MAIDIE_ADMIN_API_URL?.replace(/\/+$/, "");
  const proxySecret = process.env.MAIDIE_ADMIN_PROXY_SECRET;
  if (!apiUrl || !proxySecret) {
    return Response.json(
      { success: false, error: "production_admin_unavailable" },
      { status: 503 },
    );
  }

  const { path } = await context.params;
  const target = `${apiUrl}/${path.map(encodeURIComponent).join("/")}`;
  const headers = new Headers({
    "Content-Type": "application/json",
    "X-Maidie-Admin-Proxy": proxySecret,
  });
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);
  const ownerEmail = request.headers.get("oai-authenticated-user-email");
  if (ownerEmail) headers.set("X-Maidie-Admin-Owner", ownerEmail);
  const forwardedFor = request.headers.get("cf-connecting-ip") ||
    request.headers.get("x-forwarded-for");
  if (forwardedFor) headers.set("X-Forwarded-For", forwardedFor);
  const userAgent = request.headers.get("user-agent");
  if (userAgent) headers.set("User-Agent", userAgent);

  let response: Response;
  try {
    response = await fetch(target, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method)
        ? undefined
        : await request.text(),
      cache: "no-store",
    });
  } catch {
    return Response.json(
      { success: false, error: "production_admin_unavailable" },
      { status: 503 },
    );
  }

  const responseHeaders = new Headers({
    "Cache-Control": "no-store",
    "Content-Type": response.headers.get("content-type") ??
      "application/json; charset=utf-8",
    "X-Content-Type-Options": "nosniff",
  });
  const forwardedCookie = response.headers.get(
    "x-maidie-admin-set-cookie",
  );
  const nativeCookieHeaders =
    (
      response.headers as Headers & {
        getSetCookie?: () => string[];
      }
    ).getSetCookie?.() ?? [];
  const cookieHeaders = forwardedCookie
    ? [forwardedCookie]
    : nativeCookieHeaders.length > 0
      ? nativeCookieHeaders
      : [response.headers.get("set-cookie")].filter(
        (value): value is string => Boolean(value),
      );
  for (const cookie of cookieHeaders) {
    responseHeaders.append("Set-Cookie", cookie);
  }
  return new Response(response.body, {
    status: response.status,
    headers: responseHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
