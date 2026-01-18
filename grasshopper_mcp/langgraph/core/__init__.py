"""
LangGraph Core Module - 核心系統組件

包含:
- orchestrator: Agent 調度器 (Cascade + Confidence)
- confidence: 信心度評估
- routing: 專家路由
"""

from .orchestrator import (
    AgentOrchestrator,
    OrchestratorConfig,
    OrchestratorResult,
    AgentLevel,
)
from .confidence import (
    ConfidenceEvaluator,
    ConfidenceResult,
    ConfidenceThresholds,
)
from .routing import (
    ExpertRouter,
    TaskType,
    ExpertAgent,
)

# Superpower components (v3.0)
from .intent_router import (
    IntentRouter,
    IntentType,
    IntentClassification,
    IntentPatterns,
    classify_intent,
    is_manual_trigger,
)
from .mode_selector import (
    ModeSelector,
    ModeSelection,
    ModeThresholds,
    ProcessingStrategy,
    select_mode,
)

__all__ = [
    # Orchestrator
    "AgentOrchestrator",
    "OrchestratorConfig",
    "OrchestratorResult",
    "AgentLevel",
    # Confidence
    "ConfidenceEvaluator",
    "ConfidenceResult",
    "ConfidenceThresholds",
    # Routing
    "ExpertRouter",
    "TaskType",
    "ExpertAgent",
    # Intent Router (v3.0)
    "IntentRouter",
    "IntentType",
    "IntentClassification",
    "IntentPatterns",
    "classify_intent",
    "is_manual_trigger",
    # Mode Selector (v3.0)
    "ModeSelector",
    "ModeSelection",
    "ModeThresholds",
    "ProcessingStrategy",
    "select_mode",
]
