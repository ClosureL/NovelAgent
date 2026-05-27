# encoding: utf-8
"""search_characters — 只读检索角色（供 Editor 等受限 Agent 使用）。"""

import json
from .manage_characters import execute as _original_execute


DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_characters",
        "description": (
            "只读检索角色信息。按关键词搜索或列出全部角色。"
            "不可增删改角色——仅用于查询上下文。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "list"],
                    "description": "search=按关键词检索角色; list=列出全部角色",
                },
                "keyword": {
                    "type": "string",
                    "description": "检索关键词（search 时使用），在角色名称/定位/性格/背景/成长弧线中模糊匹配",
                },
            },
            "required": ["action"],
        },
    },
}


def execute(args: dict) -> str:
    return _original_execute(args)
