# encoding: utf-8
"""create_outline — 以卷-事件弧-章-关键点层级结构管理小说大纲。"""

import json
from datetime import datetime
from .state import get_state


DEFINITION = {
    "type": "function",
    "function": {
        "name": "create_outline",
        "description": (
            "管理小说大纲，采用「卷 → 事件弧 → 章 → 关键点」四级层级结构。"
            "支持创建、增量更新和删除操作，无需一次性填满所有层级。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "update", "delete", "view"],
                    "description": (
                        "create=完整替换大纲（用于初次创建或重大重构）; "
                        "update=增量添加/修改某卷、某弧或某章; "
                        "delete=删除指定卷/弧/章; "
                        "view=查看当前大纲（只读，不修改；可选 path 定位到特定层级）"
                    ),
                },

                # ── create 参数 ──
                "title": {"type": "string", "description": "小说标题（create 时必填）"},
                "genre": {"type": "string", "description": "小说类型/流派（create 时必填）"},
                "summary": {"type": "string", "description": "故事梗概（200字以内，create 时必填）"},
                "volumes": {
                    "type": "array",
                    "description": "卷列表（create 时可选，后续可用 update 增量补充）",
                    "items": {
                        "type": "object",
                        "properties": {
                            "number": {"type": "integer", "description": "卷编号，从 1 开始"},
                            "title": {"type": "string", "description": "卷标题"},
                            "summary": {"type": "string", "description": "本卷概要"},
                            "arcs": {
                                "type": "array",
                                "description": "事件弧列表（可选）",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "number": {"type": "integer", "description": "弧编号，卷内从 1 开始"},
                                        "title": {"type": "string", "description": "事件弧标题"},
                                        "summary": {"type": "string", "description": "事件弧概要"},
                                        "chapters": {
                                            "type": "array",
                                            "description": "章列表（可选）",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "number": {"type": "integer", "description": "章编号，弧内从 1 开始"},
                                                    "title": {"type": "string", "description": "章标题"},
                                                    "summary": {"type": "string", "description": "章概要"},
                                                    "key_points": {
                                                        "type": "array",
                                                        "items": {"type": "string"},
                                                        "description": "本章关键情节节点",
                                                    },
                                                },
                                                "required": ["number", "title"],
                                            },
                                        },
                                    },
                                    "required": ["number", "title"],
                                },
                            },
                        },
                        "required": ["number", "title"],
                    },
                },

                # ── update / delete 共用定位参数 ──
                "path": {
                    "type": "object",
                    "description": (
                        "目标定位（update/delete 时必填，view 时可选）。"
                        "{\"volume\":1} 定位到卷; "
                        "{\"volume\":1,\"arc\":2} 定位到弧; "
                        "{\"volume\":1,\"arc\":2,\"chapter\":3} 定位到章"
                    ),
                    "properties": {
                        "volume": {"type": "integer", "description": "卷编号"},
                        "arc": {"type": "integer", "description": "弧编号（卷内）"},
                        "chapter": {"type": "integer", "description": "章编号（弧内）"},
                    },
                    "required": ["volume"],
                },

                # ── update 数据 ──
                "data": {
                    "type": "object",
                    "description": (
                        "要写入的数据（update 时使用）。根据 path 的层级不同，传入对应类型的数据："
                        "path=volume 时传入卷对象 {title, summary, arcs?}；"
                        "path=arc 时传入弧对象 {title, summary, chapters?}；"
                        "path=chapter 时传入章对象 {title, summary, key_points?}"
                    ),
                    "properties": {
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "key_points": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "arcs": {"type": "array"},
                        "chapters": {"type": "array"},
                    },
                },
            },
            "required": ["action"],
        },
    },
}


def _count_all(state: dict) -> str:
    """统计当前大纲的卷/弧/章数量，生成可读摘要。"""
    vols = state.get("volumes", [])
    n_vols = len(vols)
    n_arcs = sum(len(v.get("arcs", [])) for v in vols)
    n_chs = sum(
        len(a.get("chapters", []))
        for v in vols
        for a in v.get("arcs", [])
    )
    return f"{n_vols} 卷 / {n_arcs} 弧 / {n_chs} 章"


def _find_parent(state: dict, path: dict):
    """根据 path 定位目标层级，返回 (parent_list, index, target_dict)。

    路径层级：
      {"volume":V}                     → volumes[V-1]
      {"volume":V, "arc":A}            → volumes[V-1].arcs[A-1]
      {"volume":V, "arc":A, "chapter":C} → volumes[V-1].arcs[A-1].chapters[C-1]

    返回 (parent_list, index, target_dict)，parent_list 是包含目标的列表，
    index 是目标在列表中的位置，target_dict 是目标本身。
    """
    vols = state.get("volumes", [])
    v_idx = path["volume"] - 1
    if v_idx < 0:
        return None, -1, None

    # 路径仅到卷
    if "arc" not in path:
        return vols, v_idx, vols[v_idx] if v_idx < len(vols) else None

    # 确保卷存在
    if v_idx >= len(vols):
        return None, -1, None
    vol = vols[v_idx]
    if "arcs" not in vol:
        vol["arcs"] = []
    arcs = vol["arcs"]

    a_idx = path["arc"] - 1
    if a_idx < 0:
        return None, -1, None

    # 路径仅到弧
    if "chapter" not in path:
        return arcs, a_idx, arcs[a_idx] if a_idx < len(arcs) else None

    # 确保弧存在
    if a_idx >= len(arcs):
        return None, -1, None
    if "chapters" not in arcs[a_idx]:
        arcs[a_idx]["chapters"] = []
    chapters = arcs[a_idx]["chapters"]

    c_idx = path["chapter"] - 1
    if c_idx < 0:
        return None, -1, None

    return chapters, c_idx, chapters[c_idx] if c_idx < len(chapters) else None


def execute(args: dict) -> str:
    state = get_state()
    action = args["action"]

    # ── create — 完整替换 ──────────────────────────────────
    if action == "create":
        title = args.get("title", "")
        genre = args.get("genre", "")
        summary = args.get("summary", "")
        if not title:
            return json.dumps({
                "status": "error",
                "message": "create 操作需要提供 title 参数",
            }, ensure_ascii=False)

        state.outline = {
            "title": title,
            "genre": genre,
            "summary": summary,
            "volumes": args.get("volumes", []),
            "updated_at": datetime.now().isoformat(),
        }
        stats = _count_all(state.outline)
        return json.dumps({
            "status": "success",
            "message": f"大纲已创建：{title}（{stats}）",
            "outline": state.outline,
        }, ensure_ascii=False, indent=2)

    # ── view — 只读查看 ────────────────────────────────────
    if action == "view":
        if not state.outline:
            return json.dumps({
                "status": "info",
                "message": "尚未创建大纲，请先使用 create 操作",
                "outline": None,
            }, ensure_ascii=False)

        path = args.get("path")
        if path and "volume" in path:
            _, _, target = _find_parent(state.outline, path)
            if target is None:
                return json.dumps({
                    "status": "error",
                    "message": f"view 失败：path={path} 指定的层级不存在",
                }, ensure_ascii=False)
            level = "chapter" if "chapter" in path else "arc" if "arc" in path else "volume"
            return json.dumps({
                "status": "success",
                "level": level,
                "path": path,
                "data": target,
            }, ensure_ascii=False, indent=2)

        stats = _count_all(state.outline)
        return json.dumps({
            "status": "success",
            "outline": state.outline,
            "stats": stats,
        }, ensure_ascii=False, indent=2)

    # update / delete 需要已存在的大纲和 path
    if not state.outline:
        return json.dumps({
            "status": "error",
            "message": "尚未创建大纲，请先使用 create 操作",
        }, ensure_ascii=False)

    path = args.get("path")
    if not path or "volume" not in path:
        return json.dumps({
            "status": "error",
            "message": "update / delete 操作需要提供 path 参数，至少包含 volume 字段",
        }, ensure_ascii=False)

    # ── update — 增量添加/修改 ─────────────────────────────
    if action == "update":
        data = args.get("data", {})
        if not data:
            return json.dumps({
                "status": "error",
                "message": "update 操作需要提供 data 参数",
            }, ensure_ascii=False)

        parent_list, idx, existing = _find_parent(state.outline, path)
        if parent_list is None:
            return json.dumps({
                "status": "error",
                "message": f"定位失败：path={path} 中指定的上级层级不存在",
            }, ensure_ascii=False)

        level = "volume"
        if "arc" in path:
            level = "arc"
        if "chapter" in path:
            level = "chapter"

        if existing is not None and idx < len(parent_list):
            # 已有条目 → 更新
            existing["title"] = data.get("title", existing.get("title", ""))
            existing["summary"] = data.get("summary", existing.get("summary", ""))
            if level == "chapter" and "key_points" in data:
                existing["key_points"] = data["key_points"]
            # 保留并更新内嵌子列表
            if level == "volume" and "arcs" in data:
                existing["arcs"] = data["arcs"]
            if level == "arc" and "chapters" in data:
                existing["chapters"] = data["chapters"]
            verb = "已更新"
        else:
            # 新条目 → 追加（自动填充编号）
            new_entry = {"number": path.get(level, len(parent_list) + 1)}
            new_entry["title"] = data.get("title", f"第{new_entry['number']}{'卷' if level == 'volume' else '弧' if level == 'arc' else '章'}")
            new_entry["summary"] = data.get("summary", "")
            if level == "chapter":
                new_entry["key_points"] = data.get("key_points", [])
            if level == "volume":
                new_entry["arcs"] = data.get("arcs", [])
            if level == "arc":
                new_entry["chapters"] = data.get("chapters", [])
            parent_list.append(new_entry)
            verb = "已添加"

        state.outline["updated_at"] = datetime.now().isoformat()
        stats = _count_all(state.outline)
        return json.dumps({
            "status": "success",
            "message": f"{verb} path={path}（{stats}）",
            "outline": state.outline,
        }, ensure_ascii=False, indent=2)

    # ── delete — 删除指定层级 ──────────────────────────────
    if action == "delete":
        parent_list, idx, target = _find_parent(state.outline, path)
        if parent_list is None or target is None or idx >= len(parent_list):
            return json.dumps({
                "status": "error",
                "message": f"删除失败：path={path} 指定的条目不存在",
            }, ensure_ascii=False)

        removed = parent_list.pop(idx)
        removed_label = removed.get("title", str(path))

        state.outline["updated_at"] = datetime.now().isoformat()
        stats = _count_all(state.outline)
        return json.dumps({
            "status": "success",
            "message": f"已删除「{removed_label}」（{stats}）",
            "removed": removed,
        }, ensure_ascii=False, indent=2)

    return json.dumps({
        "status": "error",
        "message": f"未知操作：{action}，支持的操作：create, update, delete, view",
    }, ensure_ascii=False)
