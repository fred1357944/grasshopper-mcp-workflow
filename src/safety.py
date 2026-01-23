"""
Safety Configuration
====================
LangGraph 安全護欄設定

防止：
- 無限迴圈
- Token 爆炸
- 成本失控
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SafetyConfig:
    """安全配置"""
    
    # 迭代限制
    max_iterations: int = 5
    
    # Token 預算
    max_tokens_per_call: int = 4000
    total_token_budget: int = 50000
    
    # 時間限制
    timeout_seconds: int = 60
    max_total_time_seconds: int = 300  # 5 分鐘
    
    # 成本限制（美元）
    max_cost_per_request: float = 0.50
    
    # 分數閾值
    acceptance_threshold: float = 0.75
    require_human_approval_above_score: float = 0.95  # 太高分可能異常
    
    # 錯誤關鍵字
    critical_error_keywords: List[str] = field(default_factory=lambda: [
        "connection", "guid", "protocol", "timeout", "memory"
    ])


@dataclass
class SafetyState:
    """安全狀態追蹤"""
    
    iterations: int = 0
    total_tokens_used: int = 0
    total_cost: float = 0.0
    start_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "iterations": self.iterations,
            "total_tokens_used": self.total_tokens_used,
            "total_cost": self.total_cost,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "errors": self.errors,
            "warnings": self.warnings,
            "elapsed_seconds": self.elapsed_seconds
        }
    
    @property
    def elapsed_seconds(self) -> float:
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0


class SafetyGuard:
    """
    安全護欄檢查器
    
    用法：
        guard = SafetyGuard()
        
        # 在每次迭代前檢查
        status = guard.check(state)
        if status != "continue":
            # 處理停止邏輯
    """
    
    def __init__(self, config: SafetyConfig = None):
        self.config = config or SafetyConfig()
        self.state = SafetyState()
    
    def start(self):
        """開始追蹤"""
        self.state = SafetyState(start_time=datetime.now())
        logger.info("🛡️ Safety Guard 啟動")
    
    def check(self, graph_state: Dict[str, Any] = None) -> str:
        """
        執行安全檢查
        
        Returns:
            "continue" - 繼續執行
            "max_iterations" - 達到最大迭代次數
            "token_budget_exceeded" - Token 預算超支
            "timeout" - 超時
            "cost_exceeded" - 成本超支
            "critical_error" - 嚴重錯誤
            "score_anomaly" - 分數異常（太高）
        """
        # 1. 檢查迭代次數
        if self.state.iterations >= self.config.max_iterations:
            logger.warning(f"達到最大迭代次數 ({self.config.max_iterations})")
            return "max_iterations"
        
        # 2. 檢查 Token 預算
        if self.state.total_tokens_used > self.config.total_token_budget:
            logger.warning(f"Token 預算超支 ({self.state.total_tokens_used}/{self.config.total_token_budget})")
            return "token_budget_exceeded"
        
        # 3. 檢查時間
        if self.state.elapsed_seconds > self.config.max_total_time_seconds:
            logger.warning(f"執行超時 ({self.state.elapsed_seconds:.1f}s)")
            return "timeout"
        
        # 4. 檢查成本
        if self.state.total_cost > self.config.max_cost_per_request:
            logger.warning(f"成本超支 (${self.state.total_cost:.4f})")
            return "cost_exceeded"
        
        # 5. 檢查嚴重錯誤
        if self.state.errors:
            for error in self.state.errors:
                for keyword in self.config.critical_error_keywords:
                    if keyword.lower() in error.lower():
                        logger.error(f"嚴重錯誤: {error}")
                        return "critical_error"
        
        # 6. 檢查分數異常
        if graph_state:
            score = graph_state.get("elegance_score", 0)
            if score >= self.config.require_human_approval_above_score:
                logger.warning(f"分數異常高 ({score})，需要人工確認")
                return "score_anomaly"
        
        return "continue"
    
    def record_iteration(self, tokens_used: int = 0, cost: float = 0.0):
        """記錄迭代"""
        self.state.iterations += 1
        self.state.total_tokens_used += tokens_used
        self.state.total_cost += cost
        
        logger.info(f"迭代 {self.state.iterations}: "
                   f"tokens={self.state.total_tokens_used}, "
                   f"cost=${self.state.total_cost:.4f}")
    
    def record_error(self, error: str):
        """記錄錯誤"""
        self.state.errors.append(error)
        logger.error(f"錯誤: {error}")
    
    def record_warning(self, warning: str):
        """記錄警告"""
        self.state.warnings.append(warning)
        logger.warning(f"警告: {warning}")
    
    def summary(self) -> str:
        """產生摘要"""
        return f"""
🛡️ Safety Guard 報告
==================
迭代次數: {self.state.iterations}/{self.config.max_iterations}
Token 使用: {self.state.total_tokens_used}/{self.config.total_token_budget}
成本: ${self.state.total_cost:.4f}/${self.config.max_cost_per_request}
執行時間: {self.state.elapsed_seconds:.1f}s/{self.config.max_total_time_seconds}s
錯誤數: {len(self.state.errors)}
警告數: {len(self.state.warnings)}
"""


# ============================================================
# Token 計算工具
# ============================================================

def estimate_tokens(text: str) -> int:
    """估算文字的 token 數（簡化版）"""
    # 粗略估算：英文約 4 字元/token，中文約 1.5 字元/token
    english_chars = sum(1 for c in text if ord(c) < 128)
    chinese_chars = len(text) - english_chars
    
    return int(english_chars / 4 + chinese_chars / 1.5)


def estimate_cost(tokens: int, model: str = "claude-3-sonnet") -> float:
    """估算 API 成本"""
    # 價格表（美元/1M tokens）
    prices = {
        "claude-3-opus": {"input": 15.0, "output": 75.0},
        "claude-3-sonnet": {"input": 3.0, "output": 15.0},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        "gpt-4": {"input": 30.0, "output": 60.0},
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    }
    
    price = prices.get(model, prices["claude-3-sonnet"])
    
    # 假設 input/output 各半
    avg_price = (price["input"] + price["output"]) / 2
    
    return (tokens / 1_000_000) * avg_price


# ============================================================
# 與 LangGraph 整合
# ============================================================

def create_safe_graph_state(
    design_intent: str,
    config: SafetyConfig = None
) -> Dict[str, Any]:
    """創建帶安全配置的 GraphState"""
    config = config or SafetyConfig()
    
    return {
        # 使用者輸入
        "design_intent": design_intent,
        "constraints": [],
        
        # 安全追蹤
        "iteration_count": 0,
        "max_iterations": config.max_iterations,
        "total_tokens_used": 0,
        "max_token_budget": config.total_token_budget,
        "acceptance_threshold": config.acceptance_threshold,
        
        # 狀態追蹤
        "critique_history": [],
        "modification_history": [],
        "has_error": False,
        "error_message": None,
        "warnings": [],
        
        # 安全配置引用
        "_safety_config": config.__dict__
    }


def safety_condition(state: Dict[str, Any]) -> str:
    """
    LangGraph 條件邊界函數
    
    用於決定是否繼續迭代
    """
    # 檢查迭代次數
    if state.get("iteration_count", 0) >= state.get("max_iterations", 5):
        return "max_iterations"
    
    # 檢查 token 預算
    if state.get("total_tokens_used", 0) > state.get("max_token_budget", 50000):
        return "token_budget_exceeded"
    
    # 檢查錯誤
    if state.get("has_error", False):
        return "error"
    
    # 檢查分數
    score = state.get("elegance_score", 0)
    threshold = state.get("acceptance_threshold", 0.75)
    
    if score >= threshold:
        return "accept"
    
    # 繼續迭代
    return "continue"
