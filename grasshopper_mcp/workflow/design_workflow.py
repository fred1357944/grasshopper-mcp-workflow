#!/usr/bin/env python3
"""
設計先行工作流程 (Design-First Workflow)
=========================================

六階段互動式設計流程，結合 Claude Code 對話 + VSCode 編輯：

Phase 1: 需求釐清 (Clarify Requirements)
Phase 2: 幾何分解 (Decompose Geometry) → part_info.mmd
Phase 3: 組件規劃 (Plan Components) → component_info.mmd
Phase 4: GUID 查詢 (Query GUIDs) → 更新 component_info.mmd
Phase 5: 執行部署 (Execute Deployment) → placement_info.json → GH
Phase 6: 歸檔整理 (Archive) → GH_PKG/

工作流程：
    Claude Code: 對話 + 生成檔案
    VSCode: 預覽 Mermaid + 編輯微調
    使用者: 在 Claude Code 確認後進入下一階段

使用方式：
    from grasshopper_mcp.workflow import DesignWorkflow

    wf = DesignWorkflow("spiral_staircase")
    wf.check_status()  # 查看目前進度
    wf.phase1_clarify("設計一個螺旋樓梯")  # 開始新設計
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class WorkflowPhase(Enum):
    """工作流程階段"""
    INIT = 0           # 初始化
    CLARIFY = 1        # Phase 1: 需求釐清
    DECOMPOSE = 2      # Phase 2: 幾何分解
    PLAN = 3           # Phase 3: 組件規劃
    QUERY_GUID = 4     # Phase 4: GUID 查詢
    PRE_CHECK = 45     # Phase 4.5: Pre-Execution Checklist (NEW)
    EXECUTE = 5        # Phase 5: 執行部署
    ARCHIVE = 6        # Phase 6: 歸檔


@dataclass
class DesignSpec:
    """設計規格"""
    name: str
    description: str = ""
    constraints: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    confirmed: bool = False


class DesignWorkflow:
    """
    設計先行工作流程管理器

    核心理念：
    - 檔案即介面：生成 .mmd 檔案供 VSCode 預覽/編輯
    - 對話即控制：使用者在 Claude Code 確認後進入下一階段
    - 狀態即檔案：根據 GH_WIP/ 檔案狀態判斷進度
    """

    # 目錄配置
    WIP_DIR = "GH_WIP"
    PKG_DIR = "GH_PKG"

    # 檔案名稱
    PART_INFO = "part_info.mmd"
    COMPONENT_INFO = "component_info.mmd"
    PLACEMENT_INFO = "placement_info.json"
    ID_MAP = "component_id_map.json"

    def __init__(self, project_name: str, base_path: Optional[str] = None):
        """
        初始化工作流程

        Args:
            project_name: 專案名稱 (如 "spiral_staircase")
            base_path: 專案根目錄 (預設為當前目錄)
        """
        self.project_name = project_name
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.wip_path = self.base_path / self.WIP_DIR
        self.pkg_path = self.base_path / self.PKG_DIR

        # 確保目錄存在
        self.wip_path.mkdir(exist_ok=True)
        self.pkg_path.mkdir(exist_ok=True)

        # 設計規格
        self.spec: Optional[DesignSpec] = None

    # =========================================================================
    # 狀態檢查
    # =========================================================================

    def check_status(self) -> Dict[str, Any]:
        """
        檢查目前工作流程狀態

        根據 GH_WIP/ 中的檔案判斷目前階段
        """
        files = {
            "part_info": (self.wip_path / self.PART_INFO).exists(),
            "component_info": (self.wip_path / self.COMPONENT_INFO).exists(),
            "placement_info": (self.wip_path / self.PLACEMENT_INFO).exists(),
            "id_map": (self.wip_path / self.ID_MAP).exists(),
        }

        # 判斷階段
        if not files["part_info"]:
            phase = WorkflowPhase.CLARIFY
            next_action = "執行 phase1_clarify() 或 phase2_decompose()"
        elif not files["component_info"]:
            phase = WorkflowPhase.DECOMPOSE
            next_action = "在 VSCode 確認 part_info.mmd 後執行 phase3_plan()"
        elif not files["placement_info"]:
            phase = WorkflowPhase.PLAN
            next_action = "在 VSCode 確認 component_info.mmd 後生成 placement_info.json"
        elif not files["id_map"]:
            # placement_info.json 存在但未執行 → 需要先通過 Pre-Check
            phase = WorkflowPhase.PRE_CHECK
            next_action = "執行 phase4_pre_check() 驗證後再 phase5_execute()"
        else:
            phase = WorkflowPhase.ARCHIVE
            next_action = "執行 phase6_archive() 歸檔專案"

        status = {
            "project_name": self.project_name,
            "current_phase": phase.name,
            "phase_number": phase.value,
            "files": files,
            "next_action": next_action,
            "wip_path": str(self.wip_path),
        }

        return status

    def print_status(self):
        """打印目前狀態"""
        status = self.check_status()

        print("=" * 60)
        print(f"  設計工作流程狀態: {self.project_name}")
        print("=" * 60)
        print(f"  階段: Phase {status['phase_number']} - {status['current_phase']}")
        print(f"  下一步: {status['next_action']}")
        print()
        print("  檔案狀態:")
        for name, exists in status['files'].items():
            icon = "✓" if exists else "○"
            print(f"    {icon} {name}")
        print()
        print(f"  工作目錄: {status['wip_path']}")
        print("=" * 60)

    # =========================================================================
    # Phase 1: 需求釐清
    # =========================================================================

    def phase1_clarify(self, design_intent: str) -> Dict[str, Any]:
        """
        Phase 1: 需求釐清

        這個階段主要是對話，不產生檔案。
        返回需要確認的問題列表。

        Args:
            design_intent: 使用者的設計意圖描述

        Returns:
            需要釐清的問題和建議規格
        """
        # 分析設計意圖
        questions = []
        suggestions = {}

        intent_lower = design_intent.lower()

        # 根據關鍵字提出問題
        if "樓梯" in intent_lower or "stair" in intent_lower:
            questions.extend([
                "階梯數量範圍？（建議 6-30 階）",
                "總高度約多少？（單位 cm）",
                "需要扶手嗎？",
                "風格偏好？（工業/現代/極簡）",
            ])
            suggestions = {
                "steps": {"min": 6, "max": 30, "default": 12},
                "total_height": {"min": 150, "max": 500, "default": 300},
                "has_handrail": True,
                "style": "modern",
            }
        elif "桌" in intent_lower or "table" in intent_lower:
            questions.extend([
                "桌面尺寸？（長 x 寬，cm）",
                "桌腳數量？（4 腳 / 中央單柱）",
                "總高度？（cm）",
            ])
            suggestions = {
                "width": {"min": 60, "max": 200, "default": 120},
                "length": {"min": 60, "max": 300, "default": 80},
                "height": {"min": 50, "max": 100, "default": 75},
                "leg_count": 4,
            }
        elif "椅" in intent_lower or "chair" in intent_lower:
            questions.extend([
                "座椅類型？（辦公椅/餐椅/休閒椅）",
                "是否需要扶手？",
                "座高範圍？（cm）",
            ])
            suggestions = {
                "seat_height": {"min": 40, "max": 55, "default": 45},
                "has_armrest": False,
            }
        else:
            questions.extend([
                "請描述物件的基本形狀和尺寸",
                "有哪些可調整的參數？",
                "是否有特殊的幾何約束？",
            ])

        return {
            "phase": "clarify",
            "design_intent": design_intent,
            "questions": questions,
            "suggestions": suggestions,
            "next_step": "回答以上問題，或直接說「使用建議規格」",
        }

    # =========================================================================
    # Phase 2: 幾何分解
    # =========================================================================

    def phase2_decompose(self, spec: Dict[str, Any]) -> str:
        """
        Phase 2: 幾何分解 → 生成 part_info.mmd

        Args:
            spec: 確認後的設計規格

        Returns:
            生成的檔案路徑
        """
        self.spec = DesignSpec(
            name=self.project_name,
            description=spec.get("description", ""),
            constraints=spec.get("constraints", []),
            parameters=spec.get("parameters", {}),
            confirmed=True,
        )

        # 生成 part_info.mmd (erDiagram 格式)
        mmd_content = self._generate_part_info(spec)

        # 寫入檔案
        output_path = self.wip_path / self.PART_INFO
        output_path.write_text(mmd_content, encoding="utf-8")

        print(f"\n✓ 已生成: {output_path}")
        print("  請在 VSCode 開啟此檔案：")
        print(f"  code {output_path}")
        print("\n  確認後回來說「確認，繼續」")

        return str(output_path)

    def _generate_part_info(self, spec: Dict[str, Any]) -> str:
        """生成 part_info.mmd (erDiagram 格式)"""
        # 這是模板，實際內容會根據 spec 動態生成
        project_name = self.project_name.upper().replace("_", " ")

        mmd = f"""erDiagram
    %% {project_name} - 幾何分解圖
    %% 生成時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}

"""

        # 根據專案類型或描述生成不同的結構
        desc_lower = spec.get("description", "").lower()
        name_lower = self.project_name.lower()

        if any(kw in name_lower or kw in desc_lower for kw in ["stair", "樓梯", "helix", "螺旋"]):
            mmd += self._generate_staircase_parts(spec)
        elif any(kw in name_lower or kw in desc_lower for kw in ["table", "桌"]):
            mmd += self._generate_table_parts(spec)
        else:
            mmd += self._generate_generic_parts(spec)

        return mmd

    def _generate_staircase_parts(self, spec: Dict[str, Any]) -> str:
        """生成螺旋樓梯的 part_info"""
        has_handrail = spec.get("parameters", {}).get("has_handrail", True)

        parts = """    STAIRCASE ||--o{ STEP : contains
    STAIRCASE ||--|| CENTER_POLE : contains
"""
        if has_handrail:
            parts += """    STAIRCASE ||--|| HANDRAIL : contains
"""

        parts += f"""
    STAIRCASE {{
        string name "螺旋樓梯"
        int step_count "{spec.get('parameters', {}).get('steps', {}).get('default', 12)}"
        float total_height "{spec.get('parameters', {}).get('total_height', {}).get('default', 300)}"
    }}

    STEP {{
        string sketch_type "Center Box"
        string forming_method "Rotate around center"
        float width "OuterR - InnerR"
        float thickness "5.0"
        plane base_plane "計算自 angle 和 height"
    }}

    CENTER_POLE {{
        string sketch_type "Circle"
        string forming_method "Cylinder"
        float radius "InnerR"
        float height "TotalH"
        point base_point "Origin (0, 0, 0)"
    }}
"""

        if has_handrail:
            parts += """
    HANDRAIL {{
        string sketch_type "Points"
        string forming_method "Interpolate + Pipe"
        float rail_height "90.0"
        float pipe_radius "3.0"
        curve path "螺旋曲線，沿外側"
    }}
"""

        return parts

    def _generate_table_parts(self, spec: Dict[str, Any]) -> str:
        """生成桌子的 part_info"""
        leg_count = spec.get("parameters", {}).get("leg_count", 4)

        return f"""    TABLE ||--|| TABLE_TOP : contains
    TABLE ||--o{{ TABLE_LEG : contains

    TABLE_TOP ||--o{{ TABLE_LEG : supports

    TABLE {{
        string name "桌子"
        int leg_count "{leg_count}"
        float total_height "{spec.get('parameters', {}).get('height', {}).get('default', 75)}"
    }}

    TABLE_TOP {{
        string sketch_type "Rectangle"
        string forming_method "Extrude"
        float width "{spec.get('parameters', {}).get('width', {}).get('default', 120)}"
        float length "{spec.get('parameters', {}).get('length', {}).get('default', 80)}"
        float height "5.0"
        plane base_plane "XY Plane at Z=height-5"
    }}

    TABLE_LEG {{
        string sketch_type "Circle"
        string forming_method "Extrude"
        float radius "2.5"
        float height "{spec.get('parameters', {}).get('height', {}).get('default', 75) - 5}"
        plane base_plane "四個角落位置"
        int count "{leg_count}"
    }}
"""

    def _generate_generic_parts(self, spec: Dict[str, Any]) -> str:
        """生成通用的 part_info"""
        return f"""    OBJECT {{
        string name "{self.project_name}"
        string description "待定義"
    }}

    %% 請根據實際需求編輯此檔案
    %% 添加更多零件和關係
"""

    # =========================================================================
    # Phase 3: 組件規劃
    # =========================================================================

    def phase3_plan(self) -> str:
        """
        Phase 3: 組件規劃 → 生成 component_info.mmd

        讀取 part_info.mmd，生成 GH 組件連接圖

        Returns:
            生成的檔案路徑
        """
        # 讀取 part_info.mmd
        part_info_path = self.wip_path / self.PART_INFO
        if not part_info_path.exists():
            raise FileNotFoundError(f"請先完成 Phase 2: {part_info_path}")

        part_info = part_info_path.read_text(encoding="utf-8")

        # 生成 component_info.mmd (flowchart 格式)
        mmd_content = self._generate_component_info(part_info)

        # 寫入檔案
        output_path = self.wip_path / self.COMPONENT_INFO
        output_path.write_text(mmd_content, encoding="utf-8")

        print(f"\n✓ 已生成: {output_path}")
        print("  請在 VSCode 開啟此檔案：")
        print(f"  code {output_path}")
        print("\n  確認連接關係後回來說「確認，繼續」")

        return str(output_path)

    def _generate_component_info(self, part_info: str) -> str:
        """生成 component_info.mmd (flowchart 格式)"""
        mmd = f"""flowchart LR
    %% {self.project_name.upper()} - GH 組件連接圖
    %% 生成時間: {datetime.now().strftime("%Y-%m-%d %H:%M")}
    %%
    %% 請在 VSCode 中預覽並編輯：
    %% 1. 確認組件類型正確
    %% 2. 確認連接關係正確
    %% 3. 調整後儲存

"""

        # 根據專案類型或規格生成不同的組件圖
        # 讀取 part_info 來判斷類型
        name_lower = self.project_name.lower()

        if any(kw in name_lower or kw in part_info.lower() for kw in ["stair", "樓梯", "helix", "螺旋"]):
            mmd += self._generate_staircase_components()
        elif any(kw in name_lower or kw in part_info.lower() for kw in ["table", "桌"]):
            mmd += self._generate_table_components()
        else:
            mmd += self._generate_generic_components()

        return mmd

    def _generate_staircase_components(self) -> str:
        """生成螺旋樓梯的 component_info"""
        return """    subgraph PARAMS["參數 Sliders"]
        STEPS["Number Slider<br/>nickname: Steps<br/>value: 12<br/>range: 6-30"]
        TOTALH["Number Slider<br/>nickname: TotalH<br/>value: 300<br/>range: 150-500"]
        OUTERR["Number Slider<br/>nickname: OuterR<br/>value: 120<br/>range: 80-200"]
        INNERR["Number Slider<br/>nickname: InnerR<br/>value: 25<br/>range: 15-50"]
        ROTATION["Number Slider<br/>nickname: Rotation<br/>value: 1.0<br/>range: 0.5-3.0"]
        STEPT["Number Slider<br/>nickname: StepT<br/>value: 5<br/>range: 3-10"]
    end

    subgraph CALC["計算邏輯"]
        SERIES["Series<br/>nickname: StepSeries"]
        DIV_ANGLE["Division<br/>nickname: AnglePerStep"]
        DIV_HEIGHT["Division<br/>nickname: HeightPerStep"]
        MUL_ANGLES["Multiplication<br/>nickname: StepAngles"]
        MUL_HEIGHTS["Multiplication<br/>nickname: StepHeights"]
    end

    subgraph TRIG["三角函數"]
        RADS["Radians<br/>nickname: Rads"]
        SIN["Sine<br/>nickname: SinA"]
        COS["Cosine<br/>nickname: CosA"]
    end

    subgraph GEO["幾何生成"]
        MUL_X["Multiplication<br/>nickname: Xs"]
        MUL_Y["Multiplication<br/>nickname: Ys"]
        PT["Construct Point<br/>nickname: StepCenters"]
        BOX["Center Box<br/>nickname: StepBoxes"]
        ROTATE["Rotate<br/>nickname: RotatedSteps"]
    end

    %% 連接
    STEPS -->|"N → C"| SERIES
    SERIES -->|"S → A"| MUL_ANGLES
    DIV_ANGLE -->|"Result → B"| MUL_ANGLES

    MUL_ANGLES -->|"Result → D"| RADS
    RADS -->|"Radians → x"| SIN
    RADS -->|"Radians → x"| COS

    COS -->|"y → A"| MUL_X
    SIN -->|"y → A"| MUL_Y

    MUL_X -->|"Result → X"| PT
    MUL_Y -->|"Result → Y"| PT
    MUL_HEIGHTS -->|"Result → Z"| PT

    PT -->|"Pt → B"| BOX
    BOX -->|"B → G"| ROTATE
    RADS -->|"Radians → A"| ROTATE
"""

    def _generate_table_components(self) -> str:
        """生成桌子的 component_info"""
        return """    subgraph PARAMS["參數 Sliders"]
        WIDTH["Number Slider<br/>nickname: Width<br/>value: 120"]
        LENGTH["Number Slider<br/>nickname: Length<br/>value: 80"]
        HEIGHT["Number Slider<br/>nickname: Height<br/>value: 75"]
        LEG_R["Number Slider<br/>nickname: LegRadius<br/>value: 2.5"]
    end

    subgraph TOP["桌面"]
        XY_PLANE["XY Plane<br/>nickname: BasePlane"]
        RECT["Rectangle<br/>nickname: TopRect"]
        BOUNDARY["Boundary Surfaces<br/>nickname: TopSurf"]
        EXTRUDE_TOP["Extrude<br/>nickname: TopExtrude"]
    end

    subgraph LEGS["桌腳"]
        LEG_POSITIONS["Construct Point<br/>nickname: LegPositions<br/>%% 四個角落"]
        CIRCLES["Circle<br/>nickname: LegCircles"]
        EXTRUDE_LEGS["Extrude<br/>nickname: LegExtrude"]
    end

    %% 連接
    WIDTH -->|"N → X"| RECT
    LENGTH -->|"N → Y"| RECT
    XY_PLANE -->|"Plane"| RECT
    RECT -->|"Rectangle"| BOUNDARY
    BOUNDARY -->|"Surface → B"| EXTRUDE_TOP

    LEG_POSITIONS -->|"Pt → P"| CIRCLES
    LEG_R -->|"N → R"| CIRCLES
    CIRCLES -->|"C → B"| EXTRUDE_LEGS
"""

    def _generate_generic_components(self) -> str:
        """生成通用的 component_info"""
        return """    subgraph PARAMS["參數"]
        SLIDER1["Number Slider<br/>nickname: Param1"]
        SLIDER2["Number Slider<br/>nickname: Param2"]
    end

    subgraph PROCESS["處理"]
        COMP1["Component1<br/>nickname: Process1"]
    end

    subgraph OUTPUT["輸出"]
        OUT["Output<br/>nickname: Result"]
    end

    SLIDER1 --> COMP1
    SLIDER2 --> COMP1
    COMP1 --> OUT

    %% 請根據實際需求編輯此檔案
"""

    # =========================================================================
    # Phase 4.5: Pre-Execution Checklist (NEW)
    # =========================================================================

    def phase4_pre_check(self, auto_continue: bool = False) -> Dict[str, Any]:
        """
        Phase 4.5: Pre-Execution Checklist

        在執行部署前驗證 placement_info.json，檢查：
        - 組件 GUID 是否可信
        - 連接參數是否有 FuzzyMatcher 風險
        - Slider/Panel 是否有初始值

        Args:
            auto_continue: 若為 True，有 warning 時自動繼續；否則需要確認

        Returns:
            驗證結果，包含是否可以繼續執行
        """
        from grasshopper_mcp.pre_execution_checker import PreExecutionChecker

        placement_path = self.wip_path / self.PLACEMENT_INFO
        if not placement_path.exists():
            return {
                "phase": "pre_check",
                "passed": False,
                "message": f"placement_info.json 不存在，請先完成 Phase 4: {placement_path}",
                "can_continue": False,
            }

        # 載入配置
        with open(placement_path, encoding="utf-8") as f:
            placement_info = json.load(f)

        # 執行驗證
        checker = PreExecutionChecker()
        results = checker.check_placement_info(placement_info)
        report = checker.generate_report()

        # 輸出報告
        print("\n" + "=" * 60)
        print("  Phase 4.5: Pre-Execution Checklist")
        print("=" * 60)
        print(report)

        # 判斷結果
        critical = [r for r in results if r.severity == "critical"]
        warnings = [r for r in results if r.severity == "warning"]

        if critical:
            print("\n❌ 驗證失敗：請修復 Critical 問題後重試")
            return {
                "phase": "pre_check",
                "passed": False,
                "critical_count": len(critical),
                "warning_count": len(warnings),
                "can_continue": False,
                "message": "請修復 Critical 問題",
            }

        if warnings and not auto_continue:
            print("\n⚠️ 有 Warning，需要確認是否繼續")
            print("  說「繼續執行」或「修復後重試」")
            return {
                "phase": "pre_check",
                "passed": True,
                "critical_count": 0,
                "warning_count": len(warnings),
                "can_continue": "ask_user",
                "message": "有 Warning，等待確認",
            }

        print("\n✅ 驗證通過，可以進入 Phase 5")
        return {
            "phase": "pre_check",
            "passed": True,
            "critical_count": 0,
            "warning_count": len(warnings),
            "can_continue": True,
            "message": "驗證通過",
        }

    # =========================================================================
    # Phase 5: 執行部署
    # =========================================================================

    def phase5_execute(
        self,
        clear_first: bool = True,
        use_smart_layout: bool = True,
        skip_pre_check: bool = False
    ) -> Dict[str, Any]:
        """
        Phase 5: 執行部署到 Grasshopper

        讀取 component_info.mmd，生成 placement_info.json，然後部署

        Args:
            clear_first: 是否先清空 GH 畫布（預設 True）
            use_smart_layout: 是否使用智能佈局避免重疊（預設 True）
            skip_pre_check: 是否跳過 Pre-Execution Checklist

        Returns:
            部署結果
        """
        # 檢查 component_info.mmd 存在
        component_info_path = self.wip_path / self.COMPONENT_INFO
        if not component_info_path.exists():
            raise FileNotFoundError(f"請先完成 Phase 3: {component_info_path}")

        # Phase 4.5: Pre-Execution Checklist
        if not skip_pre_check:
            pre_check_result = self.phase4_pre_check(auto_continue=False)
            if not pre_check_result["can_continue"]:
                return {
                    "phase": "execute",
                    "status": "blocked",
                    "message": "Pre-Execution Checklist 未通過",
                    "pre_check": pre_check_result,
                }
            if pre_check_result["can_continue"] == "ask_user":
                return {
                    "phase": "execute",
                    "status": "pending_confirmation",
                    "message": "等待使用者確認 Warning 後繼續",
                    "pre_check": pre_check_result,
                }

        # 檢查 placement_info.json 存在
        placement_info_path = self.wip_path / self.PLACEMENT_INFO
        if not placement_info_path.exists():
            return {
                "phase": "execute",
                "status": "error",
                "message": f"請先生成 placement_info.json: {placement_info_path}",
            }

        # 使用 PlacementExecutor 執行部署
        print("\n🚀 Phase 5 執行部署...")
        print(f"   clear_first: {clear_first}")
        print(f"   use_smart_layout: {use_smart_layout}")

        try:
            from grasshopper_tools import PlacementExecutor

            executor = PlacementExecutor()
            result = executor.execute_placement_info(
                json_path=str(placement_info_path),
                clear_first=clear_first,
                use_smart_layout=use_smart_layout,
                save_id_map=True,
                id_map_path=str(self.wip_path / self.ID_MAP),
            )

            if result["success"]:
                print("\n✅ 部署成功！")
                return {
                    "phase": "execute",
                    "status": "success",
                    "message": "部署完成",
                    "result": result,
                }
            else:
                print("\n⚠️ 部署有部分失敗")
                return {
                    "phase": "execute",
                    "status": "partial_success",
                    "message": "部分命令失敗",
                    "result": result,
                }

        except ImportError as e:
            # 如果 PlacementExecutor 無法導入，提供 CLI 命令
            print(f"\n⚠️ 無法導入 PlacementExecutor: {e}")
            print("  請使用 CLI 命令執行：")
            clear_flag = "--clear-first" if clear_first else ""
            layout_flag = "" if use_smart_layout else "--no-smart-layout"
            cmd = f"python -m grasshopper_tools.cli execute-placement {placement_info_path} {clear_flag} {layout_flag}".strip()
            print(f"  {cmd}")
            return {
                "phase": "execute",
                "status": "pending",
                "message": "請使用 CLI 命令執行",
                "command": cmd,
            }

        except Exception as e:
            print(f"\n❌ 部署錯誤: {e}")
            return {
                "phase": "execute",
                "status": "error",
                "message": str(e),
            }

    # =========================================================================
    # Phase 6: 歸檔
    # =========================================================================

    def phase6_archive(self) -> str:
        """
        Phase 6: 歸檔整理

        將 GH_WIP 中的檔案移動到 GH_PKG，加上時間戳記

        Returns:
            歸檔目錄路徑
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        archive_name = f"{timestamp}-{self.project_name}"
        archive_path = self.pkg_path / archive_name

        # 創建歸檔目錄
        archive_path.mkdir(exist_ok=True)

        # 複製檔案
        import shutil
        for f in [self.PART_INFO, self.COMPONENT_INFO, self.PLACEMENT_INFO, self.ID_MAP]:
            src = self.wip_path / f
            if src.exists():
                shutil.copy(src, archive_path / f)

        print(f"\n✓ 已歸檔到: {archive_path}")

        return str(archive_path)


# =============================================================================
# 便捷函數
# =============================================================================

def new_design(name: str) -> DesignWorkflow:
    """開始新設計"""
    wf = DesignWorkflow(name)
    wf.print_status()
    return wf


def check_progress() -> Dict[str, Any]:
    """檢查目前進度"""
    wf = DesignWorkflow("current")
    return wf.check_status()


# =============================================================================
# 測試
# =============================================================================

if __name__ == "__main__":
    # 測試
    wf = DesignWorkflow("test_staircase")
    wf.print_status()

    # Phase 1
    result = wf.phase1_clarify("設計一個螺旋樓梯，12階，300cm高，要扶手")
    print("\n=== Phase 1 Result ===")
    for q in result["questions"]:
        print(f"  Q: {q}")
