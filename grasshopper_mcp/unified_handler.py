#!/usr/bin/env python3
"""
UnifiedHandler - 三層架構統一入口
==================================

核心理念：「讓需求驅動複雜度」
- Layer 1: 直接執行 (80% 場景) - Golden Knowledge 匹配，0 次 Claude 調用
- Layer 2: Claude 補充 (15% 場景) - 部分匹配，1 次 Claude 調用
- Layer 3: LangGraph 探索 (5% 場景) - 探索性需求，3-5 次 Claude 調用

Usage:
    from grasshopper_mcp import UnifiedHandler

    handler = UnifiedHandler()
    result = handler.handle("用 WASP 做立方體聚集")

    print(f"Layer: {result.layer}")
    print(f"Claude calls: {result.claude_calls}")
    print(f"Success: {result.success}")
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Awaitable
import json
import time

from .integration_bridge import IntegrationBridge
from .pre_execution_checker import PreExecutionChecker, CheckResult, Severity
from .hitl_collaborator import HITLCollaborator, QuestionType


class Layer(Enum):
    """三層架構層級"""
    DIRECT = "direct"          # Layer 1: Golden 直接執行 (0 Claude calls)
    SUPPLEMENT = "supplement"  # Layer 2: Claude 補充 (1 Claude call)
    EXPLORE = "explore"        # Layer 3: LangGraph 流程 (3-5 Claude calls)


@dataclass
class HandleResult:
    """處理結果"""
    success: bool
    layer: Layer
    data: Optional[Dict] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    claude_calls: int = 0
    latency_ms: float = 0.0
    placement_info: Optional[Dict] = None
    knowledge_source: Optional[str] = None  # "golden", "community", "personal", "none"


class UnifiedHandler:
    """
    三層架構統一入口

    整合：
    - IntegrationBridge (統一搜尋)
    - PreExecutionChecker (執行前驗證)
    - WorkflowExecutor (執行引擎)
    - LearningAgent (學習代理)
    """

    # 探索性關鍵字 (觸發 Layer 3)
    EXPLORATION_KEYWORDS = [
        # 中文
        "探索", "討論", "比較", "幫我想", "怎麼做比較好",
        "有什麼方法", "有哪些選擇", "建議怎麼做",
        # English
        "explore", "discuss", "compare", "help me think",
        "what are the options", "how should i", "what would be best"
    ]

    # Golden 匹配閾值
    GOLDEN_CONFIDENCE_THRESHOLD = 0.8

    def __init__(
        self,
        config_dir: str = "config",
        reference_library_dir: str = "reference_library",
        user_id: str = "default",
        mcp_client: Optional[Any] = None,
        auto_execute: bool = True,
        auto_mode: bool = False,
        user_callback: Optional[Callable[[str], Awaitable[str]]] = None,
        wip_dir: str = "GH_WIP"
    ):
        """
        初始化三層架構處理器

        Args:
            config_dir: 配置目錄路徑
            reference_library_dir: Reference Library 路徑
            user_id: 用戶 ID (用於個人經驗庫)
            mcp_client: MCP 客戶端 (可選，用於實際執行)
            auto_execute: 是否自動執行 (False 時只生成 placement_info)
            auto_mode: HITL 自動模式 (True 時使用預設值，不詢問)
            user_callback: HITL 用戶互動回調 (async)
            wip_dir: 工作目錄路徑
        """
        self.config_dir = Path(config_dir)
        self.ref_dir = Path(reference_library_dir)
        self.wip_dir = Path(wip_dir)
        self.user_id = user_id
        self.mcp_client = mcp_client
        self.auto_execute = auto_execute
        self.auto_mode = auto_mode

        # 確保工作目錄存在
        self.wip_dir.mkdir(exist_ok=True)

        # 初始化各系統
        self.bridge = IntegrationBridge(
            config_dir=str(self.config_dir),
            reference_library_dir=str(self.ref_dir),
            user_id=user_id
        )
        self.pre_checker = PreExecutionChecker(config_dir=self.config_dir)

        # 初始化 HITL 協作器
        self.hitl = HITLCollaborator(
            user_callback=user_callback,
            auto_mode=auto_mode
        )

        # 延遲初始化 ClaudePlanGenerator (按需)
        self._plan_generator = None

        # 統計
        self._stats = {
            "total_requests": 0,
            "layer1_count": 0,
            "layer2_count": 0,
            "layer3_count": 0,
            "total_claude_calls": 0,
        }

    @property
    def plan_generator(self):
        """延遲初始化 ClaudePlanGenerator"""
        if self._plan_generator is None:
            from .claude_plan_generator import ClaudePlanGenerator
            self._plan_generator = ClaudePlanGenerator(config_dir=str(self.config_dir))
        return self._plan_generator

    def handle(self, user_input: str, context: Optional[Dict] = None) -> HandleResult:
        """
        處理用戶請求，按需選擇 Layer

        Layer 路由邏輯 (探索性需求優先):
        1. 若為探索性需求 → Layer 3 (LangGraph)
        2. 搜尋知識庫
        3. 若為 Golden 高信心匹配 → Layer 1 (直接執行)
        4. 其他 → Layer 2 (Claude 補充)

        Args:
            user_input: 用戶請求
            context: 額外上下文

        Returns:
            HandleResult
        """
        start_time = time.time()
        context = context or {}

        self._stats["total_requests"] += 1

        # Layer 3 判斷 (探索性需求優先！)
        # 即使有 Golden 匹配，探索性請求也應該進入多輪對話
        if self._needs_exploration(user_input):
            self._stats["layer3_count"] += 1
            knowledge = self.bridge.search(user_input)
            result = self._execute_layer3(user_input, knowledge, context)
            result.latency_ms = (time.time() - start_time) * 1000
            return result

        # 搜尋知識庫
        knowledge = self.bridge.search(user_input)

        # Layer 1: Golden 直接執行
        if self._is_golden_match(knowledge):
            self._stats["layer1_count"] += 1
            result = self._execute_layer1(knowledge, user_input)
            result.latency_ms = (time.time() - start_time) * 1000
            return result

        # Layer 2: Claude 補充
        self._stats["layer2_count"] += 1
        result = self._execute_layer2(user_input, knowledge, context)
        result.latency_ms = (time.time() - start_time) * 1000
        return result

    def _is_golden_match(self, knowledge: Dict) -> bool:
        """
        判斷是否為高信心度 Golden 匹配

        條件:
        - source == "golden"
        - reliability == "verified_by_experts"
        - content 不為空
        """
        exp = knowledge.get("experience", {})

        # 基本條件
        if exp.get("source") != "golden":
            return False
        if exp.get("reliability") != "verified_by_experts":
            return False
        if not exp.get("content"):
            return False

        # 檢查 content 中是否有 solution
        content = exp.get("content", {})
        solution = content.get("solution", {})

        # 必須有 components
        if not solution.get("components"):
            return False

        return True

    def _needs_exploration(self, user_input: str) -> bool:
        """
        判斷是否需要探索性流程 (Layer 3)

        觸發條件: 包含探索性關鍵字
        """
        user_lower = user_input.lower()
        return any(kw.lower() in user_lower for kw in self.EXPLORATION_KEYWORDS)

    def _execute_layer1(self, knowledge: Dict, user_input: str) -> HandleResult:
        """
        Layer 1: 直接執行 Golden Knowledge

        流程:
        1. 從 knowledge 提取 solution
        2. 轉換為 placement_info
        3. Pre-execution 驗證
        4. (可選) 執行
        """
        experience = knowledge["experience"]["content"]
        solution = experience.get("solution", {})

        # 轉換為 placement_info
        placement_info = self._solution_to_placement(solution, experience)

        # Pre-execution 驗證
        check_results = self.pre_checker.check_placement_info(placement_info)

        # 分類檢查結果
        critical_issues = [r for r in check_results if r.severity == Severity.CRITICAL]
        warnings = [r for r in check_results if r.severity == Severity.WARNING]

        if critical_issues:
            return HandleResult(
                success=False,
                layer=Layer.DIRECT,
                errors=[r.message for r in critical_issues],
                warnings=[r.message for r in warnings],
                claude_calls=0,
                placement_info=placement_info,
                knowledge_source="golden"
            )

        # 執行 (如果啟用)
        if self.auto_execute:
            exec_result = self._execute_placement(placement_info)

            if not exec_result.get("success", False):
                return HandleResult(
                    success=False,
                    layer=Layer.DIRECT,
                    errors=exec_result.get("errors", ["Execution failed"]),
                    warnings=[r.message for r in warnings],
                    claude_calls=0,
                    placement_info=placement_info,
                    knowledge_source="golden"
                )

            # 學習成功案例
            self._learn_from_success(user_input, placement_info, exec_result)

        return HandleResult(
            success=True,
            layer=Layer.DIRECT,
            data={
                "experience_id": experience.get("id"),
                "experience_name": experience.get("request"),
                "components_count": len(solution.get("components", [])),
                "connections_count": len(solution.get("connections", [])),
            },
            warnings=[r.message for r in warnings],
            claude_calls=0,
            placement_info=placement_info,
            knowledge_source="golden"
        )

    def _execute_layer2(
        self,
        user_input: str,
        knowledge: Dict,
        context: Dict
    ) -> HandleResult:
        """
        Layer 2: Claude 補充

        當 Golden 不完全匹配時，用 Claude 生成計畫 (1 次調用)
        """
        # TODO: Phase 2 完整實作
        # 目前返回部分匹配的 reference 或 community 知識

        exp = knowledge.get("experience", {})
        source = exp.get("source", "none")
        content = exp.get("content")

        # 如果有 community 或 personal 知識，嘗試使用
        if content and source in ("community", "personal"):
            solution = content.get("solution", {})
            placement_info = self._solution_to_placement(solution, content)

            # Pre-execution 驗證
            check_results = self.pre_checker.check_placement_info(placement_info)
            critical_issues = [r for r in check_results if r.severity == Severity.CRITICAL]

            if not critical_issues:
                return HandleResult(
                    success=True,
                    layer=Layer.SUPPLEMENT,
                    data={
                        "source": source,
                        "note": "Using community/personal knowledge (Layer 2 fallback)"
                    },
                    claude_calls=0,  # 未實際調用 Claude
                    placement_info=placement_info,
                    knowledge_source=source
                )

        # 嘗試使用 reference library
        ref = knowledge.get("reference")
        if ref and ref.get("path"):
            try:
                with open(ref["path"], 'r', encoding='utf-8') as f:
                    ref_config = json.load(f)

                placement_info = self._reference_to_placement(ref_config)

                return HandleResult(
                    success=True,
                    layer=Layer.SUPPLEMENT,
                    data={
                        "source": "reference_library",
                        "reference_name": ref.get("name"),
                        "note": "Using reference library (Layer 2 fallback)"
                    },
                    claude_calls=0,
                    placement_info=placement_info,
                    knowledge_source="reference"
                )
            except Exception as e:
                pass  # 繼續到 Claude 補充

        # Claude 補充 (TODO: 實作 claude_plan_generator)
        return HandleResult(
            success=False,
            layer=Layer.SUPPLEMENT,
            errors=["Layer 2 Claude plan generation not yet implemented"],
            data={
                "partial_knowledge": {
                    "triplets_count": len(knowledge.get("triplets", [])),
                    "patterns_count": len(knowledge.get("patterns", [])),
                }
            },
            claude_calls=0,
            knowledge_source="none"
        )

    def _execute_layer3(
        self,
        user_input: str,
        knowledge: Dict,
        context: Dict
    ) -> HandleResult:
        """
        Layer 3: LangGraph 探索流程

        用於探索性需求，需要多輪對話
        """
        # 同步版本返回提示，需使用 handle_async
        return HandleResult(
            success=False,
            layer=Layer.EXPLORE,
            errors=["Layer 3 需要人機協作，請使用 handle_async()"],
            data={
                "detected_keywords": [
                    kw for kw in self.EXPLORATION_KEYWORDS
                    if kw.lower() in user_input.lower()
                ]
            },
            claude_calls=0,
            knowledge_source="none"
        )

    # =========================================================================
    # 異步 API (支援 HITL)
    # =========================================================================

    async def handle_async(self, user_input: str, context: Optional[Dict] = None) -> HandleResult:
        """
        異步處理用戶請求，支援所有 Layer + HITL

        Layer 路由邏輯 (與同步版本相同):
        1. 若為探索性需求 → Layer 3 (LangGraph + HITL)
        2. 搜尋知識庫
        3. 若為 Golden 高信心匹配 → Layer 1 (直接執行，無 HITL)
        4. 其他 → Layer 2 (Claude 補充 + HITL)

        Args:
            user_input: 用戶請求
            context: 額外上下文

        Returns:
            HandleResult
        """
        start_time = time.time()
        context = context or {}

        self._stats["total_requests"] += 1

        # 搜尋知識庫
        knowledge = self.bridge.search(user_input)

        # Layer 3 判斷 (探索性需求優先！)
        if self._needs_exploration(user_input):
            self._stats["layer3_count"] += 1
            result = await self._execute_layer3_with_hitl(user_input, knowledge, context)
            result.latency_ms = (time.time() - start_time) * 1000
            return result

        # Layer 1: Golden 直接執行 (無 HITL)
        if self._is_golden_match(knowledge):
            self._stats["layer1_count"] += 1
            result = self._execute_layer1(knowledge, user_input)
            result.latency_ms = (time.time() - start_time) * 1000
            return result

        # Layer 2: Claude 補充 + HITL
        self._stats["layer2_count"] += 1
        result = await self._execute_layer2_with_hitl(user_input, knowledge, context)
        result.latency_ms = (time.time() - start_time) * 1000
        return result

    async def _execute_layer2_with_hitl(
        self,
        user_input: str,
        knowledge: Dict,
        context: Dict
    ) -> HandleResult:
        """
        Layer 2: Claude 補充 + Mermaid 確認

        流程:
        1. 生成計畫 + Mermaid 可視化
        2. 提示用戶在 VSCode 預覽
        3. HITL 確認
        4. Pre-Execution Check
        5. 執行
        """
        # 1. 嘗試使用 ClaudePlanGenerator 生成計畫
        try:
            plan, mermaid_path = self.plan_generator.generate_with_mermaid(
                user_input=user_input,
                partial_knowledge=knowledge,
                wip_dir=self.wip_dir
            )
        except Exception as e:
            # 如果生成失敗，回退到原有邏輯
            return await self._execute_layer2_fallback(user_input, knowledge, context, str(e))

        if not plan.success:
            return HandleResult(
                success=False,
                layer=Layer.SUPPLEMENT,
                errors=plan.errors,
                warnings=plan.warnings,
                claude_calls=1,
                knowledge_source="none"
            )

        # 2. 提示用戶確認
        print(f"\n📊 已生成組件連接圖: {mermaid_path}")
        print("   請在 VSCode 中預覽並確認")

        # 3. HITL 確認
        confirmed = await self.hitl.confirm_workflow(
            workflow_description=plan.generation_context.get("description", user_input),
            patterns_used=plan.generation_context.get("patterns_used", []),
            estimated_components=len(plan.components),
            user_inputs_needed=plan.generation_context.get("user_inputs", [])
        )

        if not confirmed:
            return HandleResult(
                success=False,
                layer=Layer.SUPPLEMENT,
                errors=["用戶取消執行"],
                claude_calls=1,
                placement_info=plan.placement_info,
                knowledge_source="claude_generated"
            )

        # 4. Pre-Execution Check
        check_results = self.pre_checker.check_placement_info(plan.placement_info)
        critical_issues = [r for r in check_results if r.severity == Severity.CRITICAL]
        warnings = [r for r in check_results if r.severity == Severity.WARNING]

        if critical_issues:
            return HandleResult(
                success=False,
                layer=Layer.SUPPLEMENT,
                errors=[r.message for r in critical_issues],
                warnings=[r.message for r in warnings],
                claude_calls=1,
                placement_info=plan.placement_info,
                knowledge_source="claude_generated"
            )

        # 若有警告，詢問是否繼續
        if warnings and not self.auto_mode:
            continue_anyway = await self.hitl.confirm(
                f"有 {len(warnings)} 個警告，是否繼續執行？",
                default=True
            )
            if not continue_anyway:
                return HandleResult(
                    success=False,
                    layer=Layer.SUPPLEMENT,
                    errors=["用戶取消執行 (因警告)"],
                    warnings=[r.message for r in warnings],
                    claude_calls=1,
                    placement_info=plan.placement_info,
                    knowledge_source="claude_generated"
                )

        # 5. 執行 (如果啟用)
        if self.auto_execute:
            exec_result = self._execute_placement(plan.placement_info)

            if not exec_result.get("success", False):
                return HandleResult(
                    success=False,
                    layer=Layer.SUPPLEMENT,
                    errors=exec_result.get("errors", ["Execution failed"]),
                    warnings=[r.message for r in warnings],
                    claude_calls=1,
                    placement_info=plan.placement_info,
                    knowledge_source="claude_generated"
                )

            # 學習成功案例
            self._learn_from_success(user_input, plan.placement_info, exec_result)

        self._stats["total_claude_calls"] += 1

        return HandleResult(
            success=True,
            layer=Layer.SUPPLEMENT,
            data={
                "mermaid_path": str(mermaid_path),
                "components_count": len(plan.components),
                "connections_count": len(plan.connections),
            },
            warnings=[r.message for r in warnings],
            claude_calls=1,
            placement_info=plan.placement_info,
            knowledge_source="claude_generated"
        )

    async def _execute_layer2_fallback(
        self,
        user_input: str,
        knowledge: Dict,
        context: Dict,
        error_msg: str
    ) -> HandleResult:
        """Layer 2 回退邏輯 (當 ClaudePlanGenerator 失敗時)"""
        # 嘗試使用 community/personal 知識
        exp = knowledge.get("experience", {})
        source = exp.get("source", "none")
        content = exp.get("content")

        if content and source in ("community", "personal"):
            solution = content.get("solution", {})
            placement_info = self._solution_to_placement(solution, content)

            check_results = self.pre_checker.check_placement_info(placement_info)
            critical_issues = [r for r in check_results if r.severity == Severity.CRITICAL]

            if not critical_issues:
                return HandleResult(
                    success=True,
                    layer=Layer.SUPPLEMENT,
                    data={
                        "source": source,
                        "note": f"Using {source} knowledge (fallback)"
                    },
                    claude_calls=0,
                    placement_info=placement_info,
                    knowledge_source=source
                )

        return HandleResult(
            success=False,
            layer=Layer.SUPPLEMENT,
            errors=[f"Plan generation failed: {error_msg}"],
            claude_calls=0,
            knowledge_source="none"
        )

    async def _execute_layer3_with_hitl(
        self,
        user_input: str,
        knowledge: Dict,
        context: Dict
    ) -> HandleResult:
        """
        Layer 3: 完整設計流程 + HITL

        使用 DesignWorkflowV2 執行六階段工作流程
        """
        try:
            from .design_workflow_v2 import DesignWorkflowV2

            # 創建工作流程
            project_name = context.get("project_name", "design_project")
            workflow = DesignWorkflowV2(
                project_name=project_name,
                hitl=self.hitl,
                wip_dir=self.wip_dir
            )

            # 執行完整流程
            result = await workflow.run_full_workflow(user_input)

            if result.get("status") == "success":
                return HandleResult(
                    success=True,
                    layer=Layer.EXPLORE,
                    data={
                        "archive_path": result.get("archive_path"),
                        "execution": result.get("execution"),
                    },
                    claude_calls=result.get("claude_calls", 3),
                    placement_info=result.get("placement_info"),
                    knowledge_source="design_workflow"
                )

            elif result.get("status") == "cancelled":
                return HandleResult(
                    success=False,
                    layer=Layer.EXPLORE,
                    errors=[f"用戶在 {result.get('phase', 'unknown')} 階段取消"],
                    claude_calls=result.get("claude_calls", 0),
                    knowledge_source="design_workflow"
                )

            else:
                return HandleResult(
                    success=False,
                    layer=Layer.EXPLORE,
                    errors=result.get("errors", ["Workflow incomplete"]),
                    data=result,
                    claude_calls=result.get("claude_calls", 0),
                    knowledge_source="design_workflow"
                )

        except ImportError:
            # DesignWorkflowV2 尚未實作
            return HandleResult(
                success=False,
                layer=Layer.EXPLORE,
                errors=["Layer 3 DesignWorkflowV2 not yet implemented"],
                data={
                    "detected_keywords": [
                        kw for kw in self.EXPLORATION_KEYWORDS
                        if kw.lower() in user_input.lower()
                    ]
                },
                claude_calls=0,
                knowledge_source="none"
            )

        except Exception as e:
            return HandleResult(
                success=False,
                layer=Layer.EXPLORE,
                errors=[f"Layer 3 workflow error: {str(e)}"],
                claude_calls=0,
                knowledge_source="none"
            )

    def _solution_to_placement(self, solution: Dict, experience: Dict) -> Dict:
        """
        將 Experience solution 轉換為 placement_info 格式

        placement_info 格式:
        {
            "components": [...],
            "connections": [...],
            "layout": {...},
            "_meta": {...}
        }
        """
        return {
            "components": solution.get("components", []),
            "connections": solution.get("connections", []),
            "layout": solution.get("layout", {}),
            "_meta": {
                "source": "golden_knowledge",
                "experience_id": experience.get("id"),
                "experience_name": experience.get("request"),
                "patterns_used": experience.get("learned_patterns", []),
            }
        }

    def _reference_to_placement(self, ref_config: Dict) -> Dict:
        """將 Reference Library 配置轉換為 placement_info 格式"""
        return {
            "components": ref_config.get("components", []),
            "connections": ref_config.get("connections", []),
            "layout": ref_config.get("layout", {}),
            "_meta": {
                "source": "reference_library",
                **ref_config.get("_meta", {})
            }
        }

    def _execute_placement(self, placement_info: Dict) -> Dict:
        """
        執行 placement_info

        如果有 MCP client，使用它執行
        否則返回模擬成功
        """
        if self.mcp_client is None:
            # 模擬執行 (用於測試)
            return {
                "success": True,
                "simulated": True,
                "components_created": len(placement_info.get("components", [])),
                "connections_made": len(placement_info.get("connections", [])),
            }

        # 使用 MCP client 執行
        try:
            # TODO: 實作 MCP 執行邏輯
            # 這裡需要調用 mcp_client 的方法
            return {"success": True}
        except Exception as e:
            return {"success": False, "errors": [str(e)]}

    def _learn_from_success(
        self,
        user_input: str,
        placement_info: Dict,
        exec_result: Dict
    ):
        """
        從成功執行中學習

        - 記錄連接模式
        - 更新使用統計
        """
        try:
            self.bridge.learn_from_workflow_result(
                request=user_input,
                workflow_json=placement_info,
                execution_report={"status": "success", **exec_result},
                context=f"Layer1 execution, source={placement_info.get('_meta', {}).get('source')}"
            )
        except Exception as e:
            # 學習失敗不影響主流程
            pass

    # =========================================================================
    # 統計與報告
    # =========================================================================

    def get_stats(self) -> Dict:
        """獲取統計資訊"""
        total = self._stats["total_requests"]
        return {
            **self._stats,
            "layer1_rate": self._stats["layer1_count"] / total if total > 0 else 0,
            "layer2_rate": self._stats["layer2_count"] / total if total > 0 else 0,
            "layer3_rate": self._stats["layer3_count"] / total if total > 0 else 0,
            "avg_claude_calls": self._stats["total_claude_calls"] / total if total > 0 else 0,
        }

    def reset_stats(self):
        """重置統計"""
        self._stats = {
            "total_requests": 0,
            "layer1_count": 0,
            "layer2_count": 0,
            "layer3_count": 0,
            "total_claude_calls": 0,
        }


# =============================================================================
# 便捷函數
# =============================================================================

def quick_handle(user_input: str, config_dir: str = "config") -> HandleResult:
    """
    快速處理請求

    Args:
        user_input: 用戶請求
        config_dir: 配置目錄

    Returns:
        HandleResult
    """
    handler = UnifiedHandler(config_dir=config_dir, auto_execute=False)
    return handler.handle(user_input)


def check_layer(user_input: str) -> Layer:
    """
    預測請求會使用哪個 Layer (不實際執行)

    Args:
        user_input: 用戶請求

    Returns:
        Layer enum
    """
    handler = UnifiedHandler(auto_execute=False)

    # 探索性需求
    if handler._needs_exploration(user_input):
        return Layer.EXPLORE

    # 搜尋知識庫
    knowledge = handler.bridge.search(user_input)

    # Golden 匹配
    if handler._is_golden_match(knowledge):
        return Layer.DIRECT

    # 其他
    return Layer.SUPPLEMENT


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("UnifiedHandler - 三層架構統一入口")
        print("=" * 50)
        print("\nUsage:")
        print("  python unified_handler.py '<request>'")
        print("\nExamples:")
        print("  python unified_handler.py '用 WASP 做立方體聚集'")
        print("  python unified_handler.py '幫我探索怎麼做階層式聚集'")
        print("  python unified_handler.py '做一個 10x10 的網格結構'")
        sys.exit(0)

    request = " ".join(sys.argv[1:])

    print(f"\n📝 請求: {request}")
    print("=" * 50)

    handler = UnifiedHandler(auto_execute=False)
    result = handler.handle(request)

    print(f"\n📊 結果:")
    print(f"  Layer: {result.layer.value}")
    print(f"  Success: {result.success}")
    print(f"  Claude calls: {result.claude_calls}")
    print(f"  Latency: {result.latency_ms:.1f}ms")
    print(f"  Knowledge source: {result.knowledge_source}")

    if result.errors:
        print(f"\n❌ Errors:")
        for e in result.errors:
            print(f"  - {e}")

    if result.warnings:
        print(f"\n⚠️ Warnings:")
        for w in result.warnings:
            print(f"  - {w}")

    if result.data:
        print(f"\n📦 Data:")
        print(json.dumps(result.data, indent=2, ensure_ascii=False))

    if result.placement_info:
        print(f"\n📋 Placement Info:")
        print(f"  Components: {len(result.placement_info.get('components', []))}")
        print(f"  Connections: {len(result.placement_info.get('connections', []))}")
