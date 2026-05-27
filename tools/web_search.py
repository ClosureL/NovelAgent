# encoding: utf-8
"""web_search — 内置联网搜索工具（Mimo 等服务端执行）。"""

import json

DEFINITION = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "联网搜索最新信息。用于查询实时数据、新闻、百科知识等。"
            "服务端自动执行，无需客户端干预。"
        ),
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
    """web_search 由 Mimo 等服务端自动执行，此函数仅作为兜底占位。"""
    return json.dumps({
        "status": "success",
        "message": "搜索请求已由服务端处理（如果是 Mimo 等支持的模型）",
        "note": "若当前模型不支持内置搜索，此调用将无实际效果。",
    }, ensure_ascii=False)
