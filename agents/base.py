# encoding: utf-8
"""
NovelAgent 基础 Agent —— 系统提示 + 工具调用循环 + 对话管理。
具体的 agent 通过继承 BaseAgent 并指定 system_prompt / tool_names 来配置。
"""

import json
import copy
from openai import OpenAI
from config import DEFAULT_MODEL, MODEL_CONFIG, GENERATION_CONFIG, THINKING_CONFIG
from tools import get_all_definitions, execute_tool, set_messages_ref
from tools import save_state_to_file, export_all_chapters_txt, get_state, get_novel_dir, NovelState
from history import save_history


class BaseAgent:
    """通用小说写作 Agent 基类，封装 OpenAI SDK 调用与工具执行循环。"""

    # 子类可覆盖：哪些工具触发 content_tool_used 标记
    content_tool_names: set[str] = set()

    # 子类可覆盖：每轮对话后是否自动刷新上下文（仅保留 system prompt + 状态摘要）
    refresh_every_turn: bool = False

    def __init__(self, system_prompt: str, tool_names: list[str], model_name: str | None = None):
        model_name = model_name or DEFAULT_MODEL
        cfg = MODEL_CONFIG[model_name]

        self.client = OpenAI(
            api_key=cfg["api_key"],
            base_url=cfg["base_url"],
        )
        self.model = cfg["model"]
        self.model_name = model_name
        self.context_window = cfg.get("context_window", 128_000)
        self.gen_config = dict(GENERATION_CONFIG)
        self.thinking_config = dict(THINKING_CONFIG)

        all_defs = get_all_definitions()
        self.tool_definitions = [d for d in all_defs if d["function"]["name"] in tool_names]

        self.messages: list[dict] = [
            {"role": "system", "content": system_prompt}
        ]
        set_messages_ref(self.messages)

        self.session_tokens: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "api_calls": 0,
        }

        self._snapshot_state: dict | None = None
        self._snapshot_world_book: dict | None = None
        self._snapshot_msg_count: int = 0
        self._snapshot_files: set[str] = set()
        self._snapshot_has_novel_state: bool = False

        self._last_turn_stats: dict | None = None
        self._last_compact_stats: dict | None = None

    # ── 回退机制 ─────────────────────────────────────────────

    def snapshot(self):
        """保存当前状态快照 + 现有文件清单，用于一次回退。
        无论 novel_state 是否已创建，始终记录消息数量和状态，
        确保纯对话（无工具调用）的轮次也能正常回退。"""
        from tools import get_world_book
        self._snapshot_state = copy.deepcopy(get_state().to_dict())
        self._snapshot_world_book = copy.deepcopy(get_world_book())
        self._snapshot_msg_count = len(self.messages)
        self._snapshot_files = set()
        self._snapshot_has_novel_state = get_state().outline is not None
        novel_dir = get_novel_dir()
        if novel_dir and novel_dir.exists():
            # 清理上一轮 revise 留下的备份（新快照覆盖后已无用）
            import shutil
            bak_dir = novel_dir / "chapters" / ".revision_bak"
            if bak_dir.exists():
                shutil.rmtree(bak_dir)
            for p in novel_dir.rglob("*"):
                if p.is_file():
                    self._snapshot_files.add(str(p))
            snap_file = novel_dir / ".undo_snapshot.json"
            snap_file.write_text(json.dumps({
                "state": self._snapshot_state,
                "world_book": self._snapshot_world_book,
                "msg_count": self._snapshot_msg_count,
                "files": sorted(self._snapshot_files),
                "has_novel_state": self._snapshot_has_novel_state,
            }, ensure_ascii=False), encoding="utf-8")

    def _load_undo_snapshot(self):
        """启动时尝试从磁盘恢复 undo 快照。"""
        novel_dir = get_novel_dir()
        if not novel_dir:
            return
        snap_file = novel_dir / ".undo_snapshot.json"
        if not snap_file.exists():
            return
        try:
            data = json.loads(snap_file.read_text(encoding="utf-8"))
            self._snapshot_state = data.get("state")
            self._snapshot_world_book = data.get("world_book")
            self._snapshot_msg_count = data.get("msg_count", 0)
            self._snapshot_files = set(data.get("files", []))
            self._snapshot_has_novel_state = data.get("has_novel_state", False)
        except Exception:
            pass

    def rollback(self) -> bool:
        """回退到最近一次快照：截断消息、恢复状态、清除新增文件。
        若快照中未含 novel_state（纯对话轮次），仅回退消息历史。"""
        if self._snapshot_msg_count == 0:
            return False

        # 消息回退始终生效
        self.messages = self.messages[:self._snapshot_msg_count]
        set_messages_ref(self.messages)

        # 状态回退：仅在快照包含有效 novel_state 时执行
        if self._snapshot_state is not None and self._snapshot_has_novel_state:
            from tools import set_state, set_world_book, save_world_book_to_file
            set_state(NovelState.from_dict(self._snapshot_state))
            if self._snapshot_world_book is not None:
                set_world_book(copy.deepcopy(self._snapshot_world_book))

            novel_dir = get_novel_dir()
            if novel_dir and novel_dir.exists():
                # 从 .revision_bak 恢复被修改章节的原始正文
                bak_dir = novel_dir / "chapters" / ".revision_bak"
                if bak_dir.exists():
                    state = get_state()
                    for bak_file in sorted(bak_dir.glob("第*章_bak.txt")):
                        try:
                            ch_num = int(bak_file.stem.replace("章_bak", "").lstrip("第"))
                            old_content = bak_file.read_text(encoding="utf-8")
                            if ch_num in state.chapters:
                                state.chapters[ch_num]["content"] = old_content
                                state.chapters[ch_num]["word_count"] = len(old_content)
                        except Exception:
                            pass

                for p in novel_dir.rglob("*"):
                    if p.is_file() and str(p) not in self._snapshot_files:
                        try:
                            p.unlink()
                        except Exception:
                            pass
                snap_file = novel_dir / ".undo_snapshot.json"
                try:
                    snap_file.unlink()
                except Exception:
                    pass

                # 清理 .revision_bak 目录
                if bak_dir.exists():
                    try:
                        import shutil
                        shutil.rmtree(bak_dir)
                    except Exception:
                        pass

            try:
                save_state_to_file()
                save_world_book_to_file()
                export_all_chapters_txt()
            except Exception:
                pass

        self._snapshot_state = None
        self._snapshot_world_book = None
        self._snapshot_msg_count = 0
        self._snapshot_files.clear()
        self._snapshot_has_novel_state = False
        return True

    # ── Token 统计 ─────────────────────────────────────────────

    def _accumulate_tokens(self, usage):
        """累积一次 API 调用的 token 消耗。"""
        if usage is None:
            return
        self.session_tokens["prompt_tokens"] += getattr(usage, "prompt_tokens", 0)
        self.session_tokens["completion_tokens"] += getattr(usage, "completion_tokens", 0)
        self.session_tokens["total_tokens"] += getattr(usage, "total_tokens", 0)
        self.session_tokens["api_calls"] += 1

    def get_token_stats(self) -> dict:
        """返回当前会话的 token 统计摘要。"""
        return {
            **self.session_tokens,
            "context_window": self.context_window,
            "usage_pct": round(
                self.session_tokens["total_tokens"] / self.context_window * 100, 1
            ) if self.context_window else 0,
        }

    # ── 模型切换 ─────────────────────────────────────────────

    def switch_model(self, model_name: str) -> bool:
        """运行时切换模型，更新 client/model/context_window，重置 token 统计。
        返回 True 表示切换成功，False 表示目标模型不存在。"""
        if model_name not in MODEL_CONFIG:
            return False

        cfg = MODEL_CONFIG[model_name]
        self.client = OpenAI(
            api_key=cfg["api_key"],
            base_url=cfg["base_url"],
        )
        self.model = cfg["model"]
        self.model_name = model_name
        self.context_window = cfg.get("context_window", 128_000)
        self.session_tokens = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "api_calls": 0,
        }
        return True

    # ── 对话压缩 ─────────────────────────────────────────────

    def compact(self) -> str:
        """压缩当前对话上下文为摘要，以标准历史文件格式保存，并重置消息列表。
        返回新保存的历史文件路径。"""
        history_msgs = self.get_history()
        if not history_msgs:
            return ""

        # 构造压缩请求
        compact_prompt = (
            "你是一位专业的小说创作助手。请将以下对话记录压缩为一份精简的上下文摘要。\n\n"
            "要求：\n"
            "1. 保留所有已确认的小说设定（标题、类型、梗概、世界观规则、角色设定等）\n"
            "2. 保留大纲结构（卷/弧/章的标题与概要）\n"
            "3. 保留关键的创作决策和尚未解决的问题\n"
            "4. 省略过程性的讨论、选项列举、重复内容\n"
            "5. 以清晰的条目形式组织，便于后续对话直接引用\n\n"
            "--- 对话记录 ---\n"
        )
        conversation_text = ""
        for m in history_msgs:
            role = m.get("role", "?")
            content = m.get("content", "")
            if role == "tool":
                content = content[:200] + "..." if len(content) > 200 else content
            conversation_text += f"[{role}]: {content}\n\n"
        compact_prompt += conversation_text

        # 调用模型生成摘要
        summary_kwargs: dict = {
            "model": self.model,
            "messages": [{"role": "user", "content": compact_prompt}],
            "stream": False,
            "max_tokens": 4096,
        }
        if self.thinking_config.get("enabled"):
            summary_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
        response = self.client.chat.completions.create(**summary_kwargs)
        self._accumulate_tokens(response.usage)
        summary = response.choices[0].message.content or "（压缩摘要生成失败）"

        # 以标准历史文件格式保存摘要
        from datetime import datetime
        state = get_state()
        title = state.outline.get("title", "") if state.outline else ""
        novel_dir = get_novel_dir()
        target = (novel_dir / "histories") if novel_dir else None
        compact_messages = [
            {"role": "assistant", "content": summary}
        ]
        filepath = save_history(
            compact_messages,
            novel_state=state.to_save_dict(),
            title=title or "未命名",
            target_dir=target,
        )

        # 重置消息列表：系统提示 + 压缩摘要
        sys_msg = self.messages[0] if self.messages else None
        self.messages = [sys_msg] if sys_msg else []
        self.messages.append({
            "role": "assistant",
            "content": f"[上下文压缩摘要 — {datetime.now().strftime('%Y-%m-%d %H:%M')}]\n\n{summary}"
        })
        set_messages_ref(self.messages)

        # 重置 token 统计（重置前保存，供 cli.py 展示压缩消耗）
        self._last_compact_stats = self.get_token_stats()
        self.session_tokens = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "api_calls": 0,
        }

        return filepath

    # ── 对话管理 ─────────────────────────────────────────────

    def add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(
        self, content: str | None,
        tool_calls: list | None = None,
        reasoning_content: str | None = None,
    ):
        msg: dict = {"role": "assistant"}
        if content:
            msg["content"] = content
        if tool_calls:
            msg["tool_calls"] = tool_calls
        if reasoning_content:
            msg["reasoning_content"] = reasoning_content
        self.messages.append(msg)

    def add_tool_result(self, tool_call_id: str, tool_name: str, content: str):
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": content,
        })

    def _auto_save(self):
        """每轮对话结束时自动保存到 saves/{书名}/。"""
        state = get_state()
        title = state.outline.get("title", "") if state.outline else ""
        novel_dir = get_novel_dir()

        try:
            target = (novel_dir / "histories") if novel_dir else None
            save_history(
                self.get_history(), state.to_save_dict(), title=title, target_dir=target,
            )
        except Exception:
            pass

        try:
            export_all_chapters_txt()
        except Exception:
            pass

    def _auto_save_text_as_chapter(self, text: str):
        """兜底机制：模型忘记调用 write_chapter 时自动保存正文并持久化。
        仅对包含 write_chapter 工具的 agent 生效，planner 等纯策划 agent 不触发。"""
        tool_names = {d["function"]["name"] for d in self.tool_definitions}
        if "write_chapter" not in tool_names:
            return
        state = get_state()
        if not state.outline or len(text) < 500:
            return
        next_ch = max(state.chapters.keys()) + 1 if state.chapters else 1
        try:
            execute_tool("write_chapter", {
                "chapter_number": next_ch,
                "chapter_title": f"第{next_ch}章",
            })
            save_state_to_file()
            export_all_chapters_txt()
        except Exception:
            pass

    def get_history(self) -> list[dict]:
        """返回完整对话历史（不含 system prompt）。"""
        return [m for m in self.messages if m["role"] != "system"]

    def load_history_context(self, history_messages: list[dict]):
        """加载完整对话历史，保留当前系统提示，追加历史中的非系统消息。
        用于 planner 等需要完整上下文的 agent 恢复会话。"""
        sys_msg = self.messages[0] if self.messages else None
        self.messages = [sys_msg] if sys_msg else []
        for m in history_messages:
            if m.get("role") != "system":
                self.messages.append(m)
        set_messages_ref(self.messages)

    def set_state_context(self, context: str):
        """注入项目状态摘要为系统消息，替代加载完整对话历史。
        重置消息列表为系统提示 + 状态上下文，节省 token 消耗。"""
        sys_msg = self.messages[0] if self.messages else None
        self.messages = [sys_msg] if sys_msg else []
        if context:
            self.messages.append({"role": "system", "content": context})
        set_messages_ref(self.messages)

    def _refresh_context(self):
        """每轮对话后刷新上下文：仅保留系统提示 + 项目状态摘要。
        由 refresh_every_turn 控制，Writer/Editor 启用，Planner/Explorer 不启用。
        刷新前保存本轮 token 统计到 _last_turn_stats，供 cli.py 展示。"""
        from tools import build_state_context

        ctx = build_state_context()
        if not ctx:
            return
        self._last_turn_stats = self.get_token_stats()
        self.set_state_context(ctx)
        self.session_tokens = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "api_calls": 0,
        }

    # ── API 调用 ─────────────────────────────────────────────

    def _build_request_kwargs(self, stream: bool = False, tools: list | None = ...) -> dict:
        """构建 API 请求参数。tools=None 表示不传递 tools 字段（强制纯文本回复）。"""
        kwargs: dict = {
            "model": self.model,
            "messages": self.messages,
            "stream": stream,
            **self.gen_config,
        }
        if tools is ...:
            tools = self.tool_definitions
        if tools:
            kwargs["tools"] = tools

        if self.thinking_config.get("enabled"):
            kwargs["reasoning_effort"] = self.thinking_config["reasoning_effort"]
            kwargs["extra_body"] = {"thinking": {"type": "enabled"}}

        return kwargs

    # ── Agent 主循环 ─────────────────────────────────────────

    def run(self, user_input: str | None = None) -> str:
        """执行一次 agent 交互。"""
        if user_input:
            self.add_user_message(user_input)

        max_turns = 50
        content_tool_used = False
        chapters_before = len(get_state().chapters)

        for _ in range(max_turns):
            tools = None if content_tool_used else ...
            kwargs = self._build_request_kwargs(stream=False, tools=tools)
            try:
                response = self.client.chat.completions.create(**kwargs)
            except Exception as e:
                return f"（API 调用失败：{e}）"
            self._accumulate_tokens(response.usage)
            choice = response.choices[0]
            message = choice.message

            text_content = message.content or ""
            reasoning = getattr(message, "reasoning_content", None) or None

            if message.tool_calls:
                raw_tool_calls = [
                    {
                        "id": tc.id,
                        "type": tc.type if hasattr(tc, "type") else "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    if hasattr(tc, "function")
                    else {
                        "id": tc.id,
                        "type": tc.type,
                        "web_search": getattr(tc, "web_search", {}),
                    }
                    for tc in message.tool_calls
                ]
                self.add_assistant_message(
                    text_content, tool_calls=raw_tool_calls, reasoning_content=reasoning,
                )

                for tc in message.tool_calls:
                    if not hasattr(tc, "function"):
                        # web_search 等服务端执行工具：仅作观察占位
                        self.add_tool_result(
                            tc.id, "web_search",
                            json.dumps({"status": "executed", "note": "服务端已执行搜索"}, ensure_ascii=False),
                        )
                        continue

                    tool_name = tc.function.name
                    try:
                        arguments = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}
                    result = execute_tool(tool_name, arguments)
                    self.add_tool_result(tc.id, tool_name, result)

                    if tool_name in self.content_tool_names and '"status": "success"' in result:
                        content_tool_used = True

                save_state_to_file()
                continue
            else:
                self.add_assistant_message(text_content, reasoning_content=reasoning)
                chapters_after = len(get_state().chapters)
                chapter_saved = chapters_after > chapters_before
                if not content_tool_used and not chapter_saved:
                    self._auto_save_text_as_chapter(text_content)
                self._auto_save()
                if self.refresh_every_turn:
                    self._refresh_context()
                return text_content

        return "（已达到最大工具调用轮数，请简化你的请求。）"

    def run_stream(self, user_input: str | None = None):
        """流式执行 agent 交互，边生成边输出。"""
        if user_input:
            self.add_user_message(user_input)

        max_turns = 50
        content_tool_used = False
        chapters_before = len(get_state().chapters)

        for _ in range(max_turns):
            tools = None if content_tool_used else ...
            kwargs = self._build_request_kwargs(stream=True, tools=tools)
            stream = self.client.chat.completions.create(**kwargs)

            collected_content = ""
            collected_reasoning = ""
            collected_tool_calls: list[dict] = []
            current_tool_index = -1
            stream_usage = None

            for chunk in stream:
                if hasattr(chunk, "usage") and chunk.usage:
                    stream_usage = chunk.usage

                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                if delta.content:
                    collected_content += delta.content
                    yield {"type": "text", "content": delta.content}

                if getattr(delta, "reasoning_content", None):
                    collected_reasoning += delta.reasoning_content

                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx > current_tool_index:
                            current_tool_index = idx
                            tc_type = getattr(tc_delta, "type", "function")
                            if tc_type == "web_search":
                                collected_tool_calls.append({
                                    "id": tc_delta.id or "",
                                    "type": "web_search",
                                })
                            else:
                                collected_tool_calls.append({
                                    "id": tc_delta.id or "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""},
                                })
                        if tc_delta.id:
                            collected_tool_calls[idx]["id"] = tc_delta.id
                        if hasattr(tc_delta, "function") and tc_delta.function:
                            if tc_delta.function.name:
                                collected_tool_calls[idx].setdefault("function", {})["name"] = \
                                    collected_tool_calls[idx].get("function", {}).get("name", "") + tc_delta.function.name
                            if tc_delta.function.arguments:
                                collected_tool_calls[idx].setdefault("function", {})["arguments"] = \
                                    collected_tool_calls[idx].get("function", {}).get("arguments", "") + tc_delta.function.arguments

            self._accumulate_tokens(stream_usage)
            if stream_usage is None:
                self.session_tokens["api_calls"] += 1

            if collected_tool_calls:
                text = collected_content.strip()
                reasoning = collected_reasoning or None
                self.add_assistant_message(
                    text or None, tool_calls=collected_tool_calls, reasoning_content=reasoning,
                )

                for i, tc in enumerate(collected_tool_calls):
                    if tc.get("type") == "web_search":
                        # 服务端执行工具：仅观察占位
                        tool_name = "web_search"
                        yield {"type": "tool_start", "name": tool_name, "arguments": {}}
                        result = json.dumps({"status": "executed", "note": "服务端已执行搜索"}, ensure_ascii=False)
                        yield {"type": "tool_result", "name": tool_name, "content": result}
                        raw_tcs = self.messages[-1].get("tool_calls", [])
                        tc_id = raw_tcs[i]["id"] if i < len(raw_tcs) else tc["id"]
                        self.add_tool_result(tc_id, tool_name, result)
                        continue

                    tool_name = tc["function"]["name"]
                    try:
                        arguments = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        arguments = {}
                    yield {"type": "tool_start", "name": tool_name, "arguments": arguments}
                    result = execute_tool(tool_name, arguments)
                    yield {"type": "tool_result", "name": tool_name, "content": result}
                    raw_tcs = self.messages[-1].get("tool_calls", [])
                    tc_id = raw_tcs[i]["id"] if i < len(raw_tcs) else tc["id"]
                    self.add_tool_result(tc_id, tool_name, result)

                    if tool_name in self.content_tool_names and '"status": "success"' in result:
                        content_tool_used = True

                save_state_to_file()
                continue
            else:
                reasoning = collected_reasoning or None
                self.add_assistant_message(collected_content, reasoning_content=reasoning)
                chapters_after = len(get_state().chapters)
                chapter_saved = chapters_after > chapters_before
                if not content_tool_used and not chapter_saved:
                    self._auto_save_text_as_chapter(collected_content)
                self._auto_save()
                if self.refresh_every_turn:
                    self._refresh_context()
                yield {"type": "done", "content": collected_content}
                return

        yield {"type": "error", "content": "已达到最大工具调用轮数，请简化你的请求。"}
