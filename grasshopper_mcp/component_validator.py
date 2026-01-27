#!/usr/bin/env python3
"""
ComponentValidator - 組件名稱驗證器

職責：在生成 placement_info.json 前，驗證所有組件名稱

設計原則:
- 不重複造輪子：推薦用現有 kb.search_similar()，學習用現有 LearningAgent
- 只做一件事：驗證組件名稱是否有效

整合點 (只使用現有模組):
- knowledge_base.ConnectionKnowledgeBase.get_component_guid()
- knowledge_base.ConnectionKnowledgeBase.search_similar()

使用方式:
    from grasshopper_mcp.component_validator import ComponentValidator
    from grasshopper_mcp.knowledge_base import ConnectionKnowledgeBase

    kb = ConnectionKnowledgeBase()
    validator = ComponentValidator(kb)
    report = validator.validate_components([
        {"type": "Rotate"},
        {"type": "Helixx"},  # 拼錯
        {"type": "Series"}
    ])

    if report.can_proceed:
        # 直接執行
        pass
    else:
        # 顯示 report.to_markdown() 給用戶
        pass
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, TYPE_CHECKING, Any
from enum import Enum

if TYPE_CHECKING:
    from .knowledge_base import ConnectionKnowledgeBase

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """驗證狀態"""
    VALID = "valid"           # 唯一匹配，可直接使用
    AMBIGUOUS = "ambiguous"   # 多個候選 (如 Rotate)
    NOT_FOUND = "not_found"   # 找不到


@dataclass
class ComponentValidation:
    """單個組件的驗證結果"""
    component_name: str
    status: ValidationStatus

    # VALID 時填充
    resolved_guid: Optional[str] = None
    resolved_name: Optional[str] = None

    # AMBIGUOUS 時填充
    candidates: List[Dict] = field(default_factory=list)
    # [{"guid": "...", "name": "...", "category": "...", "description": "..."}]

    # NOT_FOUND 時填充
    recommendations: List[Dict] = field(default_factory=list)
    # [{"name": "...", "similarity": 0.85}]

    confidence: float = 0.0
    source: str = ""  # trusted_guids / fuzzy_search / user_decision


@dataclass
class ValidationReport:
    """整體驗證報告"""
    total_components: int
    valid_count: int
    ambiguous_count: int
    not_found_count: int

    validations: List[ComponentValidation] = field(default_factory=list)
    can_proceed: bool = False
    requires_decision: List[str] = field(default_factory=list)

    def get_validation(self, comp_name: str) -> Optional[ComponentValidation]:
        """根據名稱獲取驗證結果"""
        for v in self.validations:
            if v.component_name == comp_name:
                return v
        return None

    def get_resolved_guid(self, comp_name: str) -> Optional[str]:
        """獲取組件的解析後 GUID"""
        v = self.get_validation(comp_name)
        if v and v.status == ValidationStatus.VALID:
            return v.resolved_guid
        return None

    def to_markdown(self) -> str:
        """生成 Markdown 報告"""
        lines = ["## 組件驗證報告\n"]

        # 統計
        lines.append(f"- 總計: {self.total_components} 個組件")
        lines.append(f"- ✅ 通過: {self.valid_count}")
        lines.append(f"- ⚠️ 需選擇: {self.ambiguous_count}")
        lines.append(f"- ❌ 找不到: {self.not_found_count}")
        lines.append("")

        # 已驗證通過的組件
        valid_items = [v for v in self.validations if v.status == ValidationStatus.VALID]
        if valid_items:
            lines.append("### ✅ 已驗證組件\n")
            for v in valid_items:
                lines.append(f"- `{v.component_name}` → `{v.resolved_guid[:8]}...` ({v.source})")
            lines.append("")

        # 需要決策的項目
        if self.requires_decision:
            lines.append("### ⚠️ 需要用戶決策\n")
            for comp_name in self.requires_decision:
                v = self.get_validation(comp_name)
                if v is None:
                    continue

                if v.status == ValidationStatus.AMBIGUOUS:
                    lines.append(f"**{comp_name}** - 有多個版本:")
                    for i, c in enumerate(v.candidates):
                        category = c.get('category', 'Unknown')
                        name = c.get('name', comp_name)
                        desc = c.get('description', '')
                        lines.append(f"  [{i+1}] {category}/{name} - {desc}")

                elif v.status == ValidationStatus.NOT_FOUND:
                    lines.append(f"**{comp_name}** - 找不到，建議替代:")
                    if v.recommendations:
                        for i, r in enumerate(v.recommendations[:3]):
                            name = r.get('name', '')
                            sim = r.get('similarity', 0)
                            lines.append(f"  [{i+1}] {name} (相似度: {sim:.0%})")
                    else:
                        lines.append("  (無推薦)")

                lines.append("")

        # 結論
        if self.can_proceed:
            lines.append("### 結論: ✅ 所有組件已驗證，可以繼續執行")
        else:
            lines.append("### 結論: ⚠️ 請先處理上述問題後再繼續")

        return "\n".join(lines)

    def to_dict(self) -> Dict:
        """轉換為字典格式"""
        return {
            "total_components": self.total_components,
            "valid_count": self.valid_count,
            "ambiguous_count": self.ambiguous_count,
            "not_found_count": self.not_found_count,
            "can_proceed": self.can_proceed,
            "requires_decision": self.requires_decision,
            "validations": [
                {
                    "component_name": v.component_name,
                    "status": v.status.value,
                    "resolved_guid": v.resolved_guid,
                    "resolved_name": v.resolved_name,
                    "candidates": v.candidates,
                    "recommendations": v.recommendations,
                    "confidence": v.confidence,
                    "source": v.source,
                }
                for v in self.validations
            ]
        }


class ComponentValidator:
    """
    組件名稱驗證器

    只負責驗證，不負責學習或推薦（用現有模組）
    """

    # 已知有多版本衝突的組件 (從 CLAUDE.md 和實際除錯經驗整理)
    MULTI_VERSION_COMPONENTS = {
        "Rotate": [
            {
                "guid": "19c70daf-600f-4697-ace2-567f6702144d",
                "name": "Rotate",
                "category": "Transform/Euclidean",
                "description": "旋轉幾何 (推薦)",
                "recommended": True
            },
            {
                "guid": "5944e8e2-9fb9-4f8b-bdd4-8b18f1955360",
                "name": "Rotate",
                "category": "Vector",
                "description": "旋轉向量 (OBSOLETE)",
                "recommended": False
            }
        ],
        "Pipe": [
            {
                "guid": "1ee25749-2e2d-4fc6-9209-0ea0515081f9",
                "name": "Pipe",
                "category": "Surface/Freeform",
                "description": "沿曲線生成管 (推薦)",
                "recommended": True
            },
            {
                "guid": "nautilus-pipe-guid",
                "name": "Pipe",
                "category": "Nautilus",
                "description": "Nautilus 插件版本",
                "recommended": False
            }
        ],
        "Series": [
            {
                "guid": "651c4fa5-dff4-4be6-ba31-6dc267d3ab47",
                "name": "Series",
                "category": "Sets/Sequence",
                "description": "數列生成 (推薦)",
                "recommended": True
            }
        ],
        # 可繼續擴展其他已知衝突組件
    }

    def __init__(
        self,
        knowledge_base: Optional["ConnectionKnowledgeBase"] = None,
        config_dir: str = "config"
    ):
        """
        Args:
            knowledge_base: 可選的知識庫實例
            config_dir: 配置目錄路徑
        """
        self.kb = knowledge_base
        self.config_dir = Path(config_dir)
        self._trusted_guids: Dict[str, Any] = {}
        self._load_trusted_guids()

    def _load_trusted_guids(self):
        """載入 trusted_guids.json"""
        trusted_path = self.config_dir / "trusted_guids.json"
        if trusted_path.exists():
            try:
                with open(trusted_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._trusted_guids = data.get("components", {})
                    logger.debug(f"Loaded {len(self._trusted_guids)} trusted GUIDs")
            except Exception as e:
                logger.warning(f"Failed to load trusted_guids.json: {e}")

    def _get_trusted_guid(self, comp_name: str) -> Optional[Dict[str, Any]]:
        """從 trusted_guids.json 獲取組件信息"""
        # 直接名稱匹配
        if comp_name in self._trusted_guids:
            return self._trusted_guids[comp_name]

        # 不區分大小寫匹配
        comp_lower = comp_name.lower()
        for name, info in self._trusted_guids.items():
            if name.lower() == comp_lower:
                return info

        return None

    def validate_components(
        self,
        components: List[Dict],
        context: Optional[str] = None,
        auto_resolve_recommended: bool = True
    ) -> ValidationReport:
        """
        驗證組件列表

        Args:
            components: [{"type": "Rotate", ...}, ...]
            context: 可選上下文 (如 "螺旋樓梯")
            auto_resolve_recommended: 是否自動選擇推薦版本

        Returns:
            ValidationReport
        """
        validations = []
        seen_names = set()

        for comp in components:
            comp_name = comp.get("type") or comp.get("name", "")
            if not comp_name:
                continue

            # 去重（同名組件只驗證一次）
            if comp_name in seen_names:
                continue
            seen_names.add(comp_name)

            validation = self._validate_single(
                comp_name,
                context,
                auto_resolve_recommended
            )
            validations.append(validation)

        # 統計
        valid_count = sum(1 for v in validations if v.status == ValidationStatus.VALID)
        ambiguous_count = sum(1 for v in validations if v.status == ValidationStatus.AMBIGUOUS)
        not_found_count = sum(1 for v in validations if v.status == ValidationStatus.NOT_FOUND)

        can_proceed = (ambiguous_count == 0 and not_found_count == 0)
        requires_decision = [
            v.component_name for v in validations
            if v.status in [ValidationStatus.AMBIGUOUS, ValidationStatus.NOT_FOUND]
        ]

        return ValidationReport(
            total_components=len(validations),
            valid_count=valid_count,
            ambiguous_count=ambiguous_count,
            not_found_count=not_found_count,
            validations=validations,
            can_proceed=can_proceed,
            requires_decision=requires_decision
        )

    def _validate_single(
        self,
        comp_name: str,
        context: Optional[str] = None,  # noqa: ARG002 - reserved for future context-aware resolution
        auto_resolve_recommended: bool = True
    ) -> ComponentValidation:
        """驗證單個組件"""
        # Note: context parameter reserved for future context-aware resolution
        # e.g., "螺旋樓梯" context might prefer Transform/Rotate over Vector/Rotate

        # Step 1: 檢查是否是已知多版本組件
        if comp_name in self.MULTI_VERSION_COMPONENTS:
            candidates = self.MULTI_VERSION_COMPONENTS[comp_name]

            # 如果只有一個版本，直接返回 VALID
            if len(candidates) == 1:
                return ComponentValidation(
                    component_name=comp_name,
                    status=ValidationStatus.VALID,
                    resolved_guid=candidates[0]["guid"],
                    resolved_name=candidates[0]["name"],
                    confidence=1.0,
                    source="trusted_guids"
                )

            # 多版本，檢查是否可以自動選擇推薦版本
            if auto_resolve_recommended:
                recommended = [c for c in candidates if c.get("recommended", False)]
                if len(recommended) == 1:
                    return ComponentValidation(
                        component_name=comp_name,
                        status=ValidationStatus.VALID,
                        resolved_guid=recommended[0]["guid"],
                        resolved_name=recommended[0]["name"],
                        confidence=0.95,
                        source="auto_recommended"
                    )

            # 無法自動解析，返回 AMBIGUOUS
            return ComponentValidation(
                component_name=comp_name,
                status=ValidationStatus.AMBIGUOUS,
                candidates=candidates,
                confidence=0.7,
                source="trusted_guids"
            )

        # Step 2: 查詢 trusted_guids.json
        guid_info = self._get_trusted_guid(comp_name)

        if guid_info and guid_info.get("guid"):
            return ComponentValidation(
                component_name=comp_name,
                status=ValidationStatus.VALID,
                resolved_guid=guid_info["guid"],
                resolved_name=comp_name,
                confidence=1.0,
                source="trusted_guids"
            )

        # Step 3: 找不到，嘗試模糊推薦
        recommendations = self._find_similar_components(comp_name)

        return ComponentValidation(
            component_name=comp_name,
            status=ValidationStatus.NOT_FOUND,
            recommendations=recommendations,
            confidence=0.0,
            source="fuzzy_search"
        )

    def _find_similar_components(self, comp_name: str, top_k: int = 3) -> List[Dict]:
        """
        尋找相似的組件名稱

        使用簡單的字串相似度計算
        """
        import difflib

        comp_lower = comp_name.lower()
        results = []

        for name in self._trusted_guids.keys():
            # 使用 difflib 計算相似度
            ratio = difflib.SequenceMatcher(None, comp_lower, name.lower()).ratio()
            if ratio > 0.4:  # 相似度閾值
                results.append({"name": name, "similarity": ratio})

        # 排序並返回前 k 個
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def apply_user_decision(
        self,
        comp_name: str,
        selected_guid: str,
        selected_name: Optional[str] = None
    ) -> ComponentValidation:
        """
        應用用戶選擇

        注意：學習功能由現有 LearningAgent 處理，這裡只返回結果

        Args:
            comp_name: 原組件名稱
            selected_guid: 用戶選擇的 GUID
            selected_name: 可選，解析後的名稱

        Returns:
            更新後的 ComponentValidation
        """
        return ComponentValidation(
            component_name=comp_name,
            status=ValidationStatus.VALID,
            resolved_guid=selected_guid,
            resolved_name=selected_name or comp_name,
            confidence=0.95,
            source="user_decision"
        )

    def get_recommended_guid(self, comp_name: str) -> Optional[str]:
        """
        獲取推薦的 GUID (用於已知多版本組件)

        Args:
            comp_name: 組件名稱

        Returns:
            推薦的 GUID，如果沒有則返回 None
        """
        if comp_name in self.MULTI_VERSION_COMPONENTS:
            candidates = self.MULTI_VERSION_COMPONENTS[comp_name]
            for c in candidates:
                if c.get("recommended", False):
                    return c["guid"]
        return None


# ============================================================
# 便捷函數
# ============================================================

def validate_placement_info(
    placement_info: Dict,
    kb: "ConnectionKnowledgeBase"
) -> ValidationReport:
    """
    驗證 placement_info.json 中的組件

    Args:
        placement_info: placement_info 字典
        kb: 知識庫實例

    Returns:
        ValidationReport
    """
    validator = ComponentValidator(kb)
    components = placement_info.get("components", [])
    return validator.validate_components(components)


def quick_validate(
    component_names: List[str],
    kb: "ConnectionKnowledgeBase"
) -> ValidationReport:
    """
    快速驗證組件名稱列表

    Args:
        component_names: ["Rotate", "Series", ...]
        kb: 知識庫實例

    Returns:
        ValidationReport
    """
    validator = ComponentValidator(kb)
    components = [{"type": name} for name in component_names]
    return validator.validate_components(components)
