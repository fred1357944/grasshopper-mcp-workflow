#!/usr/bin/env python3
"""
DesignWorkflowV2 - 整合版設計工作流程
=====================================

結合:
- DesignWorkflow (六階段流程)
- HITLCollaborator (人機協作)
- UnifiedHandler (三層路由)

核心理念：
- 每個階段有明確的 HITL 確認點
- 用戶可以在任何階段取消
- Mermaid 檔案生成供 VSCode 預覽

Usage:
    from grasshopper_mcp.design_workflow_v2 import DesignWorkflowV2
    from grasshopper_mcp.hitl_collaborator import HITLCollaborator

    hitl = HITLCollaborator(user_callback=my_callback)
    workflow = DesignWorkflowV2("my_project", hitl)
    result = await workflow.run_full_workflow("設計一個螺旋樓梯")
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from .workflow.design_workflow import DesignWorkflow, WorkflowPhase
from .hitl_collaborator import HITLCollaborator, CollectedKnowledge
from .component_validator import (
    ComponentValidator,
    ValidationStatus,
    ValidationReport as ComponentValidationReport,
)


@dataclass
class WorkflowResult:
    """工作流程結果"""
    status: str  # "success", "cancelled", "blocked", "partial", "error"
    phase: str = ""
    archive_path: Optional[str] = None
    placement_info: Optional[Dict] = None
    execution: Optional[Dict] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    claude_calls: int = 0
    collected_knowledge: List[Dict] = field(default_factory=list)
    component_validation: Optional[ComponentValidationReport] = None  # 組件驗證報告


class DesignWorkflowV2:
    """
    整合版設計工作流程

    六階段流程 + HITL 確認點:
    - Phase 1: 需求釐清 + HITL (收集不明確點)
    - Phase 2: 幾何分解 → part_info.mmd + HITL 確認
    - Phase 3: 組件規劃 → component_info.mmd + HITL 確認
    - Phase 4: GUID 解析
    - Phase 4.5: Pre-Check + HITL (若有警告)
    - Phase 5: 執行部署
    - Phase 6: 歸檔
    """

    def __init__(
        self,
        project_name: str,
        hitl: HITLCollaborator,
        wip_dir: Path = Path("GH_WIP"),
        base_path: Optional[str] = None
    ):
        """
        初始化工作流程

        Args:
            project_name: 專案名稱
            hitl: HITL 協作器
            wip_dir: 工作目錄
            base_path: 專案根目錄
        """
        self.project_name = project_name
        self.hitl = hitl
        self.wip_dir = Path(wip_dir)

        # 確保目錄存在
        self.wip_dir.mkdir(exist_ok=True)

        # 初始化底層 DesignWorkflow
        self.workflow = DesignWorkflow(project_name, base_path)

        # Component Validator (Validation-First Architecture)
        self.component_validator = ComponentValidator(config_dir="config")

        # 統計
        self._claude_calls = 0

    async def run_full_workflow(self, design_intent: str) -> Dict[str, Any]:
        """
        執行完整設計流程

        Args:
            design_intent: 設計意圖描述

        Returns:
            工作流程結果字典
        """
        result = WorkflowResult(status="in_progress")

        try:
            # Phase 1: 需求釐清 + HITL
            phase1_result = await self._phase1_clarify_with_hitl(design_intent)
            if phase1_result.get("cancelled"):
                return self._to_dict(WorkflowResult(
                    status="cancelled",
                    phase="clarify",
                    claude_calls=self._claude_calls,
                    collected_knowledge=self.hitl.get_collected_knowledge_list()
                ))

            spec = phase1_result["spec"]

            # Phase 2: 幾何分解 → part_info.mmd + HITL 確認
            phase2_result = await self._phase2_decompose_with_hitl(spec)
            if phase2_result.get("cancelled"):
                return self._to_dict(WorkflowResult(
                    status="cancelled",
                    phase="decompose",
                    claude_calls=self._claude_calls,
                    collected_knowledge=self.hitl.get_collected_knowledge_list()
                ))

            # Phase 3: 組件規劃 → component_info.mmd + HITL 確認
            phase3_result = await self._phase3_plan_with_hitl()
            if phase3_result.get("cancelled"):
                return self._to_dict(WorkflowResult(
                    status="cancelled",
                    phase="plan",
                    claude_calls=self._claude_calls,
                    collected_knowledge=self.hitl.get_collected_knowledge_list()
                ))

            # Phase 4: GUID 解析 (自動，無 HITL)
            # 這個階段主要是更新 component_info.mmd 中的 GUID

            # Phase 4: Component Validation (Validation-First Architecture)
            phase4_result = await self._phase4_component_validation_with_hitl()
            if phase4_result.get("cancelled"):
                return self._to_dict(WorkflowResult(
                    status="cancelled",
                    phase="component_validation",
                    component_validation=phase4_result.get("validation"),
                    claude_calls=self._claude_calls,
                    collected_knowledge=self.hitl.get_collected_knowledge_list()
                ))

            if phase4_result.get("blocked"):
                return self._to_dict(WorkflowResult(
                    status="blocked",
                    phase="component_validation",
                    component_validation=phase4_result.get("validation"),
                    errors=phase4_result.get("errors", []),
                    claude_calls=self._claude_calls,
                    collected_knowledge=self.hitl.get_collected_knowledge_list()
                ))

            # Phase 4.5: Pre-Check + HITL (若有警告)
            phase45_result = await self._phase4_pre_check_with_hitl()
            if phase45_result.get("cancelled"):
                return self._to_dict(WorkflowResult(
                    status="cancelled",
                    phase="pre_check",
                    claude_calls=self._claude_calls,
                    collected_knowledge=self.hitl.get_collected_knowledge_list()
                ))

            if phase45_result.get("blocked"):
                return self._to_dict(WorkflowResult(
                    status="blocked",
                    phase="pre_check",
                    errors=phase45_result.get("errors", []),
                    claude_calls=self._claude_calls,
                    collected_knowledge=self.hitl.get_collected_knowledge_list()
                ))

            # Phase 5: 執行部署
            exec_result = self._phase5_execute()
            if exec_result.get("status") != "success":
                return self._to_dict(WorkflowResult(
                    status="partial",
                    phase="execute",
                    execution=exec_result,
                    errors=exec_result.get("errors", []),
                    claude_calls=self._claude_calls,
                    collected_knowledge=self.hitl.get_collected_knowledge_list()
                ))

            # Phase 6: 歸檔
            archive_path = self._phase6_archive()

            # 讀取 placement_info
            placement_info = self._load_placement_info()

            return self._to_dict(WorkflowResult(
                status="success",
                archive_path=archive_path,
                placement_info=placement_info,
                execution=exec_result,
                claude_calls=self._claude_calls,
                collected_knowledge=self.hitl.get_collected_knowledge_list()
            ))

        except Exception as e:
            return self._to_dict(WorkflowResult(
                status="error",
                errors=[str(e)],
                claude_calls=self._claude_calls,
                collected_knowledge=self.hitl.get_collected_knowledge_list()
            ))

    async def _phase1_clarify_with_hitl(self, design_intent: str) -> Dict[str, Any]:
        """
        Phase 1: 需求釐清 + HITL

        收集不明確的點，讓用戶確認或補充
        """
        print("\n" + "=" * 60)
        print("  Phase 1: 需求釐清")
        print("=" * 60)

        # 使用底層 workflow 分析設計意圖
        clarify_result = self.workflow.phase1_clarify(design_intent)

        questions = clarify_result.get("questions", [])
        suggestions = clarify_result.get("suggestions", {})

        # 如果有需要釐清的問題，使用 HITL 收集
        if questions:
            print(f"\n📋 有 {len(questions)} 個問題需要確認：")

            knowledge = await self.hitl.collaborate_on_unclear_points(
                unclear_points=questions,
                existing_knowledge={q: str(suggestions.get(q, "")) for q in questions}
            )

            # 合併知識到規格
            spec = self._merge_knowledge_to_spec(suggestions, knowledge)
        else:
            spec = suggestions

        # 最終確認
        spec_summary = self._format_spec_summary(spec)
        print(f"\n📊 設計規格摘要：\n{spec_summary}")

        confirmed = await self.hitl.confirm(
            "確認以上設計規格？",
            default=True
        )

        if not confirmed:
            return {"cancelled": True, "spec": spec}

        return {"cancelled": False, "spec": spec}

    async def _phase2_decompose_with_hitl(self, spec: Dict) -> Dict[str, Any]:
        """
        Phase 2: 幾何分解 + HITL 確認

        生成 part_info.mmd 供 VSCode 預覽
        """
        print("\n" + "=" * 60)
        print("  Phase 2: 幾何分解")
        print("=" * 60)

        # 生成 part_info.mmd
        part_path = self.workflow.phase2_decompose(spec)

        print(f"\n📊 已生成: {part_path}")
        print("   請在 VSCode 中預覽 part_info.mmd")

        # HITL 確認
        confirmed = await self.hitl.confirm(
            "請在 VSCode 確認 part_info.mmd 後繼續",
            default=True
        )

        if not confirmed:
            return {"cancelled": True, "path": part_path}

        return {"cancelled": False, "path": part_path}

    async def _phase3_plan_with_hitl(self) -> Dict[str, Any]:
        """
        Phase 3: 組件規劃 + HITL 確認

        生成 component_info.mmd 供 VSCode 預覽
        """
        print("\n" + "=" * 60)
        print("  Phase 3: 組件規劃")
        print("=" * 60)

        # 生成 component_info.mmd
        comp_path = self.workflow.phase3_plan()

        print(f"\n📊 已生成: {comp_path}")
        print("   請在 VSCode 中預覽 component_info.mmd")

        # HITL 確認
        confirmed = await self.hitl.confirm(
            "請在 VSCode 確認 component_info.mmd 後繼續",
            default=True
        )

        if not confirmed:
            return {"cancelled": True, "path": comp_path}

        return {"cancelled": False, "path": comp_path}

    async def _phase4_component_validation_with_hitl(self) -> Dict[str, Any]:
        """
        Phase 4: Component Validation (Validation-First Architecture)

        驗證所有組件名稱是否有效，處理多版本衝突
        """
        print("\n" + "=" * 60)
        print("  Phase 4: Component Validation")
        print("=" * 60)

        # 載入 placement_info
        placement_info = self._load_placement_info()
        if not placement_info:
            print("  ⚠️ 無法載入 placement_info.json")
            return {"cancelled": False, "blocked": False, "validation": None}

        components = placement_info.get("components", [])
        if not components:
            print("  ⚠️ 無組件需要驗證")
            return {"cancelled": False, "blocked": False, "validation": None}

        # 執行組件驗證
        validation_report = self.component_validator.validate_components(components)

        print(f"\n📊 組件驗證結果:")
        print(f"  - 總計: {validation_report.total_components} 個組件")
        print(f"  - ✅ 通過: {validation_report.valid_count}")
        print(f"  - ⚠️ 需選擇: {validation_report.ambiguous_count}")
        print(f"  - ❌ 找不到: {validation_report.not_found_count}")

        if validation_report.can_proceed:
            print(f"\n  ✅ 所有組件已驗證")
            return {"cancelled": False, "blocked": False, "validation": validation_report}

        # 有組件需要決策
        print(f"\n⚠️ 部分組件需要確認:")

        for comp_name in validation_report.requires_decision:
            v = validation_report.get_validation(comp_name)
            if v is None:
                continue

            if v.status == ValidationStatus.AMBIGUOUS:
                print(f"\n  📋 {comp_name}: 有多個版本")
                for i, c in enumerate(v.candidates):
                    category = c.get('category', 'Unknown')
                    desc = c.get('description', '')
                    recommended = "⭐ " if c.get('recommended') else ""
                    print(f"    [{i+1}] {recommended}{category} - {desc}")

            elif v.status == ValidationStatus.NOT_FOUND:
                print(f"\n  ❌ {comp_name}: 找不到")
                if v.recommendations:
                    print(f"    建議替代:")
                    for i, r in enumerate(v.recommendations[:3]):
                        name = r.get('name', '')
                        sim = r.get('similarity', 0)
                        print(f"    [{i+1}] {name} (相似度: {sim:.0%})")

        # HITL 確認
        confirmed = await self.hitl.confirm(
            "是否繼續執行？（組件驗證有警告）",
            default=False
        )

        if not confirmed:
            return {
                "cancelled": True,
                "blocked": False,
                "validation": validation_report,
                "errors": [f"組件驗證需要決策: {validation_report.requires_decision}"]
            }

        # 用戶選擇繼續，但可能有未解決的問題
        if validation_report.not_found_count > 0:
            return {
                "cancelled": False,
                "blocked": True,
                "validation": validation_report,
                "errors": [f"有 {validation_report.not_found_count} 個組件找不到"]
            }

        return {"cancelled": False, "blocked": False, "validation": validation_report}

    async def _phase4_pre_check_with_hitl(self) -> Dict[str, Any]:
        """
        Phase 4.5: Pre-Execution Check + HITL

        驗證 placement_info，若有警告詢問是否繼續
        """
        print("\n" + "=" * 60)
        print("  Phase 4.5: Pre-Execution Check")
        print("=" * 60)

        # 執行 Pre-Check
        pre_check = self.workflow.phase4_pre_check(auto_continue=False)

        if not pre_check["passed"]:
            return {
                "blocked": True,
                "errors": [pre_check.get("message", "Pre-check failed")]
            }

        if pre_check["can_continue"] == "ask_user":
            warning_count = pre_check.get("warning_count", 0)
            confirmed = await self.hitl.confirm(
                f"有 {warning_count} 個警告，是否繼續執行？",
                default=True
            )

            if not confirmed:
                return {"cancelled": True, "pre_check": pre_check}

        return {"cancelled": False, "blocked": False, "pre_check": pre_check}

    def _phase5_execute(self) -> Dict[str, Any]:
        """
        Phase 5: 執行部署

        使用 clear_first + smart_layout
        """
        print("\n" + "=" * 60)
        print("  Phase 5: 執行部署")
        print("=" * 60)

        return self.workflow.phase5_execute(
            clear_first=True,
            use_smart_layout=True,
            skip_pre_check=True  # 已在 Phase 4.5 檢查
        )

    def _phase6_archive(self) -> str:
        """
        Phase 6: 歸檔

        將工作檔案移動到 GH_PKG
        """
        print("\n" + "=" * 60)
        print("  Phase 6: 歸檔")
        print("=" * 60)

        return self.workflow.phase6_archive()

    def _merge_knowledge_to_spec(
        self,
        base_spec: Dict,
        knowledge: Dict[str, CollectedKnowledge]
    ) -> Dict:
        """
        合併收集的知識到設計規格

        Args:
            base_spec: 基礎規格
            knowledge: 收集的知識

        Returns:
            更新後的規格
        """
        merged = dict(base_spec)

        for key, collected in knowledge.items():
            # 嘗試解析數值
            value = collected.value
            try:
                if "." in value:
                    value = float(value)
                else:
                    value = int(value)
            except (ValueError, AttributeError):
                pass

            # 更新規格
            # 嘗試匹配 key 到 spec 中的對應欄位
            normalized_key = key.lower().replace(" ", "_")

            # 直接更新 parameters
            if "parameters" not in merged:
                merged["parameters"] = {}

            merged["parameters"][normalized_key] = value

        return merged

    def _format_spec_summary(self, spec: Dict) -> str:
        """格式化規格摘要"""
        lines = []
        params = spec.get("parameters", {})

        for key, value in params.items():
            if isinstance(value, dict):
                # 有 min/max/default 的參數
                default = value.get("default", "")
                min_val = value.get("min", "")
                max_val = value.get("max", "")
                lines.append(f"  - {key}: {default} (範圍: {min_val}-{max_val})")
            else:
                lines.append(f"  - {key}: {value}")

        return "\n".join(lines) if lines else "  (使用預設規格)"

    def _load_placement_info(self) -> Optional[Dict]:
        """載入 placement_info.json"""
        path = self.wip_dir / "placement_info.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _to_dict(self, result: WorkflowResult) -> Dict[str, Any]:
        """將 WorkflowResult 轉換為字典"""
        output = {
            "status": result.status,
            "phase": result.phase,
            "archive_path": result.archive_path,
            "placement_info": result.placement_info,
            "execution": result.execution,
            "errors": result.errors,
            "warnings": result.warnings,
            "claude_calls": result.claude_calls,
            "collected_knowledge": result.collected_knowledge,
        }

        # 添加組件驗證結果（如果有）
        if result.component_validation is not None:
            output["component_validation"] = result.component_validation.to_dict()

        return output


# =============================================================================
# 便捷函數
# =============================================================================

async def run_design_workflow(
    design_intent: str,
    project_name: str = "design_project",
    hitl: Optional[HITLCollaborator] = None,
    auto_mode: bool = False
) -> Dict[str, Any]:
    """
    快速執行設計工作流程

    Args:
        design_intent: 設計意圖
        project_name: 專案名稱
        hitl: HITL 協作器 (可選)
        auto_mode: 自動模式

    Returns:
        工作流程結果
    """
    if hitl is None:
        hitl = HITLCollaborator(auto_mode=auto_mode)

    workflow = DesignWorkflowV2(project_name, hitl)
    return await workflow.run_full_workflow(design_intent)


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import asyncio
    import sys

    async def main():
        print("DesignWorkflowV2 - 整合版設計工作流程")
        print("=" * 60)

        if len(sys.argv) < 2:
            print("\nUsage:")
            print("  python design_workflow_v2.py '<設計意圖>'")
            print("\nExamples:")
            print("  python design_workflow_v2.py '設計一個螺旋樓梯，12階'")
            return

        design_intent = " ".join(sys.argv[1:])

        # 使用 CLI 回調
        from .hitl_collaborator import cli_user_callback

        hitl = HITLCollaborator(user_callback=cli_user_callback)
        workflow = DesignWorkflowV2("cli_project", hitl)

        result = await workflow.run_full_workflow(design_intent)

        print("\n" + "=" * 60)
        print("  工作流程結果")
        print("=" * 60)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    asyncio.run(main())
