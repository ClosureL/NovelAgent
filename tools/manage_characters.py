# encoding: utf-8
"""manage_characters — 以编号索引管理小说角色设定。"""

import json
from .state import get_state


DEFINITION = {
    "type": "function",
    "function": {
        "name": "manage_characters",
        "description": (
            "管理小说角色设定，以数字编号为索引。支持添加、更新、删除和列出角色。"
            "每个角色可记录名称、定位、性格、背景、外貌、能力、成长弧线及按事件弧记录的经历。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "update", "delete", "list", "search"],
                    "description": (
                        "add=添加新角色（自动分配编号）; "
                        "update=按编号更新已有角色的任意字段; "
                        "delete=按编号删除角色; "
                        "list=列出所有角色; "
                        "search=按关键词检索角色（在名称/定位/性格/背景/成长弧线中模糊匹配）"
                    ),
                },

                # ── 角色定位 ──
                "id": {
                    "type": "integer",
                    "description": "角色编号（update/delete 时必填，用于定位目标角色）",
                },
                "name": {
                    "type": "string",
                    "description": "角色姓名/称呼（add/update 时使用）",
                },
                "role": {
                    "type": "string",
                    "description": "角色定位，如：主角、配角、反派、导师、盟友、路人 等",
                },
                "personality": {
                    "type": "string",
                    "description": "性格描述",
                },
                "background": {
                    "type": "string",
                    "description": "背景故事/身世",
                },
                "appearance": {
                    "type": "string",
                    "description": "外貌特征",
                },
                "abilities": {
                    "type": "string",
                    "description": "特殊能力/技能/特长",
                },
                "arc": {
                    "type": "string",
                    "description": "角色整体成长弧线/发展轨迹概述",
                },

                # ── 检索参数 ──
                "keyword": {
                    "type": "string",
                    "description": "检索关键词（search 时使用），在角色 name/role/personality/background/arc 中模糊匹配",
                },

                # ── 经历字段 ──
                "experience": {
                    "type": "array",
                    "description": (
                        "角色经历时间线，按事件弧为最小单位记录。"
                        "每条记录对应大纲中的一个事件弧（arc），概述角色在此弧中的关键经历。"
                        "避免逐章记录，控制在每个弧1-3句话。"
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "arc": {
                                "type": "string",
                                "description": "事件弧名称，应与大纲中该弧的 title 保持一致",
                            },
                            "summary": {
                                "type": "string",
                                "description": "角色在此弧中的经历概要（100字以内）",
                            },
                        },
                        "required": ["arc", "summary"],
                    },
                },
            },
            "required": ["action"],
        },
    },
}


def _next_id(characters: dict) -> int:
    """返回下一个可用的角色编号。"""
    if not characters:
        return 1
    int_keys = [k for k in characters if isinstance(k, int)]
    return max(int_keys) + 1 if int_keys else 1


def _find_by_id(characters: dict, cid: int):
    """按编号查找角色，返回 (key, entry) 或 (None, None)。"""
    if cid in characters:
        return cid, characters[cid]
    return None, None


def _match_character(entry: dict, keyword: str) -> bool:
    """检查角色是否匹配关键词（在 name/role/personality/background/arc 中模糊查找）。"""
    kw = keyword.lower()
    for field in ("name", "role", "personality", "background", "arc"):
        if kw in entry.get(field, "").lower():
            return True
    return False


def execute(args: dict) -> str:
    state = get_state()
    action = args["action"]

    # ── search ──────────────────────────────────────────────
    if action == "search":
        keyword = args.get("keyword", "")
        if not keyword:
            return json.dumps({
                "status": "error",
                "message": "search 操作需要提供 keyword 参数",
            }, ensure_ascii=False)
        matched = {
            str(k): v for k, v in state.characters.items()
            if _match_character(v, keyword)
        }
        if not matched:
            return json.dumps({
                "status": "info",
                "message": f"未找到匹配「{keyword}」的角色",
                "characters": {},
                "keyword": keyword,
                "total": 0,
            }, ensure_ascii=False)
        return json.dumps({
            "status": "success",
            "message": f"找到 {len(matched)} 个匹配「{keyword}」的角色",
            "characters": matched,
            "keyword": keyword,
            "total": len(matched),
        }, ensure_ascii=False, indent=2)

    # ── list ────────────────────────────────────────────────
    if action == "list":
        if not state.characters:
            return json.dumps({
                "status": "info",
                "message": "暂无角色设定",
                "characters": {},
                "total": 0,
            }, ensure_ascii=False)
        return json.dumps({
            "status": "success",
            "characters": state.characters,
            "total": len(state.characters),
            "ids": sorted(
                k for k in state.characters if isinstance(k, int)
            ),
        }, ensure_ascii=False, indent=2)

    # ── add ─────────────────────────────────────────────────
    if action == "add":
        name = args.get("name", "").strip()
        if not name:
            return json.dumps({
                "status": "error",
                "message": "角色名称不能为空",
            }, ensure_ascii=False)

        cid = _next_id(state.characters)
        state.characters[cid] = {
            "name": name,
            "role": args.get("role", ""),
            "personality": args.get("personality", ""),
            "background": args.get("background", ""),
            "appearance": args.get("appearance", ""),
            "abilities": args.get("abilities", ""),
            "arc": args.get("arc", ""),
            "experience": args.get("experience", []),
        }
        return json.dumps({
            "status": "success",
            "message": f"角色 #{cid}「{name}」已添加",
            "id": cid,
            "entry": state.characters[cid],
        }, ensure_ascii=False, indent=2)

    # ── update / delete 需要 id ──────────────────────────────
    cid = args.get("id")
    if cid is None:
        return json.dumps({
            "status": "error",
            "message": "update / delete 操作需要提供 id 参数（角色编号）",
        }, ensure_ascii=False)

    key, entry = _find_by_id(state.characters, cid)
    if entry is None:
        return json.dumps({
            "status": "error",
            "message": f"角色 #{cid} 不存在，请使用 list 查看已有角色编号",
        }, ensure_ascii=False)

    # ── update ──────────────────────────────────────────────
    if action == "update":
        updatable = [
            "name", "role", "personality", "background",
            "appearance", "abilities", "arc", "experience",
        ]
        updated_fields = []
        for field in updatable:
            if field in args:
                val = args[field]
                if field == "name" and not isinstance(val, str):
                    continue
                if field == "experience":
                    if isinstance(val, list):
                        entry[field] = val
                        updated_fields.append(field)
                elif val:
                    entry[field] = val
                    updated_fields.append(field)

        if not updated_fields:
            return json.dumps({
                "status": "error",
                "message": "update 操作未提供任何有效字段",
            }, ensure_ascii=False)

        return json.dumps({
            "status": "success",
            "message": f"角色 #{cid}「{entry.get('name', '')}」已更新（{', '.join(updated_fields)}）",
            "id": cid,
            "entry": entry,
        }, ensure_ascii=False, indent=2)

    # ── delete ──────────────────────────────────────────────
    if action == "delete":
        removed = state.characters.pop(key)
        return json.dumps({
            "status": "success",
            "message": f"角色 #{cid}「{removed.get('name', '')}」已删除",
            "deleted": removed,
        }, ensure_ascii=False, indent=2)

    return json.dumps({
        "status": "error",
        "message": f"未知操作：{action}，支持的操作：add, update, delete, list, search",
    }, ensure_ascii=False)
