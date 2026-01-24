"""
Pre-Execution Checker 測試案例
===============================

驗證 Pre-Execution Checker 能正確識別：
1. clear_canvas 等不存在的 MCP 命令
2. Rotate/Pipe/Series 等衝突組件缺少 trusted GUID
3. R, N, GEO 等 FuzzyMatcher 風險參數
4. Panel/Slider 初始值問題

基於 WASP Cube Aggregation v1→v10 的除錯經驗
"""
import json
import pytest
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from grasshopper_mcp.pre_execution_checker import (
    PreExecutionChecker,
    CheckResult,
    Severity,
    Category,
)


class TestMCPCommandValidation:
    """測試 MCP 命令驗證"""

    def test_detect_clear_canvas(self):
        """應該檢測到 clear_canvas 不存在"""
        # 模擬包含 clear_canvas 的配置（這是錯誤的）
        config = {
            "_meta": {"mcp_commands": ["clear_canvas", "add_component"]},
            "components": [],
            "connections": []
        }

        checker = PreExecutionChecker()
        results = checker.check_placement_info(config)

        # 應該有 critical 級別的 MCP 命令錯誤
        mcp_errors = [r for r in results if r.category == Category.MCP]
        assert len(mcp_errors) >= 1
        assert any("clear_canvas" in r.message for r in mcp_errors)
        assert any(r.severity == Severity.CRITICAL for r in mcp_errors)

    def test_valid_commands_pass(self):
        """有效的 MCP 命令應該通過"""
        config = {
            "_meta": {"mcp_commands": ["add_component", "connect_components", "clear_document"]},
            "components": [],
            "connections": []
        }

        checker = PreExecutionChecker()
        results = checker.check_placement_info(config)

        # 不應該有 MCP 命令錯誤
        mcp_critical = [r for r in results if r.category == Category.MCP and r.severity == Severity.CRITICAL]
        assert len(mcp_critical) == 0


class TestGUIDValidation:
    """測試組件 GUID 驗證"""

    def test_detect_rotate_without_guid(self):
        """Rotate 組件沒有 GUID 應該警告"""
        config = {
            "components": [
                {"id": "rotate1", "type": "Rotate", "nickname": "RotatedSteps"}
            ],
            "connections": []
        }

        checker = PreExecutionChecker()
        results = checker.check_placement_info(config)

        # 應該有 GUID 相關警告
        guid_warnings = [r for r in results if r.category == Category.GUID]
        assert len(guid_warnings) >= 1
        assert any("Rotate" in r.message for r in guid_warnings)

    def test_rotate_with_trusted_guid_passes(self):
        """使用 trusted GUID 的 Rotate 應該通過"""
        config = {
            "components": [
                {
                    "id": "rotate1",
                    "type": "Rotate",
                    "nickname": "RotatedSteps",
                    "guid": "19c70daf-600f-4697-ace2-567f6702144d"  # Trusted GUID
                }
            ],
            "connections": []
        }

        checker = PreExecutionChecker()
        results = checker.check_placement_info(config)

        # 不應該有 GUID 相關警告
        guid_warnings = [r for r in results if r.category == Category.GUID and "Rotate" in r.message]
        # 有 trusted GUID 時應該通過（或標記為 info）
        critical_guid = [r for r in guid_warnings if r.severity == Severity.CRITICAL]
        assert len(critical_guid) == 0


class TestFuzzyMatcherRisk:
    """測試 FuzzyMatcher 風險參數檢測"""

    def test_detect_R_param_risk(self):
        """使用 R 參數應該警告 FuzzyMatcher 風險"""
        config = {
            "components": [],
            "connections": [
                {
                    "source": "division1",
                    "target": "wasp_rule1",
                    "fromParam": "R",  # 風險參數！
                    "toParam": "Rules"
                }
            ]
        }

        checker = PreExecutionChecker()
        results = checker.check_placement_info(config)

        # 應該有參數風險警告
        param_warnings = [r for r in results if r.category == Category.PARAM]
        assert len(param_warnings) >= 1
        assert any("R" in r.message for r in param_warnings)

    def test_paramIndex_bypasses_risk(self):
        """使用 paramIndex 應該避開風險"""
        config = {
            "components": [],
            "connections": [
                {
                    "source": "division1",
                    "target": "wasp_rule1",
                    "fromParamIndex": 0,  # 使用 index 替代 name
                    "toParamIndex": 0
                }
            ]
        }

        checker = PreExecutionChecker()
        results = checker.check_placement_info(config)

        # 不應該有參數風險警告
        param_warnings = [r for r in results if r.category == Category.PARAM and r.severity == Severity.WARNING]
        assert len(param_warnings) == 0


class TestSliderPanelValidation:
    """測試 Slider/Panel 初始值驗證"""

    def test_panel_without_value_warns(self):
        """沒有內容的 Panel 應該警告（WASP 需要）"""
        config = {
            "components": [
                {"id": "panel1", "type": "Panel", "nickname": "PartName"}
                # 沒有 value！
            ],
            "connections": []
        }

        checker = PreExecutionChecker()
        results = checker.check_placement_info(config)

        # 應該有 value 相關警告
        value_warnings = [r for r in results if r.category == Category.VALUE]
        assert len(value_warnings) >= 1
        assert any("Panel" in r.message for r in value_warnings)

    def test_slider_with_value_passes(self):
        """設定了 value 的 Slider 應該通過"""
        config = {
            "components": [
                {
                    "id": "slider1",
                    "type": "Number Slider",
                    "nickname": "Steps",
                    "value": 10,
                    "min": 1,
                    "max": 100
                }
            ],
            "connections": []
        }

        checker = PreExecutionChecker()
        results = checker.check_placement_info(config)

        # 不應該有 Slider 相關警告
        slider_warnings = [r for r in results if r.category == Category.VALUE and "Slider" in r.message and "Steps" in r.message]
        critical = [r for r in slider_warnings if r.severity == Severity.CRITICAL]
        assert len(critical) == 0


class TestWASPv10Scenario:
    """基於 WASP Cube Aggregation v10 的完整測試案例"""

    def test_wasp_v10_problematic_config(self):
        """模擬 WASP v10 的問題配置"""
        # 這個配置包含了 v1→v10 過程中遇到的所有問題
        problematic_config = {
            "_meta": {
                "mcp_commands": ["clear_canvas", "add_component"]  # 錯誤！
            },
            "components": [
                {"id": "rotate1", "type": "Rotate"},  # 缺少 GUID！
                {"id": "panel1", "type": "Panel", "nickname": "PartName"},  # 缺少 value！
            ],
            "connections": [
                {
                    "source": "wasp_rule1",
                    "target": "wasp_agg1",
                    "fromParam": "R",  # 風險參數！
                    "toParam": "Rules"
                }
            ]
        }

        checker = PreExecutionChecker()
        results = checker.check_placement_info(problematic_config)
        report = checker.generate_report()

        # 應該識別出所有問題
        assert "clear_canvas" in report
        assert "Rotate" in report

        # 應該有 critical 錯誤（clear_canvas）
        critical = [r for r in results if r.severity == Severity.CRITICAL]
        assert len(critical) >= 1

        # 結論應該是不通過
        assert "不通過" in report or "❌" in report

    def test_wasp_v10_fixed_config(self):
        """修復後的 WASP v10 配置應該通過"""
        fixed_config = {
            "_meta": {
                "mcp_commands": ["add_component", "connect_components", "clear_document"]
            },
            "components": [
                {
                    "id": "rotate1",
                    "type": "Rotate",
                    "guid": "19c70daf-600f-4697-ace2-567f6702144d"  # 正確 GUID
                },
                {
                    "id": "panel1",
                    "type": "Panel",
                    "nickname": "PartName",
                    "value": "CubeModule"  # 有內容
                },
            ],
            "connections": [
                {
                    "source": "wasp_rule1",
                    "target": "wasp_agg1",
                    "fromParamIndex": 0,  # 使用 index
                    "toParamIndex": 1
                }
            ]
        }

        checker = PreExecutionChecker()
        results = checker.check_placement_info(fixed_config)

        # 不應該有 critical 錯誤
        critical = [r for r in results if r.severity == Severity.CRITICAL]
        assert len(critical) == 0


class TestReportGeneration:
    """測試報告生成"""

    def test_report_format(self):
        """驗證報告格式正確"""
        config = {
            "_meta": {"mcp_commands": ["clear_canvas"]},
            "components": [{"id": "rotate1", "type": "Rotate"}],
            "connections": []
        }

        checker = PreExecutionChecker()
        checker.check_placement_info(config)
        report = checker.generate_report()

        # 報告應該包含必要區段
        assert "Pre-Execution Checklist" in report or "驗證報告" in report
        assert "Critical" in report or "🔴" in report
        assert "結論" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
