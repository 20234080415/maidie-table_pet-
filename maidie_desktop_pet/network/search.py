from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

import requests

from network.client import NetworkClient
from network.schemas import NetworkResult


class SearchService:
    """Search provider adapter. Version one supports Tavily."""

    def __init__(self, provider: str = "tavily", api_key: str = "", timeout: int = 10) -> None:
        self.provider = provider.strip().lower() or "tavily"
        self.api_key = api_key.strip()
        self.client = NetworkClient(timeout)

    def search(self, query: str) -> dict:
        query = str(query).strip()
        if not query:
            return NetworkResult(error="搜索内容为空。", failure_reason="EMPTY_QUERY").to_dict()
        if not self.api_key:
            return NetworkResult(error="尚未配置搜索 API Key。", failure_reason="API_KEY_MISSING").to_dict()
        if self.provider != "tavily":
            return NetworkResult(error=f"暂不支持搜索服务：{self.provider}").to_dict()
        data, error = self.client.post_json(
            "https://api.tavily.com/search",
            {
                "api_key": self.api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": 5,
                "include_answer": True,
            },
        )
        if error:
            reason = "TIMEOUT" if "超时" in error else "NETWORK_ERROR"
            return NetworkResult(error=error, failure_reason=reason).to_dict()
        try:
            items = data.get("results", []) if isinstance(data, dict) else []
            sources, snippets, scores = self._normalize_sources(items)
            summary = str(data.get("answer", "")).strip() if isinstance(data, dict) else ""
            if not summary:
                summary = "\n".join(snippets)
            if not summary:
                return NetworkResult(error="没有找到可用的联网结果。",
                                     failure_reason="EMPTY_RESULTS",
                                     result_count=len(sources)).to_dict()
            if sources and scores and max(scores) < 0.2:
                return NetworkResult(error="搜索结果可信度不足。",
                                     failure_reason="LOW_CONFIDENCE_RESULTS",
                                     result_count=len(sources), sources=sources).to_dict()
            return NetworkResult(
                ok=True,
                title=f"“{query}”的联网查询结果",
                summary=summary[:4000],
                sources=sources,
                result_count=len(sources),
            ).to_dict()
        except (AttributeError, TypeError, ValueError) as exc:
            return NetworkResult(error=f"无法解析搜索结果：{exc}",
                                 failure_reason="UNKNOWN_ERROR").to_dict()

    @staticmethod
    def _normalize_sources(
        items: list[object], limit: int = 5,
    ) -> tuple[list[dict[str, str]], list[str], list[float]]:
        sources: list[dict[str, str]] = []
        snippets: list[str] = []
        scores: list[float] = []
        seen: set[tuple[str, str, int | None, str, str]] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            raw_url = str(item.get("url") or "").strip()
            try:
                parsed = urlsplit(raw_url)
                scheme = parsed.scheme.lower()
                if scheme not in {"http", "https"} or not parsed.hostname:
                    continue
                port = parsed.port
            except ValueError:
                continue
            path_key = parsed.path.rstrip("/") or "/"
            key = (scheme, parsed.hostname.lower(), port, path_key, parsed.query)
            if key in seen:
                continue
            seen.add(key)
            sources.append({
                "title": str(item.get("title") or parsed.hostname),
                "url": urlunsplit(
                    (parsed.scheme, parsed.netloc, parsed.path, parsed.query, "")
                ),
                "domain": parsed.hostname.lower(),
            })
            snippet = str(item.get("content") or "").strip()[:600]
            if snippet:
                snippets.append(snippet)
            scores.append(float(item.get("score", 1.0)))
            if len(sources) >= limit:
                break
        return sources, snippets, scores


class InviteSearchService:
    """Tavily search through Maidie's cloud using the shared invite token."""

    def __init__(
        self,
        endpoint: str,
        user_token: str,
        timeout: int = 10,
        request_session=requests,
    ) -> None:
        self.endpoint = endpoint
        self.user_token = user_token
        self.timeout = timeout
        self._requests = request_session

    def search(self, query: str) -> dict:
        query = str(query).strip()
        if not query:
            return NetworkResult(
                error="搜索内容为空。", failure_reason="EMPTY_QUERY"
            ).to_dict()
        if not self.endpoint or not self.user_token:
            return NetworkResult(
                error="邀请码搜索服务尚未配置。",
                failure_reason="API_KEY_MISSING",
            ).to_dict()
        try:
            response = self._requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.user_token}",
                    "Content-Type": "application/json",
                },
                json={"query": query},
                timeout=self.timeout,
            )
            if response.status_code == 401:
                return NetworkResult(
                    error="邀请码授权已失效。",
                    failure_reason="API_KEY_MISSING",
                ).to_dict()
            response.raise_for_status()
            payload = response.json()
            result = payload.get("result")
            if not payload.get("success") or not isinstance(result, dict):
                raise ValueError(str(payload.get("error") or "cloud_search_failed"))
            raw_sources = (
                result.get("sources")
                if isinstance(result.get("sources"), list)
                else []
            )
            sources, _snippets, _scores = SearchService._normalize_sources(
                raw_sources
            )
            return NetworkResult(
                ok=bool(result.get("ok")),
                title=str(result.get("title") or f"“{query}”的联网查询结果"),
                summary=str(result.get("summary") or "")[:4000],
                sources=sources,
                error=str(result.get("error") or ""),
                failure_reason=str(result.get("failure_reason") or ""),
                result_count=len(sources),
            ).to_dict()
        except requests.Timeout:
            return NetworkResult(
                error="联网查询超时。", failure_reason="TIMEOUT"
            ).to_dict()
        except Exception:
            return NetworkResult(
                error="联网查询暂时不可用。",
                failure_reason="NETWORK_ERROR",
            ).to_dict()
