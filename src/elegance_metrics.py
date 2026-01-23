"""
Elegance Metrics - 優雅度評估模組
==================================
量化評估 Grasshopper 方案的優雅程度
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Tuple, Optional
from enum import Enum


class MetricCategory(Enum):
    """評估指標類別"""
    SIMPLICITY = "simplicity"           # 簡潔性
    EFFICIENCY = "efficiency"           # 效率
    FLEXIBILITY = "flexibility"         # 靈活性
    MAINTAINABILITY = "maintainability" # 可維護性
    ELEGANCE = "elegance"               # 優雅度


@dataclass
class MetricResult:
    """單項指標評估結果"""
    name: str
    category: MetricCategory
    score: float  # 0-1
    weight: float
    description: str
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class EleganceReport:
    """完整的優雅度評估報告"""
    total_score: float
    metrics: List[MetricResult]
    summary: str
    grade: str  # A, B, C, D, F
    
    @property
    def weighted_score(self) -> float:
        """計算加權總分"""
        total_weight = sum(m.weight for m in self.metrics)
        if total_weight == 0:
            return 0
        return sum(m.score * m.weight for m in self.metrics) / total_weight
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_score": self.total_score,
            "grade": self.grade,
            "summary": self.summary,
            "metrics": [
                {
                    "name": m.name,
                    "category": m.category.value,
                    "score": m.score,
                    "weight": m.weight,
                    "description": m.description,
                    "issues": m.issues,
                    "suggestions": m.suggestions
                }
                for m in self.metrics
            ]
        }


# ============================================================
# 優雅元件與反模式定義
# ============================================================

ELEGANT_COMPONENTS = {
    # 優雅的數據處理元件
    "Graph Mapper": {"score_bonus": 0.15, "reason": "非線性數據映射"},
    "Remap Numbers": {"score_bonus": 0.10, "reason": "動態範圍映射"},
    "Expression": {"score_bonus": 0.12, "reason": "單元件多功能"},
    "Evaluate Surface": {"score_bonus": 0.10, "reason": "幾何驅動參數"},
    "Evaluate Curve": {"score_bonus": 0.10, "reason": "幾何驅動參數"},
    "Closest Point": {"score_bonus": 0.08, "reason": "幾何關聯"},
    "Surface CP": {"score_bonus": 0.08, "reason": "幾何驅動"},
    "Bounds": {"score_bonus": 0.05, "reason": "動態範圍"},
}

ANTI_PATTERN_COMPONENTS = {
    # 過度使用會降低分數的元件
    "Relay": {"penalty_per_excess": 0.02, "threshold": 5},
    "Panel": {"penalty_per_excess": 0.01, "threshold": 3},
    "Flatten": {"penalty_per_excess": 0.03, "threshold": 3},
    "Graft": {"penalty_per_excess": 0.03, "threshold": 3},
}

ANTI_PATTERNS = [
    {
        "name": "slider_explosion",
        "description": "Slider 數量過多",
        "detector": lambda c: sum(1 for comp in c if "slider" in comp.lower()) > 8,
        "penalty": 0.15,
        "suggestion": "使用 Gene Pool 或 Expression 合併相關參數"
    },
    {
        "name": "datatree_chaos",
        "description": "DataTree 操作過於複雜",
        "detector": lambda c: sum(1 for comp in c if any(kw in comp.lower() for kw in ["flatten", "graft", "partition"])) > 5,
        "penalty": 0.10,
        "suggestion": "重新設計數據結構，減少 DataTree 操作"
    },
    {
        "name": "isolated_components",
        "description": "存在孤立元件",
        "detector": None,  # 需要連接資訊，由外部提供
        "penalty": 0.08,
        "suggestion": "移除未使用的元件或檢查連接"
    },
    {
        "name": "duplicate_sliders",
        "description": "存在功能重複的 Slider",
        "detector": None,  # 需要更複雜的分析
        "penalty": 0.05,
        "suggestion": "合併功能相似的 Slider"
    },
]


class EleganceEvaluator:
    """
    優雅度評估器
    
    評估 Grasshopper 方案的各項指標
    """
    
    def __init__(self):
        self.metrics_config = {
            # === 簡潔性指標 ===
            "slider_count": {
                "weight": 0.15,
                "category": MetricCategory.SIMPLICITY,
                "description": "控制參數數量",
                "optimal_range": (1, 5),
                "penalty_rate": 0.1,
            },
            "component_count": {
                "weight": 0.10,
                "category": MetricCategory.SIMPLICITY,
                "description": "元件總數效率",
                "optimal_ratio": 0.8,  # 連接數/元件數
            },
            
            # === 效率指標 ===
            "connection_density": {
                "weight": 0.12,
                "category": MetricCategory.EFFICIENCY,
                "description": "連接密度",
                "optimal_range": (0.7, 1.5),
            },
            "datatree_complexity": {
                "weight": 0.10,
                "category": MetricCategory.EFFICIENCY,
                "description": "DataTree 操作複雜度",
                "penalty_components": ["Flatten", "Graft", "Partition", "Path Mapper"],
            },
            
            # === 靈活性指標 ===
            "parametric_depth": {
                "weight": 0.15,
                "category": MetricCategory.FLEXIBILITY,
                "description": "參數化深度",
            },
            "geometric_coupling": {
                "weight": 0.18,
                "category": MetricCategory.FLEXIBILITY,
                "description": "幾何驅動程度",
                "positive_components": ["Evaluate", "Closest Point", "Surface CP"],
            },
            
            # === 優雅度指標 ===
            "pattern_usage": {
                "weight": 0.12,
                "category": MetricCategory.ELEGANCE,
                "description": "優雅模式使用",
            },
            "anti_pattern_absence": {
                "weight": 0.08,
                "category": MetricCategory.ELEGANCE,
                "description": "反模式避免",
            },
        }
    
    def evaluate(self, gh_code: Dict[str, Any], patterns_matched: List[str] = None) -> EleganceReport:
        """
        執行完整評估
        
        Args:
            gh_code: GH Code 定義
            patterns_matched: 已匹配的設計模式
            
        Returns:
            EleganceReport 評估報告
        """
        components = gh_code.get("components", [])
        connections = gh_code.get("connections", [])
        sliders = gh_code.get("sliders", [])
        
        component_names = [c.get("type", c.get("name", "")).lower() for c in components]
        
        metrics = []
        
        # 1. 評估 Slider 數量
        metrics.append(self._evaluate_slider_count(sliders))
        
        # 2. 評估元件數量效率
        metrics.append(self._evaluate_component_efficiency(components, connections))
        
        # 3. 評估連接密度
        metrics.append(self._evaluate_connection_density(components, connections))
        
        # 4. 評估 DataTree 複雜度
        metrics.append(self._evaluate_datatree_complexity(component_names))
        
        # 5. 評估幾何耦合度
        metrics.append(self._evaluate_geometric_coupling(component_names))
        
        # 6. 評估模式使用
        metrics.append(self._evaluate_pattern_usage(component_names, patterns_matched or []))
        
        # 7. 評估反模式
        metrics.append(self._evaluate_anti_patterns(component_names, components, connections))
        
        # 計算總分
        total_weight = sum(m.weight for m in metrics)
        total_score = sum(m.score * m.weight for m in metrics) / total_weight if total_weight > 0 else 0
        
        # 生成等級
        grade = self._score_to_grade(total_score)
        
        # 生成摘要
        summary = self._generate_summary(metrics, total_score, grade)
        
        return EleganceReport(
            total_score=round(total_score, 3),
            metrics=metrics,
            summary=summary,
            grade=grade
        )
    
    def _evaluate_slider_count(self, sliders: List[Dict]) -> MetricResult:
        """評估 Slider 數量"""
        count = len(sliders)
        config = self.metrics_config["slider_count"]
        
        optimal_min, optimal_max = config["optimal_range"]
        
        if count == 0:
            score = 0.5
            issues = ["沒有參數化控制"]
            suggestions = ["添加 Slider 以實現參數化"]
        elif count <= optimal_max:
            score = 1.0
            issues = []
            suggestions = []
        else:
            excess = count - optimal_max
            score = max(0.3, 1.0 - excess * config["penalty_rate"])
            issues = [f"Slider 數量 ({count}) 超過建議值 ({optimal_max})"]
            suggestions = ["考慮使用 Gene Pool 或 Expression 合併參數"]
        
        return MetricResult(
            name="Slider 數量",
            category=config["category"],
            score=score,
            weight=config["weight"],
            description=f"目前 {count} 個 Slider",
            issues=issues,
            suggestions=suggestions
        )
    
    def _evaluate_component_efficiency(
        self, 
        components: List[Dict], 
        connections: List[Dict]
    ) -> MetricResult:
        """評估元件效率"""
        config = self.metrics_config["component_count"]
        
        comp_count = len(components)
        conn_count = len(connections)
        
        if comp_count == 0:
            return MetricResult(
                name="元件效率",
                category=config["category"],
                score=0.0,
                weight=config["weight"],
                description="沒有元件",
                issues=["方案為空"],
                suggestions=["需要生成元件"]
            )
        
        ratio = conn_count / comp_count
        optimal = config["optimal_ratio"]
        
        if ratio >= optimal:
            score = min(1.0, 0.7 + ratio * 0.3)
        else:
            score = max(0.4, ratio / optimal)
        
        issues = []
        suggestions = []
        
        if ratio < 0.5:
            issues.append("連接密度較低，可能存在孤立元件")
            suggestions.append("檢查並移除未連接的元件")
        
        return MetricResult(
            name="元件效率",
            category=config["category"],
            score=score,
            weight=config["weight"],
            description=f"{comp_count} 元件, {conn_count} 連接 (比率: {ratio:.2f})",
            issues=issues,
            suggestions=suggestions
        )
    
    def _evaluate_connection_density(
        self, 
        components: List[Dict], 
        connections: List[Dict]
    ) -> MetricResult:
        """評估連接密度"""
        config = self.metrics_config["connection_density"]
        
        comp_count = len(components)
        conn_count = len(connections)
        
        if comp_count <= 1:
            density = 0
        else:
            # 理想密度：每個元件平均有 1-2 個連接
            density = conn_count / max(1, comp_count - 1)
        
        optimal_min, optimal_max = config["optimal_range"]
        
        if optimal_min <= density <= optimal_max:
            score = 1.0
        elif density < optimal_min:
            score = max(0.4, density / optimal_min)
        else:
            score = max(0.6, 1.0 - (density - optimal_max) * 0.1)
        
        return MetricResult(
            name="連接密度",
            category=config["category"],
            score=score,
            weight=config["weight"],
            description=f"連接密度: {density:.2f}",
            issues=[],
            suggestions=[]
        )
    
    def _evaluate_datatree_complexity(self, component_names: List[str]) -> MetricResult:
        """評估 DataTree 複雜度"""
        config = self.metrics_config["datatree_complexity"]
        
        dt_keywords = ["flatten", "graft", "partition", "path mapper", "entwine"]
        dt_count = sum(1 for name in component_names if any(kw in name for kw in dt_keywords))
        
        if dt_count == 0:
            score = 1.0
            issues = []
            suggestions = []
        elif dt_count <= 2:
            score = 0.9
            issues = []
            suggestions = []
        elif dt_count <= 4:
            score = 0.7
            issues = [f"DataTree 操作較多 ({dt_count} 個)"]
            suggestions = ["檢查是否可以簡化數據結構"]
        else:
            score = 0.4
            issues = [f"DataTree 操作過多 ({dt_count} 個)"]
            suggestions = ["重新設計數據流，減少 DataTree 操作"]
        
        return MetricResult(
            name="DataTree 複雜度",
            category=config["category"],
            score=score,
            weight=config["weight"],
            description=f"{dt_count} 個 DataTree 操作",
            issues=issues,
            suggestions=suggestions
        )
    
    def _evaluate_geometric_coupling(self, component_names: List[str]) -> MetricResult:
        """評估幾何耦合度"""
        config = self.metrics_config["geometric_coupling"]
        
        # 幾何驅動元件
        geo_keywords = ["evaluate", "closest point", "surface cp", "point on", "curve cp"]
        geo_count = sum(1 for name in component_names if any(kw in name for kw in geo_keywords))
        
        # 數值硬編碼元件
        num_keywords = ["number slider", "panel"]
        num_count = sum(1 for name in component_names if any(kw in name for kw in num_keywords))
        
        total = len(component_names)
        
        if total == 0:
            score = 0.5
        else:
            geo_ratio = geo_count / total
            num_ratio = num_count / total
            
            # 幾何驅動比例高，數值硬編碼比例低 = 高分
            score = 0.5 + geo_ratio * 0.4 - num_ratio * 0.1
            score = max(0.3, min(1.0, score))
        
        issues = []
        suggestions = []
        
        if geo_count == 0:
            suggestions.append("考慮使用 Evaluate Surface/Curve 實現幾何驅動設計")
        
        return MetricResult(
            name="幾何耦合度",
            category=config["category"],
            score=score,
            weight=config["weight"],
            description=f"{geo_count} 個幾何驅動元件",
            issues=issues,
            suggestions=suggestions
        )
    
    def _evaluate_pattern_usage(
        self, 
        component_names: List[str], 
        patterns_matched: List[str]
    ) -> MetricResult:
        """評估優雅模式使用"""
        config = self.metrics_config["pattern_usage"]
        
        # 檢查優雅元件使用
        elegant_used = []
        for name in component_names:
            for elegant_name in ELEGANT_COMPONENTS:
                if elegant_name.lower() in name:
                    elegant_used.append(elegant_name)
        
        # 計算分數
        base_score = 0.5
        
        # 模式匹配加分
        pattern_bonus = len(patterns_matched) * 0.1
        
        # 優雅元件加分
        elegant_bonus = sum(
            ELEGANT_COMPONENTS[e]["score_bonus"] 
            for e in elegant_used 
            if e in ELEGANT_COMPONENTS
        )
        
        score = min(1.0, base_score + pattern_bonus + elegant_bonus)
        
        suggestions = []
        if not elegant_used:
            suggestions.append("考慮使用 Graph Mapper 或 Remap Numbers 實現非線性映射")
        
        return MetricResult(
            name="優雅模式使用",
            category=config["category"],
            score=score,
            weight=config["weight"],
            description=f"匹配 {len(patterns_matched)} 個模式, 使用 {len(elegant_used)} 個優雅元件",
            issues=[],
            suggestions=suggestions
        )
    
    def _evaluate_anti_patterns(
        self, 
        component_names: List[str],
        components: List[Dict],
        connections: List[Dict]
    ) -> MetricResult:
        """評估反模式"""
        config = self.metrics_config["anti_pattern_absence"]
        
        issues = []
        suggestions = []
        penalty = 0.0
        
        # 檢查已知反模式
        for anti in ANTI_PATTERNS:
            if anti["detector"] and anti["detector"](component_names):
                issues.append(anti["description"])
                suggestions.append(anti["suggestion"])
                penalty += anti["penalty"]
        
        # 檢查反模式元件過度使用
        for comp_name, rule in ANTI_PATTERN_COMPONENTS.items():
            count = sum(1 for name in component_names if comp_name.lower() in name)
            if count > rule["threshold"]:
                excess = count - rule["threshold"]
                penalty += excess * rule["penalty_per_excess"]
                issues.append(f"{comp_name} 使用過多 ({count} 個)")
        
        score = max(0.3, 1.0 - penalty)
        
        return MetricResult(
            name="反模式避免",
            category=config["category"],
            score=score,
            weight=config["weight"],
            description=f"檢測到 {len(issues)} 個潛在問題",
            issues=issues,
            suggestions=suggestions
        )
    
    def _score_to_grade(self, score: float) -> str:
        """分數轉等級"""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"
    
    def _generate_summary(
        self, 
        metrics: List[MetricResult], 
        total_score: float, 
        grade: str
    ) -> str:
        """生成評估摘要"""
        all_issues = []
        all_suggestions = []
        
        for m in metrics:
            all_issues.extend(m.issues)
            all_suggestions.extend(m.suggestions)
        
        summary_parts = [
            f"總評分: {total_score:.2f} ({grade})",
        ]
        
        if all_issues:
            summary_parts.append(f"發現 {len(all_issues)} 個問題")
        
        if grade in ["A", "B"]:
            summary_parts.append("方案優雅度良好")
        elif grade == "C":
            summary_parts.append("方案可接受，但有改進空間")
        else:
            summary_parts.append("建議重新設計以提高優雅度")
        
        return " | ".join(summary_parts)


# ============================================================
# 便利函數
# ============================================================

def evaluate_gh_code(gh_code: Dict[str, Any]) -> EleganceReport:
    """評估 GH Code 的便利函數"""
    evaluator = EleganceEvaluator()
    return evaluator.evaluate(gh_code)


def quick_score(gh_code: Dict[str, Any]) -> float:
    """快速取得評分"""
    report = evaluate_gh_code(gh_code)
    return report.total_score


if __name__ == "__main__":
    # 測試
    test_gh_code = {
        "components": [
            {"type": "Number Slider"},
            {"type": "Number Slider"},
            {"type": "Series"},
            {"type": "Sine"},
            {"type": "Cosine"},
            {"type": "Construct Point"},
            {"type": "Interpolate"},
            {"type": "Graph Mapper"},
        ],
        "connections": [
            {}, {}, {}, {}, {}, {}, {}
        ],
        "sliders": [
            {"name": "Turns"},
            {"name": "Radius"},
        ]
    }
    
    report = evaluate_gh_code(test_gh_code)
    
    print("=== Elegance Report ===")
    print(f"Grade: {report.grade}")
    print(f"Score: {report.total_score:.3f}")
    print(f"Summary: {report.summary}")
    print("\n--- Metrics ---")
    for m in report.metrics:
        print(f"  {m.name}: {m.score:.2f} (weight: {m.weight})")
        for issue in m.issues:
            print(f"    ⚠️ {issue}")
        for sug in m.suggestions:
            print(f"    💡 {sug}")
