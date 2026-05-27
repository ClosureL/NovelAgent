# encoding: utf-8
"""manage_world_book — 管理世界书/设定集词条。

世界书数据独立存储于 saves/{书名}/world_book.json，与 novel_state.json 分离。
模块级 _world_book 为运行时缓存，修改后自动落盘。
"""

import json
import copy
from pathlib import Path
from .state import get_novel_dir


# ── 运行时缓存 ──────────────────────────────────────────────

_world_book: dict[str, dict] = {}


def get_world_book() -> dict[str, dict]:
    """返回当前世界书运行时缓存。"""
    return _world_book


def set_world_book(data: dict[str, dict]):
    """替换整个世界书缓存（用于加载/回退）。"""
    global _world_book
    _world_book = data


# ── 持久化 ──────────────────────────────────────────────────

def save_world_book_to_file():
    """将世界书写入 saves/{书名}/world_book.json。"""
    novel_dir = get_novel_dir()
    if not novel_dir:
        return
    novel_dir.mkdir(parents=True, exist_ok=True)
    (novel_dir / "world_book.json").write_text(
        json.dumps(_world_book, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_world_book_from_file(novel_dir: str | Path | None = None):
    """从指定 saves 子目录加载世界书；不传则从当前 novel_dir 加载。"""
    global _world_book
    if novel_dir:
        from .state import SAVES_DIR
        fp = SAVES_DIR / novel_dir / "world_book.json"
    else:
        nd = get_novel_dir()
        if not nd:
            _world_book = {}
            return
        fp = nd / "world_book.json"

    if fp.exists():
        try:
            _world_book = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            _world_book = {}
    else:
        _world_book = {}


# ── 工具定义 ────────────────────────────────────────────────

DEFINITION = {
    "type": "function",
    "function": {
        "name": "manage_world_book",
        "description": (
            "管理世界书（设定集）词条。用于记录和检索世界观设定、专有名词、"
            "关键概念、组织/地点/物品等设定信息。支持添加、更新、删除、搜索和列出词条。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "update", "delete", "search", "list"],
                    "description": (
                        "操作类型：add=添加词条, update=更新词条, "
                        "delete=删除词条, search=按关键词检索, list=列出全部词条"
                    ),
                },
                "key": {
                    "type": "string",
                    "description": "词条主键/触发词（add/update/delete 时必填），建议使用最常用或最正式的称呼",
                },
                "content": {
                    "type": "string",
                    "description": "词条正文（add/update 时使用），描述该词条所指概念的定义、背景、关键信息",
                },
                "secondary_keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "别名/次要触发词列表，如角色外号、地点的别称等（add/update 时可选）",
                },
                "category": {
                    "type": "string",
                    "description": "词条分类标签，如：角色、地点、组织、物品、概念、事件、规则 等（add/update 时可选）",
                },
                "comment": {
                    "type": "string",
                    "description": "使用备注，如\"在涉及XX情节时触发此词条\"（add/update 时可选）",
                },
                "keyword": {
                    "type": "string",
                    "description": "检索关键词（search 时使用），在词条 key、content、secondary_keys 中模糊匹配",
                },
            },
            "required": ["action"],
        },
    },
}


def _match_entry(entry: dict, keyword: str) -> bool:
    """检查词条是否匹配关键词（在 key、secondary_keys、content 中模糊查找）。"""
    kw = keyword.lower()
    if kw in entry.get("key", "").lower():
        return True
    if kw in entry.get("content", "").lower():
        return True
    for sk in entry.get("secondary_keys", []):
        if kw in sk.lower():
            return True
    return False


def execute(args: dict) -> str:
    action = args["action"]
    entries = _world_book

    if action == "list":
        if not entries:
            return json.dumps({
                "status": "info",
                "message": "世界书暂无词条",
                "entries": {},
                "total": 0,
            }, ensure_ascii=False)
        return json.dumps({
            "status": "success",
            "entries": entries,
            "total": len(entries),
            "keys": sorted(entries.keys()),
        }, ensure_ascii=False, indent=2)

    if action == "search":
        keyword = args.get("keyword", "")
        if not keyword:
            return json.dumps({
                "status": "error",
                "message": "search 操作需要提供 keyword 参数",
            }, ensure_ascii=False)
        matched = {
            k: v for k, v in entries.items() if _match_entry(v, keyword)
        }
        if not matched:
            return json.dumps({
                "status": "info",
                "message": f"未找到匹配「{keyword}」的词条",
                "entries": {},
                "keyword": keyword,
                "total": 0,
            }, ensure_ascii=False)
        return json.dumps({
            "status": "success",
            "message": f"找到 {len(matched)} 个匹配「{keyword}」的词条",
            "entries": matched,
            "keyword": keyword,
            "total": len(matched),
        }, ensure_ascii=False, indent=2)

    key = args.get("key", "").strip()
    if not key:
        return json.dumps({
            "status": "error",
            "message": "词条 key 不能为空（add/update/delete 操作需要提供 key 参数）",
        }, ensure_ascii=False)

    if action == "add":
        if key in entries:
            return json.dumps({
                "status": "error",
                "message": f"词条「{key}」已存在，请使用 update 操作更新，或先用 delete 删除",
                "key": key,
            }, ensure_ascii=False)
        entry = {
            "key": key,
            "content": args.get("content", ""),
            "secondary_keys": args.get("secondary_keys", []),
            "category": args.get("category", ""),
            "comment": args.get("comment", ""),
        }
        entries[key] = entry
        save_world_book_to_file()
        return json.dumps({
            "status": "success",
            "message": f"词条「{key}」已添加",
            "entry": entry,
        }, ensure_ascii=False, indent=2)

    if action == "update":
        if key not in entries:
            return json.dumps({
                "status": "error",
                "message": f"词条「{key}」不存在，请使用 add 操作先创建",
                "key": key,
            }, ensure_ascii=False)
        entry = entries[key]
        if "content" in args and args["content"]:
            entry["content"] = args["content"]
        if "secondary_keys" in args:
            entry["secondary_keys"] = args["secondary_keys"]
        if "category" in args:
            entry["category"] = args["category"]
        if "comment" in args:
            entry["comment"] = args["comment"]
        save_world_book_to_file()
        return json.dumps({
            "status": "success",
            "message": f"词条「{key}」已更新",
            "entry": entry,
        }, ensure_ascii=False, indent=2)

    if action == "delete":
        if key not in entries:
            return json.dumps({
                "status": "error",
                "message": f"词条「{key}」不存在，无法删除",
                "key": key,
            }, ensure_ascii=False)
        deleted = entries.pop(key)
        save_world_book_to_file()
        return json.dumps({
            "status": "success",
            "message": f"词条「{key}」已删除",
            "deleted_entry": deleted,
        }, ensure_ascii=False, indent=2)

    return json.dumps({
        "status": "error",
        "message": f"未知操作：{action}，支持的操作：add, update, delete, search, list",
    }, ensure_ascii=False)
