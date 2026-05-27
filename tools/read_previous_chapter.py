# encoding: utf-8
"""read_previous_chapter — 读取章节正文，保持情节连贯性。"""

import json
from pathlib import Path
from .state import get_state, get_novel_dir


DEFINITION = {
    "type": "function",
    "function": {
        "name": "read_previous_chapter",
        "description": "读取指定章节的完整正文。续写时默认取最新一章回顾前文；需要核对前文细节、伏笔或跨章节内容时可传入 chapter_number 按需再读其他章节。正文优先从内存读取，若内存中无内容则从 saves/ 下的 txt 文件加载。同一轮对话中可按需调用若干次（通常1-2次），无需在每次对话开始时强制调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "chapter_number": {
                    "type": "integer",
                    "description": "要读取的章节编号。续写/回顾最新章时不传；需要查阅特定章节内容（如核对伏笔、前文事件、润色指定章）时传入对应编号。",
                },
            },
            "required": [],
        },
    },
}


def _load_content_from_disk(ch_num: int) -> str | None:
    """从 saves/{书名}/chapters/第N章.txt 读取正文。"""
    novel_dir = get_novel_dir()
    if not novel_dir:
        return None
    txt_path = novel_dir / "chapters" / f"第{ch_num}章.txt"
    if not txt_path.exists():
        return None
    try:
        return txt_path.read_text(encoding="utf-8")
    except Exception:
        return None


def execute(args: dict) -> str:
    state = get_state()
    chapters = state.chapters

    ch_num = args.get("chapter_number")
    if ch_num is not None:
        ch_num = int(ch_num)
        ch = chapters.get(ch_num)
        if ch is None:
            return json.dumps({
                "status": "error",
                "message": f"第 {ch_num} 章不存在。当前已有章节：{sorted(chapters.keys())}",
            }, ensure_ascii=False)
    else:
        if not chapters:
            return json.dumps({
                "status": "info",
                "message": "当前尚无任何已写章节。这是小说的开端，请根据大纲和角色设定开始创作第一章。",
            }, ensure_ascii=False)
        ch_num = max(chapters.keys())
        ch = chapters[ch_num]

    title = ch.get("title", f"第{ch_num}章")

    # 优先从内存读取，若为空则从 txt 文件加载
    content = ch.get("content", "")
    if not content:
        content = _load_content_from_disk(ch_num) or ""

    word_count = ch.get("word_count", len(content))

    if not content:
        return json.dumps({
            "status": "error",
            "message": f"第 {ch_num} 章「{title}」的正文未找到。内存和 saves/ 目录下均无此章内容，无法继续。请检查章节文件是否已被删除。",
            "chapter_number": ch_num,
            "chapter_title": title,
        }, ensure_ascii=False)

    return json.dumps({
        "status": "success",
        "chapter_number": ch_num,
        "chapter_title": title,
        "word_count": len(content),
        "source": "memory" if ch.get("content") else "disk",
        "content": content,
    }, ensure_ascii=False, indent=2)
