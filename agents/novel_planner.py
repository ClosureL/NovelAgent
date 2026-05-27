# encoding: utf-8
"""
NovelPlanner Agent —— 小说策划 Agent。

专注于前期策划与规划：情节构思、大纲设计、人物塑造、需求澄清。
不包含写入类工具（write_chapter / revise_content），不可撰写章节正文。
"""

from pathlib import Path
from .base import BaseAgent

PROMPT = (Path(__file__).parent / "prompts" / "novel_planner.md").read_text(encoding="utf-8")

TOOLS = [
    "create_outline",
    "manage_characters",
    "suggest_plot",
    "manage_world_book",
    "read_material",
    "read_previous_chapter",
]


class NovelPlannerAgent(BaseAgent):
    """小说策划 Agent —— 仅包含分析类与计划类工具，不含写作类工具。"""

    content_tool_names: set[str] = set()

    def __init__(self, model_name: str | None = None):
        super().__init__(system_prompt=PROMPT, tool_names=TOOLS, model_name=model_name)
