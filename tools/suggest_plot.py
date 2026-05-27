# encoding: utf-8
"""suggest_plot — 提供情节发展建议。"""

import json


DEFINITION = {
    "type": "function",
    "function": {
        "name": "suggest_plot",
        "description": "提供情节发展建议。帮助作者突破瓶颈、拓展思路。",
        "parameters": {
            "type": "object",
            "properties": {
                "context": {"type": "string", "description": "当前情节上下文/卡点描述"},
                "direction": {
                    "type": "string",
                    "enum": ["continue", "twist", "branch", "ending"],
                    "description": "建议方向：continue=继续发展, twist=反转, branch=分支路线, ending=结局方案",
                },
                "suggestions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "具体建议列表（3-5条）",
                },
                "recommendation": {"type": "string", "description": "推荐的方案及理由"},
            },
            "required": ["context", "direction", "suggestions"],
        },
    },
}


def execute(args: dict) -> str:
    return json.dumps({
        "status": "success",
        "context": args["context"],
        "direction": args["direction"],
        "suggestions": args.get("suggestions", []),
        "recommendation": args.get("recommendation", ""),
    }, ensure_ascii=False, indent=2)
