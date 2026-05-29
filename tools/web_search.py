# encoding: utf-8
"""web_search — 联网搜索工具。

Mimo 模型（web_search=True）：服务端原生搜索，直接返回搜索结果。
其他模型 / Mimo（web_search=False）：通过 MCP 协议调用配置的搜索服务器。
MCP 服务器 URL 配置在 config.py 的 MCP_CONFIG["search_servers"] 中。
"""

import json
from .mcp_client import search_web

DEFINITION = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "联网搜索最新信息。用于查询实时数据、新闻、百科知识等。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询关键词或问题",
                },
            },
            "required": ["query"],
        },
    },
}


def execute(args: dict) -> str:
    """执行联网搜索：通过 MCP 服务器完成实际搜索。"""
    query = args.get("query", "")
    if not query.strip():
        return json.dumps({
            "status": "error",
            "message": "查询关键词不能为空。",
        }, ensure_ascii=False)
    return search_web(query)
