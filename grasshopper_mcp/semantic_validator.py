#!/usr/bin/env python3
"""
Semantic Validator - 語義驗證器
================================

解決 Pre-Execution Checker 只做「語法驗證」的問題。
這個模組負責驗證配置的「語義正確性」：

1. 組件行為解釋：解釋每個組件實際做什麼
2. 資料流分析：預估輸出數量，檢測 explosion 風險
3. 參數語義檢查：Size vs Count, Radius vs Result 等

核心概念：
    語法正確 ≠ 語義正確
    GUID 正確 ≠ 組件用法正確
    連接成功 ≠ 資料流合理

2026-01-24
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum


class SemanticRisk(Enum):
    """語義風險等級"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"  # 可能導致崩潰


@dataclass
class ComponentBehavior:
    """組件行為描述"""
    name: str
    category: str
    description: str
    inputs: Dict[str, str]  # param_name -> description
    outputs: Dict[str, str]
    output_multiplier: str  # "1:1", "1:N", "N:M" 等
    warnings: List[str] = field(default_factory=list)
    common_mistakes: List[str] = field(default_factory=list)


@dataclass
class DataFlowEstimate:
    """資料流預估"""
    component_id: str
    component_type: str
    input_count: int  # 預估輸入數量
    output_count: int  # 預估輸出數量
    multiplier_reason: str  # 為什麼有這個乘數
    risk_level: SemanticRisk
    warning: Optional[str] = None


@dataclass
class SemanticCheckResult:
    """語義檢查結果"""
    passed: bool
    component_id: str
    check_type: str  # "behavior" | "dataflow" | "parameter"
    risk_level: SemanticRisk
    message: str
    explanation: Optional[str] = None
    suggestion: Optional[str] = None


from grasshopper_mcp.knowledge_base import ConnectionKnowledgeBase

class SemanticValidator:
    """
    語義驗證器

    使用方式：
    ```python
    validator = SemanticValidator()
    results = validator.validate(placement_info)
    report = validator.generate_human_readable_report()
    ```
    """

    # 組件行為知識庫
    COMPONENT_BEHAVIORS: Dict[str, ComponentBehavior] = {
        "Mesh Box": ComponentBehavior(
            name="Mesh Box",
            category="Mesh/Primitive",
            description="創建一個 Mesh 立方體，X/Y/Z 參數是「細分數量」而非尺寸",
            inputs={
                "X": "X 方向細分數量 (非尺寸！)",
                "Y": "Y 方向細分數量 (非尺寸！)",
                "Z": "Z 方向細分數量 (非尺寸！)"
            },
            outputs={"M": "輸出 Mesh，包含 X*Y*Z 個面"},
            output_multiplier="1:X*Y*Z",
            warnings=["X/Y/Z 是細分數，不是尺寸！10×10×10 = 1000 個面"],
            common_mistakes=["誤以為 X/Y/Z 是尺寸，導致面數爆炸"]
        ),
        "Center Box": ComponentBehavior(
            name="Center Box",
            category="Surface/Primitive",
            description="創建一個以原點為中心的 Brep 立方體，X/Y/Z 是真正的尺寸",
            inputs={
                "B": "基準平面",
                "X": "X 方向尺寸",
                "Y": "Y 方向尺寸",
                "Z": "Z 方向尺寸"
            },
            outputs={"B": "輸出 Brep，單一立方體"},
            output_multiplier="1:1",
            warnings=[],
            common_mistakes=[]
        ),
        "Face Normals": ComponentBehavior(
            name="Face Normals",
            category="Mesh/Analysis",
            description="計算 Mesh 每個面的中心點和法向量",
            inputs={"M": "輸入 Mesh"},
            outputs={
                "C": "面中心點 (與面數相同)",
                "N": "面法向量 (與面數相同)"
            },
            output_multiplier="1:N (N = 輸入 Mesh 面數)",
            warnings=["輸出數量 = 輸入 Mesh 面數"],
            common_mistakes=["使用高細分 Mesh 導致輸出爆炸"]
        ),
        "Deconstruct Brep": ComponentBehavior(
            name="Deconstruct Brep",
            category="Surface/Analysis",
            description="分解 Brep 為面、邊、頂點",
            inputs={"B": "輸入 Brep"},
            outputs={
                "F": "面列表",
                "E": "邊列表",
                "V": "頂點列表"
            },
            output_multiplier="1:固定 (取決於 Brep 複雜度)",
            warnings=["立方體輸出 6 個面"],
            common_mistakes=[]
        ),
        "Evaluate Surface": ComponentBehavior(
            name="Evaluate Surface",
            category="Surface/Analysis",
            description="在表面 UV 座標處評估，獲取點、法向量、Frame",
            inputs={
                "S": "輸入 Surface",
                "U": "U 參數 (0-1)",
                "V": "V 參數 (0-1)"
            },
            outputs={
                "P": "點",
                "N": "法向量",
                "F": "Frame (Plane)"
            },
            output_multiplier="1:1",
            warnings=["UV=0.5,0.5 是表面中心"],
            common_mistakes=[]
        ),
        "Wasp_Connection From Direction": ComponentBehavior(
            name="Wasp_Connection From Direction",
            category="WASP/Connection",
            description="從 Geometry、Center、Up 方向創建 WASP 連接點",
            inputs={
                "GEO": "幾何 (必須是 Mesh!)",
                "CEN": "連接點中心",
                "UP": "向上方向 (Line, 非 Vector)"
            },
            outputs={"CONN": "連接點列表"},
            output_multiplier="1:N (N = CEN 輸入數量)",
            warnings=["GEO 必須是 Mesh，UP 必須是 Line"],
            common_mistakes=["傳入 Brep 而非 Mesh", "傳入 Vector 而非 Line"]
        ),
        "Wasp_Connection From Plane": ComponentBehavior(
            name="Wasp_Connection From Plane",
            category="WASP/Connection",
            description="從 Geometry 和 Plane 創建 WASP 連接點 (推薦用法)",
            inputs={
                "GEO": "幾何",
                "PLN": "連接平面"
            },
            outputs={"CONN": "連接點列表"},
            output_multiplier="1:N (N = PLN 輸入數量)",
            warnings=[],
            common_mistakes=[]
        ),
        "Wasp_Basic Part": ComponentBehavior(
            name="Wasp_Basic Part",
            category="WASP/Part",
            description="創建 WASP Part",
            inputs={
                "NAME": "Part 名稱",
                "GEO": "幾何",
                "CONN": "連接點列表"
            },
            outputs={"PART": "WASP Part"},
            output_multiplier="1:1",
            warnings=[],
            common_mistakes=[]
        ),
        "Wasp_Rules Generator": ComponentBehavior(
            name="Wasp_Rules Generator",
            category="WASP/Rule",
            description="自動生成 WASP 規則 (推薦！只需 PART 輸入)",
            inputs={"PART": "Part 列表"},
            outputs={"R": "規則列表"},
            output_multiplier="1:N×N (全連接)",
            warnings=["輸出數量 = Part 數量 × 連接點數量"],
            common_mistakes=["與 Wasp_Rule 混淆"]
        ),
        "Wasp_Rule": ComponentBehavior(
            name="Wasp_Rule",
            category="WASP/Rule",
            description="手動定義單一 WASP 規則 (需要 P1/C1/P2/C2)",
            inputs={
                "P1": "Part 1",
                "C1": "Connection 1",
                "P2": "Part 2",
                "C2": "Connection 2"
            },
            outputs={"R": "單一規則"},
            output_multiplier="1:1",
            warnings=["需要手動定義每個連接，較繁瑣"],
            common_mistakes=["使用 Rule 而非 Rules Generator"]
        ),
        "Wasp_Stochastic Aggregation": ComponentBehavior(
            name="Wasp_Stochastic Aggregation",
            category="WASP/Aggregation",
            description="隨機聚集",
            inputs={
                "PART": "Part 列表",
                "RULES": "規則列表",
                "N": "聚集數量",
                "SEED": "隨機種子",
                "RESET": "重置 (Boolean Toggle!)"
            },
            outputs={
                "AGG": "聚集物件",
                "GEO": "幾何列表"
            },
            output_multiplier="1:N",
            warnings=["RESET 必須連接 Boolean Toggle"],
            common_mistakes=["RESET 未連接導致無法重置"]
        )
    }

    # 資料流爆炸警戒值
    OUTPUT_EXPLOSION_THRESHOLD = 100

    def __init__(self, config_dir: Optional[Path] = None):
        self.results: List[SemanticCheckResult] = []
        self.data_flow_estimates: List[DataFlowEstimate] = []
        
        # Load Knowledge Base
        if config_dir is None:
            possible_paths = [
                Path(__file__).parent.parent / "config",
                Path.cwd() / "config",
            ]
            for p in possible_paths:
                if p.exists():
                    config_dir = p
                    break
            else:
                config_dir = possible_paths[0]
        self.kb = ConnectionKnowledgeBase(storage_dir=config_dir)

    def validate(self, placement_info: Dict) -> List[SemanticCheckResult]:
        """執行語義驗證"""
        self.results = []
        self.data_flow_estimates = []

        components = placement_info.get("components", [])
        connections = placement_info.get("connections", [])

        # 1. 檢查每個組件的行為
        for comp in components:
            self._check_component_behavior(comp)

        # 2. 分析資料流
        self._analyze_data_flow(components, connections)

        # 3. 檢查特定模式的風險
        self._check_pattern_risks(components, connections)
        
        # 4. 檢查連接信心度 (KB Based)
        self._check_connection_confidence(components, connections)

        return self.results

    def _check_connection_confidence(self, components: List[Dict], connections: List[Dict]):
        """使用知識庫檢查連接的信心度 (統計學驗證)"""
        comp_lookup = {c.get("id"): c for c in components}
        
        for conn in connections:
            from_id = conn.get("from")
            to_id = conn.get("to")
            from_param = conn.get("fromParam")
            to_param = conn.get("toParam")
            
            src_comp = comp_lookup.get(from_id)
            tgt_comp = comp_lookup.get(to_id)
            
            if src_comp and tgt_comp:
                confidence = self.kb.get_connection_confidence(
                    src_comp.get("type", ""), from_param,
                    tgt_comp.get("type", ""), to_param
                )
                
                # 如果信心度過低 (且不是第一次遇到的組件)
                # 這裡假設如果 KB 是空的，confidence 會是 0，我們不希望全部報錯。
                # 所以可以加一個閾值：如果 KB 中有該組件的其他連接記錄，但沒有這個特定連接，則報警。
                
                if confidence == 0.0:
                    # 這是一個未見過的連接
                    # 我們將其標記為 Low Risk (Info)，提醒用戶這是一個新穎的用法
                    self.results.append(SemanticCheckResult(
                        passed=True,
                        component_id=from_id,
                        check_type="confidence",
                        risk_level=SemanticRisk.LOW,
                        message=f"New Pattern: {src_comp.get('type')} -> {tgt_comp.get('type')}",
                        explanation=f"This connection pattern ({from_param}->{to_param}) has not been recorded in the Knowledge Base yet.",
                        suggestion="If this works, it will be added to the KB automatically."
                    ))

    def _check_component_behavior(self, component: Dict):
        """檢查單一組件的行為是否符合預期"""
        comp_type = component.get("type", "")
        comp_id = component.get("nickname", component.get("id", "Unknown"))

        behavior = self.COMPONENT_BEHAVIORS.get(comp_type)
        if not behavior:
            return  # 未知組件，跳過

        # 檢查常見錯誤
        for mistake in behavior.common_mistakes:
            self.results.append(SemanticCheckResult(
                passed=True,  # 只是警告，不阻擋
                component_id=comp_id,
                check_type="behavior",
                risk_level=SemanticRisk.MEDIUM,
                message=f"⚠️ {comp_type}: 注意常見錯誤",
                explanation=mistake,
                suggestion=f"請確認這是你想要的行為"
            ))

        # 檢查警告
        for warning in behavior.warnings:
            self.results.append(SemanticCheckResult(
                passed=True,
                component_id=comp_id,
                check_type="behavior",
                risk_level=SemanticRisk.LOW,
                message=f"ℹ️ {comp_type}: {warning}",
                explanation=behavior.description
            ))

    def _analyze_data_flow(self, components: List[Dict], connections: List[Dict]):
        """分析資料流，預估輸出數量"""
        # 建立組件查找表
        comp_by_nickname = {c.get("nickname", c.get("id")): c for c in components}

        # 尋找潛在的資料爆炸
        for comp in components:
            comp_type = comp.get("type", "")
            comp_id = comp.get("nickname", comp.get("id", "Unknown"))
            behavior = self.COMPONENT_BEHAVIORS.get(comp_type)

            if not behavior:
                continue

            # 特殊檢查：Mesh Box
            if comp_type == "Mesh Box":
                props = comp.get("properties", {})
                x = props.get("value", 10) if comp.get("nickname") == "SizeX" else 10
                y = props.get("value", 10) if comp.get("nickname") == "SizeY" else 10
                z = props.get("value", 10) if comp.get("nickname") == "SizeZ" else 10

                # 查找實際的 slider 值
                for c in components:
                    if c.get("nickname") == "SizeX":
                        x = c.get("properties", {}).get("value", 10)
                    elif c.get("nickname") == "SizeY":
                        y = c.get("properties", {}).get("value", 10)
                    elif c.get("nickname") == "SizeZ":
                        z = c.get("properties", {}).get("value", 10)

                estimated_faces = x * y * z * 6  # 6 個方向的面

                if estimated_faces > self.OUTPUT_EXPLOSION_THRESHOLD:
                    self.results.append(SemanticCheckResult(
                        passed=False,
                        component_id=comp_id,
                        check_type="dataflow",
                        risk_level=SemanticRisk.CRITICAL,
                        message=f"🔴 資料流爆炸風險！",
                        explanation=f"Mesh Box 設定 X={x}, Y={y}, Z={z} 將產生約 {estimated_faces} 個 mesh faces",
                        suggestion="如果你想要的是一個簡單立方體，請使用 Center Box 替代"
                    ))

                self.data_flow_estimates.append(DataFlowEstimate(
                    component_id=comp_id,
                    component_type=comp_type,
                    input_count=3,
                    output_count=estimated_faces,
                    multiplier_reason=f"X*Y*Z*6 = {x}*{y}*{z}*6",
                    risk_level=SemanticRisk.CRITICAL if estimated_faces > 100 else SemanticRisk.LOW,
                    warning=f"將產生 {estimated_faces} 個面" if estimated_faces > 10 else None
                ))

    def _check_pattern_risks(self, components: List[Dict], connections: List[Dict]):
        """檢查特定模式的風險"""
        comp_types = {c.get("type", "") for c in components}

        # 檢查 WASP 模式
        if "Wasp_Stochastic Aggregation" in comp_types:
            # 檢查 RESET 是否連接
            reset_connected = any(
                conn.get("to_param") == "RESET"
                for conn in connections
            )
            if not reset_connected:
                self.results.append(SemanticCheckResult(
                    passed=False,
                    component_id="StochAggr",
                    check_type="pattern",
                    risk_level=SemanticRisk.HIGH,
                    message="⚠️ WASP Stochastic Aggregation 的 RESET 未連接",
                    explanation="RESET 輸入必須連接 Boolean Toggle，否則無法重置聚集",
                    suggestion="添加 Boolean Toggle 並連接到 RESET"
                ))

            # 檢查是否使用 Mesh Box 而非 Center Box
            if "Mesh Box" in comp_types and "Center Box" not in comp_types:
                self.results.append(SemanticCheckResult(
                    passed=False,
                    component_id="MeshBox",
                    check_type="pattern",
                    risk_level=SemanticRisk.CRITICAL,
                    message="🔴 WASP 配置可能錯誤：使用 Mesh Box 而非 Center Box",
                    explanation="WASP 通常使用 Center Box (Brep) 作為 Part 幾何，而非 Mesh Box",
                    suggestion="使用 Center Box + Deconstruct Brep + Evaluate Surface 替代"
                ))

        # 檢查是否使用 Rule 而非 Rules Generator
        if "Wasp_Rule" in comp_types and "Wasp_Rules Generator" not in comp_types:
            self.results.append(SemanticCheckResult(
                passed=True,
                component_id="Rule",
                check_type="pattern",
                risk_level=SemanticRisk.MEDIUM,
                message="⚠️ 使用手動 Rule 而非 Rules Generator",
                explanation="Rules Generator 只需 PART 輸入，會自動生成所有可能的規則",
                suggestion="考慮使用 Wasp_Rules Generator 簡化配置"
            ))

    def generate_human_readable_report(self) -> str:
        """生成人類可讀的語義驗證報告"""
        lines = ["## 🧠 語義驗證報告\n"]

        critical = [r for r in self.results if r.risk_level == SemanticRisk.CRITICAL]
        high = [r for r in self.results if r.risk_level == SemanticRisk.HIGH]
        medium = [r for r in self.results if r.risk_level == SemanticRisk.MEDIUM]

        if critical:
            lines.append("### 🔴 Critical (阻擋執行)")
            for r in critical:
                lines.append(f"- **{r.component_id}**: {r.message}")
                if r.explanation:
                    lines.append(f"  - 說明: {r.explanation}")
                if r.suggestion:
                    lines.append(f"  - 建議: {r.suggestion}")
            lines.append("")

        if high:
            lines.append("### 🟠 High Risk")
            for r in high:
                lines.append(f"- **{r.component_id}**: {r.message}")
                if r.suggestion:
                    lines.append(f"  → {r.suggestion}")
            lines.append("")

        if medium:
            lines.append("### 🟡 Medium (請確認)")
            for r in medium:
                lines.append(f"- **{r.component_id}**: {r.message}")
            lines.append("")

        # 資料流摘要
        if self.data_flow_estimates:
            lines.append("### 📊 資料流預估")
            for est in self.data_flow_estimates:
                if est.warning:
                    lines.append(f"- **{est.component_id}** ({est.component_type}): {est.warning}")
            lines.append("")

        # 結論
        if critical:
            lines.append("### 結論: ❌ 不通過 - 請修復 Critical 問題")
        elif high:
            lines.append("### 結論: ⚠️ 有風險 - 建議處理 High Risk 問題")
        else:
            lines.append("### 結論: ✅ 通過")

        return "\n".join(lines)

    def get_component_explanation(self, comp_type: str) -> Optional[str]:
        """獲取組件的人類可讀解釋"""
        behavior = self.COMPONENT_BEHAVIORS.get(comp_type)
        if not behavior:
            return None

        lines = [
            f"**{behavior.name}** ({behavior.category})",
            f"",
            f"{behavior.description}",
            f"",
            f"**輸入:**"
        ]
        for param, desc in behavior.inputs.items():
            lines.append(f"  - `{param}`: {desc}")

        lines.append(f"")
        lines.append(f"**輸出:**")
        for param, desc in behavior.outputs.items():
            lines.append(f"  - `{param}`: {desc}")

        lines.append(f"")
        lines.append(f"**輸出乘數:** {behavior.output_multiplier}")

        if behavior.warnings:
            lines.append(f"")
            lines.append(f"**⚠️ 注意:**")
            for w in behavior.warnings:
                lines.append(f"  - {w}")

        return "\n".join(lines)


def validate_placement_info(json_path: str) -> str:
    """便捷函數：驗證 placement_info.json 並返回報告"""
    with open(json_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    validator = SemanticValidator()
    validator.validate(config)
    return validator.generate_human_readable_report()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        report = validate_placement_info(sys.argv[1])
        print(report)
    else:
        print("Usage: python semantic_validator.py <placement_info.json>")
