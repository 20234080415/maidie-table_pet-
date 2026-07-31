import {
  jsonHeaders,
  jsonResponse,
} from "../_shared/http.ts";
import { authorizedMaidieUser } from "../_shared/maidie_auth.ts";

const visionPrompt = `你是 Maidie 的屏幕视觉理解模块。你只负责观察截图和提取结构化信息，不负责最终回答用户。
请根据截图和用户问题，只输出 JSON，不要 Markdown、代码块或解释。
字段必须包括：screen_summary、visible_text、task_type、important_regions、user_intent_guess、confidence。
task_type 只能是 general_screen、code_error、math_problem、document、webpage、image_question、ui_operation、unknown。
confidence 必须是 0.0 到 1.0；看不清或信息不足时也必须输出 JSON 并降低 confidence。`;

function stripFence(value: string): string {
  const text = value.trim();
  if (text.startsWith("```json") && text.endsWith("```")) {
    return text.slice(7, -3).trim();
  }
  if (text.startsWith("```") && text.endsWith("```")) {
    return text.slice(3, -3).trim();
  }
  return text;
}

Deno.serve(async (request: Request) => {
  if (request.method === "OPTIONS") {
    return new Response("ok", { headers: jsonHeaders });
  }
  if (request.method !== "POST") {
    return jsonResponse({ success: false, error: "method_not_allowed" }, 405);
  }
  const contentLength = Number(request.headers.get("content-length") ?? "0");
  if (contentLength > 8_000_000) {
    return jsonResponse({ success: false, error: "payload_too_large" }, 413);
  }
  try {
    if (!await authorizedMaidieUser(request)) {
      return jsonResponse({ success: false, error: "unauthorized" }, 401);
    }

    const body = await request.json() as Record<string, unknown>;
    const imageDataUrl = String(body.image_data_url ?? "");
    const question = String(body.user_question ?? "").trim();
    if (
      !imageDataUrl.startsWith("data:image/jpeg;base64,") ||
      imageDataUrl.length > 7_500_000 || question.length > 4000
    ) {
      return jsonResponse({ success: false, error: "invalid_request" }, 400);
    }
    const apiKey = Deno.env.get("DASHSCOPE_API_KEY") ?? "";
    const workspaceId = Deno.env.get("DASHSCOPE_WORKSPACE_ID") ?? "";
    const region = Deno.env.get("QWEN_VL_REGION") ?? "cn-beijing";
    const model = Deno.env.get("QWEN_VL_MODEL") ?? "qwen3-vl-flash";
    if (!apiKey || !workspaceId) {
      return jsonResponse({ success: false, error: "service_unavailable" }, 503);
    }
    const baseUrl =
      `https://${workspaceId}.${region}.maas.aliyuncs.com/compatible-mode/v1`;
    const upstream = await fetch(`${baseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        messages: [
          { role: "system", content: visionPrompt },
          {
            role: "user",
            content: [
              { type: "text", text: `用户原始问题：${question}` },
              { type: "image_url", image_url: { url: imageDataUrl } },
            ],
          },
        ],
        temperature: 0,
        response_format: { type: "json_object" },
      }),
      signal: AbortSignal.timeout(45000),
    });
    if (!upstream.ok) {
      return jsonResponse({ success: false, error: "upstream_error" }, 502);
    }
    const data = await upstream.json() as {
      choices?: Array<{ message?: { content?: string } }>;
    };
    const raw = String(data.choices?.[0]?.message?.content ?? "").trim();
    if (!raw) {
      return jsonResponse({ success: false, error: "empty_response" }, 502);
    }
    let context: Record<string, unknown>;
    try {
      const parsed = JSON.parse(stripFence(raw));
      context = parsed && typeof parsed === "object"
        ? parsed as Record<string, unknown>
        : {};
    } catch {
      context = {
        screen_summary: raw,
        visible_text: "",
        task_type: "unknown",
        important_regions: [],
        user_intent_guess: "",
        confidence: 0,
      };
    }
    return jsonResponse({ success: true, context, raw });
  } catch {
    return jsonResponse({ success: false, error: "service_unavailable" }, 503);
  }
});
