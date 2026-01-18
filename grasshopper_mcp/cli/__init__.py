"""
CLI Module - 命令列介面

提供 Superpower slash commands 支援：
- /think: Think-Partner 蘇格拉底式探索
- /brainstorm: 三階段腦力激盪
- /workflow: 確定性四階段管線
- /meta: Meta-Agent 動態工具創建
"""

from .commands import (
    CommandHandler,
    CommandResult,
    CommandType,
    run_cli,
    main,
)

__all__ = [
    "CommandHandler",
    "CommandResult",
    "CommandType",
    "run_cli",
    "main",
]
