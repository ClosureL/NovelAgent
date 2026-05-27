# encoding: utf-8
"""revise_content — 将修改后的文本保存到指定章节。"""

import json
from datetime import datetime
from .state import get_state, get_last_assistant_content, parse_chapter_num


DEFINITION = {
    "type": "function",
    "function": {
        "name": "revise_content",
        "description": "【必须调用】将你修改后的文本保存到指定章节。工作流程：在对话中输出修改后的完整文本 → 立即调用此工具。你只需提供 chapter_number 和 instruction，正文自动从上一条消息提取。",
        "parameters": {
            "type": "object",
            "properties": {
                "chapter_number": {"type": "integer", "description": "要修改的章节编号，如：1"},
                "instruction": {"type": "string", "description": "修改要求/润色方向"},
            },
            "required": ["chapter_number", "instruction"],
        },
    },
}


def execute(args: dict) -> str:
    ch_num = parse_chapter_num(args.get("chapter_number"))
    if ch_num is None:
        return json.dumps({
            "status": "error",
            "message": "缺少必填参数 chapter_number（章节编号，如：1）",
        }, ensure_ascii=False)

    state = get_state()
    if ch_num not in state.chapters:
        return json.dumps({
            "status": "error",
            "message": f"第 {ch_num} 章不存在。请确认章节编号是否正确（当前已有章节：{sorted(state.chapters.keys())}）",
        }, ensure_ascii=False)

    instruction = args.get("instruction", "")
    revised = get_last_assistant_content()

    if not revised:
        return json.dumps({
            "status": "error",
            "message": "未找到修改后的文本。请先在对话中写出修订内容，然后再调用 revise_content 保存。",
        }, ensure_ascii=False)

    old_title = state.chapters[ch_num].get("title", f"第{ch_num}章")
    old_content = state.chapters[ch_num].get("content", "")

    # 保存修改前备份到 chapters/ 目录（一次性临时文件，先删后建实现覆盖）
    import shutil
    from .state import get_novel_dir
    novel_dir = get_novel_dir()
    bak_path = None
    if novel_dir:
        bak_dir = novel_dir / "chapters" / ".revision_bak"
        if bak_dir.exists():
            shutil.rmtree(bak_dir)
        bak_dir.mkdir(parents=True, exist_ok=True)
        bak_path = bak_dir / f"第{ch_num}章_bak.txt"
        bak_path.write_text(old_content, encoding="utf-8")

    state.chapters[ch_num] = {
        "title": old_title,
        "content": revised,
        "word_count": len(revised),
        "written_at": datetime.now().isoformat(),
    }
    state.current_chapter = ch_num

    return json.dumps({
        "status": "success",
        "done": True,
        "message": f"第 {ch_num} 章「{old_title}」已更新（{len(revised)} 字，instruction: {instruction}）\n请立即向用户汇报修改结果，然后停止调用工具，等待用户下一步指示。",
        "revised_preview": revised[:200] + ("..." if len(revised) > 200 else ""),
        "backup_saved": str(bak_path) if novel_dir else None,
    }, ensure_ascii=False)
