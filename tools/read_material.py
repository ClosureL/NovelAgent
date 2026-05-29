# encoding: utf-8
"""read_material — 从素材库读取素材文件。支持模糊搜索→精确读取两步检索，递归搜索子目录。"""

import json
import os
from pathlib import Path
from .state import MATERIALS_DIR


DEFINITION = {
    "type": "function",
    "function": {
        "name": "read_material",
        "description": (
            "从素材库（materials/ 目录，含所有子目录）读取素材。三种操作："
            "search=按关键词模糊搜索文件名和路径（递归搜索子目录，结果按相关度排序）；"
            "list=列出文件列表（可限定子目录）；"
            "read=按精确路径读取文件内容，支持通过 offset/limit 分段读取大文件"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "read", "search"],
                    "description": "search=模糊搜索; list=列出文件; read=读取文件内容",
                },
                "path": {
                    "type": "string",
                    "description": "read 操作时必填：素材库下的相对文件路径（含子目录，如 'samples/范文.txt'）",
                },
                "query": {
                    "type": "string",
                    "description": "search 操作时必填：模糊搜索关键词（大小写不敏感）",
                },
                "subdir": {
                    "type": "string",
                    "description": "list/search 操作时可选：限定在指定子目录下操作（如 'samples'），为空则递归搜索全部素材库",
                },
                "offset": {
                    "type": "integer",
                    "description": "read 操作时可选：起始行号（0-based），默认 0 从头读取。用于分段读取大文件，避免一次性读取过多内容。",
                },
                "limit": {
                    "type": "integer",
                    "description": "read 操作时可选：最大读取行数，默认 200，上限 500。控制单次读取量，防止上下文窗口溢出。",
                },
            },
            "required": ["action"],
        },
    },
}


# ── 模糊搜索 ──────────────────────────────────────────────

def _chars_in_order(query: str, target: str) -> bool:
    """检查 query 的所有字符是否按顺序出现在 target 中（用于拼音首字母等简写匹配）。"""
    idx = 0
    for ch in query:
        idx = target.find(ch, idx)
        if idx == -1:
            return False
        idx += 1
    return True


def _fuzzy_search(query: str, subdir: str | None = None) -> list[dict]:
    """在素材库中模糊搜索文件，返回按匹配度排序的候选列表。
    subdir 非空时仅搜索 MATERIALS_DIR/subdir 下的文件。"""
    if not query:
        return []

    search_root = MATERIALS_DIR / subdir if subdir else MATERIALS_DIR
    if not search_root.is_dir():
        return []

    query_lower = query.lower().replace("\\", "/")
    candidates = []

    for root, _, filenames in os.walk(search_root):
        for fname in filenames:
            full = Path(root) / fname
            rel = str(full.relative_to(MATERIALS_DIR)).replace("\\", "/")
            fname_lower = fname.lower()
            rel_lower = rel.lower()

            if fname_lower == query_lower:
                candidates.append({"path": rel, "score": 1, "match_type": "文件名完全匹配"})
            elif query_lower in fname_lower:
                candidates.append({"path": rel, "score": 2, "match_type": "文件名包含关键词"})
            elif query_lower in rel_lower:
                candidates.append({"path": rel, "score": 3, "match_type": "路径包含关键词"})
            elif _chars_in_order(query_lower, fname_lower):
                candidates.append({"path": rel, "score": 4, "match_type": "字符序列匹配"})

    candidates.sort(key=lambda x: x["score"])
    return candidates


def _list_files(subdir: str | None = None) -> list[dict]:
    """列出素材库文件，subdir 非空时仅列出指定子目录下的文件。"""
    search_root = MATERIALS_DIR / subdir if subdir else MATERIALS_DIR
    if not search_root.is_dir():
        return []

    files = []
    for root, _, filenames in os.walk(search_root):
        for fname in filenames:
            full = Path(root) / fname
            rel = str(full.relative_to(MATERIALS_DIR)).replace("\\", "/")
            size = full.stat().st_size
            files.append({"path": rel, "size": size})

    return sorted(files, key=lambda x: x["path"])


# ── 工具执行入口 ──────────────────────────────────────────

def execute(args: dict) -> str:
    action = args["action"]
    MATERIALS_DIR.mkdir(parents=True, exist_ok=True)

    # ── list ──
    if action == "list":
        subdir = args.get("subdir", "").strip() or None
        if subdir and not (MATERIALS_DIR / subdir).is_dir():
            return json.dumps({
                "status": "error",
                "message": f"子目录不存在：'{subdir}'。可用 list（不带 subdir）查看全部素材库结构。",
            }, ensure_ascii=False)

        files = _list_files(subdir)

        if not files:
            scope = f"子目录 '{subdir}/' 下" if subdir else "素材库中"
            return json.dumps({
                "status": "info",
                "message": f"{scope}暂无文件。",
                "files": [],
            }, ensure_ascii=False, indent=2)

        scope = f"子目录 '{subdir}/' 下共" if subdir else "素材库共"
        return json.dumps({
            "status": "success",
            "message": f"{scope}{len(files)} 个文件",
            "files": files,
        }, ensure_ascii=False, indent=2)

    # ── search ──
    elif action == "search":
        query = args.get("query", "").strip()
        if not query:
            return json.dumps({
                "status": "error",
                "message": "search 操作需要提供 query 关键词。",
            }, ensure_ascii=False)

        subdir = args.get("subdir", "").strip() or None
        if subdir and not (MATERIALS_DIR / subdir).is_dir():
            return json.dumps({
                "status": "error",
                "message": f"子目录不存在：'{subdir}'。可去掉 subdir 进行全局搜索。",
            }, ensure_ascii=False)

        candidates = _fuzzy_search(query, subdir)

        scope = f"（在 '{subdir}/' 下搜索）" if subdir else ""

        if not candidates:
            return json.dumps({
                "status": "info",
                "message": (
                    f"未找到匹配 '{query}' 的文件{scope}。"
                    "用 list 浏览素材库全部文件，或用更短的关键词重试。"
                ),
                "candidates": [],
            }, ensure_ascii=False, indent=2)

        if len(candidates) == 1:
            p = candidates[0]["path"]
            return json.dumps({
                "status": "success",
                "message": f"找到 1 个匹配{scope}：'{p}'。调用 read 并传入 path=\"{p}\" 即可读取内容。",
                "candidates": candidates,
            }, ensure_ascii=False, indent=2)
        else:
            return json.dumps({
                "status": "success",
                "message": (
                    f"找到 {len(candidates)} 个匹配文件{scope}，已按相关度排序。"
                    "从中选择目标 path，调用 read 读取。"
                ),
                "candidates": candidates,
            }, ensure_ascii=False, indent=2)

    # ── read ──
    elif action == "read":
        path = args.get("path", "").strip()
        if not path:
            return json.dumps({
                "status": "error",
                "message": "read 操作需要提供 path 参数（素材库下的相对路径）。",
            }, ensure_ascii=False)

        filepath = MATERIALS_DIR / path
        if filepath.exists() and filepath.is_file():
            try:
                raw = filepath.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                raw = filepath.read_text(encoding="gbk", errors="replace")

            lines = raw.split("\n")
            total_lines = len(lines)

            offset = max(0, args.get("offset", 0))
            limit = min(max(1, args.get("limit", 200)), 500)

            if offset >= total_lines:
                return json.dumps({
                    "status": "success",
                    "path": path,
                    "file_size": filepath.stat().st_size,
                    "total_lines": total_lines,
                    "offset": offset,
                    "limit": limit,
                    "lines_read": 0,
                    "has_more": False,
                    "content": "",
                    "note": f"offset={offset} 超出文件总行数 {total_lines}，无内容可读取。",
                }, ensure_ascii=False, indent=2)

            sliced = lines[offset:offset + limit]
            content = "\n".join(sliced)
            lines_read = len(sliced)
            has_more = (offset + lines_read) < total_lines

            max_chars = 16000
            char_truncated = len(content) > max_chars
            if char_truncated:
                content = content[:max_chars] + "\n\n...（单次读取字符数已达上限，剩余内容已截断。请缩小 offset/limit 范围重试）"

            return json.dumps({
                "status": "success",
                "path": path,
                "file_size": filepath.stat().st_size,
                "total_lines": total_lines,
                "offset": offset,
                "limit": limit,
                "lines_read": lines_read,
                "has_more": has_more,
                "char_truncated": char_truncated,
                "content": content,
            }, ensure_ascii=False, indent=2)

        # ── 精确路径不存在 → 模糊搜索候选 ──
        candidates = _fuzzy_search(path)

        if not candidates:
            return json.dumps({
                "status": "error",
                "message": (
                    f"路径 '{path}' 不存在，模糊搜索也未找到匹配项。"
                    "用 list 查看素材库全部文件，或用 search 按关键词查找。"
                ),
            }, ensure_ascii=False)

        return json.dumps({
            "status": "not_found",
            "message": (
                f"路径 '{path}' 不存在。找到 {len(candidates)} 个相似文件（见 candidates），"
                "请选择正确的 path 重新调用 read。"
            ),
            "candidates": candidates,
        }, ensure_ascii=False, indent=2)

    return json.dumps({
        "status": "error",
        "message": f"未知操作：'{action}'，可选操作为 list / search / read。",
    }, ensure_ascii=False)
