import { createClient } from "@supabase/supabase-js";

import {
  jsonHeaders,
  jsonResponse,
  randomToken,
  secretSupabaseKey,
  sha256Hex,
} from "../_shared/http.ts";

Deno.serve(async (request: Request) => {
  if (request.method === "OPTIONS") {
    return new Response("ok", { headers: jsonHeaders });
  }
  if (request.method !== "POST") {
    return jsonResponse({ success: false }, 405);
  }
  const contentLength = Number(request.headers.get("content-length") ?? "0");
  if (contentLength > 4096) {
    return jsonResponse({ success: false }, 413);
  }

  try {
    const body = await request.json() as Record<string, unknown>;
    const inviteCode = String(body.invite_code ?? "").trim();
    const deviceId = String(body.device_id ?? "").trim();
    if (deviceId.length < 8 || deviceId.length > 128) {
      return jsonResponse({ success: false }, 400);
    }

    const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
    const secretKey = secretSupabaseKey();
    if (!supabaseUrl || !secretKey) {
      return jsonResponse({ success: false }, 503);
    }
    const rawToken = randomToken();
    const tokenHash = await sha256Hex(rawToken);
    const admin = createClient(supabaseUrl, secretKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
    const authorization = request.headers.get("authorization") ?? "";
    const existingToken = authorization.startsWith("Bearer ")
      ? authorization.slice(7).trim()
      : "";
    if (existingToken.length >= 32 && existingToken.length <= 256) {
      const { data: existingUser, error: existingError } = await admin
        .from("maidie_users")
        .select("id")
        .eq("token", await sha256Hex(existingToken))
        .eq("device_id", deviceId)
        .eq("status", "active")
        .maybeSingle();
      if (!existingError && existingUser) {
        return jsonResponse({
          success: true,
          already_active: true,
        });
      }
    }
    if (inviteCode.length < 4 || inviteCode.length > 64) {
      return jsonResponse({ success: false }, 400);
    }

    const { data, error } = await admin.rpc("redeem_maidie_invite", {
      p_code: inviteCode,
      p_device_id: deviceId,
      p_token_hash: tokenHash,
    });
    const activated = !error && Array.isArray(data) && data[0]?.success === true;
    if (!activated) {
      return jsonResponse({ success: false }, 400);
    }
    return jsonResponse({ success: true, token: rawToken });
  } catch {
    return jsonResponse({ success: false }, 400);
  }
});
