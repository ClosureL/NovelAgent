# encoding: utf-8
"""
NovelExplorer Agent —— 独立资料研究与随笔记录 Agent。

即插即用、可抛弃：不加载项目上下文，不影响 novel_state，
对话历史不保存，切换 agent 后直接丢弃。
"""

from pathlib import Path
from .base import BaseAgent

PROMPT = (Path(__file__).parent / "prompts" / "novel_explorer.md").read_text(encoding="utf-8")

TOOLS = [
    "read_material",
    "read_previous_chapter",
    "view_outline",
    "search_characters",
    "search_world_book",
    "save_material",
    "web_search",
]

# Mimo v2.5 内置联网搜索工具定义（非 function-calling 格式）
_MIMO_WEB_SEARCH = {
    "type": "web_search",
    "max_keyword": 5,
    "force_search": False,
    "limit": 5,
}


class NovelExplorerAgent(BaseAgent):
    """独立探索 Agent —— 读写分离，不对项目状态产生任何影响。"""

    content_tool_names = {"save_material"}

    def __init__(self, model_name: str | None = None):
        super().__init__(system_prompt=PROMPT, tool_names=TOOLS, model_name=model_name)

    def _build_request_kwargs(self, stream: bool = False, tools: list | None = ...) -> dict:
        kwargs = super()._build_request_kwargs(stream=stream, tools=tools)
        # mimo 模型：将 function-calling 格式的 web_search 替换为 Mimo 内置格式
        if "mimo" in self.model_name.lower() and tools is not None:
            current_tools = list(kwargs.get("tools", []) or [])
            # 移除 function-calling 格式的 web_search
            current_tools = [
                t for t in current_tools
                if not (t.get("type") == "function"
                        and t.get("function", {}).get("name") == "web_search")
            ]
            # 注入 Mimo 内置格式
            current_tools.append(dict(_MIMO_WEB_SEARCH))
            kwargs["tools"] = current_tools
        return kwargs

    def _auto_save(self):
        """Explorer 不保存对话历史。"""
        pass

    def _auto_save_text_as_chapter(self, text: str):
        """Explorer 不保存章节。"""
        pass
