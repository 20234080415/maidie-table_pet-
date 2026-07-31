import { createClient } from "@supabase/supabase-js";

import { secretSupabaseKey, sha256Hex } from "./http.ts";

export async function authorizedMaidieUser(
  request: Request,
): Promise<string | null> {
  const authorization = request.headers.get("authorization") ?? "";
  const token = authorization.startsWith("Bearer ")
    ? authorization.slice(7).trim()
    : "";
  if (token.length < 32 || token.length > 256) return null;

  const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
  const secretKey = secretSupabaseKey();
  if (!supabaseUrl || !secretKey) return null;
  const admin = createClient(supabaseUrl, secretKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data, error } = await admin
    .from("maidie_users")
    .select("id")
    .eq("token", await sha256Hex(token))
    .eq("status", "active")
    .maybeSingle();
  return error || !data ? null : String(data.id);
}
