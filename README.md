# NovelAgent — AI 小说创作助手

基于 OpenAI SDK 的多 Agent 小说写作系统，支持 DeepSeek / Claude / GPT-4o / Mimo 等主流模型。提供从构思、大纲、章节写作、润色编辑到资料研究的全流程辅助。

## 功能特征

- **4 个专职 Agent 协同**：Writer（创作）、Planner（策划）、Editor（编辑）、Explorer（资料研究），各司其职，权限分离
- **多模型支持**：兼容所有 OpenAI SDK 格式的 API，运行时 `/model` 一键切换。支持 DeepSeek 思考模式（reasoning_effort）
- **联网搜索**：Mimo 模型原生搜索 + 基于 MCP 协议的 Tavily 搜索，覆盖全部模型提供商
- **结构化大纲**：卷→弧→章→关键点四级大纲体系，配合角色管理和世界书设定集，保持长篇创作一致性
- **流式输出**：逐字生成，实时查看创作过程
- **上下文管理**：对话压缩（Compact）、项目摘要注入（节省 Token）、自动快照与回退（Undo）
- **素材库**：支持模糊搜索、分段读取、编码自动检测的参考材料管理系统
- **即插即用**：新增工具只需一个 `.py` 文件，自动发现注册

## 典型场景

### 场景一：从零开始写一本小说

```bash
python cli.py --planner    # 以策划模式启动
```

与 Planner 讨论故事构思，逐步建立大纲和角色：

> **你**：我想写一本赛博朋克背景的悬疑小说，主角是一个记忆被篡改的黑客。
>
> **Planner**：调用 `create_outline` 建立卷/弧框架 → 调用 `manage_characters` 记录主角设定 → 调用 `suggest_plot` 提供情节方向

大纲就绪后：

> `/agent writer` 切换到 Writer，开始逐章写作。Writer 每写完一章自动调用 `write_chapter` 存档。

### 场景二：修改已完成的章节

```
/agent editor
```

> **你**：第三章的对话太生硬了，帮我润色一下。
>
> **Editor**：调用 `read_previous_chapter` 读取第 3 章 → 输出修订版 → 调用 `revise_content` 保存（自动备份原版到 `.revision_bak/`）

Editor 只能查询和润色，无法修改大纲或角色设定——不用担心它擅自改动你的故事框架。

### 场景三：创作前的资料研究

```
/agent explorer
```

> **你**：搜一下 2024 年诺贝尔文学奖得主及其代表作的写作风格。
>
> **Explorer**：调用 `web_search` 搜索 → 返回实时信息。如需保存，调用 `save_material` 写入素材库。

Explorer 即插即弃——不加载项目上下文、不保存对话历史、不影响正在进行的创作。研究完直接切回 Writer 继续写。

### 场景四：长篇创作中途切换模型

```
/model deepseek-v4-pro
```

写作中途随时切换，根据不同任务需求选择合适的模型。

### 场景五：对话太长，压缩上下文

```
/compact
```

当对话轮数过多、上下文窗口接近上限时，压缩为结构化摘要。压缩后的摘要保留关键信息（大纲结构、角色列表、当前进度），后续对话从此摘要继续。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置模型

编辑 `config.py`：

```python
DEFAULT_MODEL = "mimo-v2.5-pro"

MODEL_CONFIG = {
    "mimo-v2.5-pro": {
        "model": "mimo-v2.5-pro",
        "display_name": "Mimo V2.5 Pro",
        "base_url": "https://api.xiaomimimo.com/v1",
        "api_key": "your-api-key",
        "context_window": 1_000_000,
        "web_search": False,  # True=原生搜索, False=MCP搜索
    },
    "deepseek-v4-pro": {
        "model": "deepseek-v4-pro",
        "display_name": "DeepSeek V4 Pro",
        "base_url": "https://api.deepseek.com",
        "api_key": "your-api-key",
        "context_window": 1_048_576,
    },
    "claude-opus-4-7": {
        "model": "claude-opus-4-7",
        "display_name": "Claude Opus 4.7",
        "base_url": "https://api.anthropic.com/v1",
        "api_key": "your-api-key",
        "context_window": 200_000,
    },
    "gpt-4o": {
        "model": "gpt-4o",
        "display_name": "GPT-4o",
        "base_url": "https://api.openai.com/v1",
        "api_key": "your-api-key",
        "context_window": 128_000,
    },
}

# MCP 搜索服务器配置（非 Mimo 模型的联网搜索依赖）
MCP_CONFIG = {
    "search_servers": [
        "https://mcp.tavily.com/mcp/?tavilyApiKey=YOUR-TAVILY-API-KEY",
    ],
}
```

支持任意兼容 OpenAI SDK 的 API，在 `MODEL_CONFIG` 中添加即可。

### 3. 启动

```bash
# 普通模式（Writer，流式输出）
python cli.py

# 策划模式
python cli.py --planner

# 非流式模式
python cli.py --planner   # Planner 默认非流式
```

## 项目结构

```
NovelAgent/
├── cli.py                       # 命令行交互界面（入口）
├── config.py                    # 模型 / API / MCP 配置
├── history.py                   # 对话历史 JSON 持久化
├── requirements.txt
├── agents/                      # Agent 定义
│   ├── __init__.py
│   ├── base.py                  # BaseAgent — 核心循环 / 快照回退 / 压缩 / 模型切换
│   ├── novel_writer.py          # NovelWriterAgent — 完整创作
│   ├── novel_planner.py         # NovelPlannerAgent — 策划顾问
│   ├── novel_editor.py          # NovelEditorAgent — 编辑润色
│   ├── novel_explorer.py        # NovelExplorerAgent — 独立研究（即插即弃）
│   └── prompts/                 # 系统提示词（Markdown）
├── tools/                       # 工具包（自动发现注册）
│   ├── __init__.py              # 扫描注册 + 统一入口
│   ├── state.py                 # NovelState / 持久化 / 项目摘要
│   ├── world_book.py            # 世界书设定集
│   ├── mcp_client.py            # MCP 协议客户端（JSON-RPC 2.0）
│   ├── create_outline.py        # 大纲管理（卷→弧→章→关键点）
│   ├── manage_characters.py     # 角色管理
│   ├── write_chapter.py         # 保存新章节
│   ├── revise_content.py        # 修订章节（自动备份）
│   ├── suggest_plot.py          # 情节建议
│   ├── read_material.py         # 素材库：搜索 / 列出 / 分段读取
│   ├── read_previous_chapter.py # 读取章节正文
│   ├── save_material.py         # 保存 Markdown 到素材库
│   ├── web_search.py            # 联网搜索（Mimo 原生 + MCP 回退）
│   ├── view_outline.py          # 只读大纲（Editor/Explorer）
│   ├── search_characters.py     # 只读角色检索（Editor/Explorer）
│   └── search_world_book.py     # 只读设定检索（Editor/Explorer）
├── saves/                       # 运行时数据（按小说分子目录）
│   └── {书名}/
│       ├── novel_state.json
│       ├── world_book.json
│       ├── chapters/            # 正文 txt + .revision_bak/
│       ├── histories/           # 对话历史 JSON
│       └── .undo_snapshot.json
├── materials/                   # 素材库（参考文档/范文/笔记）
└── mods/                        # 模组配置（MCP URL 等）
```

## 使用指南

### 四个 Agent

| Agent | 命令 | 职责 | 权限 |
|-------|------|------|------|
| **Writer** | `/agent writer` | 完整小说创作：构思、大纲、写作、修改 | 全部工具 |
| **Planner** | `/agent planner` | 策划顾问：互动式情节规划与需求澄清 | 规划工具，不写正文 |
| **Editor** | `/agent editor` | 编辑润色：修改已有章节 | 只读查询 + `revise_content` |
| **Explorer** | `/agent explorer` | 独立研究：查资料、随笔、笔记 | 只读查询 + `save_material` + `web_search` |

- **Writer / Editor**：每轮后刷新上下文（仅保留系统提示 + 项目摘要），节省 Token
- **Planner**：加载完整对话历史，适合需要上下文的策划讨论
- **Explorer**：从零开始，不加载项目上下文，对话不保存，切换 Agent 后丢弃。适合独立的资料检索和头脑风暴

### 命令列表

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助信息 |
| `/save [标题]` | 保存当前对话 |
| `/load <编号>` | 加载小说项目（`/list` 查看编号） |
| `/list` | 列出所有小说项目 |
| `/state` | 查看当前创作状态（大纲、角色、章节数） |
| `/agent <名称>` | 切换 Agent：`writer` / `planner` / `editor` / `explorer` |
| `/agents` | 列出所有 Agent |
| `/model <key>` | 切换 LLM 模型 |
| `/models` | 列出所有可用模型及配置信息 |
| `/compact` | 压缩对话上下文为摘要 |
| `/undo` | 回退最近一次对话（恢复快照） |
| `/delete <编号>` | 删除小说项目 |
| `/new` | 开始全新对话 |
| `/stream` | 切换流式输出 |
| `/exit` | 退出程序 |

每轮对话后自动显示 Token 统计和上下文窗口使用率。

### 创作工具

| 类别 | 工具 | Agent | 说明 |
|------|------|-------|------|
| 大纲 | `create_outline` | Writer / Planner | 卷→弧→章→关键点，支持增删改查 |
| 角色 | `manage_characters` | Writer / Planner | 角色增删改查，编号索引 |
| 设定 | `manage_world_book` | Writer / Planner | 世界书/设定集管理 |
| 情节 | `suggest_plot` | Writer / Planner | 情节方向建议 |
| 写作 | `write_chapter` | Writer | 保存新章节（自动提取内容） |
| 编辑 | `revise_content` | Writer / Editor | 修订章节（自动备份到 .revision_bak） |
| 阅读 | `read_previous_chapter` | 全部 | 读取章节正文（内存优先） |
| 素材 | `read_material` | 全部 | 模糊搜索 / 列表 / 分段读取（offset+limit） |
| 素材 | `save_material` | Explorer | 保存 Markdown 到素材库 |
| 查询 | `view_outline` | Editor / Explorer | 只读查看大纲 |
| 查询 | `search_characters` | Editor / Explorer | 只读检索角色 |
| 查询 | `search_world_book` | Editor / Explorer | 只读检索设定 |
| 搜索 | `web_search` | Explorer | 联网搜索（Mimo 原生 / MCP Tavily） |

### 联网搜索

**Mimo 模型**（`web_search: True`）：服务端原生搜索，无需额外配置。

**其他模型**（DeepSeek / Claude / GPT-4o / Mimo `web_search: False`）：通过 MCP 协议调用 Tavily 搜索 API。需在 `config.py` 的 `MCP_CONFIG["search_servers"]` 中配置 Tavily URL（含 API Key）。获取免费 API Key：https://tavily.com

### 素材库与分段读取

素材库位于 `materials/` 目录，支持子目录组织。`read_material` 提供三种操作：

- **search**：模糊搜索文件名和路径，按相关度排序
- **list**：列出目录结构（可限定子目录）
- **read**：读取文件内容，支持 `offset`（起始行号）和 `limit`（最大行数，默认 200，上限 500）分段读取大文件，避免上下文窗口溢出

### 对话持久化

每轮对话后自动保存：对话历史 → `saves/{书名}/histories/`，章节正文 → `saves/{书名}/chapters/`，状态 → `saves/{书名}/novel_state.json`。

## 架构设计

参考 Claude Code 的 Agent 框架：

```
用户输入 → API 调用（系统提示 + 工具定义）
        → 模型返回文本 / 工具调用
        → 工具执行 → 结果回传
        → 继续 API 调用
        → 最终文本回复 + 自动保存
```

核心分层：

1. **Agent 层**（`agents/`）— 系统提示 + 工具子集 + 模型配置。继承 `BaseAgent` 获得完整的 run/run_stream/snapshot/rollback/compact/switch_model 能力
2. **Tool 层**（`tools/`）— 每个工具一个文件，`DEFINITION` + `execute()`。`__init__.py` 自动扫描注册
3. **State 层**（`tools/state.py`）— 运行时状态、持久化、项目摘要、章节导出
4. **History 层**（`history.py`）— 对话历史 JSON 存储与加载

### Undo 机制

每轮对话前自动拍摄快照（消息计数 + 文件清单）。`/undo` 回退消息 + 恢复状态 + 清理新增文件。`revise_content` 修改章节时额外生成 `.revision_bak` 备份，undo 时自动恢复。

## 扩展指南

### 添加新工具

在 `tools/` 下新建 `.py` 文件，定义 `DEFINITION` 和 `execute(args)` 即可，无需修改任何其他文件：

```python
# tools/my_tool.py
import json

DEFINITION = {
    "type": "function",
    "function": {
        "name": "my_tool",
        "description": "我的自定义工具",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "参数1"},
            },
            "required": ["param1"],
        },
    },
}

def execute(args: dict) -> str:
    return json.dumps({"status": "success"}, ensure_ascii=False)
```

创建只读代理工具（限制 Agent 权限）时，参考 `view_outline.py`、`search_characters.py`、`search_world_book.py` 的委托模式。

### 添加新 Agent

1. 在 `agents/prompts/` 下创建系统提示 `.md` 文件
2. 新建 Agent 文件，继承 `BaseAgent`：

```python
# agents/my_agent.py
from pathlib import Path
from .base import BaseAgent

PROMPT = (Path(__file__).parent / "prompts" / "my_agent.md").read_text(encoding="utf-8")
TOOLS = ["tool_1", "tool_2"]

class MyAgent(BaseAgent):
    content_tool_names = set()
    refresh_every_turn = False  # 是否每轮后刷新上下文

    def __init__(self, model_name=None):
        super().__init__(system_prompt=PROMPT, tool_names=TOOLS, model_name=model_name)
```

3. 在 `agents/__init__.py` 导出，在 `cli.py` 的 `AVAILABLE_AGENTS` 注册。

## 依赖

- `openai` >= 1.0.0 — OpenAI SDK（兼容所有 OpenAI 格式的 API）
- `rich` >= 13.0.0 — 终端美化（可选，未安装时自动回退纯文本）
