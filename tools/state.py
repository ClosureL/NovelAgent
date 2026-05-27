# encoding: utf-8
"""
NovelAgent 共享状态 —— NovelState、持久化、消息引用、工具函数。
"""

import json
import re
from datetime import datetime
from pathlib import Path


PROJECT_DIR = Path(__file__).parent.parent
SAVES_DIR = PROJECT_DIR / "saves"
MATERIALS_DIR = PROJECT_DIR / "materials"
_messages_ref: list[dict] | None = None


def set_messages_ref(ref: list[dict]):
    global _messages_ref
    _messages_ref = ref


def get_last_assistant_content() -> str:
    """从上一条 assistant 消息中提取文本内容。"""
    if not _messages_ref:
        return ""
    for msg in reversed(_messages_ref):
        if msg.get("role") == "assistant" and msg.get("content"):
            return msg["content"]
    return ""


def parse_chapter_num(value) -> int | None:
    """解析章节编号：支持纯数字或'第N章'格式。"""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    if isinstance(value, str):
        m = re.search(r"第\s*(\d+)\s*章", value)
        if m:
            return int(m.group(1))
    return None


def safe_name(text: str, max_len: int = 50) -> str:
    """将文本转为安全的文件名片段。"""
    return "".join(c for c in text if c.isalnum() or c in "._- ")[:max_len].strip() or "未命名"


# ── NovelState ──────────────────────────────────────────────

class NovelState:
    """小说创作运行时状态。"""
    def __init__(self):
        self.outline: dict | None = None
        self.characters: dict[int, dict] = {}
        self.chapters: dict[int, dict] = {}
        self.current_chapter: int = 0

    def to_dict(self) -> dict:
        """返回运行时状态字典。章节不含正文（仅元数据），以节省快照内存。"""
        chapters_meta = {}
        for num, ch in self.chapters.items():
            chapters_meta[num] = {
                "title": ch.get("title", ""),
                "word_count": ch.get("word_count", 0),
                "written_at": ch.get("written_at", ""),
            }
        return {
            "outline": self.outline,
            "characters": self.characters,
            "chapters": chapters_meta,
            "current_chapter": self.current_chapter,
        }

    def to_save_dict(self) -> dict:
        """用于持久化的精简版 —— 章节不含正文，仅元数据。
        角色编号（int key）转为字符串以兼容 JSON。"""
        chapters_meta = {}
        for num, ch in self.chapters.items():
            chapters_meta[str(num)] = {
                "title": ch.get("title", ""),
                "word_count": ch.get("word_count", 0),
                "written_at": ch.get("written_at", ""),
            }
        chars_out = {}
        for cid, info in self.characters.items():
            chars_out[str(cid)] = info
        return {
            "outline": self.outline,
            "characters": chars_out,
            "chapters": chapters_meta,
            "current_chapter": self.current_chapter,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NovelState":
        s = cls()
        s.outline = data.get("outline")
        raw_chars = data.get("characters", {})
        for k, v in raw_chars.items():
            try:
                s.characters[int(k)] = v
            except (ValueError, TypeError):
                s.characters[k] = v
        raw_chapters = data.get("chapters", {})
        if isinstance(raw_chapters, list):
            s.chapters = {ch.get("number", i+1): ch for i, ch in enumerate(raw_chapters)}
        else:
            s.chapters = {}
            for k, v in raw_chapters.items():
                try:
                    s.chapters[int(k)] = v
                except (ValueError, TypeError):
                    s.chapters[k] = v
        s.current_chapter = data.get("current_chapter", 0)
        return s


# 全局单例
_state: NovelState | None = None


def get_state() -> NovelState:
    global _state
    if _state is None:
        _state = NovelState()
    return _state


def set_state(s: NovelState):
    global _state
    _state = s


def reset_state():
    global _state
    _state = NovelState()
    from .world_book import set_world_book
    set_world_book({})


# ── 持久化 ──────────────────────────────────────────────────

def build_state_context() -> str:
    """从当前 novel_state 生成简要项目摘要，用于 /load 时注入 Agent 上下文。"""
    state = get_state()
    if not state.outline:
        return ""

    ol = state.outline
    lines = [
        "[已加载小说项目]",
        f"标题：{ol.get('title', '未设定')}",
        f"类型：{ol.get('genre', '未设定')}",
    ]
    summary = ol.get("summary", "")
    if summary:
        lines.append(f"梗概：{summary}")

    # 新层级结构统计
    vols = ol.get("volumes", [])
    n_vols = len(vols)
    n_arcs = sum(len(v.get("arcs", [])) for v in vols)
    n_chs = sum(
        len(a.get("chapters", []))
        for v in vols for a in v.get("arcs", [])
    )
    lines.append(f"已规划：{n_vols} 卷 / {n_arcs} 弧 / {n_chs} 章")

    # 简要列出卷结构
    for v in vols:
        v_arcs = v.get("arcs", [])
        v_chs = sum(len(a.get("chapters", [])) for a in v_arcs)
        lines.append(f"  第{v['number']}卷「{v.get('title', '')}」：{len(v_arcs)} 弧 / {v_chs} 章")

    if state.characters:
        char_list = "、".join(
            f"#{cid} {info.get('name', '?')}（{info.get('role', '未设定')}）"
            for cid, info in state.characters.items()
        )
        lines.append(f"角色（{len(state.characters)}人）：{char_list}")

    if state.chapters:
        ch_lines = []
        for num in sorted(state.chapters.keys()):
            ch = state.chapters[num]
            ch_lines.append(f"第 {num} 章「{ch.get('title', '')}」（{ch.get('word_count', 0)} 字）")
        lines.append("已写章节：" + "、".join(ch_lines))
    else:
        lines.append("已写章节：无")

    lines.append(f"当前进度：第 {state.current_chapter or '未开始'} 章")
    lines.append("")
    lines.append("以上为当前项目摘要。请根据用户指令和自身判断，调用read_previous_chapter检索对应前文，再按需使用工具检索其他所需信息。")

    return "\n".join(lines)


def get_novel_dir() -> Path | None:
    """返回当前小说的 saves 子目录；大纲未创建则返回 None。"""
    state = get_state()
    if not state or not state.outline:
        return None
    return SAVES_DIR / safe_name(state.outline.get("title", "未命名"))


def save_state_to_file():
    """将当前 novel_state（不含正文）写入 saves/{书名}/novel_state.json。"""
    novel_dir = get_novel_dir()
    if not novel_dir:
        return
    novel_dir.mkdir(parents=True, exist_ok=True)
    state = get_state()
    (novel_dir / "novel_state.json").write_text(
        json.dumps(state.to_save_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_state_from_file(novel_dir: str | Path | None = None) -> NovelState | None:
    """从指定 saves 子目录恢复状态；不传则列出可选小说供交互选择。"""
    if novel_dir:
        fp = SAVES_DIR / novel_dir / "novel_state.json"
    else:
        novels = list_novels()
        if not novels:
            return None
        fp = Path(novels[0]["path"]) / "novel_state.json"

    if not fp.exists():
        return None
    data = json.loads(fp.read_text(encoding="utf-8"))
    return NovelState.from_dict(data)


def export_chapter_txt(ch_num: int | str, output_dir: Path | None = None):
    """将指定章节导出为 .txt 文件到 saves/{书名}/chapters/。"""
    state = get_state()
    ch = state.chapters.get(int(ch_num))
    if not ch:
        return None

    content = ch.get("content")
    if not content:
        return None

    od = output_dir or (get_novel_dir() / "chapters" if get_novel_dir() else None)
    if not od:
        return None
    od.mkdir(parents=True, exist_ok=True)

    for old in od.glob(f"第{ch_num}章_*.txt"):
        try:
            old.unlink()
        except Exception:
            pass

    filepath = od / f"第{ch_num}章.txt"
    filepath.write_text(content, encoding="utf-8")
    return filepath


def export_all_chapters_txt(output_dir: Path | None = None) -> list[Path]:
    """导出所有已写章节为 .txt 文件。"""
    state = get_state()
    novel_dir = get_novel_dir()
    od = output_dir or (novel_dir / "chapters" if novel_dir else None)
    if not od:
        return []

    od.mkdir(parents=True, exist_ok=True)
    paths = []
    for ch_num in sorted(state.chapters.keys()):
        p = export_chapter_txt(ch_num, od)
        if p:
            paths.append(p)
    return paths


def list_novels() -> list[dict]:
    """列出 saves/ 下所有小说项目。"""
    if not SAVES_DIR.exists():
        return []
    novels = []
    for d in sorted(SAVES_DIR.iterdir(), key=lambda x: x.name, reverse=True):
        if not d.is_dir():
            continue
        sf = d / "novel_state.json"
        if sf.exists():
            try:
                data = json.loads(sf.read_text(encoding="utf-8"))
                ol = data.get("outline", {}) or {}
                novels.append({
                    "dir": d.name,
                    "path": str(d),
                    "title": ol.get("title", d.name),
                    "genre": ol.get("genre", ""),
                    "chapter_count": len(data.get("chapters", {})),
                })
            except Exception:
                novels.append({"dir": d.name, "path": str(d), "title": d.name, "genre": "", "chapter_count": 0})
    return novels
