"""
Grasshopper MCP Bridge Server

核心模組:
- client_optimized: 優化的 GH_MCP 客戶端
- guid_registry: 可信 GUID 註冊表
- smart_resolver: 三層防護智能解析器
- auto_debugger: 自動排錯系統
- intent_router: 意圖路由器 (雙軌架構)
- meta_agent: 彈性探索代理 (雙軌架構)
- dual_mode_workflow: 雙軌工作流程
"""

__version__ = "0.3.0"

from .guid_registry import GUIDRegistry
from .smart_resolver import SmartResolver, smart_resolve, ResolutionMethod, ResolutionResult
from .auto_debugger import GHAutoDebugger, validate_before_deploy
from .intent_router import IntentRouter, ProcessingMode, IntentType, RoutingResult
from .meta_agent import MetaAgent, SearchResult, Question, SynthesizedPattern
from .dual_mode_workflow import DualModeWorkflow, WorkflowPhase, WorkflowState
from .workflow_executor import WorkflowExecutor

__all__ = [
    # 原有模組
    "GUIDRegistry",
    "SmartResolver",
    "smart_resolve",
    "ResolutionMethod",
    "ResolutionResult",
    "GHAutoDebugger",
    "validate_before_deploy",
    # 雙軌架構
    "IntentRouter",
    "ProcessingMode",
    "IntentType",
    "RoutingResult",
    "MetaAgent",
    "SearchResult",
    "Question",
    "SynthesizedPattern",
    "DualModeWorkflow",
    "WorkflowPhase",
    "WorkflowState",
    "WorkflowExecutor",
]
