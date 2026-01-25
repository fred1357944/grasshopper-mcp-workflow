#!/usr/bin/env python3
"""
Dual-Mode Workflow - 三軌智能工作流程
=====================================

整合 Reference Mode、Intent Router、Workflow Mode、Meta-Agent 的完整工作流程。

架構（優先順序從上到下）：
    ┌─────────────────────────────────────────┐
    │  Phase 0: Reference Search               │
    │  → 優先搜索 Reference Library            │
    │  → 有匹配則直接使用 Golden Config        │
    └─────────────────────────────────────────┘
                      │
           [有高信心匹配] ──────────────────┐
                      │                      │
                      ↓                      ↓
    ┌─────────────────────────────────┐    Reference Mode
    │  Intent Router                   │    (確認 → 複製 → 微調)
    │  • 分析請求 → 計算信心度         │
    └─────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
    Workflow Mode              Meta-Agent Mode
    (確定性管線)                (彈性探索)

核心理念：
    Reference Mode: 「找到 → 確認 → 複製 → 微調」
    vs 舊的: 「猜測 → 失敗 → 調試 → 重複」

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
from datetime import datetime

from .intent_router import IntentRouter, ProcessingMode, RoutingResult
from .meta_agent import MetaAgent
from .reference_mode import ReferenceMode, ReferenceMatch


# ============================================================================
# Pattern Library 學習機制
# ============================================================================

@dataclass
class PatternEntry:
    """Pattern Library 條目"""
    id: str
    name: str
    path: str
    keywords: List[str]
    description: str
    confidence: float = 0.0
    success_count: int = 0
    last_success: Optional[str] = None
    is_golden: bool = False
    source: str = "workflow"  # "workflow" | "reference" | "meta_agent"

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "keywords": self.keywords,
            "description": self.description,
            "confidence": self.confidence,
            "success_count": self.success_count,
            "last_success": self.last_success,
            "is_golden": self.is_golden,
            "source": self.source
        }


class PatternLibrary:
    """
    Pattern Library - 學習與升級機制

    流程：
    1. 成功執行 → 存入 patterns/
    2. 追蹤 success_count
    3. 連續成功 3 次 → 升級到 golden/
    """

    PROMOTION_THRESHOLD = 3  # 升級所需連續成功次數

    def __init__(self, library_path: str = "reference_library"):
        self.library_path = Path(library_path)
        self.library_path.mkdir(exist_ok=True)

    def save_pattern(
        self,
        placement_info: Dict,
        request: str,
        plugin: str = "general",
        source: str = "workflow"
    ) -> PatternEntry:
        """
        保存成功的 pattern 到 Pattern Library

        Args:
            placement_info: 部署配置
            request: 原始請求
            plugin: 目標插件
            source: 來源模式

        Returns:
            PatternEntry
        """
        plugin_dir = self.library_path / plugin
        patterns_dir = plugin_dir / "patterns"
        patterns_dir.mkdir(parents=True, exist_ok=True)

        # 生成 ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pattern_id = f"pattern_{timestamp}"

        # 提取關鍵字
        keywords = self._extract_keywords(request)

        # 創建 pattern 文件
        pattern_data = {
            "_meta": {
                "id": pattern_id,
                "name": f"Pattern from: {request[:50]}",
                "created": datetime.now().isoformat(),
                "source": source,
                "original_request": request
            },
            "components": placement_info.get("components", []),
            "connections": placement_info.get("connections", []),
            "layout": placement_info.get("layout", {}),
            "_tracking": {
                "success_count": 1,
                "last_success": datetime.now().isoformat(),
                "confidence": 0.5
            }
        }

        pattern_path = patterns_dir / f"{pattern_id}.json"
        with open(pattern_path, 'w', encoding='utf-8') as f:
            json.dump(pattern_data, f, indent=2, ensure_ascii=False)

        # 更新 metadata.json
        entry = PatternEntry(
            id=pattern_id,
            name=pattern_data["_meta"]["name"],
            path=f"patterns/{pattern_id}.json",
            keywords=keywords,
            description=f"Auto-generated from: {request}",
            confidence=0.5,
            success_count=1,
            last_success=datetime.now().isoformat(),
            source=source
        )

        self._update_metadata(plugin_dir, entry)

        print(f"  📚 Pattern 已保存: {pattern_path}")
        return entry

    def record_success(
        self,
        plugin: str,
        pattern_id: str
    ) -> Optional[PatternEntry]:
        """
        記錄成功執行，檢查是否需要升級

        Args:
            plugin: 插件名稱
            pattern_id: Pattern ID

        Returns:
            更新後的 PatternEntry，如果升級則 is_golden=True
        """
        plugin_dir = self.library_path / plugin
        metadata_path = plugin_dir / "metadata.json"

        if not metadata_path.exists():
            return None

        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        # 在 variations 和 golden_configs 中查找
        entry = None
        entry_index = None

        for i, var in enumerate(metadata.get("variations", [])):
            if var["id"] == pattern_id:
                entry = var
                entry_index = i
                break

        if not entry:
            # 檢查 golden_configs（已經是 golden，不需要再升級）
            for gc in metadata.get("golden_configs", []):
                if gc["id"] == pattern_id:
                    return PatternEntry(
                        id=gc["id"],
                        name=gc.get("name", ""),
                        path=gc.get("path", ""),
                        keywords=gc.get("keywords", []),
                        description=gc.get("description", ""),
                        confidence=gc.get("confidence", 1.0),
                        success_count=gc.get("success_count", 0),
                        last_success=gc.get("last_success"),
                        is_golden=True,
                        source=gc.get("source", "reference")
                    )

        if not entry:
            return None

        # 更新成功計數
        entry["success_count"] = entry.get("success_count", 0) + 1
        entry["last_success"] = datetime.now().isoformat()
        entry["confidence"] = min(1.0, entry.get("confidence", 0.5) + 0.1)

        # 檢查是否需要升級
        if entry["success_count"] >= self.PROMOTION_THRESHOLD:
            promoted_entry = self._promote_to_golden(plugin_dir, entry, metadata)
            if promoted_entry:
                return promoted_entry

        # 保存更新
        metadata["variations"][entry_index] = entry
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        return PatternEntry(**entry, is_golden=False)

    def _promote_to_golden(
        self,
        plugin_dir: Path,
        entry: Dict,
        metadata: Dict
    ) -> Optional[PatternEntry]:
        """
        升級 pattern 到 golden 配置

        Args:
            plugin_dir: 插件目錄
            entry: Pattern 條目
            metadata: metadata.json 內容

        Returns:
            升級後的 PatternEntry
        """
        patterns_dir = plugin_dir / "patterns"
        golden_dir = plugin_dir / "golden"
        golden_dir.mkdir(exist_ok=True)

        pattern_id = entry["id"]
        old_path = patterns_dir / f"{pattern_id}.json"

        if not old_path.exists():
            return None

        # 讀取 pattern 數據
        with open(old_path, 'r', encoding='utf-8') as f:
            pattern_data = json.load(f)

        # 更新 meta
        pattern_data["_meta"]["promoted_to_golden"] = datetime.now().isoformat()
        pattern_data["_meta"]["is_golden"] = True
        pattern_data["_tracking"]["confidence"] = 1.0

        # 移動到 golden/
        new_path = golden_dir / f"{pattern_id}.json"
        with open(new_path, 'w', encoding='utf-8') as f:
            json.dump(pattern_data, f, indent=2, ensure_ascii=False)

        # 刪除舊文件
        old_path.unlink()

        # 更新 metadata
        entry["path"] = f"golden/{pattern_id}.json"
        entry["confidence"] = 1.0
        entry["is_golden"] = True

        # 從 variations 移除
        metadata["variations"] = [
            v for v in metadata.get("variations", [])
            if v["id"] != pattern_id
        ]

        # 添加到 golden_configs
        if "golden_configs" not in metadata:
            metadata["golden_configs"] = []
        metadata["golden_configs"].append(entry)

        # 保存 metadata
        metadata_path = plugin_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        print(f"  🏆 升級為 Golden Config: {pattern_id}")
        print(f"     連續成功 {entry['success_count']} 次")

        return PatternEntry(**entry, is_golden=True)

    def _extract_keywords(self, request: str) -> List[str]:
        """從請求中提取關鍵字"""
        import re

        # 英文單詞
        english = set(re.findall(r'[a-zA-Z]+', request.lower()))

        # 中文詞彙（簡單分割）
        chinese = []
        for word in ["聚集", "立方體", "日照", "結構", "張力", "網格", "分割"]:
            if word in request:
                chinese.append(word)

        return list(english | set(chinese))

    def _update_metadata(self, plugin_dir: Path, entry: PatternEntry):
        """更新 metadata.json"""
        metadata_path = plugin_dir / "metadata.json"

        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        else:
            metadata = {
                "_meta": {
                    "library": f"{plugin_dir.name} Pattern Library",
                    "version": "1.0.0",
                    "last_updated": datetime.now().strftime("%Y-%m-%d")
                },
                "golden_configs": [],
                "variations": [],
                "keyword_index": {}
            }

        # 添加到 variations
        if "variations" not in metadata:
            metadata["variations"] = []
        metadata["variations"].append(entry.to_dict())

        # 更新關鍵字索引
        if "keyword_index" not in metadata:
            metadata["keyword_index"] = {}
        for kw in entry.keywords:
            if kw not in metadata["keyword_index"]:
                metadata["keyword_index"][kw] = []
            if entry.id not in metadata["keyword_index"][kw]:
                metadata["keyword_index"][kw].append(entry.id)

        # 更新時間戳
        metadata["_meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)


class WorkflowPhase(Enum):
    """工作流程階段"""
    # 共享階段
    ROUTING = "routing"

    # Reference Mode 階段 (優先)
    REFERENCE_SEARCH = "reference_search"
    REFERENCE_CONFIRM = "reference_confirm"
    REFERENCE_COPY = "reference_copy"
    REFERENCE_MODIFY = "reference_modify"

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

    # Reference Mode 狀態 (新增)
    reference_match: Optional[ReferenceMatch] = None
    reference_used: bool = False

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
            'reference_used': self.reference_used,
            'reference_name': self.reference_match.name if self.reference_match else None,
            'check_passed': self.check_passed,
            'errors': self.errors
        }


class DualModeWorkflow:
    """
    三軌智能工作流程

    根據請求特性自動選擇：
    - Reference Mode: 優先搜索 Reference Library，使用驗證過的 Golden Config
    - Workflow Mode: 確定性管線，適合已知模式
    - Meta-Agent Mode: 彈性探索，適合未知情況

    優先順序：Reference > Workflow > Meta-Agent
    """

    # Reference Mode 信心度閾值
    REFERENCE_THRESHOLD = 0.5

    def __init__(
        self,
        config_dir: str = "config",
        ghx_skill_db: Optional[str] = None,
        wip_dir: str = "GH_WIP",
        reference_library_path: str = "reference_library"
    ):
        """
        初始化三軌工作流程

        Args:
            config_dir: 配置目錄
            ghx_skill_db: GHX Skill 資料庫
            wip_dir: 工作目錄
            reference_library_path: Reference Library 路徑
        """
        self.config_dir = Path(config_dir)
        self.wip_dir = Path(wip_dir)
        self.wip_dir.mkdir(exist_ok=True)
        self.reference_library_path = reference_library_path

        # 初始化組件
        self.ref_mode = ReferenceMode(reference_library_path)
        self.router = IntentRouter(config_dir=self.config_dir)
        self.meta_agent = MetaAgent(
            ghx_skill_db=ghx_skill_db,
            config_dir=str(config_dir)
        )
        self.pattern_library = PatternLibrary(reference_library_path)

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
        self.on_reference_confirm: Optional[Callable[[ReferenceMatch], bool]] = None

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
        auto_confirm_reference: bool = False,
        user_callback: Optional[Callable] = None
    ) -> Dict:
        """
        執行三軌工作流程

        優先順序：Reference Mode > Workflow Mode > Meta-Agent Mode

        Args:
            request: 用戶請求
            auto_execute: 是否自動執行
            auto_confirm_reference: 是否自動確認 Reference
            user_callback: 用戶輸入回調

        Returns:
            工作流程結果
        """
        self.state = WorkflowState(request=request)
        result = {"phases": [], "final_state": None}

        try:
            # Phase 0: Reference Search（優先）
            self._set_phase(WorkflowPhase.REFERENCE_SEARCH)
            reference_match = self._phase_reference_search(request)
            result["phases"].append({"reference_search": reference_match})

            # 如果有高信心度的 Reference Match，使用 Reference Mode
            if self.state.reference_match and self.state.reference_match.confidence >= self.REFERENCE_THRESHOLD:
                print(f"\n🎯 找到 Golden Config: {self.state.reference_match.name}")
                print(f"   信心度: {self.state.reference_match.confidence:.2f}")

                ref_result = await self._run_reference_mode(
                    auto_confirm=auto_confirm_reference,
                    auto_execute=auto_execute
                )
                result["phases"].append({"reference_mode": ref_result})

                if self.state.reference_used:
                    self._set_phase(WorkflowPhase.COMPLETE)
                    result["final_state"] = self.state.to_dict()
                    return result

            # Phase 1: Routing（如果 Reference Mode 未使用）
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
            import traceback
            error_details = f"{type(e).__name__}: {str(e)}"
            self.state.errors.append(error_details)
            self._set_phase(WorkflowPhase.FAILED)
            # 打印完整堆棧以便調試
            print(f"\n❌ 錯誤: {error_details}")
            traceback.print_exc()

        result["final_state"] = self.state.to_dict()
        return result

    # ========== Reference Mode ==========

    def _phase_reference_search(self, request: str) -> Dict:
        """Phase 0: 搜索 Reference Library"""
        matches = self.ref_mode.search(request)

        if matches:
            self.state.reference_match = matches[0]
            print(f"\n【Reference Search】")
            print(f"  找到 {len(matches)} 個匹配:")
            for m in matches[:3]:
                golden_tag = " ✅ Golden" if m.is_golden else ""
                print(f"    [{m.confidence:.2f}] {m.name}{golden_tag}")
                print(f"           關鍵字: {m.keywords_matched}")

            return {
                "matches": [m.to_dict() for m in matches],
                "best_match": matches[0].to_dict()
            }

        print(f"\n【Reference Search】")
        print(f"  無匹配，將進入 Routing...")
        return {"matches": [], "best_match": None}

    async def _run_reference_mode(
        self,
        auto_confirm: bool = False,
        auto_execute: bool = False
    ) -> Dict:
        """執行 Reference Mode"""
        result = {}
        match = self.state.reference_match

        if not match:
            return {"skipped": True}

        # Phase: Confirm
        self._set_phase(WorkflowPhase.REFERENCE_CONFIRM)
        confirmed = await self._reference_confirm(match, auto_confirm)
        result["confirm"] = {"confirmed": confirmed}

        if not confirmed:
            print("  用戶未確認，將進入 Routing...")
            return result

        # Phase: Copy
        self._set_phase(WorkflowPhase.REFERENCE_COPY)
        placement_info = self._reference_copy(match)
        result["copy"] = {"components": len(placement_info.get("components", []))}

        # 標記 Reference 已使用（在 Copy 完成後就設置，以便 Archive 階段的學習機制可以正確識別）
        self.state.reference_used = True

        # Phase: Modify（如果有回調）
        self._set_phase(WorkflowPhase.REFERENCE_MODIFY)
        # 這裡可以詢問用戶是否要修改參數
        result["modify"] = {"modified": False}

        # Phase: Pre-Check
        self._set_phase(WorkflowPhase.PRE_CHECK)
        pre_check_result = self._workflow_pre_check()
        result["pre_check"] = pre_check_result

        if not self.state.check_passed:
            print("  Pre-Check 未通過")
            return result

        # Phase: Execute
        if auto_execute or self._confirm_execute():
            self._set_phase(WorkflowPhase.EXECUTE)
            exec_result = await self._workflow_execute()
            result["execute"] = exec_result

        # Phase: Archive & Learn
        self._set_phase(WorkflowPhase.ARCHIVE)
        archive_result = self._workflow_archive()
        result["archive"] = archive_result

        return result

    async def _reference_confirm(self, match: ReferenceMatch, auto_confirm: bool) -> bool:
        """確認使用 Reference"""
        preview = self.ref_mode.preview(match)

        print(f"\n【Reference Confirm】")
        print(f"  配置: {match.name}")
        print(f"  描述: {match.description}")
        print(f"  Golden: {'✅' if match.is_golden else '❌'}")
        print(f"  組件數: {len(preview['components'])}")

        if preview.get("lessons_learned"):
            print(f"\n  📝 經驗教訓:")
            for lesson in preview["lessons_learned"][:3]:
                print(f"    - {lesson}")

        if auto_confirm:
            print("\n  → 自動確認")
            return True

        if self.on_reference_confirm:
            return self.on_reference_confirm(match)

        try:
            response = input("\n使用此 Reference？(Y/N): ")
            return response.lower() == 'y'
        except Exception:
            return True

    def _reference_copy(self, match: ReferenceMatch) -> Dict:
        """複製 Reference 配置"""
        placement_info = self.ref_mode.use_reference(match)

        print(f"\n【Reference Copy】")
        print(f"  已複製 {len(placement_info['components'])} 個組件")
        print(f"  已複製 {len(placement_info['connections'])} 個連接")

        self.state.placement_info = placement_info

        # 保存到 WIP
        output_path = self.wip_dir / "placement_info.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(placement_info, f, indent=2, ensure_ascii=False)

        print(f"  已保存: {output_path}")

        return placement_info

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

                # 方式 1: 直接從 components 列表獲取
                if "components" in pattern:
                    components.update(pattern["components"])

                # 方式 2: 從 wiring 提取組件名稱
                for wire in pattern.get("wiring", []):
                    if isinstance(wire, list) and len(wire) >= 2:
                        # wiring 格式: [from_comp, to_comp, from_param, to_param]
                        components.add(wire[0])
                        components.add(wire[1])
                    elif isinstance(wire, dict):
                        # wiring 格式: {"from": ..., "to": ...}
                        if "from" in wire:
                            components.add(wire["from"])
                        if "to" in wire:
                            components.add(wire["to"])

        self.state.component_list = list(components)

        print(f"\n【Phase 2: Plan】")
        print(f"  組件數量: {len(self.state.component_list)}")
        if self.state.component_list:
            print(f"  組件: {self.state.component_list[:10]}")

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
                    if isinstance(wire, list) and len(wire) >= 2:
                        # wiring 格式: [from_comp, to_comp, from_param, to_param]
                        placement_info["connections"].append({
                            "source": wire[0],
                            "target": wire[1],
                            "fromParamIndex": wire[2] if len(wire) > 2 else 0,
                            "toParamIndex": wire[3] if len(wire) > 3 else 0
                        })
                    elif isinstance(wire, dict):
                        # wiring 格式: {"from": ..., "to": ...}
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

            checker = PreExecutionChecker(config_dir=self.config_dir)
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
                # 支援兩種格式: source/target 或 from/to
                from_comp = conn.get('source') or conn.get('from', '?')
                to_comp = conn.get('target') or conn.get('to', '?')
                log = f"connect({from_comp} -> {to_comp})"
                self.state.execution_log.append(log)
                print(f"  {log}")

        return {"log": self.state.execution_log}

    def _workflow_archive(self) -> Dict:
        """
        Workflow Phase 6: 歸檔與學習

        流程：
        1. 保存 archive 到 GH_WIP/
        2. 如果執行成功，保存到 Pattern Library
        3. 如果是 Reference Mode，記錄成功
        4. 檢查是否需要升級 pattern 到 golden
        """
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

        archive = {
            "timestamp": datetime.now().isoformat(),
            "request": self.state.request,
            "mode": self.state.mode.value,
            "design_intent": self.state.design_intent,
            "check_passed": self.state.check_passed,
            "execution_log": self.state.execution_log,
            "errors": self.state.errors,
            "reference_used": self.state.reference_used,
            "reference_name": self.state.reference_match.name if self.state.reference_match else None
        }

        archive_path = self.wip_dir / f"archive_{timestamp_str}.json"

        with open(archive_path, 'w', encoding='utf-8') as f:
            json.dump(archive, f, indent=2, ensure_ascii=False)

        self.state.output_path = str(archive_path)

        print(f"\n【Phase 6: Archive & Learn】")
        print(f"  歸檔路徑: {archive_path}")

        result: Dict = {"path": str(archive_path)}

        # 學習機制：只有在 check_passed 且無錯誤時才學習
        if self.state.check_passed and not self.state.errors:
            result["learning"] = self._learn_from_success()
        else:
            print(f"  ⏭️ 跳過學習（驗證未通過或有錯誤）")
            result["learning"] = {"skipped": True}

        return result

    def _learn_from_success(self) -> Dict:
        """
        從成功執行中學習

        如果是 Reference Mode：記錄成功次數
        如果是 Workflow/Meta-Agent Mode：保存到 Pattern Library
        """
        learning_result = {}

        # 確定目標插件
        routing = self.state.routing_result
        target_plugins = routing.target_plugins if routing else []
        plugin = target_plugins[0] if target_plugins else "general"

        if self.state.reference_used and self.state.reference_match:
            # Reference Mode: 記錄成功
            pattern_id = self.state.reference_match.id.split("/")[-1]  # e.g., "wasp/cube_basic" -> "cube_basic"
            ref_plugin = self.state.reference_match.id.split("/")[0]  # e.g., "wasp"

            entry = self.pattern_library.record_success(ref_plugin, pattern_id)

            if entry:
                learning_result["action"] = "record_success"
                learning_result["pattern_id"] = pattern_id
                learning_result["success_count"] = entry.success_count
                learning_result["promoted"] = entry.is_golden

                if entry.is_golden:
                    print(f"  🏆 Pattern 已升級為 Golden Config！")
                else:
                    print(f"  📈 成功計數: {entry.success_count}/{PatternLibrary.PROMOTION_THRESHOLD}")
            else:
                # 可能是已經是 golden config
                learning_result["action"] = "already_golden"
                print(f"  ✅ 使用 Golden Config，無需更新")

        else:
            # Workflow/Meta-Agent Mode: 保存新 pattern
            if self.state.placement_info:
                source = "meta_agent" if self.state.mode == ProcessingMode.META_AGENT else "workflow"

                entry = self.pattern_library.save_pattern(
                    placement_info=self.state.placement_info,
                    request=self.state.request,
                    plugin=plugin,
                    source=source
                )

                learning_result["action"] = "save_pattern"
                learning_result["pattern_id"] = entry.id
                learning_result["path"] = entry.path

                print(f"  📚 新 Pattern 已保存: {entry.id}")
            else:
                learning_result["action"] = "no_placement_info"
                print(f"  ⚠️ 無 placement_info，無法保存 pattern")

        return learning_result

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

        routing = self.state.routing_result
        if not routing or not routing.matched_patterns:
            return {"pattern": None}

        patterns = routing.matched_patterns[:2]
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
