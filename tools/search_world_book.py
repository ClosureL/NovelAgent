# encoding: utf-8
"""search_world_book — 只读检索世界书（供 Editor 等受限 Agent 使用）。"""

import json
from .world_book import execute as _original_execute


DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_world_book",
        "description": (
            "只读检索世界书/设定集词条。按关键词搜索或列出全部词条。"
            "不可增删改词条——仅用于查询上下文以确保设定一致。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "list"],
                    "description": "search=按关键词检索词条; list=列出全部词条",
                },
                "keyword": {
                    "type": "string",
                    "description": "检索关键词（search 时使用），在词条 key/content/secondary_keys 中模糊匹配",
                },
            },
            "required": ["action"],
        },
    },
}


def execute(args: dict) -> str:
    return _original_execute(args)
