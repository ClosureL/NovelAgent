# encoding: utf-8
"""
NovelWriter Agent —— 完整小说创作 Agent。

加载 novel_writer.md 系统提示，挂载全部 7 个工具。
如需新建其他 agent（如纯大纲规划、编辑器），参考此文件创建即可。
"""

from pathlib import Path
from .base import BaseAgent

PROMPT = (Path(__file__).parent / "prompts" / "novel_writer.md").read_text(encoding="utf-8")

TOOLS = [
    "create_outline",
    "manage_characters",
    "write_chapter",
    "revise_content",
    "suggest_plot",
    "manage_world_book",
    "read_material",
    "read_previous_chapter",
]


class NovelWriterAgent(BaseAgent):
    """完整小说创作 Agent —— 包含全部规划和写作工具。"""

    content_tool_names = {"write_chapter", "revise_content"}

    def __init__(self, model_name: str | None = None):
        super().__init__(system_prompt=PROMPT, tool_names=TOOLS, model_name=model_name)


# 向后兼容别名
NovelAgent = NovelWriterAgent
