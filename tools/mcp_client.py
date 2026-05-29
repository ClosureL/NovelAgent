# encoding: utf-8
"""MCP (Model Context Protocol) JSON-RPC 2.0 客户端。

支持 HTTP/SSE 传输，从 config.MCP_CONFIG 读取服务器 URL 配置。
"""

import json
import urllib.request
import urllib.error

from config import MCP_CONFIG


def _parse_response(body: str) -> dict:
    """解析 MCP 响应，兼容纯 JSON 与 SSE 格式。"""
    stripped = body.strip()
    # 快速路径：纯 JSON
    if stripped.startswith("{"):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
    # SSE 路径：提取 data: 行
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            data_str = line[5:].strip()
            if data_str:
                try:
                    return json.loads(data_str)
                except json.JSONDecodeError:
                    continue
    raise Exception(f"MCP 响应解析失败: {stripped[:200]}")


class MCPClient:
    """MCP JSON-RPC 2.0 客户端（HTTP/SSE 传输）。"""

    def __init__(self, server_url: str):
        self.server_url = server_url
        self._req_id = 0
        self._tools: list[dict] = []
        self._search_tool_name: str | None = None

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _call(self, method: str, params: dict | None = None, timeout: int = 30) -> dict:
        """发送 JSON-RPC 请求，返回解析后的结果。"""
        payload = {"jsonrpc": "2.0", "method": method, "id": self._next_id()}
        if params is not None:
            payload["params"] = params

        req = urllib.request.Request(
            self.server_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream, application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.URLError as e:
            raise ConnectionError(f"MCP 服务器不可达: {e}")

        return _parse_response(body)

    def ensure_initialized(self):
        """懒初始化：握手 + 工具发现。"""
        if self._tools:
            return
        self._call("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "novelagent", "version": "1.0.0"},
        })
        result = self._call("tools/list")
        self._tools = result.get("tools", []) or result.get("result", {}).get("tools", [])
        for t in self._tools:
            if "search" in t.get("name", "").lower():
                self._search_tool_name = t["name"]
                break
        if not self._search_tool_name and self._tools:
            self._search_tool_name = self._tools[0]["name"]

    def search(self, query: str) -> dict:
        """执行搜索，返回 MCP tools/call 的原始 result。"""
        self.ensure_initialized()
        if not self._search_tool_name:
            raise RuntimeError("MCP 服务器未提供搜索工具")
        return self._call("tools/call", {
            "name": self._search_tool_name,
            "arguments": {"query": query},
        })


_clients: dict[str, MCPClient] = {}


def search_web(query: str) -> str:
    """通过 MCP 服务器执行联网搜索。返回 JSON 字符串。"""
    urls = MCP_CONFIG.get("search_servers", [])
    if not urls:
        return json.dumps({
            "status": "error",
            "message": (
                "未配置 MCP 搜索服务器。"
                "请在 config.py 的 MCP_CONFIG['search_servers'] 中添加 MCP 服务器 URL。"
            ),
        }, ensure_ascii=False)

    errors = []
    for url in urls:
        try:
            if url not in _clients:
                _clients[url] = MCPClient(url)
            client = _clients[url]
            result = client.search(query)

            # 提取搜索结果内容
            content_items = []
            raw = result.get("result", result)
            if isinstance(raw, dict):
                for item in raw.get("content", []):
                    if isinstance(item, dict) and item.get("type") == "text":
                        content_items.append(item.get("text", ""))

            return json.dumps({
                "status": "success",
                "source": url.split("?")[0],
                "query": query,
                "results": content_items,
            }, ensure_ascii=False)
        except Exception as e:
            if url in _clients:
                del _clients[url]
            errors.append(f"{url}: {e}")
            continue

    return json.dumps({
        "status": "error",
        "message": f"所有 MCP 搜索服务器均不可用：{'；'.join(errors)}",
    }, ensure_ascii=False)
