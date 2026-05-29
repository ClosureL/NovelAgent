# encoding: utf-8
"""
NovelEditor Agent —— 小说改写 Agent。

负责对已有章节进行大刀阔斧的重写与风格重塑，打破大模型文风惯性。
无权改动大纲、角色和世界书，可只读查询以确认上下文。
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
    """小说改写 Agent —— 含修订工具和只读查询工具，不可修改大纲/角色/世界书。"""

    content_tool_names = {"revise_content"}
    refresh_every_turn = True

    def __init__(self, model_name: str | None = None):
        super().__init__(system_prompt=PROMPT, tool_names=TOOLS, model_name=model_name)
