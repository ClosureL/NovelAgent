# NovelAgent — AI 小说创作助手

基于 OpenAI SDK 的 AI 小说写作代理，参考 Claude Code 的 Agent 架构设计。支持从构思、大纲、章节写作到润色编辑的全流程辅助，提供 4 个专职 Agent 协同工作。

## 项目结构

```
NovelAgent/
├── cli.py                       # 命令行交互界面（入口）
├── config.py                    # 模型与 API 配置（多提供商支持）
├── history.py                   # 对话历史管理（独立 JSON 文件存储）
├── requirements.txt             # Python 依赖
├── agents/                      # Agent 定义（系统提示 + 工具列表 + 模型）
│   ├── __init__.py
│   ├── base.py                  # 通用 Agent 循环 + 快照/回退/压缩/模型切换
│   ├── novel_writer.py          # NovelWriterAgent — 完整创作（规划 + 写作）
│   ├── novel_planner.py         # NovelPlannerAgent — 策划顾问（规划 + 需求澄清）
│   ├── novel_editor.py          # NovelEditorAgent — 编辑润色（只读查询 + 修订）
│   ├── novel_explorer.py        # NovelExplorerAgent — 独立探索（查资料/随笔，即插即弃）
│   └── prompts/
│       ├── novel_writer.md
│       ├── novel_planner.md
│       ├── novel_editor.md
│       └── novel_explorer.md
├── tools/                       # 工具包（一个工具一个文件，自动发现注册）
│   ├── __init__.py              # 自动发现 → 注册 → 统一入口
│   ├── state.py                 # NovelState、持久化、项目摘要
│   ├── world_book.py            # 世界书/设定集管理（增删改查）
│   ├── create_outline.py        # 大纲管理（卷→弧→章→关键点 四级结构）
│   ├── manage_characters.py     # 角色管理（编号索引，含检索）
│   ├── write_chapter.py         # 保存新章节
│   ├── revise_content.py        # 修改已有章节（含预编辑备份）
│   ├── suggest_plot.py          # 情节发展建议
│   ├── read_material.py         # 读取素材库文件
│   ├── read_previous_chapter.py # 读取章节正文（内存 / 磁盘回退）
│   ├── save_material.py         # 保存 Markdown 到素材库（Explorer 使用）
│   ├── web_search.py            # 联网搜索工具（Mimo 等服务端执行）
│   ├── view_outline.py          # 只读查看大纲（Editor/Explorer 使用）
│   ├── search_characters.py     # 只读检索角色（Editor/Explorer 使用）
│   └── search_world_book.py     # 只读检索世界书（Editor/Explorer 使用）
├── saves/                       # 运行时数据（按小说分子目录）
│   └── {书名}/
│       ├── novel_state.json     # 创作状态元数据
│       ├── world_book.json      # 世界书/设定集
│       ├── chapters/            # 正文 txt 导出
│       │   └── .revision_bak/   # 编辑备份（revise_content 自动生成）
│       ├── histories/           # 对话历史 JSON
│       └── .undo_snapshot.json  # 回退快照
├── materials/                   # 素材库（参考范文、研究笔记等）
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置模型

编辑 `config.py`，支持多个提供商的模型：

```python
DEFAULT_MODEL = "mimo-v2.5-pro"

MODEL_CONFIG = {
    "mimo-v2.5-pro": {
        "model": "mimo-v2.5-pro",
        "display_name": "MiMo V2.5 Pro",
        "base_url": "https://api.xiaomimimo.com/v1",
        "api_key": "your-api-key",
    },
    "deepseek-v4-pro": {
        "model": "deepseek-v4-pro",
        "display_name": "DeepSeek V4 Pro",
        "base_url": "https://api.deepseek.com",
        "api_key": "your-api-key",
    },
}
```

支持任意兼容 OpenAI SDK 的 API，在 `MODEL_CONFIG` 中添加即可。运行时可通过 `/model` 命令切换。

### 3. 启动

```bash
# 普通模式（默认 Writer+stream）
python cli.py

# 策划模式启动
python cli.py --planner
```

## 使用指南

### 四个 Agent

| Agent | 命令 | 职责 | 权限 |
|-------|------|------|------|
| **Writer** | `/agent writer` | 完整小说创作：构思、大纲、写作、修改 | 全部工具 |
| **Planner** | `/agent planner` | 策划顾问：互动式情节规划与需求澄清 | 规划工具，不可写正文 |
| **Editor** | `/agent editor` | 编辑润色：修改已有章节 | 只读查询 + `revise_content`，不可改大纲/角色/设定 |
| **Explorer** | `/agent explorer` | 独立探索：查资料、随笔、笔记 | 只读查询 + `save_material` + 联网搜索，即插即弃 |

Explorer 特性：从零开始（不加载项目上下文）、对话不保存（切换后丢弃）、仅用户明确要求"总结"时输出到 `materials/`。

### 命令列表

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助信息 |
| `/save [标题]` | 保存当前对话 |
| `/load <编号>` | 加载小说项目（`/list` 查看编号） |
| `/list` | 列出所有小说项目 |
| `/state` | 查看当前创作状态 |
| `/agent <名称>` | 切换 Agent（writer / planner / editor / explorer） |
| `/agents` | 列出所有 Agent |
| `/model <key>` | 切换 LLM 模型 |
| `/models` | 列出所有可用模型 |
| `/compact` | 压缩对话上下文为摘要 |
| `/undo` | 回退最近一次对话 |
| `/delete <编号>` | 删除小说项目 |
| `/new` | 开始全新对话 |
| `/stream` | 切换流式输出 |
| `/exit` | 退出程序 |

每轮对话后自动显示 Token 统计和上下文窗口使用率。

### 创作工具

| 类别 | 工具 | 说明 |
|------|------|------|
| 大纲 | `create_outline` | 大纲管理（卷→弧→章→关键点），支持 create/update/delete/view |
| 角色 | `manage_characters` | 角色管理（编号索引），支持 add/update/delete/list/search |
| 设定 | `manage_world_book` | 世界书/设定集，支持 add/update/delete/search/list |
| 情节 | `suggest_plot` | 记录情节发展建议 |
| 写作 | `write_chapter` | 撰写并保存新章节 |
| 编辑 | `revise_content` | 修改已有章节（自动备份到 .revision_bak） |
| 阅读 | `read_previous_chapter` | 读取章节正文（内存优先，磁盘回退） |
| 素材 | `read_material` | 浏览/读取素材库文件 |
| 素材 | `save_material` | 保存 Markdown 到素材库（Explorer 使用） |
| 查询 | `view_outline` | 只读查看大纲（Editor/Explorer 使用） |
| 查询 | `search_characters` | 只读检索角色（Editor/Explorer 使用） |
| 查询 | `search_world_book` | 只读检索世界书（Editor/Explorer 使用） |
| 搜索 | `web_search` | 联网搜索（Mimo 模型服务端执行） |

### 对话历史与持久化

每轮对话结束后自动保存：对话历史 → `saves/{书名}/histories/`，章节正文 → `saves/{书名}/chapters/`，创作状态 → `saves/{书名}/novel_state.json`。

启动时自动加载最近项目。Writer/Editor 仅加载项目摘要（节省 token），Planner 加载完整对话历史。Explorer 不保存任何对话记录。

### 上下文压缩

当对话历史过长时使用 `/compact`：将当前上下文压缩为精简摘要，以标准历史文件格式保存。压缩后对话从摘要继续，token 统计重置。适用于长会话的上下文管理。

## 架构设计

参考 Claude Code 的 Agent 框架：

```
用户输入 → API 调用（携带系统提示 + 工具定义）
       → 模型返回文本 / 工具调用
       → 工具执行 → 结果回传
       → 继续 API 调用
       → 最终文本回复 + 自动保存
```

核心分层：

1. **Agent 层**（`agents/`）— 系统提示 + 工具子集 + 模型配置。继承 `BaseAgent` 获得完整的 run/run_stream/snapshot/rollback/compact/switch_model 能力
2. **Tool 层**（`tools/`）— 每个工具一个文件，包含 `DEFINITION`（OpenAI function calling JSON Schema）和 `execute`。`__init__.py` 自动扫描注册，无需手动维护
3. **State 层**（`tools/state.py`）— 运行时状态、持久化读写、项目摘要生成、章节 txt 导出
4. **History 层**（`history.py`）— 对话历史 JSON 存储与加载

### Undo 机制

每轮对话前自动拍摄快照（含消息计数和 novel_state 元数据）。`/undo` 回退消息 + 恢复状态。`revise_content` 修改章节时额外生成 `.revision_bak` 备份，undo 时自动恢复。

## 扩展指南

### 添加新工具

在 `tools/` 下新建 `.py` 文件，定义 `DEFINITION` 和 `execute(args)` 即可，无需修改任何其他文件：

```python
# tools/my_tool.py
import json
from .state import get_state

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
    return json.dumps({"status": "success", "message": "done"}, ensure_ascii=False)
```

如需创建只读代理工具（限制 Agent 权限），参考 `view_outline.py` / `search_characters.py` / `search_world_book.py` 的委托模式。

### 添加新 Agent

1. 在 `agents/prompts/` 下创建系统提示 `.md` 文件
2. 新建 Agent 文件，继承 `BaseAgent`：

```python
# agents/my_agent.py
from pathlib import Path
from .base import BaseAgent

PROMPT = (Path(__file__).parent / "prompts" / "my_agent.md").read_text(encoding="utf-8")
TOOLS = ["tool_1", "tool_2"]  # 选择需要的工具子集

class MyAgent(BaseAgent):
    content_tool_names = set()  # 写入类工具名，触发后限制后续工具调用

    def __init__(self, model_name=None):
        super().__init__(system_prompt=PROMPT, tool_names=TOOLS, model_name=model_name)
```

3. 在 `agents/__init__.py` 导出，在 `cli.py` 的 `AVAILABLE_AGENTS` 注册。

## 依赖

- `openai` >= 1.0.0 — OpenAI SDK（兼容任何 OpenAI 格式的 API）
- `rich` >= 13.0.0 — 终端美化（可选，未安装时自动回退到纯文本）
