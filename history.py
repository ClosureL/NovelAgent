# encoding: utf-8
"""
NovelAgent 对话历史管理。
每次对话保存为独立的 JSON 文件，存放在 saves/{书名}/histories/ 中。
"""

import json
from datetime import datetime
from pathlib import Path


SAVES_DIR = Path(__file__).parent / "saves"


def generate_filename(title: str = "") -> str:
    """生成历史文件名：时间戳_标题。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in title if c.isalnum() or c in "._- ")[:30].strip()
    if safe_title:
        return f"{timestamp}_{safe_title}.json"
    return f"{timestamp}_session.json"


def save_history(
    messages: list[dict],
    novel_state: dict | None = None,
    title: str = "",
    extra: dict | None = None,
    target_dir: Path | None = None,
) -> str:
    """
    保存当前对话历史到独立文件。

    参数：
        messages: 完整的对话消息列表
        novel_state: 小说创作状态（大纲、角色、章节元数据）
        title: 会话标题（用于文件名）
        extra: 额外元数据
        target_dir: 目标目录（默认 saves/{title}/histories/）

    返回：
        保存的文件路径
    """
    if target_dir is None:
        safe = "".join(c for c in title if c.isalnum() or c in "._- ")[:50].strip() or "未命名"
        target_dir = SAVES_DIR / safe / "histories"

    target_dir.mkdir(parents=True, exist_ok=True)
    filename = generate_filename(title)
    filepath = target_dir / filename

    record = {
        "version": 1,
        "created_at": datetime.now().isoformat(),
        "title": title or "未命名会话",
        "message_count": len(messages),
        "messages": messages,
        "novel_state": novel_state,
        "extra": extra or {},
    }

    filepath.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    return str(filepath)


def load_history(filepath: str) -> dict:
    """从文件加载对话历史。"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def list_histories(target_dir: Path | None = None) -> list[dict]:
    """列出指定目录下所有历史记录（按时间倒序）。不传则列出 saves/ 下所有。"""
    dirs_to_scan: list[Path] = []
    if target_dir:
        dirs_to_scan = [target_dir]
    else:
        if SAVES_DIR.exists():
            for d in SAVES_DIR.iterdir():
                hd = d / "histories"
                if hd.is_dir():
                    dirs_to_scan.append(hd)

    records = []
    for hd in dirs_to_scan:
        for f in sorted(hd.glob("*.json"), reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                records.append({
                    "filename": f.name,
                    "filepath": str(f),
                    "created_at": data.get("created_at", ""),
                    "title": data.get("title", "无标题"),
                    "message_count": data.get("message_count", 0),
                })
            except Exception:
                records.append({
                    "filename": f.name,
                    "filepath": str(f),
                    "created_at": "",
                    "title": "（读取失败）",
                    "message_count": 0,
                })

    records.sort(key=lambda r: r["created_at"], reverse=True)
    return records


def delete_history(filename: str) -> bool:
    """删除指定的历史文件。"""
    filepath = Path(filename) if Path(filename).is_absolute() else SAVES_DIR / filename
    if filepath.exists():
        filepath.unlink()
        return True
    return False
