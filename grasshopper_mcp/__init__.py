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
- knowledge_base: 連接模式知識庫
- learning_agent: 自動學習代理
- vision_diagnostic_client: Vision 診斷客戶端 (整合 GH_MCP_Vision)
- experience_db: 三層知識庫 (Golden → Community → Personal)
- hitl_collaborator: HITL 協作互動
- experience_driven_workflow: 經驗驅動工作流
"""

__version__ = "0.4.0"

from .guid_registry import GUIDRegistry
from .smart_resolver import SmartResolver, smart_resolve, ResolutionMethod, ResolutionResult
from .auto_debugger import GHAutoDebugger, validate_before_deploy
from .intent_router import IntentRouter, ProcessingMode, IntentType, RoutingResult
from .meta_agent import MetaAgent, SearchResult, Question, SynthesizedPattern
from .dual_mode_workflow import DualModeWorkflow, WorkflowPhase, WorkflowState
from .workflow_executor import WorkflowExecutor
from .knowledge_base import ConnectionKnowledgeBase, lookup, get_guid, is_cmd_ok
from .learning_agent import LearningAgent
from .vision_diagnostic_client import (
    VisionDiagnosticClient,
    ExecutionDiagnosticHelper,
    DiagnosticLevel,
    DiagnosticResult
)
from .experience_db import (
    ExperienceDB,
    Experience,
    KnowledgeResult,
    KnowledgeSource,
    DomainKnowledge,
    GoldenKnowledgeBuilder,
)
from .hitl_collaborator import (
    HITLCollaborator,
    QuestionType,
    Question,
    Answer,
    CollectedKnowledge,
)
from .experience_driven_workflow import (
    ExperienceDrivenWorkflow,
    WorkflowResult,
    ParsedRequest,
)
from .unified_handler import (
    UnifiedHandler,
    HandleResult,
    Layer,
    quick_handle,
    check_layer,
)
from .claude_plan_generator import (
    ClaudePlanGenerator,
    ExecutionPlan,
    generate_plan,
)
from .design_workflow_v2 import (
    DesignWorkflowV2,
    run_design_workflow,
)

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
    # 學習系統
    "ConnectionKnowledgeBase",
    "lookup",
    "get_guid",
    "is_cmd_ok",
    "LearningAgent",
    # Vision 診斷
    "VisionDiagnosticClient",
    "ExecutionDiagnosticHelper",
    "DiagnosticLevel",
    "DiagnosticResult",
    # 三層知識庫
    "ExperienceDB",
    "Experience",
    "KnowledgeResult",
    "KnowledgeSource",
    "DomainKnowledge",
    "GoldenKnowledgeBuilder",
    # HITL 協作
    "HITLCollaborator",
    "QuestionType",
    "Question",
    "Answer",
    "CollectedKnowledge",
    # 經驗驅動工作流
    "ExperienceDrivenWorkflow",
    "WorkflowResult",
    "ParsedRequest",
    # 三層架構統一入口
    "UnifiedHandler",
    "HandleResult",
    "Layer",
    "quick_handle",
    "check_layer",
    # Layer 2 計畫生成器
    "ClaudePlanGenerator",
    "ExecutionPlan",
    "generate_plan",
    # Layer 3 設計工作流程
    "DesignWorkflowV2",
    "run_design_workflow",
]
