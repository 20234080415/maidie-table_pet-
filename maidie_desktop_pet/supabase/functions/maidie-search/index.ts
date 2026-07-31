import {
  jsonHeaders,
  jsonResponse,
} from "../_shared/http.ts";
import { authorizedMaidieUser } from "../_shared/maidie_auth.ts";

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
    const query = String(body.query ?? "").trim();
    if (!query || query.length > 2000) {
      return jsonResponse({ success: false, error: "invalid_request" }, 400);
    }
    const tavilyKey = Deno.env.get("TAVILY_API_KEY") ?? "";
    if (!tavilyKey) {
      return jsonResponse({ success: false, error: "service_unavailable" }, 503);
    }
    const upstream = await fetch("https://api.tavily.com/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        api_key: tavilyKey,
        query,
        search_depth: "basic",
        max_results: 5,
        include_answer: true,
      }),
      signal: AbortSignal.timeout(20000),
    });
    if (!upstream.ok) {
      return jsonResponse({ success: false, error: "upstream_error" }, 502);
    }
    const data = await upstream.json() as {
      answer?: string;
      results?: Array<Record<string, unknown>>;
    };
    const sources: Array<Record<string, unknown>> = [];
    const snippets: string[] = [];
    const seen = new Set<string>();
    for (const item of data.results ?? []) {
      try {
        const url = new URL(String(item.url ?? ""));
        if (!["http:", "https:"].includes(url.protocol)) continue;
        url.hash = "";
        const key = url.toString().toLowerCase();
        if (seen.has(key)) continue;
        seen.add(key);
        sources.push({
          title: String(item.title ?? url.hostname),
          url: url.toString(),
          domain: url.hostname.toLowerCase(),
          score: Number(item.score ?? 1),
        });
        const snippet = String(item.content ?? "").trim().slice(0, 600);
        if (snippet) snippets.push(snippet);
      } catch {
        continue;
      }
    }
    const summary = String(data.answer ?? "").trim() || snippets.join("\n");
    if (!summary) {
      return jsonResponse({
        success: true,
        result: {
          ok: false,
          type: "search",
          error: "没有找到可用的联网结果。",
          failure_reason: "EMPTY_RESULTS",
          sources,
          result_count: sources.length,
        },
      });
    }
    return jsonResponse({
      success: true,
      result: {
        ok: true,
        type: "search",
        title: `“${query}”的联网查询结果`,
        summary: summary.slice(0, 4000),
        sources,
        error: "",
        failure_reason: "",
        result_count: sources.length,
      },
    });
  } catch {
    return jsonResponse({ success: false, error: "service_unavailable" }, 503);
  }
});
