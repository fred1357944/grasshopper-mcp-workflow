#!/usr/bin/env python3
"""
Dual-Mode Workflow - 雙軌智能工作流程
=====================================

整合 Intent Router、Workflow Mode、Meta-Agent 的完整工作流程。

架構：
    ┌─────────────────────────────────────────┐
    │  Intent Router                          │
    │  • 分析請求 → 計算信心度 → 選擇模式     │
    └─────────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
    Workflow Mode              Meta-Agent Mode
    (確定性管線)                (彈性探索)

Usage:
    from grasshopper_mcp.dual_mode_workflow import DualModeWorkflow

    workflow = DualModeWorkflow()
    result = await workflow.run("做一個 WASP 離散聚集")
"""

import json
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from pathlib import Path

from .intent_router import IntentRouter, ProcessingMode, RoutingResult
from .meta_agent import MetaAgent


class WorkflowPhase(Enum):
    """工作流程階段"""
    # 共享階段
    ROUTING = "routing"

    # Workflow Mode 階段
    CLARIFY = "clarify"
    DECOMPOSE = "decompose"
    PLAN = "plan"
    QUERY = "query"
    PRE_CHECK = "pre_check"
    EXECUTE = "execute"
    ARCHIVE = "archive"

    # Meta-Agent Mode 階段
    EXPLORE = "explore"
    ASK = "ask"
    SYNTHESIZE = "synthesize"

    # 結束
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class WorkflowState:
    """工作流程狀態"""
    # 基本資訊
    request: str = ""
    mode: ProcessingMode = ProcessingMode.WORKFLOW
    current_phase: WorkflowPhase = WorkflowPhase.ROUTING

    # Router 結果
    routing_result: Optional[RoutingResult] = None

    # Workflow Mode 狀態
    design_intent: Dict = field(default_factory=dict)
    component_list: List[str] = field(default_factory=list)
    placement_info: Dict = field(default_factory=dict)
    check_passed: bool = False

    # Meta-Agent Mode 狀態
    search_results: List[Dict] = field(default_factory=list)
    questions_asked: List[Dict] = field(default_factory=list)
    user_answers: List[str] = field(default_factory=list)
    synthesized_pattern: Optional[Dict] = None

    # 執行結果
    execution_log: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    output_path: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'request': self.request,
            'mode': self.mode.value,
            'phase': self.current_phase.value,
            'routing': self.routing_result.to_dict() if self.routing_result else None,
            'check_passed': self.check_passed,
            'errors': self.errors
        }


class DualModeWorkflow:
    """
    雙軌智能工作流程

    根據請求特性自動選擇：
    - Workflow Mode: 確定性管線，適合已知模式
    - Meta-Agent Mode: 彈性探索，適合未知情況
    """

    def __init__(
        self,
        config_dir: str = "config",
        ghx_skill_db: Optional[str] = None,
        wip_dir: str = "GH_WIP"
    ):
        """
        初始化雙軌工作流程

        Args:
            config_dir: 配置目錄
            ghx_skill_db: GHX Skill 資料庫
            wip_dir: 工作目錄
        """
        self.config_dir = Path(config_dir)
        self.wip_dir = Path(wip_dir)
        self.wip_dir.mkdir(exist_ok=True)

        # 初始化組件
        self.router = IntentRouter(config_dir=self.config_dir)
        self.meta_agent = MetaAgent(
            ghx_skill_db=ghx_skill_db,
            config_dir=str(config_dir)
        )

        # 載入配置
        self.patterns: Dict = {}
        self.trusted_guids: Dict = {}
        self._load_configs()

        # 狀態
        self.state = WorkflowState()

        # 回調函數（用於與外部系統整合）
        self.on_phase_change: Optional[Callable] = None
        self.on_question: Optional[Callable] = None
        self.on_execute: Optional[Callable] = None

    def _load_configs(self):
        """載入配置"""
        patterns_path = self.config_dir / "connection_patterns.json"
        if patterns_path.exists():
            with open(patterns_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.patterns = data.get("patterns", {})

        guids_path = self.config_dir / "trusted_guids.json"
        if guids_path.exists():
            with open(guids_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.trusted_guids = data.get("components", {})

    async def run(
        self,
        request: str,
        auto_execute: bool = False,
        user_callback: Optional[Callable] = None
    ) -> Dict:
        """
        執行雙軌工作流程

        Args:
            request: 用戶請求
            auto_execute: 是否自動執行
            user_callback: 用戶輸入回調

        Returns:
            工作流程結果
        """
        self.state = WorkflowState(request=request)
        result = {"phases": [], "final_state": None}

        try:
            # Phase 0: Routing
            self._set_phase(WorkflowPhase.ROUTING)
            routing_result = self._phase_routing(request)
            result["phases"].append({"routing": routing_result})

            # 根據模式執行
            if self.state.mode == ProcessingMode.WORKFLOW:
                workflow_result = await self._run_workflow_mode(auto_execute)
                result["phases"].append({"workflow": workflow_result})

            elif self.state.mode == ProcessingMode.META_AGENT:
                meta_result = await self._run_meta_agent_mode(user_callback)
                result["phases"].append({"meta_agent": meta_result})

            else:  # HYBRID
                # 先嘗試 Workflow，失敗則切換到 Meta-Agent
                workflow_result = await self._run_workflow_mode(auto_execute)
                result["phases"].append({"workflow": workflow_result})

                if not self.state.check_passed:
                    print("Workflow Mode 未通過，切換到 Meta-Agent...")
                    meta_result = await self._run_meta_agent_mode(user_callback)
                    result["phases"].append({"meta_agent": meta_result})

            self._set_phase(WorkflowPhase.COMPLETE)

        except Exception as e:
            self.state.errors.append(str(e))
            self._set_phase(WorkflowPhase.FAILED)

        result["final_state"] = self.state.to_dict()
        return result

    def _set_phase(self, phase: WorkflowPhase):
        """設置當前階段"""
        self.state.current_phase = phase
        if self.on_phase_change:
            self.on_phase_change(phase)

    # ========== Routing ==========

    def _phase_routing(self, request: str) -> Dict:
        """
        Phase 0: 意圖路由
        """
        result = self.router.route(request)
        self.state.routing_result = result
        self.state.mode = result.mode

        print(f"\n【Routing】")
        print(f"  模式: {result.mode.value}")
        print(f"  信心度: {result.confidence:.2f}")
        print(f"  意圖: {result.intent_type.value}")
        print(f"  插件: {result.target_plugins}")
        print(f"  匹配模式: {result.matched_patterns}")

        return result.to_dict()

    # ========== Workflow Mode ==========

    async def _run_workflow_mode(self, auto_execute: bool) -> Dict:
        """執行 Workflow Mode"""
        result = {}

        # Phase 1: Clarify
        self._set_phase(WorkflowPhase.CLARIFY)
        result["clarify"] = self._workflow_clarify()

        # Phase 2: Plan
        self._set_phase(WorkflowPhase.PLAN)
        result["plan"] = self._workflow_plan()

        # Phase 3: Query
        self._set_phase(WorkflowPhase.QUERY)
        result["query"] = self._workflow_query()

        # Phase 4: Pre-Check
        self._set_phase(WorkflowPhase.PRE_CHECK)
        result["pre_check"] = self._workflow_pre_check()

        # Phase 5: Execute (if passed)
        if self.state.check_passed:
            if auto_execute or self._confirm_execute():
                self._set_phase(WorkflowPhase.EXECUTE)
                result["execute"] = await self._workflow_execute()

        # Phase 6: Archive
        self._set_phase(WorkflowPhase.ARCHIVE)
        result["archive"] = self._workflow_archive()

        return result

    def _workflow_clarify(self) -> Dict:
        """Workflow Phase 1: 需求釐清"""
        routing = self.state.routing_result

        self.state.design_intent = {
            "keywords": routing.keywords if routing else [],
            "plugins": routing.target_plugins if routing else [],
            "patterns": routing.matched_patterns if routing else [],
            "intent_type": routing.intent_type.value if routing else "unknown"
        }

        print(f"\n【Phase 1: Clarify】")
        print(f"  關鍵字: {self.state.design_intent['keywords']}")
        print(f"  插件: {self.state.design_intent['plugins']}")

        return self.state.design_intent

    def _workflow_plan(self) -> Dict:
        """Workflow Phase 2: 組件規劃"""
        # 從匹配的模式獲取組件
        components = set()

        for pattern_name in self.state.design_intent.get("patterns", []):
            if pattern_name in self.patterns:
                pattern = self.patterns[pattern_name]
                components.update(pattern.get("components", []))

        self.state.component_list = list(components)

        print(f"\n【Phase 2: Plan】")
        print(f"  組件數量: {len(self.state.component_list)}")
        if self.state.component_list:
            print(f"  組件: {self.state.component_list[:5]}...")

        return {"components": self.state.component_list}

    def _workflow_query(self) -> Dict:
        """Workflow Phase 3: GUID 查詢"""
        placement_info = {
            "version": "2.0",
            "design_intent": self.state.design_intent,
            "components": [],
            "connections": [],
            "mcp_calls": [
                {"command": "clear_document"},
                {"command": "add_component"},
                {"command": "connect_components"}
            ]
        }

        # 添加組件（帶 GUID）
        for i, comp_name in enumerate(self.state.component_list):
            comp_info = self.trusted_guids.get(comp_name, {})
            component = {
                "id": f"comp_{i}",
                "type": comp_name,
                "nickname": comp_name,
                "position": {"x": 100 + (i % 5) * 150, "y": 100 + (i // 5) * 100}
            }
            if comp_info.get("guid"):
                component["guid"] = comp_info["guid"]

            placement_info["components"].append(component)

        # 從模式獲取連接
        for pattern_name in self.state.design_intent.get("patterns", []):
            if pattern_name in self.patterns:
                pattern = self.patterns[pattern_name]
                for wire in pattern.get("wiring", []):
                    placement_info["connections"].append({
                        "source": wire.get("from"),
                        "target": wire.get("to"),
                        "fromParamIndex": wire.get("fromParam", 0),
                        "toParamIndex": wire.get("toParam", 0)
                    })

        self.state.placement_info = placement_info

        # 保存
        output_path = self.wip_dir / "placement_info.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(placement_info, f, indent=2, ensure_ascii=False)

        print(f"\n【Phase 3: Query】")
        print(f"  組件: {len(placement_info['components'])}")
        print(f"  連接: {len(placement_info['connections'])}")

        return {
            "path": str(output_path),
            "components": len(placement_info["components"]),
            "connections": len(placement_info["connections"])
        }

    def _workflow_pre_check(self) -> Dict:
        """Workflow Phase 4: Pre-Execution Check"""
        try:
            from .pre_execution_checker import PreExecutionChecker

            checker = PreExecutionChecker(self.config_dir)
            checker.check_placement_info(self.state.placement_info)
            report = checker.generate_report()

            # Check for critical issues
            critical_count = len([r for r in checker.results if r.severity == "critical"])
            self.state.check_passed = critical_count == 0

            print(f"\n【Phase 4: Pre-Check】")
            print(report)

            return {
                "passed": self.state.check_passed,
                "critical": critical_count,
                "warnings": len([r for r in checker.results if r.severity == "warning"]),
                "report": report
            }
        except ImportError:
            print("Pre-Execution Checker 未安裝，跳過驗證")
            self.state.check_passed = True
            return {"passed": True, "skipped": True}

    def _confirm_execute(self) -> bool:
        """確認執行"""
        try:
            response = input("\n繼續執行？(Y/N): ")
            return response.lower() == 'y'
        except Exception:
            return False

    async def _workflow_execute(self) -> Dict:
        """Workflow Phase 5: 執行"""
        print(f"\n【Phase 5: Execute】")

        # 實際執行（如果有 on_execute 回調）
        if self.on_execute:
            await self.on_execute(self.state.placement_info)
        else:
            # 模擬執行
            for comp in self.state.placement_info.get("components", []):
                log = f"add_component({comp['type']})"
                self.state.execution_log.append(log)
                print(f"  {log}")

            for conn in self.state.placement_info.get("connections", []):
                log = f"connect({conn['source']} -> {conn['target']})"
                self.state.execution_log.append(log)
                print(f"  {log}")

        return {"log": self.state.execution_log}

    def _workflow_archive(self) -> Dict:
        """Workflow Phase 6: 歸檔"""
        import datetime

        archive = {
            "timestamp": datetime.datetime.now().isoformat(),
            "request": self.state.request,
            "mode": self.state.mode.value,
            "design_intent": self.state.design_intent,
            "check_passed": self.state.check_passed,
            "execution_log": self.state.execution_log,
            "errors": self.state.errors
        }

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.wip_dir / f"archive_{timestamp}.json"

        with open(archive_path, 'w', encoding='utf-8') as f:
            json.dump(archive, f, indent=2, ensure_ascii=False)

        self.state.output_path = str(archive_path)

        print(f"\n【Phase 6: Archive】")
        print(f"  路徑: {archive_path}")

        return {"path": str(archive_path)}

    # ========== Meta-Agent Mode ==========

    async def _run_meta_agent_mode(
        self,
        user_callback: Optional[Callable] = None
    ) -> Dict:
        """執行 Meta-Agent Mode"""
        result = {}

        # Phase 1: Explore (搜尋)
        self._set_phase(WorkflowPhase.EXPLORE)
        result["explore"] = await self._meta_explore()

        # Phase 2: Ask (提問)
        self._set_phase(WorkflowPhase.ASK)
        result["ask"] = await self._meta_ask(user_callback)

        # Phase 3: Synthesize (合成)
        routing = self.state.routing_result
        if routing and len(routing.matched_patterns) >= 2:
            self._set_phase(WorkflowPhase.SYNTHESIZE)
            result["synthesize"] = self._meta_synthesize()

        # 如果成功合成，嘗試走 Workflow
        if self.state.synthesized_pattern:
            print("\n模式合成成功，切換到 Workflow Mode...")

            # 更新 design_intent
            self.state.design_intent["patterns"] = [
                self.state.synthesized_pattern["name"]
            ]
            self.state.component_list = self.state.synthesized_pattern.get(
                "components", []
            )

            # 繼續 Workflow
            result["workflow"] = await self._run_workflow_mode(auto_execute=False)

        return result

    async def _meta_explore(self) -> Dict:
        """Meta-Agent Phase 1: 探索"""
        print(f"\n【Meta-Agent: Explore】")

        search_results = await self.meta_agent.search(self.state.request)

        self.state.search_results = [
            {
                "source": r.source,
                "item": r.item,
                "score": r.score,
                "details": r.details
            }
            for r in search_results
        ]

        print(f"  找到 {len(search_results)} 個相關結果:")
        for r in search_results[:3]:
            print(f"    [{r.source}] {r.item} ({r.score:.2f})")

        return {"results": self.state.search_results}

    async def _meta_ask(self, user_callback: Optional[Callable] = None) -> Dict:
        """Meta-Agent Phase 2: 提問"""
        print(f"\n【Meta-Agent: Ask】")

        routing = self.state.routing_result
        questions = routing.questions if routing else []

        if not questions:
            # 生成問題
            question = self.meta_agent.ask_user(
                intent_type=routing.intent_type.value if routing else "unknown",
                context={
                    "target_plugins": routing.target_plugins if routing else [],
                    "search_results": len(self.state.search_results)
                }
            )
            questions = [question.text]

        for q in questions:
            print(f"  問題: {q}")
            self.state.questions_asked.append({"text": q})

            if user_callback:
                answer = await user_callback(q)
            elif self.on_question:
                answer = self.on_question(q)
            else:
                try:
                    answer = input("  回答: ")
                except Exception:
                    answer = ""

            self.state.user_answers.append(answer)

        return {
            "questions": self.state.questions_asked,
            "answers": self.state.user_answers
        }

    def _meta_synthesize(self) -> Dict:
        """Meta-Agent Phase 3: 合成"""
        print(f"\n【Meta-Agent: Synthesize】")

        patterns = self.state.routing_result.matched_patterns[:2]
        synthesized = self.meta_agent.synthesize(patterns)

        if synthesized:
            self.state.synthesized_pattern = {
                "name": synthesized.name,
                "description": synthesized.description,
                "components": synthesized.components,
                "confidence": synthesized.confidence
            }

            # 添加到 patterns（臨時）
            self.patterns[synthesized.name] = {
                "description": synthesized.description,
                "components": synthesized.components,
                "wiring": synthesized.connections,
                "plugins": list(set(
                    p for pat in patterns
                    for p in self.patterns.get(pat, {}).get("plugins", [])
                ))
            }

            print(f"  合成模式: {synthesized.name}")
            print(f"  組件數: {len(synthesized.components)}")
            print(f"  信心度: {synthesized.confidence:.2f}")

        return {"pattern": self.state.synthesized_pattern}


# ============================================================================
# 便捷函數
# ============================================================================

def create_dual_mode_workflow(
    config_dir: str = "config",
    ghx_skill_db: Optional[str] = None
) -> DualModeWorkflow:
    """創建雙軌工作流程實例"""
    return DualModeWorkflow(
        config_dir=config_dir,
        ghx_skill_db=ghx_skill_db
    )


async def run_workflow(request: str, **kwargs) -> Dict:
    """快速執行工作流程"""
    workflow = create_dual_mode_workflow(**kwargs)
    return await workflow.run(request)


# ============================================================================
# CLI
# ============================================================================

async def main():
    """命令行測試"""
    import sys

    test_requests = [
        "做一個 WASP 離散聚集",
        "幫我分析日照",
        "結合 Ladybug 和 WASP 做設計",
        "這個設計有錯誤",
        "做個東西",
    ]

    if len(sys.argv) > 1:
        test_requests = [" ".join(sys.argv[1:])]

    workflow = DualModeWorkflow()

    print("=" * 60)
    print("Dual-Mode Workflow 測試")
    print("=" * 60)

    for request in test_requests[:1]:  # 只測試第一個
        print(f"\n{'='*60}")
        print(f"請求: {request}")
        print("=" * 60)

        result = await workflow.run(request, auto_execute=True)

        print(f"\n【最終結果】")
        print(f"  模式: {result['final_state']['mode']}")
        print(f"  階段: {result['final_state']['phase']}")
        print(f"  驗證: {'通過' if result['final_state']['check_passed'] else '未通過'}")


if __name__ == "__main__":
    asyncio.run(main())
