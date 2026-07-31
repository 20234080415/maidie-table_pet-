import {
  jsonHeaders,
  jsonResponse,
} from "../_shared/http.ts";
import { authorizedMaidieUser } from "../_shared/maidie_auth.ts";

type ChatMessage = { role: "system" | "user" | "assistant"; content: string };

function validatedMessages(value: unknown): ChatMessage[] | null {
  if (!Array.isArray(value) || value.length < 1 || value.length > 24) return null;
  let totalLength = 0;
  const messages: ChatMessage[] = [];
  for (const item of value) {
    if (!item || typeof item !== "object") return null;
    const role = String((item as Record<string, unknown>).role ?? "");
    const content = String((item as Record<string, unknown>).content ?? "");
    if (!["system", "user", "assistant"].includes(role)) return null;
    if (!content || content.length > 12000) return null;
    totalLength += content.length;
    if (totalLength > 48000) return null;
    messages.push({ role: role as ChatMessage["role"], content });
  }
  return messages;
}

Deno.serve(async (request: Request) => {
  if (request.method === "OPTIONS") {
    return new Response("ok", { headers: jsonHeaders });
  }
  if (request.method !== "POST") {
    return jsonResponse({ success: false, error: "method_not_allowed" }, 405);
  }

  try {
    if (!await authorizedMaidieUser(request)) {
      return jsonResponse({ success: false, error: "unauthorized" }, 401);
    }

    const body = await request.json() as Record<string, unknown>;
    const messages = validatedMessages(body.messages);
    const profile = String(body.profile ?? "chat");
    if (!messages || !["chat", "technical"].includes(profile)) {
      return jsonResponse({ success: false, error: "invalid_request" }, 400);
    }
    const requestedTemperature = Number(body.temperature ?? 0.8);
    const temperature = Number.isFinite(requestedTemperature)
      ? Math.max(0, Math.min(1, requestedTemperature))
      : 0.8;
    const requestedTokens = Number(body.max_tokens ?? 2048);
    const maxTokens = Number.isFinite(requestedTokens)
      ? Math.max(64, Math.min(4096, Math.trunc(requestedTokens)))
      : 2048;

    const providerKey = Deno.env.get("DEEPSEEK_API_KEY") ?? "";
    const providerBase = (
      Deno.env.get("MAIDIE_AI_BASE_URL") ?? "https://api.deepseek.com"
    ).replace(/\/+$/, "");
    const model = profile === "technical"
      ? Deno.env.get("MAIDIE_AI_TECHNICAL_MODEL") ?? "deepseek-v4-pro"
      : Deno.env.get("MAIDIE_AI_CHAT_MODEL") ?? "deepseek-v4-flash";
    if (!providerKey) {
      return jsonResponse({ success: false, error: "service_unavailable" }, 503);
    }

    const providerResponse = await fetch(`${providerBase}/chat/completions`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${providerKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        messages,
        temperature,
        max_tokens: maxTokens,
        ...(body.json_mode === true
          ? { response_format: { type: "json_object" } }
          : {}),
        ...(profile === "chat" && body.json_mode !== true
          ? { thinking: { type: "disabled" } }
          : {}),
      }),
      signal: AbortSignal.timeout(45000),
    });
    if (!providerResponse.ok) {
      return jsonResponse({ success: false, error: "upstream_error" }, 502);
    }
    const providerPayload = await providerResponse.json() as {
      choices?: Array<{ message?: { content?: string } }>;
    };
    const content = String(
      providerPayload.choices?.[0]?.message?.content ?? "",
    ).trim();
    if (!content) {
      return jsonResponse({ success: false, error: "empty_response" }, 502);
    }
    return jsonResponse({ success: true, content });
  } catch {
    return jsonResponse({ success: false, error: "service_unavailable" }, 503);
  }
});
