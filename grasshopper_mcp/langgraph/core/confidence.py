"""
Confidence Evaluator - 信心度評估系統

對應策略: Cascade (Boosting) + Confidence Threshold

信心度來源:
1. 嵌入相似度 (從 graph_learner 獲取)
2. 模式匹配度 (歷史連接模式)
3. 錯誤率 (執行歷史)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
import numpy as np


class ConfidenceSource(str, Enum):
    """信心度來源"""
    EMBEDDING = "embedding"      # 嵌入向量相似度
    PATTERN = "pattern"          # 連接模式匹配
    HISTORY = "history"          # 歷史成功率
    VALIDATION = "validation"    # 驗證結果


@dataclass
class ConfidenceThresholds:
    """信心度門檻配置"""
    # Cascade 門檻：決定是否需要升級到下一層
    cascade_pass: float = 0.8      # 高於此值 → 直接通過
    cascade_review: float = 0.6    # 高於此值 → 需要評審
    cascade_fail: float = 0.4      # 低於此值 → 需要重做

    # 權重配置
    embedding_weight: float = 0.3
    pattern_weight: float = 0.4
    history_weight: float = 0.2
    validation_weight: float = 0.1

    def __post_init__(self):
        total = (self.embedding_weight + self.pattern_weight +
                 self.history_weight + self.validation_weight)
        if abs(total - 1.0) > 0.01:
            # 正規化
            self.embedding_weight /= total
            self.pattern_weight /= total
            self.history_weight /= total
            self.validation_weight /= total


@dataclass
class ConfidenceResult:
    """信心度評估結果"""
    total_score: float                    # 總分 (0-1)
    scores: Dict[ConfidenceSource, float] # 各來源分數
    action: str                           # "pass" | "review" | "retry"
    details: Dict = field(default_factory=dict)

    @property
    def is_confident(self) -> bool:
        return self.action == "pass"

    @property
    def needs_review(self) -> bool:
        return self.action == "review"

    def to_dict(self) -> Dict:
        return {
            "total_score": self.total_score,
            "scores": {k.value: v for k, v in self.scores.items()},
            "action": self.action,
            "details": self.details,
        }


class ConfidenceEvaluator:
    """
    信心度評估器

    整合多種信心度來源，計算綜合信心分數，
    決定是否需要升級到下一個 Agent 層級。

    Usage:
        evaluator = ConfidenceEvaluator()
        evaluator.load_embeddings("knowledge/component_embeddings.json")

        result = evaluator.evaluate(
            component_type="Number Slider",
            target_param="N",
            context={"stage": "connectivity"}
        )

        if result.is_confident:
            # 直接執行
        elif result.needs_review:
            # 請求 Gemini 評審
        else:
            # 重試或人工介入
    """

    def __init__(
        self,
        thresholds: ConfidenceThresholds = None,
        embeddings_path: Optional[str] = None
    ):
        self.thresholds = thresholds or ConfidenceThresholds()
        self.embeddings: Dict[str, np.ndarray] = {}
        self.patterns: Dict[str, int] = {}
        self.history: Dict[str, List[bool]] = {}

        if embeddings_path:
            self.load_embeddings(embeddings_path)

    def load_embeddings(self, path: str) -> bool:
        """載入組件嵌入向量"""
        p = Path(path)
        if not p.exists():
            return False

        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 載入嵌入
        for name, vec in data.get('embeddings', {}).items():
            self.embeddings[name] = np.array(vec)

        # 載入模式
        self.patterns = data.get('top_patterns', {})

        return True

    def evaluate(
        self,
        component_type: str,
        target_param: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> ConfidenceResult:
        """
        評估組件操作的信心度

        Args:
            component_type: 組件類型
            target_param: 目標參數（可選）
            context: 上下文信息

        Returns:
            ConfidenceResult
        """
        scores = {}
        details = {}

        # 1. 嵌入相似度
        emb_score = self._evaluate_embedding(component_type)
        scores[ConfidenceSource.EMBEDDING] = emb_score
        details["embedding"] = {"found": component_type in self.embeddings}

        # 2. 模式匹配度
        pattern_score = self._evaluate_pattern(component_type, target_param)
        scores[ConfidenceSource.PATTERN] = pattern_score
        details["pattern"] = {"matched_patterns": self._count_patterns(component_type)}

        # 3. 歷史成功率
        history_score = self._evaluate_history(component_type)
        scores[ConfidenceSource.HISTORY] = history_score
        details["history"] = {"sample_count": len(self.history.get(component_type, []))}

        # 4. 驗證分數（預設為中等）
        validation_score = context.get("validation_score", 0.5) if context else 0.5
        scores[ConfidenceSource.VALIDATION] = validation_score

        # 計算加權總分
        total = (
            scores[ConfidenceSource.EMBEDDING] * self.thresholds.embedding_weight +
            scores[ConfidenceSource.PATTERN] * self.thresholds.pattern_weight +
            scores[ConfidenceSource.HISTORY] * self.thresholds.history_weight +
            scores[ConfidenceSource.VALIDATION] * self.thresholds.validation_weight
        )

        # 決定行動
        if total >= self.thresholds.cascade_pass:
            action = "pass"
        elif total >= self.thresholds.cascade_review:
            action = "review"
        else:
            action = "retry"

        return ConfidenceResult(
            total_score=total,
            scores=scores,
            action=action,
            details=details
        )

    def _evaluate_embedding(self, component_type: str) -> float:
        """評估嵌入相似度"""
        if component_type in self.embeddings:
            return 0.95  # 精確匹配

        component_lower = component_type.lower()

        # 嘗試模糊匹配
        for name in self.embeddings:
            if component_lower in name.lower() or name.lower() in component_lower:
                return 0.8  # 部分匹配

        # 嘗試單詞匹配
        for word in component_lower.split():
            if len(word) > 2:  # 忽略太短的詞
                for name in self.embeddings:
                    if word in name.lower():
                        return 0.6  # 詞彙匹配

        return 0.35  # 未知組件

    def _evaluate_pattern(
        self,
        component_type: str,
        target_param: Optional[str]
    ) -> float:
        """評估連接模式匹配度"""
        if not self.patterns:
            return 0.5  # 無模式資料

        # 計算匹配的模式數量
        matched = 0
        total_weight = 0
        component_lower = component_type.lower()

        for pattern, count in self.patterns.items():
            pattern_lower = pattern.lower()

            # 檢查組件名稱是否在模式中
            if component_lower in pattern_lower:
                matched += 1
                total_weight += count

                # 如果有目標參數，檢查參數匹配
                if target_param and target_param.lower() in pattern_lower:
                    matched += 2  # 參數匹配加分
            else:
                # 嘗試部分匹配（例如 "Box" 匹配 "Bounding Box"）
                for word in component_lower.split():
                    if word in pattern_lower:
                        matched += 0.5
                        total_weight += count * 0.5
                        break

        if matched == 0:
            return 0.3

        # 根據匹配數量和權重計算分數
        # 更積極的分數計算
        score = min(0.95, 0.4 + (matched / 5) * 0.3 + (total_weight / 50) * 0.2)
        return score

    def _count_patterns(self, component_type: str) -> int:
        """計算匹配的模式數量"""
        return sum(1 for p in self.patterns if component_type in p)

    def _evaluate_history(self, component_type: str) -> float:
        """評估歷史成功率"""
        history = self.history.get(component_type, [])
        if not history:
            return 0.5  # 無歷史

        success_rate = sum(history) / len(history)
        return success_rate

    def record_result(self, component_type: str, success: bool):
        """記錄執行結果（用於歷史信心度）"""
        if component_type not in self.history:
            self.history[component_type] = []

        self.history[component_type].append(success)

        # 保留最近 20 筆
        if len(self.history[component_type]) > 20:
            self.history[component_type] = self.history[component_type][-20:]

    def get_cascade_decision(
        self,
        component_type: str,
        current_level: int = 0
    ) -> Tuple[str, float]:
        """
        獲取 Cascade 決策

        Returns:
            (decision, confidence)
            decision: "execute" | "escalate" | "abort"
        """
        result = self.evaluate(component_type)

        if result.is_confident:
            return "execute", result.total_score
        elif result.needs_review and current_level < 2:
            return "escalate", result.total_score
        elif result.needs_review:
            return "execute", result.total_score  # 最高層級，勉強執行
        else:
            return "abort", result.total_score
