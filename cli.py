# encoding: utf-8
"""
NovelAgent 命令行界面。
提供交互式 REPL 和斜杠命令，连接 agent 与用户。
"""

import sys
import shutil
from config import MODEL_CONFIG, DEFAULT_MODEL
from agents import NovelWriterAgent, NovelPlannerAgent, NovelEditorAgent, NovelExplorerAgent
from tools import (
    NovelState, get_state, reset_state, list_novels, load_state_from_file,
    get_novel_dir, build_state_context, load_world_book_from_file,
)
from history import save_history, delete_history, load_history, list_histories

# 尝试导入 rich，如果不可用则回退到纯文本
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


# ── 终端色彩（无 rich 时的回退） ─────────────────────────
class Colors:
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    BLUE = "\033[34m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


# ── Agent 注册表 ──────────────────────────────────────────

AVAILABLE_AGENTS = {
    "writer":   ("NovelWriter",   NovelWriterAgent),
    "planner":  ("NovelPlanner",  NovelPlannerAgent),
    "editor":   ("NovelEditor",   NovelEditorAgent),
    "explorer": ("NovelExplorer", NovelExplorerAgent),
}
DEFAULT_AGENT = "writer"


def switch_agent(agent, current_key: str, target_key: str, model_name: str = DEFAULT_MODEL):
    """切换到目标 Agent 类型，保留小说状态和 undo 快照。
    Explorer 不加载任何上下文，从零开始；切换离开 explorer 时对话直接丢弃。
    返回 (新 agent 实例, 新 agent_key)，失败时返回 (None, current_key)。"""
    if target_key not in AVAILABLE_AGENTS:
        cprint(f"未知 Agent：{target_key}，可用：{', '.join(AVAILABLE_AGENTS)}", "red")
        return None, current_key

    if target_key == current_key:
        cprint(f"当前已是 {AVAILABLE_AGENTS[current_key][0]} Agent。", "yellow")
        return agent, current_key

    name, agent_cls = AVAILABLE_AGENTS[target_key]
    new_agent = agent_cls(model_name=model_name)

    # Explorer：从零开始，不加载任何上下文，不需要快照
    if target_key == "explorer":
        cprint(f"已切换至 {name} Agent（独立模式，不加载项目上下文，对话不保存）。", "green")
        return new_agent, target_key

    history_loaded = False
    if target_key == "planner":
        # Planner 加载完整对话历史；Writer/Editor 仅加载状态摘要以节省 token
        novel_dir = get_novel_dir()
        if novel_dir:
            history_dir = novel_dir / "histories"
            if history_dir.is_dir():
                hist_files = sorted(history_dir.glob("*.json"), reverse=True)
                if hist_files:
                    try:
                        record = load_history(str(hist_files[0]))
                        history_msgs = record.get("messages", [])
                        history_state = record.get("novel_state", {})
                        if history_state:
                            from tools import set_state
                            set_state(NovelState.from_dict(history_state))
                        new_agent.load_history_context(history_msgs)
                        history_loaded = True
                    except Exception:
                        pass

    if not history_loaded:
        ctx = build_state_context()
        if ctx:
            new_agent.set_state_context(ctx)

    load_world_book_from_file()
    new_agent._load_undo_snapshot()
    if new_agent._snapshot_state is None:
        new_agent.snapshot()

    if history_loaded:
        cprint(f"已切换至 {name} Agent（已恢复 {len(history_msgs)} 条历史消息）。", "green")
    else:
        cprint(f"已切换至 {name} Agent。", "green")
    return new_agent, target_key


def show_agent_list():
    """显示可用 Agent 列表。"""
    if HAS_RICH:
        table = Table(title="可用 Agent", border_style="dim")
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("名称", style="green")
        table.add_column("说明")
        table.add_row("writer", "NovelWriter", "完整小说创作：包含全部规划与写作工具")
        table.add_row("planner", "NovelPlanner", "小说策划顾问：专注情节规划与需求澄清，不含写作工具")
        table.add_row("editor", "NovelEditor", "小说编辑润色：修改已有章节，只读查询大纲/角色/设定")
        table.add_row("explorer", "NovelExplorer", "独立探索：查资料/随笔/记录，即插即用，不保存历史")
        console.print(table)
    else:
        print(f"\n{Colors.BOLD}可用 Agent：{Colors.RESET}")
        print(f"  {Colors.CYAN}writer{Colors.RESET}   - NovelWriter（完整创作：规划 + 写作）")
        print(f"  {Colors.CYAN}planner{Colors.RESET}  - NovelPlanner（策划顾问：规划 + 需求澄清）")
        print(f"  {Colors.CYAN}editor{Colors.RESET}   - NovelEditor（编辑润色：修改已有章节）")
        print(f"  {Colors.CYAN}explorer{Colors.RESET} - NovelExplorer（独立探索：查资料/随笔，即插即弃）")


def cprint(text: str, color: str = "", bold: bool = False):
    """带颜色的打印（兼容 rich 和纯文本）。"""
    if HAS_RICH:
        style = ""
        if bold:
            style += "bold "
        if color:
            style += color
        console.print(text, style=style.strip() or None)
    else:
        prefix = ""
        if bold:
            prefix += Colors.BOLD
        color_map = {
            "cyan": Colors.CYAN, "green": Colors.GREEN,
            "yellow": Colors.YELLOW, "red": Colors.RED,
            "magenta": Colors.MAGENTA, "blue": Colors.BLUE, "dim": Colors.DIM,
        }
        prefix += color_map.get(color, "")
        print(f"{prefix}{text}{Colors.RESET}")


def print_divider(char: str = "─", width: int = 60):
    if HAS_RICH:
        console.print(char * width, style="dim")
    else:
        print(f"{Colors.DIM}{char * width}{Colors.RESET}")


def print_banner():
    banner = r"""
  █▄   █ █▀▀█ ▀█▀ █▀▀ █     █▀▀█ █▀▀▀ █▀▀ █▀▀▄ ▀▀█▀▀
  █ ▀▄ █ █  █  █  █▀▀ █     █▄▄█ █ ▀▄ █▀▀ █  █   █
  █   █▄ █▀▀▀ ▀█▀ ▀▀▀ ▀▀▀   █    ▀▀▀▀ ▀▀▀ ▀  ▀   ▀
  """
    cprint(banner, "cyan", bold=True)
    cprint("  AI 小说创作助手 — 构思、写作、润色，全程陪伴", "dim")


# ── 命令处理 ───────────────────────────────────────────────

def show_help():
    """显示帮助信息。"""
    if HAS_RICH:
        table = Table(title="可用命令", border_style="dim")
        table.add_column("命令", style="cyan", no_wrap=True)
        table.add_column("说明", style="green")
        table.add_row("/help", "显示此帮助信息")
        table.add_row("/save [标题]", "保存当前对话历史")
        table.add_row("/load <编号>", "加载历史对话")
        table.add_row("/list", "列出所有历史记录")
        table.add_row("/state", "查看当前小说创作状态")
        table.add_row("/agent [名称]", "切换 Agent（writer / planner）")
        table.add_row("/agents", "列出所有可用 Agent")
        table.add_row("/undo", "回退最近一次对话的所有改动")
        table.add_row("/compact", "压缩当前对话上下文为摘要并保存")
        table.add_row("/delete <编号>", "删除指定历史记录")
        table.add_row("/new", "开始全新对话（丢弃当前状态）")
        table.add_row("/stream", "切换流式输出模式")
        table.add_row("/model <key>", "切换 LLM 模型（使用 /models 查看可用）")
        table.add_row("/models", "列出所有可用模型")
        table.add_row("/exit, /quit", "退出程序")
        console.print(table)
    else:
        print(f"\n{Colors.CYAN}{Colors.BOLD}可用命令：{Colors.RESET}")
        cmds = [
            ("/help", "显示帮助"),
            ("/save [标题]", "保存当前对话"),
            ("/load <编号>", "加载历史对话"),
            ("/list", "列出历史记录"),
            ("/state", "查看创作状态"),
            ("/agent [名称]", "切换 Agent"),
            ("/agents", "列出可用 Agent"),
            ("/undo", "回退最近一次对话"),
            ("/compact", "压缩上下文并保存"),
            ("/delete <编号>", "删除历史记录"),
            ("/new", "开始全新对话"),
            ("/stream", "切换流式输出"),
            ("/model <key>", "切换 LLM 模型"),
            ("/models", "列出可用模型"),
            ("/exit, /quit", "退出"),
        ]
        for cmd, desc in cmds:
            print(f"  {Colors.CYAN}{cmd:<20}{Colors.RESET} {desc}")


def show_models(current_key: str = ""):
    """显示 MODEL_CONFIG 中所有可用模型。"""
    if HAS_RICH:
        table = Table(title="可用模型", border_style="dim")
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("名称", style="green")
        table.add_column("提供商", style="magenta")
        table.add_column("上下文窗口")
        table.add_column("状态")
        for key, cfg in MODEL_CONFIG.items():
            is_current = "✔" if key == current_key else ""
            has_key = "已配置" if cfg.get("api_key") else "未配置"
            provider = cfg["base_url"].split("://")[-1].split("/")[0]
            cw = f"{cfg['context_window']:,}"
            table.add_row(
                key, cfg.get("display_name", key), provider, cw,
                f"{is_current} {has_key}".strip(),
            )
        console.print(table)
    else:
        print(f"\n{Colors.BOLD}可用模型：{Colors.RESET}")
        for key, cfg in MODEL_CONFIG.items():
            marker = f" {Colors.GREEN}◀ 当前{Colors.RESET}" if key == current_key else ""
            has_key = "已配置" if cfg.get("api_key") else "未配置"
            provider = cfg["base_url"].split("://")[-1].split("/")[0]
            print(
                f"  {Colors.CYAN}{key:<22}{Colors.RESET} "
                f"{cfg.get('display_name', key):<20} "
                f"{provider:<20} {cfg['context_window']:,} tokens  "
                f"[{has_key}]{marker}"
            )


def show_state():
    """显示当前小说创作状态。"""
    state = get_state()
    if HAS_RICH:
        console.print(Panel.fit("📖 当前创作状态", border_style="cyan"))
        if state.outline:
            ol = state.outline
            console.print(f"  标题：{ol.get('title', '未设定')}", style="bold")
            console.print(f"  类型：{ol.get('genre', '')}")
            console.print(f"  梗概：{ol.get('summary', '')}")
            console.print(f"  已规划章节：{len(ol.get('chapters', []))}")
        else:
            console.print("  大纲：未创建", style="dim")

        console.print(f"\n  角色数量：{len(state.characters)}")
        if state.characters:
            for cid, info in state.characters.items():
                console.print(f"    #{cid} {info.get('name', '?')}（{info.get('role', '未设定')}）")

        console.print(f"\n  已写章节：{len(state.chapters)}")
        if state.chapters:
            for num, ch in sorted(state.chapters.items()):
                console.print(f"    第 {num} 章：{ch.get('title', '')}（{ch.get('word_count', 0)} 字）")
        console.print(f"\n  当前进度：第 {state.current_chapter or '未开始'} 章")
    else:
        print(f"\n{Colors.BOLD}📖 当前创作状态{Colors.RESET}")
        if state.outline:
            print(f"  标题：{state.outline.get('title', '未设定')}")
            print(f"  类型：{state.outline.get('genre', '')}")
            print(f"  章节规划：{len(state.outline.get('chapters', []))} 章")
        print(f"  角色：{len(state.characters)} 个")
        print(f"  已写章节：{len(state.chapters)} 章")


def show_novel_list():
    """显示 saves/ 下所有小说项目。"""
    novels = list_novels()
    if not novels:
        cprint("（暂无保存的小说项目）", "dim")
        return

    if HAS_RICH:
        table = Table(title="已保存的小说项目", border_style="dim")
        table.add_column("#", style="dim", width=4)
        table.add_column("书名", style="cyan")
        table.add_column("类型", style="green", width=14)
        table.add_column("章节", justify="right", width=6)
        for i, n in enumerate(novels, 1):
            table.add_row(str(i), n["title"], n.get("genre", ""), str(n["chapter_count"]))
        console.print(table)
    else:
        print(f"\n{Colors.BOLD}已保存的小说项目：{Colors.RESET}")
        for i, n in enumerate(novels, 1):
            print(f"  {Colors.CYAN}{i}.{Colors.RESET} {n['title']}（{n.get('genre', '')}，{n['chapter_count']} 章）")


# ── 主循环 ─────────────────────────────────────────────────

def run_cli(stream_mode: bool = False, planner_mode: bool = False):
    """启动交互式命令行界面。"""
    print_banner()

    current_model = DEFAULT_MODEL

    if planner_mode:
        agent = NovelPlannerAgent(model_name=current_model)
        agent_key = "planner"
    else:
        agent = NovelWriterAgent(model_name=current_model)
        agent_key = DEFAULT_AGENT
    use_stream = stream_mode

    model_display = MODEL_CONFIG[current_model].get("display_name", current_model)
    cprint(f"  模型: {model_display} ({current_model})", "dim")

    # 启动时自动加载最近的小说项目
    novels = list_novels()
    if novels:
        latest = novels[0]
        novel_saved = load_state_from_file(latest["dir"])
        if novel_saved:
            from tools import set_state
            set_state(novel_saved)

            if agent_key == "planner":
                # Planner：加载完整对话历史；Writer/Editor 仅加载状态摘要
                from pathlib import Path as _Path
                history_dir = _Path(latest["path"]) / "histories"
                hist_files = sorted(history_dir.glob("*.json"), reverse=True) if history_dir.is_dir() else []
                if hist_files:
                    try:
                        record = load_history(str(hist_files[0]))
                        history_msgs = record.get("messages", [])
                        history_state = record.get("novel_state", {})
                        if history_state:
                            set_state(NovelState.from_dict(history_state))
                        agent.load_history_context(history_msgs)
                        cprint(
                            f"已自动加载项目：{latest['title']}"
                            f"（{latest['chapter_count']} 章，{len(history_msgs)} 条历史消息）\n",
                            "dim",
                        )
                    except Exception:
                        ctx = build_state_context()
                        if ctx:
                            agent.set_state_context(ctx)
                        cprint(f"已自动加载项目：{latest['title']}（{latest['chapter_count']} 章）\n", "dim")
                else:
                    ctx = build_state_context()
                    if ctx:
                        agent.set_state_context(ctx)
                    cprint(f"已自动加载项目：{latest['title']}（{latest['chapter_count']} 章）\n", "dim")
            else:
                # Writer：仅加载 novel_state，不加载对话历史（节省上下文）
                ctx = build_state_context()
                if ctx:
                    agent.set_state_context(ctx)
                cprint(f"已自动加载项目：{latest['title']}（{latest['chapter_count']} 章）\n", "dim")

            load_world_book_from_file()
            agent._load_undo_snapshot()
            if agent._snapshot_state is None:
                agent.snapshot()
    else:
        cprint("输入 /help 查看命令列表，直接输入文字开始创作对话\n", "dim")

    while True:
        try:
            agent_display = AVAILABLE_AGENTS[agent_key][0]
            if HAS_RICH:
                user_input = Prompt.ask(
                    f"\n[bold cyan]你[/] [dim]({agent_display} | {current_model})[/]"
                ).strip()
            else:
                user_input = input(
                    f"\n{Colors.CYAN}{Colors.BOLD}你{Colors.RESET} "
                    f"[{agent_display} | {current_model}]> "
                ).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n")
            break

        if not user_input:
            continue

        # ── 处理斜杠命令 ──
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd in ("/exit", "/quit", "/q"):
                cprint("再见！期待你的下一部作品。", "yellow")
                break

            elif cmd == "/help":
                show_help()

            elif cmd == "/undo":
                if agent.rollback():
                    cprint("已回退到上一次对话前的状态。", "green")
                else:
                    cprint("没有可用的回退点（只能回退最近一次对话）。", "yellow")

            elif cmd == "/compact":
                stat_before = agent.get_token_stats()
                cprint(f"压缩前上下文: {stat_before['total_tokens']:,} / {stat_before['context_window']:,} tokens ({stat_before['usage_pct']}%)", "yellow")
                cprint("正在生成上下文摘要...", "dim")
                filepath = agent.compact()
                if filepath:
                    stat_after = agent._last_compact_stats or agent.get_token_stats()
                    agent._last_compact_stats = None
                    cprint(f"压缩完成！摘要已保存至: {filepath}", "green")
                    cprint(f"压缩后上下文: {stat_after['total_tokens']:,} tokens（token 统计已重置）", "green")
                else:
                    cprint("压缩失败：当前没有可压缩的对话历史。", "red")

            elif cmd == "/new":
                agent = AVAILABLE_AGENTS[agent_key][1](model_name=current_model)
                reset_state()
                cprint(
                    f"已开始全新对话（{AVAILABLE_AGENTS[agent_key][0]} Agent"
                    f" | {MODEL_CONFIG[current_model].get('display_name', current_model)}）。",
                    "green",
                )

            elif cmd == "/save":
                state = get_state()
                title = arg or (state.outline.get("title") if state.outline else "")
                messages = agent.get_history()
                novel_dir = get_novel_dir()
                target = (novel_dir / "histories") if novel_dir else None
                filepath = save_history(messages, state.to_save_dict(), title=title, target_dir=target)
                cprint(f"对话已保存至：{filepath}", "green")

            elif cmd == "/load":
                novels = list_novels()
                if not novels:
                    cprint("没有可加载的小说项目。", "yellow")
                    continue
                try:
                    idx = int(arg) - 1
                    if idx < 0 or idx >= len(novels):
                        raise ValueError
                except ValueError:
                    cprint("请输入有效的小说编号（使用 /list 查看）", "red")
                    continue

                novel_dir_name = novels[idx]["dir"]

                if agent_key == "planner":
                    # Planner：加载完整对话历史 + novel_state + world_book
                    from pathlib import Path as _Path
                    history_dir = _Path(novels[idx]["path"]) / "histories"
                    hist_files = sorted(history_dir.glob("*.json"), reverse=True) if history_dir.is_dir() else []
                    if not hist_files:
                        cprint("该项目没有对话历史记录。", "yellow")
                        continue

                    record = load_history(str(hist_files[0]))
                    history_msgs = record.get("messages", [])
                    history_state = record.get("novel_state", {})

                    # 恢复 novel_state
                    if history_state:
                        from tools import set_state
                        set_state(NovelState.from_dict(history_state))
                    else:
                        novel_saved = load_state_from_file(novel_dir_name)
                        if novel_saved:
                            from tools import set_state
                            set_state(novel_saved)

                    # 恢复世界书
                    load_world_book_from_file()

                    # 注入完整对话历史（保留当前系统提示）
                    agent.load_history_context(history_msgs)

                    # undo 快照
                    agent._load_undo_snapshot()
                    if agent._snapshot_state is None:
                        agent.snapshot()

                    msg_count = len(history_msgs)
                    cprint(
                        f"已加载：{novels[idx]['title']}"
                        f"（{novels[idx]['chapter_count']} 章，{msg_count} 条历史消息）",
                        "green",
                    )
                else:
                    # Writer：仅恢复 novel_state，不加载对话历史（节省上下文）
                    novel_saved = load_state_from_file(novel_dir_name)
                    if novel_saved:
                        from tools import set_state
                        set_state(novel_saved)
                        ctx = build_state_context()
                        if ctx:
                            agent.set_state_context(ctx)
                        load_world_book_from_file()
                        agent._load_undo_snapshot()
                        if agent._snapshot_state is None:
                            agent.snapshot()
                        cprint(f"已加载：{novels[idx]['title']}（{novels[idx]['chapter_count']} 章）", "green")
                    else:
                        cprint(f"无法加载项目：{novels[idx]['title']}", "red")

            elif cmd == "/list":
                show_novel_list()

            elif cmd == "/delete":
                novels = list_novels()
                try:
                    idx = int(arg) - 1
                    if idx < 0 or idx >= len(novels):
                        raise ValueError
                except ValueError:
                    cprint("请输入有效的小说编号（使用 /list 查看）", "red")
                    continue
                shutil.rmtree(novels[idx]["path"])
                cprint(f"已删除项目：{novels[idx]['title']}", "green")

            elif cmd == "/state":
                show_state()

            elif cmd == "/agent":
                if not arg:
                    cprint("请指定 Agent 名称，使用 /agents 查看可用列表", "yellow")
                else:
                    new_agent, agent_key = switch_agent(agent, agent_key, arg.lower(), current_model)
                    if new_agent:
                        agent = new_agent

            elif cmd == "/agents":
                show_agent_list()

            elif cmd == "/stream":
                use_stream = not use_stream
                status = "开启" if use_stream else "关闭"
                cprint(f"流式输出已{status}", "green")

            elif cmd == "/models":
                show_models(current_model)

            elif cmd == "/model":
                target = arg.strip()
                if not target:
                    cprint("请指定模型 key，使用 /models 查看可用列表", "yellow")
                elif target not in MODEL_CONFIG:
                    cprint(f"未知模型：{target}，使用 /models 查看可用列表", "red")
                elif target == current_model:
                    cprint(f"当前已是 {MODEL_CONFIG[target].get('display_name', target)}。", "yellow")
                elif not MODEL_CONFIG[target].get("api_key"):
                    cprint(f"模型 {target} 未配置 API key，请在 config.py 中填入后重试。", "red")
                else:
                    old_display = MODEL_CONFIG[current_model].get("display_name", current_model)
                    if agent.switch_model(target):
                        current_model = target
                        new_display = MODEL_CONFIG[target].get("display_name", target)
                        cprint(
                            f"已从 {old_display} 切换至 {new_display} "
                            f"（上下文窗口: {agent.context_window:,} tokens）",
                            "green",
                        )
                    else:
                        cprint(f"切换模型失败。", "red")

            else:
                cprint(f"未知命令：{cmd}，输入 /help 查看可用命令", "red")
            continue

        # ── 正常对话 ──
        if agent_key != "explorer":
            agent.snapshot()
        print_divider()
        if HAS_RICH:
            cprint(f"{agent_display}：", "green", bold=True)
        else:
            print(f"{Colors.GREEN}{Colors.BOLD}{agent_display}：{Colors.RESET}")

        if use_stream:
            # 流式输出
            full_response = ""
            for chunk in agent.run_stream(user_input):
                ctype = chunk["type"]
                if ctype == "text":
                    print(chunk["content"], end="", flush=True)
                    full_response += chunk["content"]
                elif ctype == "tool_start":
                    cprint(f"\n  🔧 调用工具：{chunk['name']}...", "dim")
                elif ctype == "tool_result":
                    cprint(f"  ✅ 工具 {chunk['name']} 执行完成", "dim")
                elif ctype == "done":
                    print()  # 换行
                elif ctype == "error":
                    cprint(f"\n  ⚠ {chunk['content']}", "red")
        else:
            # 普通输出
            response = agent.run(user_input)
            if HAS_RICH:
                try:
                    console.print(Markdown(response))
                except Exception:
                    print(response)
            else:
                print(response)

        # Token 统计（优先用 _last_turn_stats，Writer/Editor 刷新时会保存）
        stats = agent._last_turn_stats or agent.get_token_stats()
        agent._last_turn_stats = None
        color = "yellow" if stats["usage_pct"] > 50 else ("red" if stats["usage_pct"] > 80 else "dim")
        cprint(
            f"📊 Token: {stats['total_tokens']:,} / {stats['context_window']:,} "
            f"({stats['usage_pct']}%) | API 调用: {stats['api_calls']}",
            color,
        )

        print_divider()


# ── 入口 ───────────────────────────────────────────────────

def main():
    stream_mode = "--stream" in sys.argv or "-s" in sys.argv
    planner_mode = "--planner" in sys.argv or "-p" in sys.argv

    if "--help" in sys.argv or "-h" in sys.argv:
        print("NovelAgent - AI 小说创作助手")
        print("用法：python cli.py [选项]")
        print("  --stream, -s    默认开启流式输出")
        print("  --planner, -p   以策划模式启动（加载完整对话历史）")
        print("  --help, -h      显示此帮助")
        return

    try:
        run_cli(stream_mode=stream_mode, planner_mode=planner_mode)
    except KeyboardInterrupt:
        print("\n")
        cprint("已退出。", "yellow")


if __name__ == "__main__":
    main()
