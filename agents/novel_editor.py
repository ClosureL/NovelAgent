# encoding: utf-8
"""
NovelEditor Agent —— 小说编辑润色 Agent。

仅负责修改润色已有章节，无改动大纲、角色和世界书的权限。
可只读查询大纲/角色/世界书以确认上下文。
"""

from pathlib import Path
from .base import BaseAgent

PROMPT = (Path(__file__).parent / "prompts" / "novel_editor.md").read_text(encoding="utf-8")

TOOLS = [
    "revise_content",
    "view_outline",
    "search_characters",
    "search_world_book",
    "read_previous_chapter",
    "read_material",
]


class NovelEditorAgent(BaseAgent):
    """小说编辑 Agent —— 仅含修订工具和只读查询工具，不可修改大纲/角色/世界书。"""

    content_tool_names = {"revise_content"}
    refresh_every_turn = True

    def __init__(self, model_name: str | None = None):
        super().__init__(system_prompt=PROMPT, tool_names=TOOLS, model_name=model_name)
