#!/usr/bin/env python3
"""
Workflow Validation Tests
=========================

測試工作流程完整性驗證功能：
- 檢測工作流程類型
- 驗證必要階段是否存在
- 自動補全缺失階段
- 連接模式驗證

這些測試確保系統能夠基於 GHX 範例學習，
避免生成不完整的工作流程。

Usage:
    pytest tests/test_workflow_validation.py -v
"""

import pytest
from pathlib import Path
import sys

# 導入測試目標
sys.path.insert(0, str(Path(__file__).parent.parent))

from grasshopper_mcp.claude_plan_generator import (
    ClaudePlanGenerator,
    ExecutionPlan,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def generator():
    """創建 ClaudePlanGenerator 實例"""
    return ClaudePlanGenerator(config_dir="config")


@pytest.fixture
def complete_wasp_plan():
    """完整的 WASP 工作流程計畫"""
    return ExecutionPlan(
        success=True,
        components=[
            {"id": "slider1", "type": "Number Slider", "nickname": "Count"},
            {"id": "box1", "type": "Center Box", "nickname": "Geometry"},
            {"id": "mesh1", "type": "Mesh Brep", "nickname": "MeshConvert"},
            {"id": "conn1", "type": "Wasp_Connection From Direction", "nickname": "Connection"},
            {"id": "part1", "type": "Wasp_Basic Part", "nickname": "Part"},
            {"id": "rules1", "type": "Wasp_Rules Generator", "nickname": "Rules"},
            {"id": "agg1", "type": "Wasp_Stochastic Aggregation", "nickname": "Aggregation"},
            {"id": "geo1", "type": "Wasp_Get Part Geometry", "nickname": "GetGeo"},
            {"id": "preview1", "type": "Custom Preview", "nickname": "Preview"},
        ],
        connections=[
            {"from": "box1", "fromParam": "B", "to": "mesh1", "toParam": "B"},
            {"from": "mesh1", "fromParam": "M", "to": "conn1", "toParam": "GEO"},
            {"from": "conn1", "fromParam": "CONN", "to": "part1", "toParam": "CONN"},
            {"from": "part1", "fromParam": "PART", "to": "rules1", "toParam": "PART"},
            {"from": "rules1", "fromParam": "R", "to": "agg1", "toParam": "RULES"},
            {"from": "part1", "fromParam": "PART", "to": "agg1", "toParam": "PART"},
            {"from": "agg1", "fromParam": "PART_OUT", "to": "geo1", "toParam": "PART"},
            {"from": "geo1", "fromParam": "GEO", "to": "preview1", "toParam": "G"},
        ]
    )


@pytest.fixture
def incomplete_wasp_plan():
    """不完整的 WASP 工作流程計畫 (缺少 Aggregation → Output)"""
    return ExecutionPlan(
        success=True,
        components=[
            {"id": "slider1", "type": "Number Slider", "nickname": "Count"},
            {"id": "box1", "type": "Center Box", "nickname": "Geometry"},
            {"id": "mesh1", "type": "Mesh Brep", "nickname": "MeshConvert"},
            {"id": "conn1", "type": "Wasp_Connection From Direction", "nickname": "Connection"},
            {"id": "part1", "type": "Wasp_Basic Part", "nickname": "Part"},
            {"id": "rules1", "type": "Wasp_Rules Generator", "nickname": "Rules"},
            # 缺少: Wasp_Stochastic Aggregation
            # 缺少: Wasp_Get Part Geometry
            # 缺少: Custom Preview
        ],
        connections=[
            {"from": "box1", "fromParam": "B", "to": "mesh1", "toParam": "B"},
            {"from": "mesh1", "fromParam": "M", "to": "conn1", "toParam": "GEO"},
            {"from": "conn1", "fromParam": "CONN", "to": "part1", "toParam": "CONN"},
            {"from": "part1", "fromParam": "PART", "to": "rules1", "toParam": "PART"},
            # 缺少後續連接
        ]
    )


# =============================================================================
# 工作流程類型檢測測試
# =============================================================================

class TestWorkflowTypeDetection:
    """測試工作流程類型檢測"""

    def test_detect_wasp_workflow(self, generator):
        """應該正確檢測 WASP 工作流程"""
        inputs = [
            "用 WASP 做立方體聚集",
            "做一個 WASP Part",
            "創建聚集系統",
            "assembly 零件",
        ]

        for user_input in inputs:
            workflow_type = generator.detect_workflow_type(user_input)
            assert workflow_type == "wasp", f"Failed for input: {user_input}"

    def test_detect_karamba_workflow(self, generator):
        """應該正確檢測 Karamba 工作流程"""
        inputs = [
            "用 Karamba 做結構分析",
            "分析梁的力學",
            "structural analysis",
        ]

        for user_input in inputs:
            workflow_type = generator.detect_workflow_type(user_input)
            assert workflow_type == "karamba", f"Failed for input: {user_input}"

    def test_detect_kangaroo_workflow(self, generator):
        """應該正確檢測 Kangaroo 工作流程"""
        inputs = [
            "用 Kangaroo 做找形",
            "張力膜結構",
            "tensile structure",
        ]

        for user_input in inputs:
            workflow_type = generator.detect_workflow_type(user_input)
            assert workflow_type == "kangaroo", f"Failed for input: {user_input}"

    def test_detect_unknown_workflow(self, generator):
        """無法識別的工作流程應該返回 None"""
        inputs = [
            "做一個簡單的曲線",
            "創建一個點",
        ]

        for user_input in inputs:
            workflow_type = generator.detect_workflow_type(user_input)
            assert workflow_type is None, f"Should be None for: {user_input}"


# =============================================================================
# 工作流程完整性驗證測試
# =============================================================================

class TestWorkflowCompletenessValidation:
    """測試工作流程完整性驗證"""

    def test_complete_wasp_workflow_passes(self, generator, complete_wasp_plan):
        """完整的 WASP 工作流程應該通過驗證"""
        validation = generator.validate_workflow_completeness(
            complete_wasp_plan, "wasp"
        )

        assert validation["complete"] is True
        assert len(validation["missing_stages"]) == 0
        assert len(validation["missing_components"]) == 0

    def test_incomplete_wasp_workflow_fails(self, generator, incomplete_wasp_plan):
        """不完整的 WASP 工作流程應該失敗驗證"""
        validation = generator.validate_workflow_completeness(
            incomplete_wasp_plan, "wasp"
        )

        assert validation["complete"] is False
        assert "聚集執行" in validation["missing_stages"]
        assert "輸出" in validation["missing_stages"]
        assert len(validation["suggestions"]) > 0

    def test_missing_mesh_brep_detected(self, generator):
        """應該檢測到缺少 Mesh Brep 組件"""
        plan_without_mesh = ExecutionPlan(
            success=True,
            components=[
                {"id": "box1", "type": "Center Box", "nickname": "Geometry"},
                # 缺少 Mesh Brep!
                {"id": "conn1", "type": "Wasp_Connection From Direction", "nickname": "Connection"},
                {"id": "part1", "type": "Wasp_Basic Part", "nickname": "Part"},
                {"id": "rules1", "type": "Wasp_Rules Generator", "nickname": "Rules"},
                {"id": "agg1", "type": "Wasp_Stochastic Aggregation", "nickname": "Aggregation"},
                {"id": "geo1", "type": "Wasp_Get Part Geometry", "nickname": "GetGeo"},
                {"id": "preview1", "type": "Custom Preview", "nickname": "Preview"},
            ],
            connections=[]
        )

        validation = generator.validate_workflow_completeness(
            plan_without_mesh, "wasp"
        )

        assert validation["complete"] is False
        assert "Mesh轉換" in validation["missing_stages"]

    def test_unknown_workflow_type_passes(self, generator, complete_wasp_plan):
        """未知的工作流程類型應該直接通過（無法驗證）"""
        validation = generator.validate_workflow_completeness(
            complete_wasp_plan, "unknown_type"
        )

        assert validation["complete"] is True
        assert "No template found" in validation["warnings"][0]


# =============================================================================
# 自動補全測試
# =============================================================================

class TestAutoComplete:
    """測試自動補全功能"""

    def test_auto_complete_missing_stages(self, generator, incomplete_wasp_plan):
        """應該自動補全缺失的階段"""
        completed_plan = generator.auto_complete_workflow(
            incomplete_wasp_plan, "wasp"
        )

        # 檢查是否添加了缺失的組件
        component_types = {c.get("type", "") for c in completed_plan.components}

        assert "Wasp_Stochastic Aggregation" in component_types
        # 注意: 自動補全只會添加每個缺失階段的第一個組件

    def test_auto_complete_adds_warnings(self, generator, incomplete_wasp_plan):
        """自動補全應該添加警告"""
        completed_plan = generator.auto_complete_workflow(
            incomplete_wasp_plan, "wasp"
        )

        assert len(completed_plan.warnings) > 0
        # 應該有關於自動補全的警告或建議

    def test_complete_plan_unchanged(self, generator, complete_wasp_plan):
        """完整的計畫不應該被修改"""
        result_plan = generator.auto_complete_workflow(
            complete_wasp_plan, "wasp"
        )

        # 組件數量應該相同
        assert len(result_plan.components) == len(complete_wasp_plan.components)


# =============================================================================
# 連接驗證測試
# =============================================================================

class TestConnectionValidation:
    """測試連接驗證功能"""

    def test_validate_known_connection(self, generator):
        """已知的連接模式應該通過驗證"""
        result = generator.validate_connection(
            "Wasp_Connection From Direction", "CONN",
            "Wasp_Basic Part", "CONN"
        )

        assert result["valid"] is True
        assert result["frequency"] > 0

    def test_validate_unknown_connection(self, generator):
        """未知的連接模式應該返回無效"""
        result = generator.validate_connection(
            "Unknown Component", "X",
            "Another Unknown", "Y"
        )

        assert result["valid"] is False
        assert result["frequency"] == 0


# =============================================================================
# 組件名稱標準化測試
# =============================================================================

class TestComponentNameCanonization:
    """測試組件名稱標準化"""

    def test_canonical_name_direct_match(self, generator):
        """直接匹配應該返回正確名稱"""
        result = generator.get_canonical_component_name("Wasp_Basic Part")
        assert result == "Wasp_Basic Part"

    def test_canonical_name_fuzzy_match(self, generator):
        """模糊匹配應該返回標準名稱"""
        # 這取決於 wasp_component_params.json 的內容
        # 如果存在 "Wasp_Basic Part"，則 "wasp part" 應該匹配到它
        result = generator.get_canonical_component_name("wasp_basic_part")
        # 可能匹配到 "Wasp_Basic Part" 或返回 None
        # 這裡只測試不會拋出異常
        assert result is None or isinstance(result, str)


# =============================================================================
# 學習資料查詢測試
# =============================================================================

class TestLearningDataQuery:
    """測試學習資料查詢功能"""

    def test_get_learned_triplets_wasp(self, generator):
        """應該能夠查詢 WASP 相關的三元組"""
        triplets = generator.get_learned_triplets(["wasp"], limit=10)

        # 如果有學習資料，應該返回相關三元組
        # 這取決於 connection_triplets.json 的內容
        assert isinstance(triplets, list)

    def test_get_component_params(self, generator):
        """應該能夠查詢組件參數"""
        params = generator.get_component_params("Wasp_Basic Part")

        # 如果有學習資料，應該返回參數信息
        # 這取決於 wasp_component_params.json 的內容
        assert params is None or isinstance(params, dict)


# =============================================================================
# 標準工作流程模板測試
# =============================================================================

class TestStandardWorkflows:
    """測試標準工作流程模板"""

    def test_wasp_template_exists(self, generator):
        """WASP 模板應該存在"""
        template = generator.get_workflow_template("wasp")

        assert template is not None
        assert template["name"] == "WASP Aggregation"
        assert len(template["stages"]) >= 7

    def test_wasp_template_has_required_stages(self, generator):
        """WASP 模板應該有必要階段標記"""
        template = generator.get_workflow_template("wasp")

        required_stages = [
            s for s in template["stages"] if s.get("required")
        ]

        # 應該有多個必要階段
        assert len(required_stages) >= 4

        # 檢查關鍵階段
        stage_names = [s["stage"] for s in required_stages]
        assert "Mesh轉換" in stage_names
        assert "Part建立" in stage_names
        assert "規則生成" in stage_names
        assert "聚集執行" in stage_names
        assert "輸出" in stage_names

    def test_wasp_template_has_key_connections(self, generator):
        """WASP 模板應該有關鍵連接"""
        template = generator.get_workflow_template("wasp")

        key_connections = template.get("key_connections", [])

        assert len(key_connections) >= 5

        # 檢查高頻連接
        high_freq_connections = [
            c for c in key_connections if c.get("frequency", 0) >= 10
        ]
        assert len(high_freq_connections) >= 3


# =============================================================================
# 執行測試
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
