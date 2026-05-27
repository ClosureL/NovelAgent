# encoding: utf-8
"""
NovelAgent 工具包 —— 自动发现并注册所有工具模块。

每个工具模块只需定义 DEFINITION（OpenAI function schema）和 execute(args) 函数，
放置在此目录下即可被自动发现。无需手动注册。
"""

import importlib
from pathlib import Path

# ── 公开 state 模块的全部接口 ──
from .state import (
    NovelState, get_state, set_state, reset_state,
    get_novel_dir, save_state_to_file, load_state_from_file,
    export_chapter_txt, export_all_chapters_txt, list_novels,
    set_messages_ref, parse_chapter_num, build_state_context,
)

from .world_book import (
    get_world_book, set_world_book,
    save_world_book_to_file, load_world_book_from_file,
)


_tool_registry: dict[str, dict] = {}


def _discover_tools():
    """扫描本目录下所有 .py 文件，自动注册符合条件的工具模块。"""
    tools_dir = Path(__file__).parent
    for f in sorted(tools_dir.glob("*.py")):
        name = f.stem
        if name.startswith("_") or name in ("state",):
            continue
        mod = importlib.import_module(f".{name}", __package__)
        if hasattr(mod, "DEFINITION") and hasattr(mod, "execute"):
            defn = mod.DEFINITION
            tool_name = defn["function"]["name"]
            _tool_registry[tool_name] = {
                "definition": defn,
                "execute": mod.execute,
            }


_discover_tools()


def get_all_definitions() -> list[dict]:
    """返回所有工具的 OpenAI function calling 格式定义。"""
    return [t["definition"] for t in _tool_registry.values()]


def execute_tool(name: str, arguments: dict) -> str:
    """统一的工具执行入口。"""
    import json
    entry = _tool_registry.get(name)
    if entry is None:
        return json.dumps({"status": "error", "message": f"未知工具：{name}"}, ensure_ascii=False)
    try:
        return entry["execute"](arguments)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)


# 向后兼容别名 —— 首次导入时缓存
TOOL_DEFINITIONS: list[dict] = []


def _init_compat():
    global TOOL_DEFINITIONS
    TOOL_DEFINITIONS = get_all_definitions()


_init_compat()
