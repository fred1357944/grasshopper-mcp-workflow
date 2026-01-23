"""
Grasshopper MCP Bridge Server

核心模組:
- client_optimized: 優化的 GH_MCP 客戶端
- guid_registry: 可信 GUID 註冊表
- smart_resolver: 三層防護智能解析器
- auto_debugger: 自動排錯系統
"""

__version__ = "0.2.0"

from .guid_registry import GUIDRegistry
from .smart_resolver import SmartResolver, smart_resolve, ResolutionMethod, ResolutionResult
from .auto_debugger import GHAutoDebugger, validate_before_deploy

__all__ = [
    "GUIDRegistry",
    "SmartResolver",
    "smart_resolve",
    "ResolutionMethod",
    "ResolutionResult",
    "GHAutoDebugger",
    "validate_before_deploy",
]
