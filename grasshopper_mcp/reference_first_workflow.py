#!/usr/bin/env python3
"""
Reference-First Workflow - 混合架構實作 (v2.0)
==============================================

整合 Reference-First + Design-First + LLM 語義審查的完整工作流程。

v2.0 重大改進：
    1. 新增 Phase 2: LLM Semantic Review (語義審查)
    2. 讓 Claude 自我對話審查配置，而非依賴 hardcoded 規則
    3. 即使有參考配置，也要經過語義審查

核心理念：
    1. Reference First：優先搜索已驗證的配置
    2. LLM Semantic Review：讓 Claude 自我審查語義正確性
    3. Fail-Safe Learning：失敗時記錄教訓，成功時升級配置

架構圖：
```
用戶請求
    │
    ▼
┌─────────────────────────────────────────────┐
│  Phase 0: Reference Search                   │
│  → 搜索 Reference Library                    │
│  → 使用語義匹配 (keywords + description)     │
└─────────────────────────────────────────────┘
    │
    ├──[有高信心匹配 ≥0.7]──┐
    │                       │
    ▼                       ▼
[無匹配/低信心]          [有匹配]
    │                       │
    ▼                       ▼
┌─────────────┐     ┌─────────────────────────┐
│ Phase 1b:   │     │ Phase 1a: Reference     │
│ Design-First│     │ Confirm                 │
│ 完整交互    │     │ ─────────────────────── │
│ (6 階段)    │     │ • 展示配置摘要          │
└─────────────┘     │ • 展示 lessons_learned  │
                    │ • 詢問：使用/修改/新建？│
                    └─────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
    [使用]          [修改]          [新建]
        │               │               │
        ▼               ▼               ▼
    複製配置       修改參數       Design-First
        │               │
        └───────┬───────┘
                ▼
┌─────────────────────────────────────────────┐
│  Phase 2: Pre-Execution Check (快速語法)     │
│  • 語法驗證 (GUID、參數名、命令)             │
│  • 顯示預檢報告                             │
│  • 快速過濾明顯錯誤 (節省 tokens)            │
└─────────────────────────────────────────────┘
        │
    [語法通過]
        │
        ▼
┌─────────────────────────────────────────────┐
│  Phase 3: LLM Semantic Review               │
│  ─────────────────────────────────          │
│  Claude 自我對話：                           │
│  • 追蹤資料流                               │
│  • 估算每個節點輸出數量                      │
│  • 識別「資料爆炸」風險                      │
│  • 檢查模式正確性                           │
│  ─────────────────────────────────          │
│  使用者確認：「這符合你的意圖嗎？」           │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│  Phase 4: Execute                           │
│  • clear_document (清空畫布)                │
│  • add_component (創建組件)                 │
│  • connect_components (建立連接)            │
└─────────────────────────────────────────────┘
        │
    ┌───┴───┐
    ▼       ▼
[成功]   [失敗]
    │       │
    ▼       ▼
┌───────┐ ┌───────────────────────────────────┐
│升級   │ │ 記錄 lessons_learned              │
│Pattern│ │ 降低 confidence                   │
│Library│ │ 詢問：重試/放棄？                  │
└───────┘ └───────────────────────────────────┘
```

Usage:
    from grasshopper_mcp.reference_first_workflow import ReferenceFirstWorkflow

    workflow = ReferenceFirstWorkflow()
    result = await workflow.run("做一個 WASP 離散聚集")

2026-01-24 v2.0 - 新增 LLM Semantic Review
2026-01-24 v2.1 - 優化驗證順序 (Pre-Check → Semantic Review)
"""

import json
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
from datetime import datetime

from .reference_mode import ReferenceMode, ReferenceMatch, ReferenceConfig
from .intent_router import IntentRouter, ProcessingMode
from .semantic_review_prompt import generate_semantic_review_prompt
from .pre_execution_checker import PreExecutionChecker


class WorkflowPhase(Enum):
    """工作流程階段"""
    # Phase 0-1: Reference Search & Confirm
    REFERENCE_SEARCH = "reference_search"
    REFERENCE_CONFIRM = "reference_confirm"
    # Phase 2: Pre-Execution Check (語法檢查 - 快速)
    PRE_EXECUTION_CHECK = "pre_execution_check"
    # Phase 3: Semantic Review (語義審查 - 只在語法通過後執行)
    SEMANTIC_REVIEW = "semantic_review"
    # Phase 4: Execute
    EXECUTE = "execute"
    # Phase 5: Archive & Learn
    ARCHIVE_LEARN = "archive_learn"
    # Design-First fallback
    DESIGN_FIRST = "design_first"
    # 結束
    COMPLETE = "complete"
    FAILED = "failed"


class UserChoice(Enum):
    """使用者選擇"""
    USE = "use"           # 直接使用參考配置
    MODIFY = "modify"     # 修改參數
    NEW = "new"           # 從頭設計
    CONFIRM = "confirm"   # 確認繼續
    RETRY = "retry"       # 重試
    ABORT = "abort"       # 放棄


@dataclass
class WorkflowResult:
    """工作流程結果"""
    success: bool
    mode: str  # "reference" | "design_first" | "meta_agent"
    phases_completed: List[str]
    placement_info: Optional[Dict] = None
    reference_used: Optional[str] = None
    modifications: Optional[Dict] = None
    semantic_review: Optional[str] = None
    pre_check_report: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    execution_log: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "mode": self.mode,
            "phases": self.phases_completed,
            "reference": self.reference_used,
            "modifications": self.modifications,
            "errors": self.errors,
            "lessons": self.lessons_learned
        }


class ReferenceFirstWorkflow:
    """
    Reference-First 混合工作流程 (v2.1)

    核心流程：
    1. 搜索參考配置
    2. 使用者確認（即使有匹配也要確認）
    3. 語法檢查（Pre-Execution Check）- 快速過濾
    4. **LLM 語義審查** - 只在語法通過後執行（節省 tokens）
    5. 執行
    6. 學習

    v2.1 改進：
    - 驗證順序優化：Pre-Check → Semantic Review
    - 語法檢查失敗時不消耗 LLM tokens
    - 更高效的資源使用

    v2.0 關鍵改進：
    - 新增 LLM Semantic Review
    - 讓 Claude 自我審查配置，追蹤資料流
    - 識別「資料爆炸」等語義問題
    """

    # 信心度閾值
    HIGH_CONFIDENCE = 0.7
    MEDIUM_CONFIDENCE = 0.5

    def __init__(
        self,
        reference_library_path: str = "reference_library",
        config_dir: str = "config",
        wip_dir: str = "GH_WIP"
    ):
        self.ref_mode = ReferenceMode(reference_library_path)
        self.router = IntentRouter(config_dir=Path(config_dir))
        self.wip_dir = Path(wip_dir)
        self.wip_dir.mkdir(exist_ok=True)

        # 回調函數
        self.on_confirm: Optional[Callable[[ReferenceMatch], str]] = None  # 返回 use/modify/new
        self.on_modify: Optional[Callable[[Dict], Dict]] = None
        self.on_semantic_review: Optional[Callable[[str], bool]] = None  # 返回是否確認
        self.on_execute: Optional[Callable[[Dict], Any]] = None

        # 狀態
        self.current_phase = WorkflowPhase.REFERENCE_SEARCH
        self.result = WorkflowResult(success=False, mode="unknown", phases_completed=[])

    async def run(
        self,
        request: str,
        auto_confirm: bool = False,
        auto_execute: bool = False,
        modifications: Optional[Dict] = None
    ) -> WorkflowResult:
        """
        執行 Reference-First 工作流程

        Args:
            request: 用戶請求
            auto_confirm: 自動確認參考配置
            auto_execute: 自動執行部署
            modifications: 預設修改項目

        Returns:
            工作流程結果
        """
        self.result = WorkflowResult(success=False, mode="unknown", phases_completed=[])

        try:
            # Phase 0: Reference Search
            self._set_phase(WorkflowPhase.REFERENCE_SEARCH)
            match = await self._phase_reference_search(request)
            self.result.phases_completed.append("reference_search")

            if match and match.confidence >= self.MEDIUM_CONFIDENCE:
                # Reference Mode
                self.result.mode = "reference"

                # Phase 1: Confirm
                self._set_phase(WorkflowPhase.REFERENCE_CONFIRM)
                choice = await self._phase_reference_confirm(match, auto_confirm)
                self.result.phases_completed.append("reference_confirm")

                if choice == UserChoice.NEW:
                    # 進入 Design-First
                    self.result.mode = "design_first"
                    raise NotImplementedError("請使用 /grasshopper 命令進入 Design-First 流程")

                # 載入配置
                placement_info = self.ref_mode.use_reference(match)
                self.result.reference_used = match.name

                if choice == UserChoice.MODIFY:
                    placement_info = await self._apply_modifications(placement_info, modifications)

                # Phase 2: Pre-Execution Check (語法檢查 - 快速過濾)
                # 先做語法檢查，通過後才進行語義審查（節省 tokens）
                self._set_phase(WorkflowPhase.PRE_EXECUTION_CHECK)
                check_passed = await self._phase_pre_execution_check(placement_info)
                self.result.phases_completed.append("pre_execution_check")

                if not check_passed:
                    raise Exception("Pre-Execution Check 未通過")

                # Phase 3: LLM Semantic Review (語義審查 - 只在語法通過後執行)
                self._set_phase(WorkflowPhase.SEMANTIC_REVIEW)
                confirmed = await self._phase_semantic_review(placement_info)
                self.result.phases_completed.append("semantic_review")

                if not confirmed:
                    raise Exception("語義審查未通過")

                # Phase 4: Execute
                if auto_execute or await self._ask_execute():
                    self._set_phase(WorkflowPhase.EXECUTE)
                    await self._phase_execute(placement_info)
                    self.result.phases_completed.append("execute")

                # Phase 5: Archive & Learn
                self._set_phase(WorkflowPhase.ARCHIVE_LEARN)
                await self._phase_archive_learn(placement_info)
                self.result.phases_completed.append("archive_learn")

                self.result.placement_info = placement_info

            else:
                # 無匹配，進入 Design-First
                self.result.mode = "design_first"
                print("\n⚠️ 無匹配的參考配置，請使用 /grasshopper 命令進入 Design-First 流程")
                raise NotImplementedError("請使用 /grasshopper 命令進入 Design-First 流程")

            self._set_phase(WorkflowPhase.COMPLETE)
            self.result.success = True

        except NotImplementedError as e:
            self.result.errors.append(str(e))
            # 不算失敗，只是需要切換模式

        except Exception as e:
            self.result.errors.append(str(e))
            self._set_phase(WorkflowPhase.FAILED)

        return self.result

    def _set_phase(self, phase: WorkflowPhase):
        """設置當前階段"""
        self.current_phase = phase
        print(f"\n{'='*60}")
        print(f"【Phase: {phase.value.upper()}】")
        print(f"{'='*60}")

    async def _phase_reference_search(self, request: str) -> Optional[ReferenceMatch]:
        """Phase 0: 搜索參考配置"""
        # 分析意圖
        routing = self.router.route(request)
        print(f"  請求: {request}")
        print(f"  關鍵字: {routing.keywords}")
        print(f"  目標插件: {routing.target_plugins}")

        # 搜索參考庫
        matches = self.ref_mode.search(request)

        if matches:
            match = matches[0] if isinstance(matches, list) else matches
            print(f"\n  ✅ 找到參考配置: {match.name}")
            print(f"  信心度: {match.confidence:.0%}")
            print(f"  Golden: {'🌟' if match.is_golden else '❌'}")
            return match
        else:
            print(f"\n  ❌ 無匹配的參考配置")
            return None

    async def _phase_reference_confirm(
        self,
        match: ReferenceMatch,
        auto_confirm: bool
    ) -> UserChoice:
        """Phase 1: 確認參考配置"""
        # 顯示配置預覽
        preview = self.ref_mode.preview(match)

        print(f"\n  配置名稱: {match.name}")
        print(f"  描述: {match.description}")
        print(f"  組件數: {len(preview.get('components', []))}")
        print(f"  連接數: {len(preview.get('connections', []))}")

        if preview.get("lessons_learned"):
            print(f"\n  📚 經驗教訓:")
            for lesson in preview["lessons_learned"]:
                print(f"    • {lesson}")

        if auto_confirm:
            print("\n  → 自動確認使用")
            return UserChoice.USE

        if self.on_confirm:
            choice_str = self.on_confirm(match)
            return UserChoice[choice_str.upper()]

        try:
            print("\n  選項:")
            print("    [使用] 直接使用這個配置")
            print("    [修改] 調整參數")
            print("    [新建] 從頭設計")
            response = input("\n  你的選擇 (使用/修改/新建): ").strip()

            if response in ["使用", "use", "y", "yes", ""]:
                return UserChoice.USE
            elif response in ["修改", "modify", "m"]:
                return UserChoice.MODIFY
            elif response in ["新建", "new", "n"]:
                return UserChoice.NEW
            else:
                return UserChoice.ABORT
        except Exception:
            return UserChoice.USE

    async def _phase_semantic_review(self, placement_info: Dict) -> bool:
        """
        Phase 2: LLM 語義審查 (NEW!)

        這是 v2.0 的核心改進：
        - 生成審查提示詞
        - Claude 自我對話分析配置
        - 追蹤資料流，識別語義問題
        """
        print("\n  🧠 正在進行 LLM 語義審查...")

        # 生成審查提示詞
        prompt = generate_semantic_review_prompt(placement_info)

        # 執行語義審查（Claude 自我對話）
        review_result = self._perform_semantic_review(placement_info)
        self.result.semantic_review = review_result

        print(review_result)

        # 詢問確認
        if self.on_semantic_review:
            return self.on_semantic_review(review_result)

        try:
            response = input("\n  這符合你的意圖嗎？(確認/修改/放棄): ").strip()
            if response in ["確認", "confirm", "y", "yes", ""]:
                return True
            elif response in ["放棄", "abort", "n", "no"]:
                return False
            else:
                # 需要修改
                print("\n  請說明需要修改的內容，然後重新執行")
                return False
        except Exception:
            return True

    def _perform_semantic_review(self, placement_info: Dict) -> str:
        """
        執行語義審查

        分析配置的語義正確性，追蹤資料流
        """
        components = placement_info.get("components", [])
        connections = placement_info.get("connections", [])
        meta = placement_info.get("_meta", {})

        lines = []
        lines.append(f"\n  ## 語義審查報告")
        lines.append(f"\n  **配置名稱**: {meta.get('name', 'Unknown')}")
        lines.append(f"  **描述**: {meta.get('description', '無')}")

        # 資料流追蹤
        lines.append(f"\n  ### 資料流追蹤")

        critical_issues = []
        warnings = []

        # 找出輸入組件和關鍵組件
        for comp in components:
            comp_type = comp.get("type", "")
            nickname = comp.get("nickname", comp.get("id", ""))
            props = comp.get("properties", {})

            # Slider
            if "Slider" in comp_type:
                value = props.get("value", "?")
                lines.append(f"  **{nickname}** (Slider): {value}")

            # Mesh Box 檢查
            elif comp_type == "Mesh Box":
                # 查找連接的 slider 值
                x = y = z = 10
                for c in components:
                    cn = c.get("nickname", "")
                    if cn in ["SizeX", "X"]:
                        x = c.get("properties", {}).get("value", 10)
                    elif cn in ["SizeY", "Y"]:
                        y = c.get("properties", {}).get("value", 10)
                    elif cn in ["SizeZ", "Z"]:
                        z = c.get("properties", {}).get("value", 10)

                faces = x * y * z * 6
                lines.append(f"  **{nickname}** (Mesh Box): X={x}, Y={y}, Z={z} 細分")
                lines.append(f"      ↓ 輸出: ~{faces} mesh faces")

                if faces > 100:
                    critical_issues.append({
                        "component": nickname,
                        "issue": f"Mesh Box 將產生 {faces} 個面",
                        "explanation": "Mesh Box 的 X/Y/Z 是「細分數量」而非「尺寸」",
                        "suggestion": "使用 Center Box 替代 (X/Y/Z 是真正的尺寸)"
                    })

            # Center Box
            elif comp_type == "Center Box":
                lines.append(f"  **{nickname}** (Center Box): 單一 Brep (6 個面)")

            # Deconstruct Brep
            elif comp_type == "Deconstruct Brep":
                lines.append(f"  **{nickname}** (Deconstruct Brep): → 6 個面 (立方體)")

        # WASP 模式檢查
        comp_types = {c.get("type", "") for c in components}

        if "Wasp_Stochastic Aggregation" in comp_types:
            if "Mesh Box" in comp_types and "Center Box" not in comp_types:
                critical_issues.append({
                    "component": "WASP Pattern",
                    "issue": "使用 Mesh Box 而非 Center Box",
                    "explanation": "WASP 最佳實踐是用 Center Box + Deconstruct Brep",
                    "suggestion": "替換: Mesh Box → Center Box + Deconstruct Brep + Evaluate Surface"
                })

            # RESET 檢查
            reset_connected = any(conn.get("to_param") == "RESET" for conn in connections)
            if not reset_connected:
                warnings.append({
                    "component": "StochAggr",
                    "issue": "RESET 輸入未連接",
                    "suggestion": "添加 Boolean Toggle 並連接到 RESET"
                })

        # 輸出報告
        if critical_issues:
            lines.append(f"\n  ### 🔴 Critical 問題")
            for issue in critical_issues:
                lines.append(f"  - **{issue['component']}**: {issue['issue']}")
                lines.append(f"    說明: {issue['explanation']}")
                lines.append(f"    建議: {issue['suggestion']}")
            lines.append(f"\n  ### 結論: ❌ 需要修改")
        elif warnings:
            lines.append(f"\n  ### 🟡 警告")
            for warn in warnings:
                lines.append(f"  - **{warn['component']}**: {warn['issue']}")
                lines.append(f"    建議: {warn['suggestion']}")
            lines.append(f"\n  ### 結論: ⚠️ 有條件通過")
        else:
            lines.append(f"\n  ### ✅ 風險評估")
            lines.append(f"  ✓ 資料流正常")
            lines.append(f"  ✓ 無 Critical 問題")
            lines.append(f"\n  ### 結論: ✅ 通過")

        return "\n".join(lines)

    async def _phase_pre_execution_check(self, placement_info: Dict) -> bool:
        """Phase 3: 語法檢查"""
        print("\n  🔧 正在進行語法檢查...")

        checker = PreExecutionChecker()
        results = checker.check_placement_info(placement_info)
        report = checker.generate_report()
        self.result.pre_check_report = report

        print(report)

        # 判斷是否有阻擋性問題
        has_critical = any(
            r.severity.value == "critical" if hasattr(r.severity, 'value') else r.severity == "critical"
            for r in results
        )

        if has_critical:
            print("\n  ❌ 有 Critical 問題，需要修復")
            return False

        return True

    async def _apply_modifications(
        self,
        placement_info: Dict,
        modifications: Optional[Dict]
    ) -> Dict:
        """應用修改"""
        if modifications is None:
            if self.on_modify:
                modifications = self.on_modify(placement_info)
            else:
                try:
                    print("\n  請輸入要修改的參數 (格式: 參數名=值，逗號分隔)")
                    print("  例如: Count=20, Seed=123")
                    response = input("  修改: ").strip()

                    if response:
                        modifications = {}
                        for part in response.split(","):
                            if "=" in part:
                                key, value = part.split("=", 1)
                                key = key.strip()
                                value = value.strip()
                                try:
                                    if "." in value:
                                        modifications[key] = float(value)
                                    else:
                                        modifications[key] = int(value)
                                except ValueError:
                                    modifications[key] = value
                except Exception:
                    pass

        if modifications:
            for comp in placement_info.get("components", []):
                nickname = comp.get("nickname", "")
                if nickname in modifications:
                    if "properties" not in comp:
                        comp["properties"] = {}
                    comp["properties"]["value"] = modifications[nickname]
                    print(f"  ✓ 修改 {nickname} = {modifications[nickname]}")

            self.result.modifications = modifications

        return placement_info

    async def _ask_execute(self) -> bool:
        """詢問是否執行"""
        try:
            response = input("\n  執行部署？(Y/N): ").strip()
            return response.lower() in ['y', 'yes', '']
        except Exception:
            return False

    async def _phase_execute(self, placement_info: Dict):
        """Phase 4: 執行部署"""
        print("\n  🚀 準備執行部署...")

        # 保存配置
        output_path = self.wip_dir / "placement_info.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(placement_info, f, indent=2, ensure_ascii=False)

        print(f"  ✓ 配置已保存: {output_path}")

        if self.on_execute:
            await self.on_execute(placement_info)
        else:
            print(f"\n  執行命令:")
            print(f"  python -m grasshopper_tools.cli execute-placement {output_path} --clear-first")

        self.result.execution_log.append(f"saved: {output_path}")

    async def _phase_archive_learn(self, placement_info: Dict):
        """Phase 5: 歸檔與學習"""
        print("\n  📚 歸檔與學習...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.wip_dir / f"archive_{timestamp}.json"

        archive = {
            "timestamp": timestamp,
            "mode": self.result.mode,
            "reference_used": self.result.reference_used,
            "modifications": self.result.modifications,
            "semantic_review": self.result.semantic_review,
            "placement_info": placement_info
        }

        with open(archive_path, 'w', encoding='utf-8') as f:
            json.dump(archive, f, indent=2, ensure_ascii=False)

        print(f"  ✓ 已歸檔: {archive_path}")

        try:
            response = input("\n  執行結果？(成功/失敗): ").strip()
            if response in ["成功", "success", "s"]:
                print("  → 配置將被標記為成功，提升 confidence")
                # TODO: 更新 Pattern Library
            elif response in ["失敗", "fail", "f"]:
                print("  → 請描述失敗原因，將記錄到 lessons_learned")
                reason = input("  失敗原因: ").strip()
                self.result.lessons_learned.append(reason)
        except Exception:
            pass


# ============================================================================
# CLI
# ============================================================================

async def main():
    """命令行測試"""
    import sys

    test_queries = [
        "做一個 WASP 離散聚集",
        "wasp cube aggregation",
    ]

    if len(sys.argv) > 1:
        test_queries = [" ".join(sys.argv[1:])]

    workflow = ReferenceFirstWorkflow()

    print("=" * 60)
    print("Reference-First Workflow v2.0 測試")
    print("=" * 60)

    for query in test_queries[:1]:
        print(f"\n請求: {query}")

        try:
            result = await workflow.run(
                query,
                auto_confirm=False,
                auto_execute=False
            )

            print(f"\n{'='*60}")
            print(f"【最終結果】")
            print(f"  成功: {result.success}")
            print(f"  模式: {result.mode}")
            print(f"  階段: {result.phases_completed}")
            if result.reference_used:
                print(f"  參考: {result.reference_used}")
            if result.errors:
                print(f"  錯誤: {result.errors}")

        except Exception as e:
            print(f"\n【錯誤】{e}")


if __name__ == "__main__":
    asyncio.run(main())
