# encoding: utf-8
"""read_material — 从素材库读取素材文件。"""

import json
import os
from pathlib import Path
from .state import MATERIALS_DIR


DEFINITION = {
    "type": "function",
    "function": {
        "name": "read_material",
        "description": "从素材库（materials/ 目录）读取素材文件内容。可浏览文件列表或读取指定文件。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "read"],
                    "description": "操作类型：list=浏览素材库文件列表, read=读取指定文件内容",
                },
                "path": {
                    "type": "string",
                    "description": "read 操作时必填：素材库下的相对文件路径（如 'samples/范文.txt'）",
                },
            },
            "required": ["action"],
        },
    },
}


def execute(args: dict) -> str:
    action = args["action"]
    MATERIALS_DIR.mkdir(parents=True, exist_ok=True)

    if action == "list":
        if not MATERIALS_DIR.exists():
            return json.dumps({"status": "info", "message": "素材库为空", "files": []}, ensure_ascii=False)

        files = []
        for root, _, filenames in os.walk(MATERIALS_DIR):
            for fname in filenames:
                full = Path(root) / fname
                rel = full.relative_to(MATERIALS_DIR)
                size = full.stat().st_size
                files.append({"path": str(rel).replace("\\", "/"), "size": size})

        return json.dumps({
            "status": "success",
            "message": f"素材库共 {len(files)} 个文件",
            "files": sorted(files, key=lambda x: x["path"]),
        }, ensure_ascii=False, indent=2)

    elif action == "read":
        path = args.get("path", "")
        if not path:
            return json.dumps({"status": "error", "message": "请提供要读取的文件路径（素材库下的相对路径）"}, ensure_ascii=False)

        filepath = MATERIALS_DIR / path
        if not filepath.exists():
            return json.dumps({"status": "error", "message": f"文件不存在：{path}"}, ensure_ascii=False)
        if not filepath.is_file():
            return json.dumps({"status": "error", "message": f"路径不是文件：{path}"}, ensure_ascii=False)

        try:
            content = filepath.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = filepath.read_text(encoding="gbk", errors="replace")

        max_chars = 12000
        truncated = len(content) > max_chars
        if truncated:
            content = content[:max_chars] + "\n\n...（内容过长，已截断，剩余部分未展示）"

        return json.dumps({
            "status": "success",
            "path": path,
            "file_size": filepath.stat().st_size,
            "char_count": len(content),
            "truncated": truncated,
            "content": content,
        }, ensure_ascii=False, indent=2)

    return json.dumps({"status": "error", "message": f"未知操作：{action}"}, ensure_ascii=False)
