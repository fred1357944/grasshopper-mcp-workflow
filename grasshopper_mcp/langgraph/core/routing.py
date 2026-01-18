"""
Expert Router - 專家路由系統

對應策略: Expert Routing (MoE - Mixture of Experts)

根據任務類型將請求路由到專門的 Agent:
- Geometry Expert: 幾何建模任務
- Connection Expert: 組件連接任務
- Parameter Expert: 參數優化任務
- Layout Expert: 布局排版任務
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
import re


class TaskType(str, Enum):
    """任務類型"""
    GEOMETRY = "geometry"           # 幾何建模
    CONNECTION = "connection"       # 組件連接
    PARAMETER = "parameter"         # 參數調整
    LAYOUT = "layout"               # 布局排版
    VALIDATION = "validation"       # 驗證檢查
    GENERAL = "general"             # 通用任務


class ExpertLevel(str, Enum):
    """專家層級"""
    RULE_BASED = "rule_based"       # 規則驅動
    ML_ENHANCED = "ml_enhanced"     # ML 增強
    AI_POWERED = "ai_powered"       # AI 驅動


@dataclass
class ExpertAgent:
    """專家 Agent 定義"""
    name: str
    task_type: TaskType
    level: ExpertLevel
    confidence_threshold: float
    handler: Optional[Callable] = None
    keywords: List[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = self._default_keywords()

    def _default_keywords(self) -> List[str]:
        """根據任務類型返回預設關鍵字"""
        keywords_map = {
            TaskType.GEOMETRY: [
                "box", "sphere", "cylinder", "extrude", "loft",
                "surface", "curve", "point", "brep", "mesh",
                "geometry", "shape", "form", "solid"
            ],
            TaskType.CONNECTION: [
                "connect", "wire", "link", "input", "output",
                "parameter", "from", "to", "source", "target"
            ],
            TaskType.PARAMETER: [
                "slider", "number", "value", "range", "adjust",
                "optimize", "tune", "set", "modify"
            ],
            TaskType.LAYOUT: [
                "position", "arrange", "layout", "organize",
                "group", "align", "spacing", "canvas"
            ],
            TaskType.VALIDATION: [
                "validate", "check", "verify", "error", "fix",
                "diagnose", "test", "confirm"
            ],
        }
        return keywords_map.get(self.task_type, [])

    def matches(self, text: str) -> float:
        """計算文本與此專家的匹配度"""
        if not self.keywords:
            return 0.0

        text_lower = text.lower()
        matched = sum(1 for kw in self.keywords if kw in text_lower)
        return matched / len(self.keywords)


class ExpertRouter:
    """
    專家路由器

    使用 Mixture of Experts 模式，根據任務特徵
    將請求路由到最適合的專家 Agent。

    Usage:
        router = ExpertRouter()

        # 根據任務描述路由
        expert = router.route("建立一個 Box 並連接到 Move")
        # -> ExpertAgent(name="geometry", ...)

        # 根據組件類型路由
        expert = router.route_by_component("Number Slider")
        # -> ExpertAgent(name="parameter", ...)
    """

    def __init__(self):
        self.experts: Dict[TaskType, ExpertAgent] = {}
        self._register_default_experts()

        # 組件類型到任務類型的映射
        self.component_type_map: Dict[str, TaskType] = {
            # Geometry
            "Box": TaskType.GEOMETRY,
            "Sphere": TaskType.GEOMETRY,
            "Cylinder": TaskType.GEOMETRY,
            "Extrude": TaskType.GEOMETRY,
            "Loft": TaskType.GEOMETRY,
            "Surface": TaskType.GEOMETRY,
            "Brep": TaskType.GEOMETRY,
            "Mesh": TaskType.GEOMETRY,
            "Curve": TaskType.GEOMETRY,
            "Line": TaskType.GEOMETRY,
            "Circle": TaskType.GEOMETRY,
            "Rectangle": TaskType.GEOMETRY,

            # Parameter
            "Number Slider": TaskType.PARAMETER,
            "Panel": TaskType.PARAMETER,
            "Slider": TaskType.PARAMETER,
            "Number": TaskType.PARAMETER,
            "Integer": TaskType.PARAMETER,

            # Connection helpers
            "Merge": TaskType.CONNECTION,
            "Entwine": TaskType.CONNECTION,
            "Graft": TaskType.CONNECTION,
            "Flatten": TaskType.CONNECTION,

            # Layout
            "Group": TaskType.LAYOUT,
            "Cluster": TaskType.LAYOUT,

            # Validation
            "Null": TaskType.VALIDATION,
            "Clean": TaskType.VALIDATION,
        }

    def _register_default_experts(self):
        """註冊預設專家"""
        defaults = [
            ExpertAgent(
                name="geometry_expert",
                task_type=TaskType.GEOMETRY,
                level=ExpertLevel.ML_ENHANCED,
                confidence_threshold=0.7,
            ),
            ExpertAgent(
                name="connection_expert",
                task_type=TaskType.CONNECTION,
                level=ExpertLevel.RULE_BASED,
                confidence_threshold=0.8,
            ),
            ExpertAgent(
                name="parameter_expert",
                task_type=TaskType.PARAMETER,
                level=ExpertLevel.RULE_BASED,
                confidence_threshold=0.85,
            ),
            ExpertAgent(
                name="layout_expert",
                task_type=TaskType.LAYOUT,
                level=ExpertLevel.RULE_BASED,
                confidence_threshold=0.6,
            ),
            ExpertAgent(
                name="validation_expert",
                task_type=TaskType.VALIDATION,
                level=ExpertLevel.AI_POWERED,
                confidence_threshold=0.9,
            ),
            ExpertAgent(
                name="general_expert",
                task_type=TaskType.GENERAL,
                level=ExpertLevel.AI_POWERED,
                confidence_threshold=0.5,
            ),
        ]

        for expert in defaults:
            self.experts[expert.task_type] = expert

    def register_expert(self, expert: ExpertAgent):
        """註冊自定義專家"""
        self.experts[expert.task_type] = expert

    def route(self, task_description: str) -> ExpertAgent:
        """
        根據任務描述路由到專家

        Args:
            task_description: 任務描述文本

        Returns:
            最匹配的 ExpertAgent
        """
        scores: Dict[TaskType, float] = {}

        for task_type, expert in self.experts.items():
            score = expert.matches(task_description)
            scores[task_type] = score

        # 找出最高分
        if not scores:
            return self.experts[TaskType.GENERAL]

        best_type = max(scores, key=scores.get)

        # 如果最高分太低，使用通用專家
        if scores[best_type] < 0.1:
            return self.experts[TaskType.GENERAL]

        return self.experts[best_type]

    def route_by_component(self, component_type: str) -> ExpertAgent:
        """
        根據組件類型路由到專家

        Args:
            component_type: 組件類型名稱

        Returns:
            對應的 ExpertAgent
        """
        # 精確匹配
        if component_type in self.component_type_map:
            task_type = self.component_type_map[component_type]
            return self.experts.get(task_type, self.experts[TaskType.GENERAL])

        # 模糊匹配
        component_lower = component_type.lower()

        for comp, task_type in self.component_type_map.items():
            if comp.lower() in component_lower or component_lower in comp.lower():
                return self.experts.get(task_type, self.experts[TaskType.GENERAL])

        return self.experts[TaskType.GENERAL]

    def route_by_stage(self, stage: str) -> ExpertAgent:
        """
        根據工作流程階段路由

        Args:
            stage: 工作流程階段

        Returns:
            對應的 ExpertAgent
        """
        stage_map = {
            "requirements": TaskType.GENERAL,
            "decomposition": TaskType.GEOMETRY,
            "connectivity": TaskType.CONNECTION,
            "guid_resolution": TaskType.CONNECTION,
            "execution": TaskType.GENERAL,
            "evaluation": TaskType.VALIDATION,
            "optimization": TaskType.PARAMETER,
        }

        task_type = stage_map.get(stage, TaskType.GENERAL)
        return self.experts.get(task_type, self.experts[TaskType.GENERAL])

    def get_expert_for_operation(
        self,
        operation: str,
        component_type: Optional[str] = None,
        stage: Optional[str] = None
    ) -> ExpertAgent:
        """
        綜合路由：結合操作、組件、階段信息

        Args:
            operation: 操作描述
            component_type: 組件類型（可選）
            stage: 工作流程階段（可選）

        Returns:
            最適合的 ExpertAgent
        """
        candidates: List[tuple] = []  # (expert, score)

        # 1. 根據操作描述
        op_expert = self.route(operation)
        op_score = op_expert.matches(operation)
        candidates.append((op_expert, op_score + 0.1))

        # 2. 根據組件類型
        if component_type:
            comp_expert = self.route_by_component(component_type)
            candidates.append((comp_expert, 0.3))

        # 3. 根據階段
        if stage:
            stage_expert = self.route_by_stage(stage)
            candidates.append((stage_expert, 0.2))

        # 選擇最高分
        if not candidates:
            return self.experts[TaskType.GENERAL]

        best = max(candidates, key=lambda x: x[1])
        return best[0]

    def explain_routing(self, task_description: str) -> Dict[str, Any]:
        """
        解釋路由決策

        Args:
            task_description: 任務描述

        Returns:
            路由決策解釋
        """
        scores = {}
        for task_type, expert in self.experts.items():
            score = expert.matches(task_description)
            matched_keywords = [
                kw for kw in expert.keywords
                if kw in task_description.lower()
            ]
            scores[task_type.value] = {
                "score": score,
                "matched_keywords": matched_keywords,
                "expert_name": expert.name,
            }

        chosen = self.route(task_description)

        return {
            "chosen_expert": chosen.name,
            "chosen_type": chosen.task_type.value,
            "confidence": max(s["score"] for s in scores.values()),
            "all_scores": scores,
        }
