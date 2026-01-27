#!/usr/bin/env python3
"""
ComponentValidator 單元測試
"""

import pytest
from grasshopper_mcp.component_validator import (
    ComponentValidator,
    ValidationStatus,
    ComponentValidation,
    ValidationReport,
    quick_validate,
)


@pytest.fixture
def validator():
    """建立測試用的 validator"""
    return ComponentValidator(config_dir="config")


class TestComponentValidation:
    """測試單個組件驗證"""

    def test_valid_component(self, validator):
        """測試有效組件"""
        result = validator._validate_single("Number Slider")
        assert result.status == ValidationStatus.VALID
        assert result.resolved_guid is not None
        assert result.source == "trusted_guids"

    def test_ambiguous_rotate_auto_resolve(self, validator):
        """測試 Rotate 多版本 - 自動選擇推薦"""
        result = validator._validate_single("Rotate", auto_resolve_recommended=True)
        assert result.status == ValidationStatus.VALID
        assert result.resolved_guid == "19c70daf-600f-4697-ace2-567f6702144d"
        assert result.source == "auto_recommended"

    def test_ambiguous_rotate_no_auto(self, validator):
        """測試 Rotate 多版本 - 不自動選擇"""
        result = validator._validate_single("Rotate", auto_resolve_recommended=False)
        assert result.status == ValidationStatus.AMBIGUOUS
        assert len(result.candidates) >= 2

    def test_not_found(self, validator):
        """測試找不到的組件"""
        result = validator._validate_single("NonExistentComponentXYZ")
        assert result.status == ValidationStatus.NOT_FOUND

    def test_case_insensitive(self, validator):
        """測試不區分大小寫"""
        result1 = validator._validate_single("Number Slider")
        result2 = validator._validate_single("number slider")
        assert result1.status == result2.status == ValidationStatus.VALID

    def test_series_single_version(self, validator):
        """測試 Series (只有一個版本)"""
        result = validator._validate_single("Series")
        # Series 在 MULTI_VERSION_COMPONENTS 只有一個版本，應該直接 VALID
        # 或者從 trusted_guids.json 載入
        assert result.status == ValidationStatus.VALID


class TestValidationReport:
    """測試驗證報告"""

    def test_all_valid(self, validator):
        """測試所有組件都有效"""
        report = validator.validate_components([
            {"type": "Number Slider"},
            {"type": "Series"},
            {"type": "Addition"},
        ])
        assert report.can_proceed is True
        assert report.valid_count == 3
        assert report.ambiguous_count == 0
        assert report.not_found_count == 0

    def test_mixed_results(self, validator):
        """測試混合結果"""
        report = validator.validate_components([
            {"type": "Number Slider"},
            {"type": "Rotate"},  # 多版本，自動解析
            {"type": "NonExistent"},  # 找不到
        ])
        assert report.can_proceed is False
        assert report.valid_count == 2
        assert report.not_found_count == 1
        assert "NonExistent" in report.requires_decision

    def test_deduplication(self, validator):
        """測試去重（同名組件只驗證一次）"""
        report = validator.validate_components([
            {"type": "Number Slider"},
            {"type": "Number Slider"},
            {"type": "Number Slider"},
        ])
        assert report.total_components == 1

    def test_markdown_output(self, validator):
        """測試 Markdown 報告生成"""
        report = validator.validate_components([
            {"type": "Rotate"},
            {"type": "Series"},
        ])
        md = report.to_markdown()
        assert "組件驗證報告" in md
        assert "總計" in md

    def test_dict_output(self, validator):
        """測試字典輸出"""
        report = validator.validate_components([
            {"type": "Number Slider"},
        ])
        d = report.to_dict()
        assert "total_components" in d
        assert "validations" in d
        assert len(d["validations"]) == 1


class TestUserDecision:
    """測試用戶決策應用"""

    def test_apply_decision(self, validator):
        """測試應用用戶選擇"""
        result = validator.apply_user_decision(
            comp_name="Rotate",
            selected_guid="19c70daf-600f-4697-ace2-567f6702144d",
            selected_name="Rotate (Transform)"
        )
        assert result.status == ValidationStatus.VALID
        assert result.source == "user_decision"
        assert result.confidence == 0.95


class TestConvenienceFunctions:
    """測試便捷函數"""

    def test_quick_validate(self):
        """測試 quick_validate"""
        from grasshopper_mcp.knowledge_base import ConnectionKnowledgeBase
        kb = ConnectionKnowledgeBase()
        report = quick_validate(["Number Slider", "Series"], kb)
        # Note: quick_validate 需要 kb 參數，但 ComponentValidator 現在可以不用 kb
        # 這個測試可能需要調整

    def test_get_recommended_guid(self, validator):
        """測試獲取推薦 GUID"""
        guid = validator.get_recommended_guid("Rotate")
        assert guid == "19c70daf-600f-4697-ace2-567f6702144d"

        # 非多版本組件應返回 None
        guid2 = validator.get_recommended_guid("Number Slider")
        assert guid2 is None


class TestSimilarComponents:
    """測試相似組件推薦"""

    def test_find_similar(self, validator):
        """測試找相似組件"""
        # Line 和其他組件的相似度
        result = validator._validate_single("Lien")  # 拼錯的 Line
        assert result.status == ValidationStatus.NOT_FOUND
        # 應該推薦 Line
        if result.recommendations:
            names = [r["name"] for r in result.recommendations]
            assert "Line" in names or any("Line" in n for n in names)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
