#!/usr/bin/env python3
"""
Experience-Driven Workflow - 經驗驅動工作流
==========================================

核心理念：
1. 經驗累積 - 從成功案例學習
2. HITL 協作 - 利用用戶專業知識
3. 按需搜尋 - 遇到未知再查
4. 三層知識 - Golden → Community → Personal

流程：
    用戶需求 → 語意解析 → 經驗搜尋 → [有經驗:確認執行 / 無經驗:HITL協作] → 執行 → 學習
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Awaitable

# 內部模組
from .experience_db import (
    ExperienceDB,
    Experience,
    KnowledgeResult,
    KnowledgeSource,
    DomainKnowledge,
)
from .hitl_collaborator import (
    HITLCollaborator,
    QuestionType,
    CollectedKnowledge,
)
from .knowledge_base import ConnectionKnowledgeBase
from .learning_agent import LearningAgent

# Vision 診斷（可選）
try:
    from .vision_diagnostic_client import (
        VisionDiagnosticClient,
        ExecutionDiagnosticHelper,
        DiagnosticLevel,
    )
    VISION_AVAILABLE = True
except ImportError:
    VISION_AVAILABLE = False


class WorkflowPhase(Enum):
    """工作流程階段"""
    PARSE = "parse"                      # 語意解析
    SEARCH_EXPERIENCE = "search_experience"  # 搜尋經驗
    CONFIRM_EXPERIENCE = "confirm_experience"  # 確認使用經驗
    COLLABORATE = "collaborate"          # HITL 協作
    PRE_CHECK = "pre_check"              # 預執行檢查
    EXECUTE = "execute"                  # 執行
    LEARN = "learn"                      # 學習
    COMPLETE = "complete"                # 完成
    FAILED = "failed"                    # 失敗


@dataclass
class ParsedRequest:
    """解析後的請求"""
    original_text: str
    keywords: List[str] = field(default_factory=list)
    task_type: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)
    unclear_points: List[str] = field(default_factory=list)


@dataclass
class WorkflowResult:
    """工作流程結果"""
    success: bool
    phase: WorkflowPhase
    request: str

    # 使用的經驗（如果有）
    experience_used: Optional[Experience] = None
    experience_source: Optional[KnowledgeSource] = None

    # 收集的知識
    collected_knowledge: List[Dict] = field(default_factory=list)

    # 執行結果
    execution_result: Optional[Dict] = None

    # 學習結果
    learned_experience_id: Optional[str] = None

    # 錯誤
    errors: List[str] = field(default_factory=list)

    # 診斷（如果有）
    diagnostic: Optional[Dict] = None


class ExperienceDrivenWorkflow:
    """
    經驗驅動工作流

    整合：
    - ExperienceDB (三層知識庫)
    - HITLCollaborator (人機協作)
    - ConnectionKnowledgeBase (連接知識)
    - LearningAgent (學習代理)
    - VisionDiagnosticClient (診斷，可選)
    """

    # 領域關鍵字（輕量語意解析）
    DOMAIN_KEYWORDS: Dict[str, List[str]] = {
        'wasp': ['wasp', '離散', '聚集', 'aggregation', 'part', 'module', '模組', '立方體', 'cube'],
        'structural': ['結構', 'karamba', 'beam', 'column', '柱', '樑', 'src', 'rc'],
        'solar': ['日照', 'ladybug', 'solar', 'shadow', '陰影', '遮陽'],
        'form_finding': ['kangaroo', '找形', '張力', 'tensile', 'membrane', '膜'],
        'regulation': ['法規', '建蔽率', '容積率', 'coverage', 'far', '退縮'],
        'geometry': ['voronoi', 'mesh', 'surface', 'curve', 'brep', '網格', '曲面'],
    }

    # 常見不明確點（需要詢問）
    COMMON_UNCLEAR_POINTS: Dict[str, List[str]] = {
        'wasp': ['組件數量', '聚集規則', '邊界限制'],
        'structural': ['結構類型', '柱子尺寸', '跨距'],
        'solar': ['法規公式', '道路寬度', '方位角'],
        'regulation': ['建蔽率', '容積率', '退縮距離'],
    }

    def __init__(
        self,
        storage_dir: str = "config",
        user_id: str = "default",
        user_callback: Optional[Callable[[str], Awaitable[str]]] = None,
        web_search_callback: Optional[Callable[[str], Awaitable[str]]] = None,
        mcp_client: Optional[Any] = None,
        auto_confirm: bool = False,
        enable_vision: bool = True,
    ):
        """
        Args:
            storage_dir: 儲存目錄
            user_id: 用戶 ID
            user_callback: 用戶互動回調
            web_search_callback: 網頁搜尋回調
            mcp_client: GH_MCP 客戶端
            auto_confirm: 自動確認模式
            enable_vision: 啟用 Vision 診斷
        """
        self.storage_dir = Path(storage_dir)
        self.user_id = user_id
        self.mcp = mcp_client
        self.auto_confirm = auto_confirm

        # 初始化三層知識庫
        self.experience_db = ExperienceDB(
            storage_dir=self.storage_dir,
            user_id=user_id
        )

        # 初始化 HITL 協作器
        self.hitl = HITLCollaborator(
            user_callback=user_callback,
            web_search_callback=web_search_callback,
            auto_mode=auto_confirm
        )

        # 連接知識庫
        self.connection_kb = ConnectionKnowledgeBase(storage_dir=self.storage_dir)

        # 學習代理
        self.learning_agent = LearningAgent(
            knowledge_base=self.connection_kb,
            storage_dir=self.storage_dir,
            auto_save=True
        )

        # Vision 診斷（可選）
        self.enable_vision = enable_vision and VISION_AVAILABLE
        if self.enable_vision:
            self.vision_client = VisionDiagnosticClient()
            self.diagnostic_helper = ExecutionDiagnosticHelper(self.vision_client)
        else:
            self.vision_client = None
            self.diagnostic_helper = None

    async def run(self, user_request: str, context: Optional[Dict] = None) -> WorkflowResult:
        """
        主執行流程

        Args:
            user_request: 用戶請求
            context: 額外上下文

        Returns:
            WorkflowResult
        """
        context = context or {}

        print(f"\n{'='*60}")
        print(f"📝 用戶請求: {user_request}")
        print(f"{'='*60}")

        # ========== Phase 1: 語意解析（輕量）==========
        print(f"\n🔍 Phase 1: 語意解析...")
        parsed = self._parse_request(user_request)
        print(f"  關鍵字: {parsed.keywords}")
        print(f"  任務類型: {parsed.task_type}")
        if parsed.unclear_points:
            print(f"  不明確點: {parsed.unclear_points}")

        # ========== Phase 2: 搜尋經驗庫 ==========
        print(f"\n📚 Phase 2: 搜尋經驗...")
        experience_result = self.experience_db.search(
            query=user_request,
            keywords=parsed.keywords,
            task_type=parsed.task_type
        )

        print(f"  來源: {experience_result.source.value}")
        print(f"  可靠度: {experience_result.reliability}")

        # ========== Phase 3: 根據搜尋結果決定路徑 ==========
        if experience_result.source != KnowledgeSource.NONE:
            # 有經驗 → 確認後使用
            return await self._run_with_experience(
                parsed=parsed,
                experience_result=experience_result,
                context=context
            )
        else:
            # 沒經驗 → HITL 協作
            return await self._run_collaborative(
                parsed=parsed,
                context=context
            )

    async def _run_with_experience(
        self,
        parsed: ParsedRequest,
        experience_result: KnowledgeResult,
        context: Dict
    ) -> WorkflowResult:
        """使用經驗執行"""

        experience = experience_result.content
        if not experience:
            return WorkflowResult(
                success=False,
                phase=WorkflowPhase.SEARCH_EXPERIENCE,
                request=parsed.original_text,
                errors=["經驗內容為空"]
            )

        # ========== Phase 3a: 確認使用經驗 ==========
        print(f"\n✨ Phase 3: 確認使用經驗...")
        print(f"  找到: {experience.request}")
        print(f"  來源: {experience_result.source.value} ({experience_result.reliability})")

        if not self.auto_confirm:
            confirmed = await self.hitl.confirm(
                f"找到類似案例:\n"
                f"  📋 {experience.request}\n"
                f"  📊 成功率: {experience.success_rate:.0%}\n"
                f"  🏷️ 來源: {experience_result.source.value}\n\n"
                f"使用這個方案？"
            )

            if not confirmed:
                print("  用戶選擇不使用，改為協作模式")
                return await self._run_collaborative(parsed, context)

        # ========== Phase 4: 執行 ==========
        print(f"\n🚀 Phase 4: 執行...")
        exec_result = await self._execute_solution(experience.solution)

        if not exec_result.get("success"):
            # 執行失敗
            errors = exec_result.get("errors", [])
            diagnostic = None

            # Vision 診斷
            if self.enable_vision and self.diagnostic_helper and errors:
                print(f"\n🔍 執行失敗，調用 Vision 診斷...")
                diagnostic = self.diagnostic_helper.diagnose_execution_failure(
                    config=experience.solution,
                    errors=errors,
                    level=DiagnosticLevel.STANDARD
                )

            # 記錄失敗
            self.experience_db.record_failure(
                request=parsed.original_text,
                error="; ".join(errors),
                diagnostic=diagnostic
            )

            return WorkflowResult(
                success=False,
                phase=WorkflowPhase.EXECUTE,
                request=parsed.original_text,
                experience_used=experience,
                experience_source=experience_result.source,
                errors=errors,
                diagnostic=diagnostic
            )

        # ========== Phase 5: 學習 ==========
        print(f"\n🧠 Phase 5: 更新經驗...")
        # 更新使用統計
        learned_exp = self.experience_db.learn(
            request=parsed.original_text,
            solution=experience.solution,
            domain_knowledge=experience.domain_knowledge,
            patterns_used=experience.learned_patterns
        )

        print(f"\n{'='*60}")
        print(f"✅ 執行成功（使用 {experience_result.source.value} 經驗）")
        print(f"{'='*60}")

        return WorkflowResult(
            success=True,
            phase=WorkflowPhase.COMPLETE,
            request=parsed.original_text,
            experience_used=experience,
            experience_source=experience_result.source,
            execution_result=exec_result,
            learned_experience_id=learned_exp.id
        )

    async def _run_collaborative(
        self,
        parsed: ParsedRequest,
        context: Dict
    ) -> WorkflowResult:
        """協作式執行（沒有經驗時）"""

        print(f"\n🤝 Phase 3: HITL 協作...")
        print(f"  沒有找到匹配經驗，開始協作式設計")

        # ========== 收集領域知識 ==========
        collected_knowledge = {}

        # 從不明確點收集
        if parsed.unclear_points:
            print(f"\n  需要澄清 {len(parsed.unclear_points)} 個問題：")

            for point in parsed.unclear_points:
                # 先查經驗庫有沒有相關知識
                existing = self.experience_db.search_knowledge(point)
                existing_value = existing.value if existing else None

                knowledge = await self.hitl.collect_knowledge(
                    topic=point,
                    context=parsed.original_text,
                    existing_knowledge=existing_value,
                    allow_search=True
                )

                collected_knowledge[point] = knowledge.value
                print(f"    ✓ {point}: {knowledge.value[:50]}...")

        # ========== 生成解決方案 ==========
        print(f"\n⚙️ Phase 4: 生成解決方案...")

        # 基於收集的知識生成方案
        solution = await self._generate_solution(
            parsed=parsed,
            collected_knowledge=collected_knowledge,
            context=context
        )

        if not solution:
            return WorkflowResult(
                success=False,
                phase=WorkflowPhase.COLLABORATE,
                request=parsed.original_text,
                collected_knowledge=self.hitl.get_collected_knowledge_list(),
                errors=["無法生成解決方案"]
            )

        # ========== 確認方案 ==========
        if not self.auto_confirm:
            patterns_used = solution.get("patterns_used", [])
            components = solution.get("components", [])

            confirmed = await self.hitl.confirm_workflow(
                workflow_description=f"基於您提供的知識生成的 {parsed.task_type} 工作流",
                patterns_used=patterns_used,
                estimated_components=len(components),
                user_inputs_needed=list(collected_knowledge.keys())
            )

            if not confirmed:
                return WorkflowResult(
                    success=False,
                    phase=WorkflowPhase.COLLABORATE,
                    request=parsed.original_text,
                    collected_knowledge=self.hitl.get_collected_knowledge_list(),
                    errors=["用戶取消"]
                )

        # ========== 執行 ==========
        print(f"\n🚀 Phase 5: 執行...")
        exec_result = await self._execute_solution(solution)

        if not exec_result.get("success"):
            errors = exec_result.get("errors", [])
            diagnostic = None

            # Vision 診斷
            if self.enable_vision and self.diagnostic_helper and errors:
                diagnostic = self.diagnostic_helper.diagnose_execution_failure(
                    config=solution,
                    errors=errors,
                    level=DiagnosticLevel.STANDARD
                )

            return WorkflowResult(
                success=False,
                phase=WorkflowPhase.EXECUTE,
                request=parsed.original_text,
                collected_knowledge=self.hitl.get_collected_knowledge_list(),
                errors=errors,
                diagnostic=diagnostic
            )

        # ========== 學習新經驗 ==========
        print(f"\n🧠 Phase 6: 學習新經驗...")

        # 將收集的知識轉換為 domain_knowledge 格式
        domain_knowledge_list = [
            {"key": k, "value": v, "source": "user_provided"}
            for k, v in collected_knowledge.items()
        ]

        learned_exp = self.experience_db.learn(
            request=parsed.original_text,
            solution=solution,
            domain_knowledge=domain_knowledge_list,
            patterns_used=solution.get("patterns_used", [])
        )

        print(f"  ✅ 新經驗已儲存: {learned_exp.id}")

        # 詢問是否分享到社群
        if not self.auto_confirm:
            share = await self.hitl.confirm(
                "這個解決方案運作良好！是否分享到社群幫助其他用戶？",
                default=False
            )

            if share:
                self.experience_db.share_to_community(learned_exp.id)
                print(f"  🌐 已分享到社群")

        print(f"\n{'='*60}")
        print(f"✅ 協作式執行成功（新經驗已學習）")
        print(f"{'='*60}")

        return WorkflowResult(
            success=True,
            phase=WorkflowPhase.COMPLETE,
            request=parsed.original_text,
            collected_knowledge=self.hitl.get_collected_knowledge_list(),
            execution_result=exec_result,
            learned_experience_id=learned_exp.id
        )

    # =========================================================================
    # 輔助方法
    # =========================================================================

    def _parse_request(self, text: str) -> ParsedRequest:
        """輕量語意解析"""
        text_lower = text.lower()
        keywords = []
        task_type = "general"

        # 提取關鍵字
        for category, kws in self.DOMAIN_KEYWORDS.items():
            for kw in kws:
                if kw.lower() in text_lower:
                    keywords.append(kw.lower())
                    if task_type == "general":
                        task_type = category

        # 提取數字實體
        entities = {}
        import re
        numbers = re.findall(r'(\d+)\s*個?', text)
        if numbers:
            entities["count"] = int(numbers[0])

        # 識別不明確點
        unclear_points = []
        for point in self.COMMON_UNCLEAR_POINTS.get(task_type, []):
            # 如果在文本中沒有明確提到，加入不明確點
            point_lower = point.lower()
            if point_lower not in text_lower:
                unclear_points.append(point)

        return ParsedRequest(
            original_text=text,
            keywords=keywords,
            task_type=task_type,
            entities=entities,
            unclear_points=unclear_points[:3]  # 最多 3 個問題
        )

    async def _generate_solution(
        self,
        parsed: ParsedRequest,
        collected_knowledge: Dict[str, str],
        context: Dict
    ) -> Optional[Dict]:
        """生成解決方案"""

        # 根據任務類型和收集的知識生成方案
        # TODO: 這裡可以整合 LLM 或規則引擎

        # 暫時使用基礎模板
        if parsed.task_type == "wasp":
            return self._generate_wasp_solution(parsed, collected_knowledge)
        elif parsed.task_type == "structural":
            return self._generate_structural_solution(parsed, collected_knowledge)
        else:
            # 通用模板
            return {
                "task_type": parsed.task_type,
                "patterns_used": [],
                "components": [],
                "connections": [],
                "parameters": collected_knowledge,
                "generated": True
            }

    def _generate_wasp_solution(
        self,
        parsed: ParsedRequest,
        knowledge: Dict[str, str]
    ) -> Dict:
        """生成 WASP 解決方案"""

        count = parsed.entities.get("count", 3)

        return {
            "task_type": "wasp",
            "patterns_used": ["wasp_basic_aggregation"],
            "components": [
                {"type": "Mesh Box", "nickname": "Geometry"},
                {"type": "WASP Connection From Direction", "nickname": "Connections"},
                {"type": "WASP Part", "nickname": "Part"},
                {"type": "WASP Stochastic Aggregation", "nickname": "Aggregation"},
            ],
            "connections": [
                {"from": "Geometry.M", "to": "Part.GEO"},
                {"from": "Connections.CONN", "to": "Part.CONN"},
                {"from": "Part.PART", "to": "Aggregation.PART"},
            ],
            "parameters": {
                "part_count": count,
                "aggregation_count": 50,
                **knowledge
            },
            "generated": True
        }

    def _generate_structural_solution(
        self,
        parsed: ParsedRequest,
        knowledge: Dict[str, str]
    ) -> Dict:
        """生成結構解決方案"""

        return {
            "task_type": "structural",
            "patterns_used": ["structural_grid_basic"],
            "components": [
                {"type": "Rectangle Grid", "nickname": "Grid"},
                {"type": "Line", "nickname": "Columns"},
                {"type": "Extrude", "nickname": "ColumnVolume"},
            ],
            "connections": [
                {"from": "Grid.Pt", "to": "Columns.A"},
            ],
            "parameters": knowledge,
            "generated": True
        }

    async def _execute_solution(self, solution: Dict) -> Dict:
        """執行解決方案"""

        if self.mcp is None:
            # 模擬執行
            print("  ⚠️ 無 MCP Client，模擬執行")

            components = solution.get("components", [])
            connections = solution.get("connections", [])

            for comp in components[:5]:
                print(f"    ➕ add_component({comp.get('type')})")

            if len(components) > 5:
                print(f"    ... 還有 {len(components) - 5} 個組件")

            print(f"    🔗 建立 {len(connections)} 條連接")

            return {"success": True, "simulated": True}

        # 實際執行
        try:
            # TODO: 整合 MCP 執行邏輯
            return {"success": True}
        except Exception as e:
            return {"success": False, "errors": [str(e)]}


# =============================================================================
# CLI
# =============================================================================

async def cli_callback(prompt: str) -> str:
    """CLI 回調"""
    print(prompt)
    try:
        return input("> ").strip()
    except EOFError:
        return ""


async def main():
    """測試入口"""
    print("Experience-Driven Workflow 測試")
    print("=" * 60)

    workflow = ExperienceDrivenWorkflow(
        storage_dir="config",
        user_id="test_user",
        user_callback=cli_callback,
        auto_confirm=False,
        enable_vision=False  # 測試時禁用
    )

    # 測試案例
    test_cases = [
        "做一個 WASP 立方體聚集，3個組件",
        "做一個結構柱網系統",
    ]

    for request in test_cases[:1]:  # 只測試第一個
        print(f"\n{'='*60}")
        print(f"測試: {request}")
        print(f"{'='*60}")

        result = await workflow.run(request)

        print(f"\n結果: {'✅ 成功' if result.success else '❌ 失敗'}")
        print(f"階段: {result.phase.value}")

        if result.collected_knowledge:
            print(f"收集的知識:")
            for k in result.collected_knowledge:
                print(f"  {k['key']}: {k['value']}")


if __name__ == "__main__":
    asyncio.run(main())
