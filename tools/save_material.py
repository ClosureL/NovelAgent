# encoding: utf-8
"""save_material — 将文本以 Markdown 格式保存到 materials/ 目录。"""

import json
from datetime import datetime
from pathlib import Path
from .state import MATERIALS_DIR


DEFINITION = {
    "type": "function",
    "function": {
        "name": "save_material",
        "description": (
            "将文本保存为 Markdown 文件到 materials/ 目录。"
            "仅当用户明确要求「总结」或「保存」时调用。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "文件名（不含扩展名，自动追加 .md）",
                },
                "content": {
                    "type": "string",
                    "description": "要保存的 Markdown 格式文本内容",
                },
            },
            "required": ["filename", "content"],
        },
    },
}


def execute(args: dict) -> str:
    filename = args.get("filename", "").strip()
    content = args.get("content", "")

    if not filename:
        return json.dumps({
            "status": "error",
            "message": "filename 不能为空",
        }, ensure_ascii=False)

    if not content:
        return json.dumps({
            "status": "error",
            "message": "content 不能为空",
        }, ensure_ascii=False)

    safe_name = "".join(c for c in filename if c.isalnum() or c in "._- ")[:80].strip()
    if not safe_name:
        safe_name = f"material_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    filepath = MATERIALS_DIR / f"{safe_name}.md"
    MATERIALS_DIR.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")

    return json.dumps({
        "status": "success",
        "message": f"已保存至 materials/{filepath.name}",
        "filepath": str(filepath),
    }, ensure_ascii=False)
