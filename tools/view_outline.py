# encoding: utf-8
"""view_outline — 只读查看大纲（供 Editor 等受限 Agent 使用）。"""

import json
from .create_outline import execute as _original_execute
from .state import get_state


DEFINITION = {
    "type": "function",
    "function": {
        "name": "view_outline",
        "description": (
            "只读查看当前大纲结构。查看完整大纲或定位到特定卷/弧/章。"
            "不可修改大纲——仅用于查询上下文。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "object",
                    "description": (
                        "可选：定位到特定层级查看。"
                        "{\"volume\":1} 定位到卷; "
                        "{\"volume\":1,\"arc\":2} 定位到弧; "
                        "{\"volume\":1,\"arc\":2,\"chapter\":3} 定位到章。"
                        "不传则返回完整大纲"
                    ),
                    "properties": {
                        "volume": {"type": "integer", "description": "卷编号"},
                        "arc": {"type": "integer", "description": "弧编号（卷内）"},
                        "chapter": {"type": "integer", "description": "章编号（弧内）"},
                    },
                    "required": ["volume"],
                },
            },
        },
    },
}


def execute(args: dict) -> str:
    path = args.get("path")
    if path:
        return _original_execute({"action": "view", "path": path})

    state = get_state()
    if not state.outline:
        return json.dumps({
            "status": "info",
            "message": "尚未创建大纲",
            "outline": None,
        }, ensure_ascii=False)

    # 生成可读摘要而非全量输出
    vols = state.outline.get("volumes", [])
    lines = [
        f"标题：{state.outline.get('title', '未设定')}",
        f"类型：{state.outline.get('genre', '未设定')}",
        f"梗概：{state.outline.get('summary', '未设定')}",
        "",
    ]
    for v in vols:
        lines.append(f"第{v['number']}卷「{v.get('title', '')}」— {v.get('summary', '')}")
        for a in v.get("arcs", []):
            lines.append(f"  弧{a['number']}「{a.get('title', '')}」— {a.get('summary', '')}")
            for c in a.get("chapters", []):
                kps = c.get("key_points", [])
                kp_str = " | ".join(kps) if kps else "（无关键点）"
                lines.append(f"    第{c['number']}章「{c.get('title', '')}」— {c.get('summary', '')}")
                lines.append(f"      关键点: {kp_str}")

    result = "\n".join(lines)
    return json.dumps({
        "status": "success",
        "outline_text": result,
        "stats": {
            "volumes": len(vols),
            "arcs": sum(len(v.get("arcs", [])) for v in vols),
            "chapters": sum(
                len(a.get("chapters", []))
                for v in vols for a in v.get("arcs", [])
            ),
        },
    }, ensure_ascii=False, indent=2)
