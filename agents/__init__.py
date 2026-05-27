# encoding: utf-8
"""
NovelAgent Agents 包 —— 每个 agent = 系统提示 + 工具列表 + 模型配置。

添加新 agent：
  1. 在 prompts/ 下创建 .md 系统提示文件
  2. 新建一个 .py 文件，继承 BaseAgent，指定 system_prompt 和 tool_names
  3. 在此 __init__.py 中导出（可选）
"""

from .base import BaseAgent
from .novel_writer import NovelWriterAgent, NovelAgent
from .novel_planner import NovelPlannerAgent
from .novel_editor import NovelEditorAgent
from .novel_explorer import NovelExplorerAgent
