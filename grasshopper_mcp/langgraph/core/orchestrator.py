"""
Agent Orchestrator - 智慧調度器

實現 Cascade + Confidence + Expert Routing 的組合策略

架構:
┌─────────────────────────────────────────────────────────────┐
│                     Agent Orchestrator                       │
├─────────────────────────────────────────────────────────────┤
│  Level 0: Rule-Based Agent                                   │
│  ├─ 快速規則匹配                                             │
│  ├─ 嵌入向量查詢                                             │
│  └─ 信心度評估 → 通過/升級                                   │
├─────────────────────────────────────────────────────────────┤
│  Level 1: ML-Enhanced Agent                                  │
│  ├─ 模式匹配 (graph_learner)                                 │
│  ├─ 相似組件推薦                                             │
│  └─ 信心度評估 → 通過/升級                                   │
├─────────────────────────────────────────────────────────────┤
│  Level 2: AI-Powered Agent (Gemini Review)                   │
│  ├─ Gemini 語義驗證                                          │
│  ├─ 自動修復建議                                             │
│  └─ 信心度評估 → 通過/人工                                   │
├─────────────────────────────────────────────────────────────┤
│  Level 3: Human-in-the-Loop                                  │
│  └─ 人工確認                                                 │
└─────────────────────────────────────────────────────────────┘
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Callable, Awaitable
from pathlib import Path
import asyncio
import json
import logging

from .confidence import ConfidenceEvaluator, ConfidenceResult, ConfidenceThresholds
from .routing import ExpertRouter, TaskType, ExpertAgent

logger = logging.getLogger(__name__)


class AgentLevel(IntEnum):
    """Agent 層級"""
    RULE_BASED = 0      # 規則驅動
    ML_ENHANCED = 1     # ML 增強
    AI_POWERED = 2      # AI 驅動
    HUMAN = 3           # 人工介入


@dataclass
class OrchestratorConfig:
    """調度器配置"""
    # 層級配置
    max_level: AgentLevel = AgentLevel.AI_POWERED
    enable_human_fallback: bool = True

    # 信心度門檻
    confidence_thresholds: ConfidenceThresholds = field(
        default_factory=ConfidenceThresholds
    )

    # 超時配置 (毫秒)
    level_timeouts: Dict[AgentLevel, int] = field(default_factory=lambda: {
        AgentLevel.RULE_BASED: 1000,
        AgentLevel.ML_ENHANCED: 3000,
        AgentLevel.AI_POWERED: 30000,
    })

    # 嵌入向量路徑
    embeddings_path: Optional[str] = None


@dataclass
class OrchestratorResult:
    """調度結果"""
    success: bool
    result: Any
    level_used: AgentLevel
    confidence: float
    escalation_path: List[AgentLevel]
    execution_time_ms: float
    details: Dict = field(default_factory=dict)

    @property
    def was_escalated(self) -> bool:
        return len(self.escalation_path) > 1

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "level_used": self.level_used.name,
            "confidence": self.confidence,
            "escalation_path": [l.name for l in self.escalation_path],
            "execution_time_ms": self.execution_time_ms,
            "was_escalated": self.was_escalated,
            "details": self.details,
        }


class AgentOrchestrator:
    """
    智慧 Agent 調度器

    實現 Cascade + Confidence + Expert Routing 的組合策略:

    1. Cascade (串聯): 從低層級開始，信心不足時升級到高層級
    2. Confidence: 每層都有信心度評估，決定是否通過
    3. Expert Routing: 根據任務類型路由到專門的 Agent

    Usage:
        orchestrator = AgentOrchestrator(OrchestratorConfig(
            embeddings_path="knowledge/component_embeddings.json"
        ))

        # 執行任務
        result = await orchestrator.execute(
            task="連接 Number Slider 到 Box 的 X 參數",
            context={"stage": "connectivity"}
        )

        if result.success:
            print(f"成功，使用層級: {result.level_used.name}")
            print(f"信心度: {result.confidence:.2f}")
    """

    def __init__(self, config: OrchestratorConfig = None):
        self.config = config or OrchestratorConfig()
        self.confidence_evaluator = ConfidenceEvaluator(
            thresholds=self.config.confidence_thresholds,
            embeddings_path=self.config.embeddings_path
        )
        self.router = ExpertRouter()

        # Agent handlers (可被外部註冊)
        self.handlers: Dict[AgentLevel, Callable] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        """註冊預設 handlers"""
        self.handlers[AgentLevel.RULE_BASED] = self._rule_based_handler
        self.handlers[AgentLevel.ML_ENHANCED] = self._ml_enhanced_handler
        self.handlers[AgentLevel.AI_POWERED] = self._ai_powered_handler

    def register_handler(
        self,
        level: AgentLevel,
        handler: Callable[..., Awaitable[Any]]
    ):
        """註冊自定義 handler"""
        self.handlers[level] = handler

    async def execute(
        self,
        task: str,
        context: Optional[Dict] = None,
        start_level: AgentLevel = AgentLevel.RULE_BASED
    ) -> OrchestratorResult:
        """
        執行任務，使用 Cascade 策略

        Args:
            task: 任務描述
            context: 上下文信息
            start_level: 起始層級

        Returns:
            OrchestratorResult
        """
        import time
        start_time = time.time()

        context = context or {}
        escalation_path = []
        current_level = start_level
        last_result = None
        last_confidence = 0.0

        while current_level <= self.config.max_level:
            escalation_path.append(current_level)
            logger.info(f"[Orchestrator] 執行層級 {current_level.name}")

            try:
                # 獲取 handler
                handler = self.handlers.get(current_level)
                if not handler:
                    logger.warning(f"[Orchestrator] 未找到層級 {current_level.name} 的 handler")
                    current_level = AgentLevel(current_level + 1)
                    continue

                # 執行 handler
                timeout = self.config.level_timeouts.get(current_level, 5000) / 1000
                result = await asyncio.wait_for(
                    handler(task, context),
                    timeout=timeout
                )

                # 評估信心度
                confidence_result = self._evaluate_confidence(task, result, context)
                last_confidence = confidence_result.total_score

                logger.info(
                    f"[Orchestrator] 層級 {current_level.name} "
                    f"信心度: {last_confidence:.2f}, 動作: {confidence_result.action}"
                )

                if confidence_result.is_confident:
                    # 信心足夠，返回結果
                    execution_time = (time.time() - start_time) * 1000
                    return OrchestratorResult(
                        success=True,
                        result=result,
                        level_used=current_level,
                        confidence=last_confidence,
                        escalation_path=escalation_path,
                        execution_time_ms=execution_time,
                        details={
                            "confidence_details": confidence_result.to_dict(),
                            "expert": self.router.route(task).name,
                        }
                    )

                # 需要升級
                last_result = result
                current_level = AgentLevel(current_level + 1)

            except asyncio.TimeoutError:
                logger.warning(f"[Orchestrator] 層級 {current_level.name} 超時")
                current_level = AgentLevel(current_level + 1)
            except Exception as e:
                logger.error(f"[Orchestrator] 層級 {current_level.name} 錯誤: {e}")
                current_level = AgentLevel(current_level + 1)

        # 所有層級都嘗試過
        execution_time = (time.time() - start_time) * 1000

        if self.config.enable_human_fallback:
            escalation_path.append(AgentLevel.HUMAN)
            return OrchestratorResult(
                success=False,
                result=last_result,
                level_used=AgentLevel.HUMAN,
                confidence=last_confidence,
                escalation_path=escalation_path,
                execution_time_ms=execution_time,
                details={"requires_human": True}
            )

        return OrchestratorResult(
            success=False,
            result=last_result,
            level_used=escalation_path[-1] if escalation_path else AgentLevel.RULE_BASED,
            confidence=last_confidence,
            escalation_path=escalation_path,
            execution_time_ms=execution_time,
            details={"all_levels_failed": True}
        )

    def _evaluate_confidence(
        self,
        task: str,
        result: Any,
        context: Dict
    ) -> ConfidenceResult:
        """評估結果的信心度"""
        # 提取組件類型（如果有）
        component_type = context.get("component_type", "")
        if not component_type and isinstance(result, dict):
            component_type = result.get("component_type", "")

        # 提取參數（如果有）
        target_param = context.get("target_param")
        if not target_param and isinstance(result, dict):
            target_param = result.get("target_param")

        # 驗證分數（如果有）
        validation_score = 0.5
        if isinstance(result, dict) and "validation_score" in result:
            validation_score = result["validation_score"]

        context_with_validation = {**context, "validation_score": validation_score}

        return self.confidence_evaluator.evaluate(
            component_type=component_type or task[:50],
            target_param=target_param,
            context=context_with_validation
        )

    # ===== Default Handlers =====

    async def _rule_based_handler(self, task: str, context: Dict) -> Dict:
        """
        Level 0: 規則驅動

        使用預定義規則和嵌入向量進行快速處理
        """
        # 路由到專家
        expert = self.router.route(task)

        # 檢查嵌入
        has_embedding = False
        similar_components = []

        for word in task.split():
            if word in self.confidence_evaluator.embeddings:
                has_embedding = True
                break

        return {
            "handler": "rule_based",
            "expert": expert.name,
            "task_type": expert.task_type.value,
            "has_embedding": has_embedding,
            "validation_score": 0.6 if has_embedding else 0.4,
        }

    async def _ml_enhanced_handler(self, task: str, context: Dict) -> Dict:
        """
        Level 1: ML 增強

        使用 graph_learner 的嵌入進行模式匹配和相似推薦
        """
        expert = self.router.route(task)

        # 模式匹配
        matched_patterns = []
        for pattern in self.confidence_evaluator.patterns:
            for word in task.split():
                if word.lower() in pattern.lower():
                    matched_patterns.append(pattern)
                    break

        return {
            "handler": "ml_enhanced",
            "expert": expert.name,
            "matched_patterns": matched_patterns[:5],
            "pattern_count": len(matched_patterns),
            "validation_score": min(0.8, 0.5 + len(matched_patterns) * 0.1),
        }

    async def _ai_powered_handler(self, task: str, context: Dict) -> Dict:
        """
        Level 2: AI 驅動

        使用 Gemini 或其他 AI 進行語義驗證
        （這裡是 placeholder，實際需要整合 Gemini API）
        """
        expert = self.router.route(task)

        # Placeholder: 模擬 AI 處理
        # 實際實現會調用 Gemini API
        return {
            "handler": "ai_powered",
            "expert": expert.name,
            "ai_review": "pending_implementation",
            "validation_score": 0.75,
            "suggestions": [],
        }

    # ===== Utility Methods =====

    def explain_decision(self, task: str, context: Optional[Dict] = None) -> Dict:
        """
        解釋調度決策

        Args:
            task: 任務描述
            context: 上下文

        Returns:
            決策解釋
        """
        context = context or {}

        # 路由解釋
        routing_explanation = self.router.explain_routing(task)

        # 信心度評估
        confidence_result = self.confidence_evaluator.evaluate(
            component_type=context.get("component_type", task[:50]),
            target_param=context.get("target_param"),
            context=context
        )

        # 預測的升級路徑
        predicted_path = []
        if confidence_result.is_confident:
            predicted_path = [AgentLevel.RULE_BASED]
        elif confidence_result.needs_review:
            predicted_path = [AgentLevel.RULE_BASED, AgentLevel.ML_ENHANCED]
        else:
            predicted_path = [
                AgentLevel.RULE_BASED,
                AgentLevel.ML_ENHANCED,
                AgentLevel.AI_POWERED
            ]

        return {
            "routing": routing_explanation,
            "confidence": confidence_result.to_dict(),
            "predicted_path": [l.name for l in predicted_path],
            "estimated_max_time_ms": sum(
                self.config.level_timeouts.get(l, 1000)
                for l in predicted_path
            ),
        }

    def get_statistics(self) -> Dict:
        """獲取調度器統計信息"""
        return {
            "embeddings_loaded": len(self.confidence_evaluator.embeddings),
            "patterns_loaded": len(self.confidence_evaluator.patterns),
            "experts_registered": len(self.router.experts),
            "handlers_registered": len(self.handlers),
            "config": {
                "max_level": self.config.max_level.name,
                "enable_human_fallback": self.config.enable_human_fallback,
                "confidence_thresholds": {
                    "pass": self.config.confidence_thresholds.cascade_pass,
                    "review": self.config.confidence_thresholds.cascade_review,
                    "fail": self.config.confidence_thresholds.cascade_fail,
                }
            }
        }
