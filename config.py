# encoding: utf-8

DEFAULT_MODEL = "mimo-v2.5-pro"

# 模型配置
MODEL_CONFIG = {
    "deepseek-v4-pro": {
        "model": "deepseek-v4-pro",
        "display_name": "DeepSeek V4 Pro",
        "base_url": "https://api.deepseek.com",
        "api_key": "",
        "context_window": 1_048_576,
    },
    "claude-opus-4-7": {
        "model": "claude-opus-4-7",
        "display_name": "Claude Opus 4.7",
        "base_url": "https://api.anthropic.com/v1",
        "api_key": "",
        "context_window": 200_000,
    },
    "gpt-4o": {
        "model": "gpt-4o",
        "display_name": "GPT-4o",
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "context_window": 128_000,
    },
    "mimo-v2.5-pro": {
        "model": "mimo-v2.5-pro",
        "display_name": "Mimo V2.5 Pro",
        "base_url": "https://api.xiaomimimo.com/v1",
        "api_key": "",
        "context_window": 1_000_000,
        "web_search": False,  # True=原生服务端搜索, False=回退MCP搜索
    },
}

# 生成参数
GENERATION_CONFIG = {
    "temperature": 0.9,
    "max_tokens": 32000,
    "top_p": 0.9,
}

# DeepSeek 思考模式配置可用max，Mimo最高为high
THINKING_CONFIG = {
    "enabled": True,
    "reasoning_effort": "high",  # high / max
}

# MCP 搜索服务器配置 (目前仅支持tavily)
MCP_CONFIG = {
    "search_servers": [
        "https://mcp.tavily.com/mcp/?tavilyApiKey=YOUR-API-KEY",
    ],
}
