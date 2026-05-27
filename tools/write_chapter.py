# encoding: utf-8
"""write_chapter — 将章节正文保存到作品。"""

import json
from datetime import datetime
from .state import get_state, get_last_assistant_content, parse_chapter_num


DEFINITION = {
    "type": "function",
    "function": {
        "name": "write_chapter",
        "description": "【必须调用】将你之前输出的章节正文保存到作品中。工作位置：在对话中完整输出章节正文之后，会立即调用此工具保存。你只需提供 chapter_number 和 chapter_title，正文会自动从你的上一条消息中提取。如果你输出了章节正文却没有调用此工具，正文将不会被保存为 txt 文件。此工具必须在输出正文的同一轮对话中调用，不得延迟。",
        "parameters": {
            "type": "object",
            "properties": {
                "chapter_number": {"type": "integer", "description": "章节数字编号，如：1"},
                "chapter_title": {"type": "string", "description": "章节标题"},
            },
            "required": ["chapter_number", "chapter_title"],
        },
    },
}


def execute(args: dict) -> str:
    state = get_state()
    ch_num = parse_chapter_num(args.get("chapter_number"))
    if ch_num is None:
        return json.dumps({
            "status": "error",
            "message": "缺少必填参数 chapter_number（章节编号，如：1）",
        }, ensure_ascii=False)

    title = args.get("chapter_title", f"第{ch_num}章")
    content = get_last_assistant_content()

    if not content:
        return json.dumps({
            "status": "error",
            "message": "未找到章节内容。请先在对话中写出章节正文，然后再调用 write_chapter 保存（只需提供 chapter_number 和 chapter_title，不要传 content）。",
        }, ensure_ascii=False)

    is_overwrite = ch_num in state.chapters
    state.chapters[ch_num] = {
        "title": title,
        "content": content,
        "word_count": len(content),
        "written_at": datetime.now().isoformat(),
    }
    state.current_chapter = ch_num

    overwrite_note = "（覆盖了旧版本）" if is_overwrite else ""
    return json.dumps({
        "status": "success",
        "done": True,
        "message": f"第 {ch_num} 章「{title}」已写入{overwrite_note}（{state.chapters[ch_num]['word_count']} 字）\n请立即向用户汇报本章摘要和字数，然后停止调用工具，等待用户下一步指示。",
    }, ensure_ascii=False)
