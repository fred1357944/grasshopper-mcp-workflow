"""
Integration Module - 整合 Graph Learner 與 Orchestrator

這個模組負責:
1. 從 gh_learning 載入嵌入向量
2. 初始化 Orchestrator
3. 提供統一的 API
"""

from pathlib import Path
from typing import Dict, Optional, Any
import json
import sys

# 確保可以導入 gh_learning
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from .orchestrator import AgentOrchestrator, OrchestratorConfig, OrchestratorResult, AgentLevel
from .confidence import ConfidenceEvaluator, ConfidenceThresholds
from .routing import ExpertRouter, TaskType


class GHOrchestrator:
    """
    Grasshopper 專用 Orchestrator

    整合:
    - gh_learning 的嵌入向量
    - 連接模式知識
    - Cascade + Confidence 策略

    Usage:
        gh_orch = GHOrchestrator.create()

        # 執行任務
        result = await gh_orch.execute(
            task="連接 Number Slider 到 Box",
            stage="connectivity"
        )

        # 獲取組件建議
        suggestions = gh_orch.suggest_components("Box")
    """

    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        knowledge_path: Optional[Path] = None
    ):
        self.orchestrator = orchestrator
        self.knowledge_path = knowledge_path

        # 快取的知識
        self._component_knowledge: Dict = {}
        self._connection_patterns: Dict = {}

    @classmethod
    def create(
        cls,
        embeddings_path: Optional[str] = None,
        knowledge_dir: Optional[str] = None
    ) -> "GHOrchestrator":
        """
        工廠方法：建立 GHOrchestrator

        Args:
            embeddings_path: 嵌入向量路徑
            knowledge_dir: 知識庫目錄

        Returns:
            GHOrchestrator 實例
        """
        # 預設路徑
        if knowledge_dir is None:
            knowledge_dir = str(PROJECT_ROOT / "gh_learning" / "knowledge")

        if embeddings_path is None:
            embeddings_path = str(Path(knowledge_dir) / "component_embeddings.json")

        # 建立配置
        config = OrchestratorConfig(
            embeddings_path=embeddings_path,
            confidence_thresholds=ConfidenceThresholds(
                cascade_pass=0.8,
                cascade_review=0.6,
                cascade_fail=0.4,
            )
        )

        orchestrator = AgentOrchestrator(config)

        instance = cls(
            orchestrator=orchestrator,
            knowledge_path=Path(knowledge_dir)
        )

        # 載入知識
        instance._load_knowledge()

        return instance

    def _load_knowledge(self):
        """載入知識庫"""
        if not self.knowledge_path:
            return

        # 載入提取的知識
        extracted = self.knowledge_path / "extracted_knowledge.json"
        if extracted.exists():
            with open(extracted, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._component_knowledge = data.get('components', {})
            self._connection_patterns = data.get('connection_patterns', {})

            # 同步連接模式到 confidence evaluator
            self.orchestrator.confidence_evaluator.patterns = self._connection_patterns

            print(f"[GHOrchestrator] 載入 {len(self._component_knowledge)} 組件")
            print(f"[GHOrchestrator] 載入 {len(self._connection_patterns)} 連接模式")

    async def execute(
        self,
        task: str,
        stage: Optional[str] = None,
        component_type: Optional[str] = None,
        **kwargs
    ) -> OrchestratorResult:
        """
        執行 GH 任務

        Args:
            task: 任務描述
            stage: 工作流程階段
            component_type: 組件類型
            **kwargs: 其他上下文

        Returns:
            OrchestratorResult
        """
        context = {
            "stage": stage or "general",
            "component_type": component_type or "",
            **kwargs
        }

        return await self.orchestrator.execute(task, context)

    def suggest_components(
        self,
        component_type: str,
        top_k: int = 5
    ) -> list:
        """
        建議相似組件

        Args:
            component_type: 源組件類型
            top_k: 返回數量

        Returns:
            相似組件列表
        """
        embeddings = self.orchestrator.confidence_evaluator.embeddings

        if component_type not in embeddings:
            # 嘗試模糊匹配
            for name in embeddings:
                if component_type.lower() in name.lower():
                    component_type = name
                    break
            else:
                return []

        import numpy as np

        target = embeddings[component_type]
        results = []

        for name, vec in embeddings.items():
            if name != component_type:
                norm_t = np.linalg.norm(target)
                norm_v = np.linalg.norm(vec)
                if norm_t > 0 and norm_v > 0:
                    sim = float(np.dot(target, vec) / (norm_t * norm_v))
                    results.append((name, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def get_connection_suggestions(
        self,
        source_component: str,
        target_component: Optional[str] = None
    ) -> list:
        """
        獲取連接建議

        Args:
            source_component: 源組件
            target_component: 目標組件（可選）

        Returns:
            建議的連接模式
        """
        suggestions = []
        source_lower = source_component.lower()

        for pattern, count in self._connection_patterns.items():
            pattern_lower = pattern.lower()

            # 模糊匹配源組件
            source_match = (
                source_lower in pattern_lower or
                any(word in pattern_lower for word in source_lower.split() if len(word) > 2)
            )

            if source_match:
                # 如果指定目標，也檢查目標
                if target_component is not None:
                    target_lower = target_component.lower()
                    target_match = (
                        target_lower in pattern_lower or
                        any(word in pattern_lower for word in target_lower.split() if len(word) > 2)
                    )
                    if not target_match:
                        continue

                suggestions.append({
                    "pattern": pattern,
                    "frequency": count,
                })

        # 按頻率排序
        suggestions.sort(key=lambda x: x["frequency"], reverse=True)
        return suggestions[:10]

    def explain_task(self, task: str) -> Dict:
        """
        解釋任務的處理方式

        Args:
            task: 任務描述

        Returns:
            處理解釋
        """
        explanation = self.orchestrator.explain_decision(task)

        # 補充 GH 特定信息
        explanation["gh_info"] = {
            "known_components": len(self._component_knowledge),
            "known_patterns": len(self._connection_patterns),
        }

        return explanation

    def get_statistics(self) -> Dict:
        """獲取統計信息"""
        base_stats = self.orchestrator.get_statistics()

        return {
            **base_stats,
            "gh_knowledge": {
                "components": len(self._component_knowledge),
                "patterns": len(self._connection_patterns),
            }
        }


# === Enhanced Orchestrator with Superpower Integration ===

from .intent_router import IntentRouter, IntentType, IntentClassification
from .mode_selector import ModeSelector, ModeSelection, ProcessingStrategy

from ..nodes.think_partner import (
    think_partner_node,
    enter_think_partner_mode,
    exit_think_partner_mode,
    add_user_response,
)
from ..nodes.brainstorm import (
    brainstorm_node,
    enter_brainstorm_mode,
    exit_brainstorm_mode,
)
from ..nodes.meta_agent import (
    meta_agent_node,
    enter_meta_agent_mode,
    exit_meta_agent_mode,
)
from ..nodes.workflow_pipeline import (
    intent_decomposition_node,
    tool_retrieval_node,
    prompt_generation_node,
    config_assembly_node,
    enter_workflow_mode,
)
from ..state import DesignState, create_initial_state


class EnhancedGHOrchestrator(GHOrchestrator):
    """
    增強版 GH Orchestrator - 支援多模式處理

    整合:
    - Intent Router: 意圖分類
    - Mode Selector: 模式選擇
    - Think-Partner: 蘇格拉底式探索
    - Brainstorm: 三階段腦力激盪
    - Meta-Agent: 動態工具創建
    - Workflow Pipeline: 確定性四階段管線

    Usage:
        orch = EnhancedGHOrchestrator.create()

        # 自動模式選擇
        result = await orch.execute_with_mode_selection(
            task="brainstorm ideas for a parametric table",
            context={}
        )

        # 手動觸發特定模式
        result = await orch.execute_with_mode_selection(
            task="/think what makes a good chair design",
            context={}
        )
    """

    def __init__(
        self,
        orchestrator: AgentOrchestrator,
        knowledge_path: Optional[Path] = None
    ):
        super().__init__(orchestrator, knowledge_path)

        # Superpower components
        self.intent_router = IntentRouter()
        self.mode_selector = ModeSelector(
            confidence_evaluator=self.orchestrator.confidence_evaluator,
            intent_router=self.intent_router
        )

        # Current state for stateful operations
        self._current_state: Optional[DesignState] = None

    @classmethod
    def create(
        cls,
        embeddings_path: Optional[str] = None,
        knowledge_dir: Optional[str] = None
    ) -> "EnhancedGHOrchestrator":
        """工廠方法：建立 EnhancedGHOrchestrator"""
        # 使用父類建立基礎 orchestrator
        base = GHOrchestrator.create(embeddings_path, knowledge_dir)

        # 轉換為增強版
        enhanced = cls(
            orchestrator=base.orchestrator,
            knowledge_path=base.knowledge_path
        )

        # 複製已載入的知識
        enhanced._component_knowledge = base._component_knowledge
        enhanced._connection_patterns = base._connection_patterns

        return enhanced

    async def execute_with_mode_selection(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        force_mode: Optional[IntentType] = None
    ) -> Dict[str, Any]:
        """
        使用模式選擇執行任務

        Args:
            task: 任務描述
            context: 上下文信息
            force_mode: 強制使用特定模式

        Returns:
            處理結果 (包含狀態更新)
        """
        context = context or {}

        # 初始化或獲取狀態
        if self._current_state is None:
            self._current_state = create_initial_state(task)

        state = dict(self._current_state)
        state["topic"] = task

        # 模式選擇
        if force_mode:
            mode_selection = ModeSelection(
                intent_type=force_mode,
                strategy=ProcessingStrategy.DIRECT,
                confidence=1.0,
                should_ask_clarification=False,
                clarification_question=None,
                reasoning=f"Forced mode: {force_mode.value}"
            )
        else:
            mode_selection = self.mode_selector.select(task, state)

        # 更新狀態
        state["intent_type"] = mode_selection.intent_type.value
        state["intent_confidence"] = mode_selection.confidence

        # 根據模式處理
        result = await self._process_by_mode(
            mode_selection.intent_type,
            state,
            task
        )

        # 保存狀態
        self._current_state = DesignState(**{**state, **result})

        return {
            "mode": mode_selection.intent_type.value,
            "strategy": mode_selection.strategy.value,
            "confidence": mode_selection.confidence,
            "reasoning": mode_selection.reasoning,
            "state_updates": result,
            "should_ask_clarification": mode_selection.should_ask_clarification,
            "clarification_question": mode_selection.clarification_question,
        }

    async def _process_by_mode(
        self,
        mode: IntentType,
        state: Dict[str, Any],
        task: str
    ) -> Dict[str, Any]:
        """根據模式調用對應處理函數"""

        if mode == IntentType.THINK_PARTNER:
            # 進入 Think-Partner 模式
            entry_updates = enter_think_partner_mode(state)
            state.update(entry_updates)
            return think_partner_node(state)

        elif mode == IntentType.BRAINSTORM:
            # 進入 Brainstorm 模式
            entry_updates = enter_brainstorm_mode(state)
            state.update(entry_updates)
            return brainstorm_node(state)

        elif mode == IntentType.META_AGENT:
            # 進入 Meta-Agent 模式
            entry_updates = enter_meta_agent_mode(state)
            state.update(entry_updates)
            return meta_agent_node(state)

        elif mode == IntentType.WORKFLOW:
            # 進入 Workflow 模式
            entry_updates = enter_workflow_mode(state)
            state.update(entry_updates)
            return await self._run_workflow_pipeline(state)

        else:
            # 未知模式，回退到標準執行
            result = await self.execute(task, stage="general")
            return {
                "errors": state.get("errors", []) + [
                    f"Unknown mode, fallback to standard execution: {result.success}"
                ]
            }

    async def _run_workflow_pipeline(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """執行四階段 Workflow Pipeline"""
        # Stage 1: Decomposition
        decomp_result = intent_decomposition_node(state)
        state.update(decomp_result)

        # Stage 2: Tool Retrieval
        retrieval_result = tool_retrieval_node(state)
        state.update(retrieval_result)

        # Stage 3: Prompt Generation
        prompt_result = prompt_generation_node(state)
        state.update(prompt_result)

        # Stage 4: Config Assembly
        assembly_result = config_assembly_node(state)
        state.update(assembly_result)

        return assembly_result

    def continue_conversation(
        self,
        user_response: str
    ) -> Dict[str, Any]:
        """
        繼續對話 (用於 Think-Partner 和 Brainstorm)

        Args:
            user_response: 用戶回應

        Returns:
            狀態更新
        """
        if self._current_state is None:
            return {"error": "No active session"}

        state = dict(self._current_state)
        mode = state.get("intent_type")

        if mode == IntentType.THINK_PARTNER.value:
            # 處理 Think-Partner 回應
            updates = add_user_response(state, user_response)
            state.update(updates)
            result = think_partner_node(state)
            state.update(result)
            self._current_state = DesignState(**state)
            return result

        elif mode == IntentType.BRAINSTORM.value:
            # 處理 Brainstorm 回應
            from ..nodes.brainstorm import add_constraint, add_success_criterion

            # 根據當前階段處理
            phase = state.get("brainstorm_phase")
            if phase == "understanding":
                # 假設回應是約束或成功標準
                if "constraint" in user_response.lower():
                    updates = add_constraint(state, user_response)
                else:
                    updates = add_success_criterion(state, user_response)
                state.update(updates)

            result = brainstorm_node(state)
            state.update(result)
            self._current_state = DesignState(**state)
            return result

        return {"error": f"Cannot continue in mode: {mode}"}

    def reset_session(self):
        """重置會話狀態"""
        self._current_state = None

    def get_current_state(self) -> Optional[DesignState]:
        """獲取當前狀態"""
        return self._current_state

    def get_mode_description(self, mode: IntentType) -> str:
        """獲取模式描述"""
        return self.intent_router.get_mode_description(mode)


# 便捷函數
async def quick_execute(
    task: str,
    stage: str = "general"
) -> OrchestratorResult:
    """
    快速執行任務

    Args:
        task: 任務描述
        stage: 工作流程階段

    Returns:
        OrchestratorResult
    """
    gh_orch = GHOrchestrator.create()
    return await gh_orch.execute(task, stage=stage)


async def quick_execute_with_mode(
    task: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    快速執行任務（自動模式選擇）

    Args:
        task: 任務描述
        context: 上下文信息

    Returns:
        處理結果
    """
    orch = EnhancedGHOrchestrator.create()
    return await orch.execute_with_mode_selection(task, context)
