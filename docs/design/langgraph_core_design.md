# LangGraph Core 模組設計

## 目錄結構

```
grasshopper_mcp/langgraph/
├── core/                          # 新增核心模組
│   ├── __init__.py
│   ├── convergence.py             # 收斂判斷系統
│   ├── fallback.py                # Fallback Chain
│   ├── state_manager.py           # 狀態修剪與持久化
│   ├── trust.py                   # 信任等級系統
│   ├── errors.py                  # 錯誤分類與處理
│   └── dual_ai.py                 # Claude + Gemini 協作
├── state.py                       # 核心狀態定義 (擴展)
├── graphs/
│   ├── iterative_workflow.py
│   └── multivariant_workflow.py
├── nodes/
│   ├── requirements.py
│   ├── decomposition.py
│   ├── connectivity.py
│   ├── execution.py
│   ├── optimization.py            # 整合 dual_ai
│   └── human_review.py
└── checkpointers/
    └── file_checkpointer.py       # 整合 state_manager
```

---

## 1. core/convergence.py

```python
"""收斂判斷系統 - 含震盪檢測與品質門檻"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

class ConvergenceReason(str, Enum):
    HEALTHY = "healthy_convergence"
    OSCILLATION = "oscillation_detected"
    MAX_ITERATIONS = "max_iterations_reached"
    LOW_QUALITY = "converged_but_low_quality"
    STILL_OPTIMIZING = "still_optimizing"

@dataclass
class ConvergenceConfig:
    threshold: float = 0.85
    min_iterations: int = 2
    max_iterations: int = 10
    oscillation_window: int = 3
    early_stop_patience: int = 3
    quality_floor: float = 0.6
    
    # 根據任務複雜度動態調整
    @classmethod
    def for_complexity(cls, complexity: Literal["simple", "medium", "complex"]) -> "ConvergenceConfig":
        presets = {
            "simple": cls(threshold=0.90, max_iterations=5, quality_floor=0.7),
            "medium": cls(threshold=0.85, max_iterations=10, quality_floor=0.6),
            "complex": cls(threshold=0.75, max_iterations=15, quality_floor=0.5),
        }
        return presets[complexity]

@dataclass
class ConvergenceResult:
    converged: bool
    reason: ConvergenceReason
    confidence: float
    suggestion: str | None = None

class ConvergenceChecker:
    def __init__(self, config: ConvergenceConfig):
        self.config = config
    
    def check(
        self,
        convergence_scores: list[float],
        quality_scores: list[float]
    ) -> ConvergenceResult:
        """檢查是否應該收斂"""
        
        if len(convergence_scores) < self.config.min_iterations:
            return ConvergenceResult(
                converged=False,
                reason=ConvergenceReason.STILL_OPTIMIZING,
                confidence=0.0,
                suggestion=f"至少需要 {self.config.min_iterations} 輪迭代"
            )
        
        # 檢測震盪
        if self._detect_oscillation(convergence_scores):
            return ConvergenceResult(
                converged=True,
                reason=ConvergenceReason.OSCILLATION,
                confidence=0.7,
                suggestion="檢測到收斂震盪，建議人工選擇最佳方案"
            )
        
        # 超過最大迭代
        if len(convergence_scores) >= self.config.max_iterations:
            return ConvergenceResult(
                converged=True,
                reason=ConvergenceReason.MAX_ITERATIONS,
                confidence=0.5,
                suggestion="達到最大迭代次數，建議檢查任務定義"
            )
        
        current_score = convergence_scores[-1]
        current_quality = quality_scores[-1] if quality_scores else 1.0
        
        # 收斂但品質太低
        if current_score >= self.config.threshold:
            if current_quality < self.config.quality_floor:
                return ConvergenceResult(
                    converged=False,
                    reason=ConvergenceReason.LOW_QUALITY,
                    confidence=current_score,
                    suggestion="收斂分數達標但品質不足，需要人工介入"
                )
            return ConvergenceResult(
                converged=True,
                reason=ConvergenceReason.HEALTHY,
                confidence=min(current_score, current_quality)
            )
        
        return ConvergenceResult(
            converged=False,
            reason=ConvergenceReason.STILL_OPTIMIZING,
            confidence=current_score
        )
    
    def _detect_oscillation(self, scores: list[float]) -> bool:
        """檢測收斂分數震盪"""
        window = self.config.oscillation_window
        if len(scores) < window * 2:
            return False
        
        recent = scores[-window:]
        previous = scores[-window*2:-window]
        threshold = self.config.threshold
        
        # 兩個窗口都在閾值附近來回穿越
        recent_crosses = max(recent) > threshold > min(recent)
        previous_crosses = max(previous) > threshold > min(previous)
        
        return recent_crosses and previous_crosses
```

---

## 2. core/fallback.py

```python
"""Fallback Chain - 多層降級機制"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Callable, Awaitable
import asyncio
import logging

logger = logging.getLogger(__name__)

class DegradationLevel(IntEnum):
    FULL = 0          # 雙 AI 協作
    SINGLE_AI = 1     # 單 AI 自我評審
    RULE_BASED = 2    # 純規則驗證
    FAILED = 3        # 完全失敗

@dataclass
class FallbackResult:
    result: Any
    degradation_level: DegradationLevel
    confidence: float
    error_log: list[str] = None
    
    @property
    def is_degraded(self) -> bool:
        return self.degradation_level > DegradationLevel.FULL
    
    @property
    def quality_warning(self) -> str | None:
        warnings = {
            DegradationLevel.SINGLE_AI: "⚠️ Gemini 不可用，使用 Claude 自我評審",
            DegradationLevel.RULE_BASED: "⚠️ AI 評審不可用，僅使用規則驗證",
            DegradationLevel.FAILED: "❌ 所有評審機制失敗",
        }
        return warnings.get(self.degradation_level)

class FallbackChain:
    """可配置的 Fallback Chain"""
    
    def __init__(self):
        self.handlers: list[tuple[str, Callable, float]] = []
        self.error_log: list[str] = []
    
    def add_handler(
        self,
        name: str,
        handler: Callable[..., Awaitable[Any]],
        confidence: float = 1.0
    ) -> "FallbackChain":
        """添加處理器，按順序嘗試"""
        self.handlers.append((name, handler, confidence))
        return self
    
    async def execute(self, *args, timeout: float = 30, **kwargs) -> FallbackResult:
        """依序嘗試每個 handler，直到成功"""
        self.error_log = []
        
        for i, (name, handler, confidence) in enumerate(self.handlers):
            try:
                result = await asyncio.wait_for(
                    handler(*args, **kwargs),
                    timeout=timeout
                )
                return FallbackResult(
                    result=result,
                    degradation_level=DegradationLevel(i),
                    confidence=confidence,
                    error_log=self.error_log if self.error_log else None
                )
            except asyncio.TimeoutError:
                msg = f"[{name}] Timeout after {timeout}s"
                self.error_log.append(msg)
                logger.warning(msg)
            except Exception as e:
                msg = f"[{name}] Error: {type(e).__name__}: {e}"
                self.error_log.append(msg)
                logger.warning(msg)
        
        # 全部失敗
        return FallbackResult(
            result=None,
            degradation_level=DegradationLevel.FAILED,
            confidence=0.0,
            error_log=self.error_log
        )

# 預設 Chain 工廠
def create_default_review_chain(
    gemini_reviewer: Callable,
    claude_self_reviewer: Callable,
    rule_validator: Callable
) -> FallbackChain:
    return (
        FallbackChain()
        .add_handler("gemini_review", gemini_reviewer, confidence=1.0)
        .add_handler("claude_self_review", claude_self_reviewer, confidence=0.7)
        .add_handler("rule_validation", rule_validator, confidence=0.4)
    )
```

---

## 3. core/state_manager.py

```python
"""狀態管理 - 修剪、分層存儲、可追溯"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypedDict
import json
import hashlib
from datetime import datetime

class StateArchive(TypedDict):
    archive_id: str
    timestamp: str
    item_count: int
    summary: str

@dataclass
class StateManagerConfig:
    hot_data_limit: int = 5          # 記憶體中保留的輪數
    archive_dir: Path = Path(".gh_mcp_archives")
    enable_compression: bool = True
    max_errors_kept: int = 10

class StateManager:
    def __init__(self, config: StateManagerConfig = None):
        self.config = config or StateManagerConfig()
        self.config.archive_dir.mkdir(parents=True, exist_ok=True)
    
    def prune(self, state: dict) -> dict:
        """修剪狀態，分離冷熱數據"""
        pruned = {**state}
        
        # 1. Proposals: 保留最近 N 輪，其餘歸檔
        proposals = state.get("proposals", [])
        if len(proposals) > self.config.hot_data_limit:
            cold_proposals = proposals[:-self.config.hot_data_limit]
            hot_proposals = proposals[-self.config.hot_data_limit:]
            
            archive = self._archive(cold_proposals, "proposals")
            pruned["proposals"] = hot_proposals
            pruned["archived_proposals"] = state.get("archived_proposals", []) + [archive]
        
        # 2. Decisions: 壓縮為摘要
        decisions = state.get("decisions_made", [])
        if decisions:
            pruned["decisions_summary"] = self._summarize_decisions(decisions)
            pruned["decisions_made"] = []
        
        # 3. Errors: 去重並限制數量
        errors = state.get("errors", [])
        pruned["errors"] = self._dedupe_errors(errors)[-self.config.max_errors_kept:]
        
        # 4. 記錄修剪時間
        pruned["last_pruned"] = datetime.now().isoformat()
        
        return pruned
    
    def _archive(self, data: list, data_type: str) -> StateArchive:
        """歸檔冷數據到磁碟"""
        content = json.dumps(data, ensure_ascii=False, indent=2)
        archive_id = hashlib.sha256(content.encode()).hexdigest()[:12]
        
        archive_path = self.config.archive_dir / f"{data_type}_{archive_id}.json"
        archive_path.write_text(content, encoding="utf-8")
        
        return StateArchive(
            archive_id=archive_id,
            timestamp=datetime.now().isoformat(),
            item_count=len(data),
            summary=self._generate_summary(data, data_type)
        )
    
    def restore_archive(self, archive: StateArchive, data_type: str) -> list:
        """從磁碟恢復歸檔數據"""
        archive_path = self.config.archive_dir / f"{data_type}_{archive['archive_id']}.json"
        if archive_path.exists():
            return json.loads(archive_path.read_text(encoding="utf-8"))
        raise FileNotFoundError(f"Archive not found: {archive['archive_id']}")
    
    def _summarize_decisions(self, decisions: list[dict]) -> list[dict]:
        """壓縮決策記錄，保留關鍵信息"""
        return [
            {
                "question": d.get("question", "")[:100],
                "choice": d.get("choice"),
                "reasoning": d.get("reasoning", "")[:200],
                "timestamp": d.get("timestamp"),
            }
            for d in decisions
        ]
    
    def _dedupe_errors(self, errors: list) -> list:
        """錯誤去重"""
        seen = set()
        unique = []
        for e in errors:
            key = f"{e.get('component_id')}:{e.get('message')}"
            if key not in seen:
                seen.add(key)
                unique.append(e)
        return unique
    
    def _generate_summary(self, data: list, data_type: str) -> str:
        """生成歸檔摘要"""
        if data_type == "proposals":
            return f"包含 {len(data)} 個提案，涵蓋組件: {', '.join(set(p.get('component_type', 'unknown') for p in data[:5]))}"
        return f"{len(data)} items archived"
```

---

## 4. core/trust.py

```python
"""信任等級系統 - 含動態調整"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal
from collections import deque

class TrustLevel(str, Enum):
    NOVICE = "novice"        # 每步確認 + 詳細解釋
    STANDARD = "standard"    # 關鍵步驟確認
    EXPERT = "expert"        # 只在錯誤時暫停

@dataclass
class InteractionEvent:
    action: Literal["accept", "modify", "reject", "ask_help"]
    stage: str
    timestamp: str = ""

@dataclass 
class TrustConfig:
    initial_level: TrustLevel = TrustLevel.STANDARD
    history_window: int = 10
    upgrade_threshold: int = 5      # 連續 N 次接受 → 升級
    downgrade_threshold: float = 0.6  # 修改率超過 60% → 降級
    enable_auto_adjust: bool = True

class AdaptiveTrustSystem:
    """根據用戶行為動態調整信任等級"""
    
    def __init__(self, config: TrustConfig = None):
        self.config = config or TrustConfig()
        self.level = self.config.initial_level
        self.history: deque[InteractionEvent] = deque(maxlen=self.config.history_window)
        self._level_locked = False
    
    def record(self, event: InteractionEvent) -> TrustLevel:
        """記錄互動事件，可能觸發等級調整"""
        self.history.append(event)
        
        if self.config.enable_auto_adjust and not self._level_locked:
            self._maybe_adjust()
        
        return self.level
    
    def lock_level(self):
        """鎖定當前等級，不再自動調整"""
        self._level_locked = True
    
    def unlock_level(self):
        self._level_locked = False
    
    def set_level(self, level: TrustLevel):
        """手動設置等級"""
        self.level = level
    
    def should_pause(self, stage: str, has_errors: bool = False) -> bool:
        """判斷是否應該暫停等待確認"""
        if has_errors:
            return True  # 有錯誤時總是暫停
        
        critical_stages = {"decomposition", "execution", "final_review"}
        
        if self.level == TrustLevel.EXPERT:
            return False
        elif self.level == TrustLevel.STANDARD:
            return stage in critical_stages
        else:  # NOVICE
            return True
    
    def get_explanation_level(self) -> Literal["detailed", "normal", "minimal"]:
        """根據信任等級決定解釋詳細程度"""
        return {
            TrustLevel.NOVICE: "detailed",
            TrustLevel.STANDARD: "normal",
            TrustLevel.EXPERT: "minimal",
        }[self.level]
    
    def _maybe_adjust(self):
        """根據歷史記錄調整等級"""
        if len(self.history) < 5:
            return
        
        recent = list(self.history)[-self.config.history_window:]
        
        # 檢查是否應該升級
        accept_streak = 0
        for event in reversed(recent):
            if event.action == "accept":
                accept_streak += 1
            else:
                break
        
        if accept_streak >= self.config.upgrade_threshold:
            self._upgrade()
            return
        
        # 檢查是否應該降級
        modify_count = sum(1 for e in recent if e.action in ("modify", "ask_help"))
        modify_rate = modify_count / len(recent)
        
        if modify_rate >= self.config.downgrade_threshold:
            self._downgrade()
    
    def _upgrade(self):
        if self.level == TrustLevel.NOVICE:
            self.level = TrustLevel.STANDARD
        elif self.level == TrustLevel.STANDARD:
            self.level = TrustLevel.EXPERT
    
    def _downgrade(self):
        if self.level == TrustLevel.EXPERT:
            self.level = TrustLevel.STANDARD
        # NOVICE 不再降級，但可以記錄需要更多幫助
```

---

## 5. core/errors.py

```python
"""錯誤分類與處理系統"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

class ErrorSeverity(str, Enum):
    CRITICAL = "critical"    # 必須修復：連接錯誤、組件不存在
    WARNING = "warning"      # 建議修復：參數超出建議範圍
    INFO = "info"           # 可忽略：優化建議

class ErrorCategory(str, Enum):
    CONNECTION = "connection"        # 連接問題
    COMPONENT = "component"          # 組件問題
    PARAMETER = "parameter"          # 參數問題
    GEOMETRY = "geometry"            # 幾何問題
    PERFORMANCE = "performance"      # 性能問題

@dataclass
class GHError:
    severity: ErrorSeverity
    category: ErrorCategory
    component_id: str
    message: str
    auto_fixable: bool = False
    suggested_fix: str | None = None
    fix_confidence: float = 0.0      # 自動修復的信心度
    
    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "component_id": self.component_id,
            "message": self.message,
            "auto_fixable": self.auto_fixable,
            "suggested_fix": self.suggested_fix,
            "fix_confidence": self.fix_confidence,
        }

class ErrorAction(str, Enum):
    AUTO_FIX = "auto_fix"
    PAUSE_FOR_REVIEW = "pause_for_review"
    CONTINUE_WITH_LOG = "continue_with_log"
    ABORT = "abort"

@dataclass
class ErrorHandlingResult:
    action: ErrorAction
    errors_to_fix: list[GHError]
    errors_to_log: list[GHError]
    message: str

class ErrorHandler:
    """根據錯誤類型和信任等級決定處理方式"""
    
    def __init__(self, auto_fix_confidence_threshold: float = 0.8):
        self.confidence_threshold = auto_fix_confidence_threshold
    
    def handle(
        self,
        errors: list[GHError],
        trust_level: "TrustLevel"
    ) -> ErrorHandlingResult:
        """決定錯誤處理方式"""
        from .trust import TrustLevel
        
        critical = [e for e in errors if e.severity == ErrorSeverity.CRITICAL]
        warnings = [e for e in errors if e.severity == ErrorSeverity.WARNING]
        infos = [e for e in errors if e.severity == ErrorSeverity.INFO]
        
        # 可自動修復的嚴重錯誤
        auto_fixable_critical = [
            e for e in critical 
            if e.auto_fixable and e.fix_confidence >= self.confidence_threshold
        ]
        
        # 需要人工處理的嚴重錯誤
        manual_critical = [e for e in critical if e not in auto_fixable_critical]
        
        # 決策邏輯
        if manual_critical:
            # 有無法自動修復的嚴重錯誤 → 必須暫停
            return ErrorHandlingResult(
                action=ErrorAction.PAUSE_FOR_REVIEW,
                errors_to_fix=[],
                errors_to_log=errors,
                message=f"發現 {len(manual_critical)} 個需要人工處理的嚴重錯誤"
            )
        
        if auto_fixable_critical:
            if trust_level == TrustLevel.EXPERT:
                # 專家模式 + 全部可自動修復 → 直接修
                return ErrorHandlingResult(
                    action=ErrorAction.AUTO_FIX,
                    errors_to_fix=auto_fixable_critical,
                    errors_to_log=warnings + infos,
                    message=f"自動修復 {len(auto_fixable_critical)} 個錯誤"
                )
            else:
                # 非專家模式 → 詢問確認
                return ErrorHandlingResult(
                    action=ErrorAction.PAUSE_FOR_REVIEW,
                    errors_to_fix=auto_fixable_critical,
                    errors_to_log=warnings + infos,
                    message=f"發現 {len(auto_fixable_critical)} 個可自動修復的錯誤，是否執行？"
                )
        
        if warnings:
            # 只有警告 → 記錄但繼續
            return ErrorHandlingResult(
                action=ErrorAction.CONTINUE_WITH_LOG,
                errors_to_fix=[],
                errors_to_log=warnings + infos,
                message=f"發現 {len(warnings)} 個警告，已記錄"
            )
        
        # 只有 info → 繼續
        return ErrorHandlingResult(
            action=ErrorAction.CONTINUE_WITH_LOG,
            errors_to_fix=[],
            errors_to_log=infos,
            message="無嚴重問題"
        )

# 錯誤工廠函數
def connection_error(component_id: str, target_id: str, param: str) -> GHError:
    return GHError(
        severity=ErrorSeverity.CRITICAL,
        category=ErrorCategory.CONNECTION,
        component_id=component_id,
        message=f"無法連接到 {target_id} 的 {param} 參數",
        auto_fixable=True,
        suggested_fix=f"嘗試連接到 {target_id} 的替代參數",
        fix_confidence=0.7
    )

def missing_component_error(component_type: str) -> GHError:
    return GHError(
        severity=ErrorSeverity.CRITICAL,
        category=ErrorCategory.COMPONENT,
        component_id="unknown",
        message=f"組件類型 '{component_type}' 不存在",
        auto_fixable=False
    )

def parameter_warning(component_id: str, param: str, value: float, suggested: tuple) -> GHError:
    return GHError(
        severity=ErrorSeverity.WARNING,
        category=ErrorCategory.PARAMETER,
        component_id=component_id,
        message=f"參數 {param}={value} 超出建議範圍 {suggested}",
        auto_fixable=True,
        suggested_fix=f"調整為 {sum(suggested)/2}",
        fix_confidence=0.9
    )
```

---

## 6. core/dual_ai.py

```python
"""Claude + Gemini 雙 AI 協作系統"""

from dataclasses import dataclass
from typing import Any, Protocol
import json
import os

from .fallback import FallbackChain, FallbackResult, create_default_review_chain

class AIReviewer(Protocol):
    async def review(self, proposal: dict) -> dict: ...

@dataclass
class ReviewResult:
    score: float              # 0-100
    issues: list[str]
    suggestions: list[str]
    raw_response: dict

@dataclass
class DualAIResult:
    claude_proposal: dict
    review_result: ReviewResult
    fallback_info: FallbackResult
    consensus_score: float    # Claude 和 Gemini 的一致性
    final_recommendation: dict

class GeminiReviewer:
    """Gemini API 評審器"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client = None
    
    async def review(self, proposal: dict, context: str = "") -> ReviewResult:
        if not self._client:
            await self._init_client()
        
        prompt = self._build_review_prompt(proposal, context)
        response = await self._client.generate_content_async(prompt)
        
        return self._parse_response(response.text)
    
    async def _init_client(self):
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel('gemini-1.5-pro')
        except ImportError:
            raise ImportError("請安裝 google-generativeai: pip install google-generativeai")
    
    def _build_review_prompt(self, proposal: dict, context: str) -> str:
        return f"""作為 Grasshopper 參數化設計專家，評審以下設計提案：

背景：{context}

提案內容：
{json.dumps(proposal, ensure_ascii=False, indent=2)}

請評估：
1. 幾何邏輯正確性 (組件連接是否合理)
2. 參數化程度適當性 (哪些應該是參數、哪些應該固定)
3. 可擴展性 (是否容易修改和擴展)
4. 效能考量 (是否有不必要的複雜度)

請以 JSON 格式回覆：
{{
    "score": 0-100 的整數,
    "issues": ["問題1", "問題2", ...],
    "suggestions": ["建議1", "建議2", ...],
    "confidence": 0-1 的浮點數表示評審信心度
}}"""
    
    def _parse_response(self, text: str) -> ReviewResult:
        # 清理可能的 markdown 標記
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        try:
            data = json.loads(text)
            return ReviewResult(
                score=data.get("score", 50),
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                raw_response=data
            )
        except json.JSONDecodeError:
            # Fallback: 嘗試從文本提取信息
            return ReviewResult(
                score=50,
                issues=["無法解析 Gemini 回應"],
                suggestions=[],
                raw_response={"raw_text": text}
            )

class ClaudeSelfReviewer:
    """Claude 自我評審 (Fallback)"""
    
    async def review(self, proposal: dict, context: str = "") -> ReviewResult:
        # 這裡會透過 MCP 或直接 API 調用 Claude
        # 使用不同的 system prompt 來模擬「評審者」角色
        
        # Placeholder - 實際實現需要 Claude API
        return ReviewResult(
            score=70,
            issues=["(自我評審) 需要進一步驗證"],
            suggestions=["建議人工確認關鍵連接"],
            raw_response={"mode": "self_review"}
        )

class RuleBasedValidator:
    """純規則驗證 (最後 Fallback)"""
    
    RULES = {
        "has_output": lambda p: "outputs" in p and len(p["outputs"]) > 0,
        "has_connections": lambda p: "connections" in p and len(p["connections"]) > 0,
        "no_orphans": lambda p: True,  # 簡化：實際需要圖分析
    }
    
    async def review(self, proposal: dict, context: str = "") -> ReviewResult:
        issues = []
        passed = 0
        
        for rule_name, check in self.RULES.items():
            try:
                if check(proposal):
                    passed += 1
                else:
                    issues.append(f"規則 '{rule_name}' 未通過")
            except Exception as e:
                issues.append(f"規則 '{rule_name}' 檢查失敗: {e}")
        
        score = (passed / len(self.RULES)) * 100
        
        return ReviewResult(
            score=score,
            issues=issues,
            suggestions=["建議啟用 AI 評審以獲得更詳細的分析"],
            raw_response={"mode": "rule_based", "rules_passed": passed}
        )

class DualAIOptimizer:
    """整合 Claude 提案 + Gemini/Fallback 評審"""
    
    def __init__(self, gemini_api_key: str = None):
        self.gemini = GeminiReviewer(gemini_api_key)
        self.claude_fallback = ClaudeSelfReviewer()
        self.rule_validator = RuleBasedValidator()
        
        self.review_chain = create_default_review_chain(
            gemini_reviewer=self.gemini.review,
            claude_self_reviewer=self.claude_fallback.review,
            rule_validator=self.rule_validator.review
        )
    
    async def optimize(
        self,
        claude_proposal: dict,
        context: str = "",
        timeout: float = 30
    ) -> DualAIResult:
        """執行雙 AI 優化流程"""
        
        # 執行帶 Fallback 的評審
        fallback_result = await self.review_chain.execute(
            claude_proposal,
            context,
            timeout=timeout
        )
        
        review = fallback_result.result
        if review is None:
            review = ReviewResult(
                score=0,
                issues=["所有評審機制都失敗"],
                suggestions=["請檢查 API 配置"],
                raw_response={}
            )
        
        # 計算共識分數 (如果是降級模式，共識較低)
        consensus = self._calculate_consensus(
            claude_proposal,
            review,
            fallback_result.degradation_level
        )
        
        # 生成最終建議
        final = self._generate_recommendation(claude_proposal, review)
        
        return DualAIResult(
            claude_proposal=claude_proposal,
            review_result=review,
            fallback_info=fallback_result,
            consensus_score=consensus,
            final_recommendation=final
        )
    
    def _calculate_consensus(
        self,
        proposal: dict,
        review: ReviewResult,
        degradation_level: int
    ) -> float:
        """計算共識分數"""
        base_consensus = review.score / 100
        
        # 降級會降低共識信心
        degradation_penalty = degradation_level * 0.15
        
        return max(0, base_consensus - degradation_penalty)
    
    def _generate_recommendation(
        self,
        proposal: dict,
        review: ReviewResult
    ) -> dict:
        """根據評審結果生成最終建議"""
        if review.score >= 80:
            action = "accept"
            message = "提案品質良好，建議採納"
        elif review.score >= 60:
            action = "revise"
            message = f"提案需要修改: {', '.join(review.issues[:2])}"
        else:
            action = "reject"
            message = "提案品質不足，建議重新設計"
        
        return {
            "action": action,
            "message": message,
            "priority_fixes": review.issues[:3],
            "suggestions": review.suggestions[:3],
        }
```

---

## 7. core/__init__.py

```python
"""LangGraph Core Module - 核心系統組件"""

from .convergence import (
    ConvergenceConfig,
    ConvergenceChecker,
    ConvergenceResult,
    ConvergenceReason,
)
from .fallback import (
    FallbackChain,
    FallbackResult,
    DegradationLevel,
    create_default_review_chain,
)
from .state_manager import (
    StateManager,
    StateManagerConfig,
    StateArchive,
)
from .trust import (
    TrustLevel,
    TrustConfig,
    AdaptiveTrustSystem,
    InteractionEvent,
)
from .errors import (
    GHError,
    ErrorSeverity,
    ErrorCategory,
    ErrorAction,
    ErrorHandler,
    ErrorHandlingResult,
    connection_error,
    missing_component_error,
    parameter_warning,
)
from .dual_ai import (
    DualAIOptimizer,
    DualAIResult,
    GeminiReviewer,
    ReviewResult,
)

__all__ = [
    # Convergence
    "ConvergenceConfig",
    "ConvergenceChecker", 
    "ConvergenceResult",
    "ConvergenceReason",
    # Fallback
    "FallbackChain",
    "FallbackResult",
    "DegradationLevel",
    "create_default_review_chain",
    # State
    "StateManager",
    "StateManagerConfig",
    "StateArchive",
    # Trust
    "TrustLevel",
    "TrustConfig",
    "AdaptiveTrustSystem",
    "InteractionEvent",
    # Errors
    "GHError",
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorAction",
    "ErrorHandler",
    "ErrorHandlingResult",
    "connection_error",
    "missing_component_error",
    "parameter_warning",
    # Dual AI
    "DualAIOptimizer",
    "DualAIResult",
    "GeminiReviewer",
    "ReviewResult",
]
```

---

## 使用範例

```python
# optimization.py 整合範例
from langgraph.core import (
    DualAIOptimizer,
    ConvergenceChecker,
    ConvergenceConfig,
    StateManager,
    AdaptiveTrustSystem,
    ErrorHandler,
    TrustLevel,
)

async def optimize_parameters_node(state: dict) -> dict:
    # 初始化系統
    optimizer = DualAIOptimizer()
    convergence = ConvergenceChecker(ConvergenceConfig.for_complexity(state["complexity"]))
    state_mgr = StateManager()
    trust = AdaptiveTrustSystem()
    error_handler = ErrorHandler()
    
    # 1. Claude 提案 (假設已有)
    claude_proposal = state["current_proposal"]
    
    # 2. 雙 AI 評審
    result = await optimizer.optimize(claude_proposal, context=state["topic"])
    
    # 3. 錯誤處理
    if result.review_result.issues:
        errors = [...]  # 轉換為 GHError
        handling = error_handler.handle(errors, trust.level)
        if handling.action == ErrorAction.PAUSE_FOR_REVIEW:
            return {"awaiting_confirmation": True, "errors": errors}
    
    # 4. 檢查收斂
    state["convergence_scores"].append(result.consensus_score)
    state["quality_scores"].append(result.review_result.score / 100)
    
    conv_result = convergence.check(
        state["convergence_scores"],
        state["quality_scores"]
    )
    
    # 5. 狀態修剪
    state = state_mgr.prune(state)
    
    # 6. 返回結果
    if conv_result.converged:
        return {
            **state,
            "awaiting_confirmation": trust.should_pause("final_review"),
            "convergence_reason": conv_result.reason.value,
        }
    
    return {**state, "continue_optimization": True}
```
`
}{
  `path`: `Projects/GH_MCP/langgraph_core_design.md`,
  `content`: `# LangGraph Core 模組設計

## 目錄結構

```
grasshopper_mcp/langgraph/
├── core/                          # 新增核心模組
│   ├── __init__.py
│   ├── convergence.py             # 收斂判斷系統
│   ├── fallback.py                # Fallback Chain
│   ├── state_manager.py           # 狀態修剪與持久化
│   ├── trust.py                   # 信任等級系統
│   ├── errors.py                  # 錯誤分類與處理
│   └── dual_ai.py                 # Claude + Gemini 協作
├── state.py                       # 核心狀態定義 (擴展)
├── graphs/
│   ├── iterative_workflow.py
│   └── multivariant_workflow.py
├── nodes/
│   ├── requirements.py
│   ├── decomposition.py
│   ├── connectivity.py
│   ├── execution.py
│   ├── optimization.py            # 整合 dual_ai
│   └── human_review.py
└── checkpointers/
    └── file_checkpointer.py       # 整合 state_manager
```

---

## 1. core/convergence.py

```python
"""收斂判斷系統 - 含震盪檢測與品質門檻"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

class ConvergenceReason(str, Enum):
    HEALTHY = "healthy_convergence"
    OSCILLATION = "oscillation_detected"
    MAX_ITERATIONS = "max_iterations_reached"
    LOW_QUALITY = "converged_but_low_quality"
    STILL_OPTIMIZING = "still_optimizing"

@dataclass
class ConvergenceConfig:
    threshold: float = 0.85
    min_iterations: int = 2
    max_iterations: int = 10
    oscillation_window: int = 3
    early_stop_patience: int = 3
    quality_floor: float = 0.6
    
    # 根據任務複雜度動態調整
    @classmethod
    def for_complexity(cls, complexity: Literal["simple", "medium", "complex"]) -> "ConvergenceConfig":
        presets = {
            "simple": cls(threshold=0.90, max_iterations=5, quality_floor=0.7),
            "medium": cls(threshold=0.85, max_iterations=10, quality_floor=0.6),
            "complex": cls(threshold=0.75, max_iterations=15, quality_floor=0.5),
        }
        return presets[complexity]

@dataclass
class ConvergenceResult:
    converged: bool
    reason: ConvergenceReason
    confidence: float
    suggestion: str | None = None

class ConvergenceChecker:
    def __init__(self, config: ConvergenceConfig):
        self.config = config
    
    def check(
        self,
        convergence_scores: list[float],
        quality_scores: list[float]
    ) -> ConvergenceResult:
        """檢查是否應該收斂"""
        
        if len(convergence_scores) < self.config.min_iterations:
            return ConvergenceResult(
                converged=False,
                reason=ConvergenceReason.STILL_OPTIMIZING,
                confidence=0.0,
                suggestion=f"至少需要 {self.config.min_iterations} 輪迭代"
            )
        
        # 檢測震盪
        if self._detect_oscillation(convergence_scores):
            return ConvergenceResult(
                converged=True,
                reason=ConvergenceReason.OSCILLATION,
                confidence=0.7,
                suggestion="檢測到收斂震盪，建議人工選擇最佳方案"
            )
        
        # 超過最大迭代
        if len(convergence_scores) >= self.config.max_iterations:
            return ConvergenceResult(
                converged=True,
                reason=ConvergenceReason.MAX_ITERATIONS,
                confidence=0.5,
                suggestion="達到最大迭代次數，建議檢查任務定義"
            )
        
        current_score = convergence_scores[-1]
        current_quality = quality_scores[-1] if quality_scores else 1.0
        
        # 收斂但品質太低
        if current_score >= self.config.threshold:
            if current_quality < self.config.quality_floor:
                return ConvergenceResult(
                    converged=False,
                    reason=ConvergenceReason.LOW_QUALITY,
                    confidence=current_score,
                    suggestion="收斂分數達標但品質不足，需要人工介入"
                )
            return ConvergenceResult(
                converged=True,
                reason=ConvergenceReason.HEALTHY,
                confidence=min(current_score, current_quality)
            )
        
        return ConvergenceResult(
            converged=False,
            reason=ConvergenceReason.STILL_OPTIMIZING,
            confidence=current_score
        )
    
    def _detect_oscillation(self, scores: list[float]) -> bool:
        """檢測收斂分數震盪"""
        window = self.config.oscillation_window
        if len(scores) < window * 2:
            return False
        
        recent = scores[-window:]
        previous = scores[-window*2:-window]
        threshold = self.config.threshold
        
        # 兩個窗口都在閾值附近來回穿越
        recent_crosses = max(recent) > threshold > min(recent)
        previous_crosses = max(previous) > threshold > min(previous)
        
        return recent_crosses and previous_crosses
```

---

## 2. core/fallback.py

```python
"""Fallback Chain - 多層降級機制"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Callable, Awaitable
import asyncio
import logging

logger = logging.getLogger(__name__)

class DegradationLevel(IntEnum):
    FULL = 0          # 雙 AI 協作
    SINGLE_AI = 1     # 單 AI 自我評審
    RULE_BASED = 2    # 純規則驗證
    FAILED = 3        # 完全失敗

@dataclass
class FallbackResult:
    result: Any
    degradation_level: DegradationLevel
    confidence: float
    error_log: list[str] = None
    
    @property
    def is_degraded(self) -> bool:
        return self.degradation_level > DegradationLevel.FULL
    
    @property
    def quality_warning(self) -> str | None:
        warnings = {
            DegradationLevel.SINGLE_AI: "⚠️ Gemini 不可用，使用 Claude 自我評審",
            DegradationLevel.RULE_BASED: "⚠️ AI 評審不可用，僅使用規則驗證",
            DegradationLevel.FAILED: "❌ 所有評審機制失敗",
        }
        return warnings.get(self.degradation_level)

class FallbackChain:
    """可配置的 Fallback Chain"""
    
    def __init__(self):
        self.handlers: list[tuple[str, Callable, float]] = []
        self.error_log: list[str] = []
    
    def add_handler(
        self,
        name: str,
        handler: Callable[..., Awaitable[Any]],
        confidence: float = 1.0
    ) -> "FallbackChain":
        """添加處理器，按順序嘗試"""
        self.handlers.append((name, handler, confidence))
        return self
    
    async def execute(self, *args, timeout: float = 30, **kwargs) -> FallbackResult:
        """依序嘗試每個 handler，直到成功"""
        self.error_log = []
        
        for i, (name, handler, confidence) in enumerate(self.handlers):
            try:
                result = await asyncio.wait_for(
                    handler(*args, **kwargs),
                    timeout=timeout
                )
                return FallbackResult(
                    result=result,
                    degradation_level=DegradationLevel(i),
                    confidence=confidence,
                    error_log=self.error_log if self.error_log else None
                )
            except asyncio.TimeoutError:
                msg = f"[{name}] Timeout after {timeout}s"
                self.error_log.append(msg)
                logger.warning(msg)
            except Exception as e:
                msg = f"[{name}] Error: {type(e).__name__}: {e}"
                self.error_log.append(msg)
                logger.warning(msg)
        
        # 全部失敗
        return FallbackResult(
            result=None,
            degradation_level=DegradationLevel.FAILED,
            confidence=0.0,
            error_log=self.error_log
        )

# 預設 Chain 工廠
def create_default_review_chain(
    gemini_reviewer: Callable,
    claude_self_reviewer: Callable,
    rule_validator: Callable
) -> FallbackChain:
    return (
        FallbackChain()
        .add_handler("gemini_review", gemini_reviewer, confidence=1.0)
        .add_handler("claude_self_review", claude_self_reviewer, confidence=0.7)
        .add_handler("rule_validation", rule_validator, confidence=0.4)
    )
```

---

## 3. core/state_manager.py

```python
"""狀態管理 - 修剪、分層存儲、可追溯"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypedDict
import json
import hashlib
from datetime import datetime

class StateArchive(TypedDict):
    archive_id: str
    timestamp: str
    item_count: int
    summary: str

@dataclass
class StateManagerConfig:
    hot_data_limit: int = 5          # 記憶體中保留的輪數
    archive_dir: Path = Path(".gh_mcp_archives")
    enable_compression: bool = True
    max_errors_kept: int = 10

class StateManager:
    def __init__(self, config: StateManagerConfig = None):
        self.config = config or StateManagerConfig()
        self.config.archive_dir.mkdir(parents=True, exist_ok=True)
    
    def prune(self, state: dict) -> dict:
        """修剪狀態，分離冷熱數據"""
        pruned = {**state}
        
        # 1. Proposals: 保留最近 N 輪，其餘歸檔
        proposals = state.get("proposals", [])
        if len(proposals) > self.config.hot_data_limit:
            cold_proposals = proposals[:-self.config.hot_data_limit]
            hot_proposals = proposals[-self.config.hot_data_limit:]
            
            archive = self._archive(cold_proposals, "proposals")
            pruned["proposals"] = hot_proposals
            pruned["archived_proposals"] = state.get("archived_proposals", []) + [archive]
        
        # 2. Decisions: 壓縮為摘要
        decisions = state.get("decisions_made", [])
        if decisions:
            pruned["decisions_summary"] = self._summarize_decisions(decisions)
            pruned["decisions_made"] = []
        
        # 3. Errors: 去重並限制數量
        errors = state.get("errors", [])
        pruned["errors"] = self._dedupe_errors(errors)[-self.config.max_errors_kept:]
        
        # 4. 記錄修剪時間
        pruned["last_pruned"] = datetime.now().isoformat()
        
        return pruned
    
    def _archive(self, data: list, data_type: str) -> StateArchive:
        """歸檔冷數據到磁碟"""
        content = json.dumps(data, ensure_ascii=False, indent=2)
        archive_id = hashlib.sha256(content.encode()).hexdigest()[:12]
        
        archive_path = self.config.archive_dir / f"{data_type}_{archive_id}.json"
        archive_path.write_text(content, encoding="utf-8")
        
        return StateArchive(
            archive_id=archive_id,
            timestamp=datetime.now().isoformat(),
            item_count=len(data),
            summary=self._generate_summary(data, data_type)
        )
    
    def restore_archive(self, archive: StateArchive, data_type: str) -> list:
        """從磁碟恢復歸檔數據"""
        archive_path = self.config.archive_dir / f"{data_type}_{archive['archive_id']}.json"
        if archive_path.exists():
            return json.loads(archive_path.read_text(encoding="utf-8"))
        raise FileNotFoundError(f"Archive not found: {archive['archive_id']}")
    
    def _summarize_decisions(self, decisions: list[dict]) -> list[dict]:
        """壓縮決策記錄，保留關鍵信息"""
        return [
            {
                "question": d.get("question", "")[:100],
                "choice": d.get("choice"),
                "reasoning": d.get("reasoning", "")[:200],
                "timestamp": d.get("timestamp"),
            }
            for d in decisions
        ]
    
    def _dedupe_errors(self, errors: list) -> list:
        """錯誤去重"""
        seen = set()
        unique = []
        for e in errors:
            key = f"{e.get('component_id')}:{e.get('message')}"
            if key not in seen:
                seen.add(key)
                unique.append(e)
        return unique
    
    def _generate_summary(self, data: list, data_type: str) -> str:
        """生成歸檔摘要"""
        if data_type == "proposals":
            return f"包含 {len(data)} 個提案，涵蓋組件: {', '.join(set(p.get('component_type', 'unknown') for p in data[:5]))}"
        return f"{len(data)} items archived"
```

---

## 4. core/trust.py

```python
"""信任等級系統 - 含動態調整"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal
from collections import deque

class TrustLevel(str, Enum):
    NOVICE = "novice"        # 每步確認 + 詳細解釋
    STANDARD = "standard"    # 關鍵步驟確認
    EXPERT = "expert"        # 只在錯誤時暫停

@dataclass
class InteractionEvent:
    action: Literal["accept", "modify", "reject", "ask_help"]
    stage: str
    timestamp: str = ""

@dataclass 
class TrustConfig:
    initial_level: TrustLevel = TrustLevel.STANDARD
    history_window: int = 10
    upgrade_threshold: int = 5      # 連續 N 次接受 → 升級
    downgrade_threshold: float = 0.6  # 修改率超過 60% → 降級
    enable_auto_adjust: bool = True

class AdaptiveTrustSystem:
    """根據用戶行為動態調整信任等級"""
    
    def __init__(self, config: TrustConfig = None):
        self.config = config or TrustConfig()
        self.level = self.config.initial_level
        self.history: deque[InteractionEvent] = deque(maxlen=self.config.history_window)
        self._level_locked = False
    
    def record(self, event: InteractionEvent) -> TrustLevel:
        """記錄互動事件，可能觸發等級調整"""
        self.history.append(event)
        
        if self.config.enable_auto_adjust and not self._level_locked:
            self._maybe_adjust()
        
        return self.level
    
    def lock_level(self):
        """鎖定當前等級，不再自動調整"""
        self._level_locked = True
    
    def unlock_level(self):
        self._level_locked = False
    
    def set_level(self, level: TrustLevel):
        """手動設置等級"""
        self.level = level
    
    def should_pause(self, stage: str, has_errors: bool = False) -> bool:
        """判斷是否應該暫停等待確認"""
        if has_errors:
            return True  # 有錯誤時總是暫停
        
        critical_stages = {"decomposition", "execution", "final_review"}
        
        if self.level == TrustLevel.EXPERT:
            return False
        elif self.level == TrustLevel.STANDARD:
            return stage in critical_stages
        else:  # NOVICE
            return True
    
    def get_explanation_level(self) -> Literal["detailed", "normal", "minimal"]:
        """根據信任等級決定解釋詳細程度"""
        return {
            TrustLevel.NOVICE: "detailed",
            TrustLevel.STANDARD: "normal",
            TrustLevel.EXPERT: "minimal",
        }[self.level]
    
    def _maybe_adjust(self):
        """根據歷史記錄調整等級"""
        if len(self.history) < 5:
            return
        
        recent = list(self.history)[-self.config.history_window:]
        
        # 檢查是否應該升級
        accept_streak = 0
        for event in reversed(recent):
            if event.action == "accept":
                accept_streak += 1
            else:
                break
        
        if accept_streak >= self.config.upgrade_threshold:
            self._upgrade()
            return
        
        # 檢查是否應該降級
        modify_count = sum(1 for e in recent if e.action in ("modify", "ask_help"))
        modify_rate = modify_count / len(recent)
        
        if modify_rate >= self.config.downgrade_threshold:
            self._downgrade()
    
    def _upgrade(self):
        if self.level == TrustLevel.NOVICE:
            self.level = TrustLevel.STANDARD
        elif self.level == TrustLevel.STANDARD:
            self.level = TrustLevel.EXPERT
    
    def _downgrade(self):
        if self.level == TrustLevel.EXPERT:
            self.level = TrustLevel.STANDARD
        # NOVICE 不再降級，但可以記錄需要更多幫助
```

---

## 5. core/errors.py

```python
"""錯誤分類與處理系統"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

class ErrorSeverity(str, Enum):
    CRITICAL = "critical"    # 必須修復：連接錯誤、組件不存在
    WARNING = "warning"      # 建議修復：參數超出建議範圍
    INFO = "info"           # 可忽略：優化建議

class ErrorCategory(str, Enum):
    CONNECTION = "connection"        # 連接問題
    COMPONENT = "component"          # 組件問題
    PARAMETER = "parameter"          # 參數問題
    GEOMETRY = "geometry"            # 幾何問題
    PERFORMANCE = "performance"      # 性能問題

@dataclass
class GHError:
    severity: ErrorSeverity
    category: ErrorCategory
    component_id: str
    message: str
    auto_fixable: bool = False
    suggested_fix: str | None = None
    fix_confidence: float = 0.0      # 自動修復的信心度
    
    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "component_id": self.component_id,
            "message": self.message,
            "auto_fixable": self.auto_fixable,
            "suggested_fix": self.suggested_fix,
            "fix_confidence": self.fix_confidence,
        }

class ErrorAction(str, Enum):
    AUTO_FIX = "auto_fix"
    PAUSE_FOR_REVIEW = "pause_for_review"
    CONTINUE_WITH_LOG = "continue_with_log"
    ABORT = "abort"

@dataclass
class ErrorHandlingResult:
    action: ErrorAction
    errors_to_fix: list[GHError]
    errors_to_log: list[GHError]
    message: str

class ErrorHandler:
    """根據錯誤類型和信任等級決定處理方式"""
    
    def __init__(self, auto_fix_confidence_threshold: float = 0.8):
        self.confidence_threshold = auto_fix_confidence_threshold
    
    def handle(
        self,
        errors: list[GHError],
        trust_level: "TrustLevel"
    ) -> ErrorHandlingResult:
        """決定錯誤處理方式"""
        from .trust import TrustLevel
        
        critical = [e for e in errors if e.severity == ErrorSeverity.CRITICAL]
        warnings = [e for e in errors if e.severity == ErrorSeverity.WARNING]
        infos = [e for e in errors if e.severity == ErrorSeverity.INFO]
        
        # 可自動修復的嚴重錯誤
        auto_fixable_critical = [
            e for e in critical 
            if e.auto_fixable and e.fix_confidence >= self.confidence_threshold
        ]
        
        # 需要人工處理的嚴重錯誤
        manual_critical = [e for e in critical if e not in auto_fixable_critical]
        
        # 決策邏輯
        if manual_critical:
            # 有無法自動修復的嚴重錯誤 → 必須暫停
            return ErrorHandlingResult(
                action=ErrorAction.PAUSE_FOR_REVIEW,
                errors_to_fix=[],
                errors_to_log=errors,
                message=f"發現 {len(manual_critical)} 個需要人工處理的嚴重錯誤"
            )
        
        if auto_fixable_critical:
            if trust_level == TrustLevel.EXPERT:
                # 專家模式 + 全部可自動修復 → 直接修
                return ErrorHandlingResult(
                    action=ErrorAction.AUTO_FIX,
                    errors_to_fix=auto_fixable_critical,
                    errors_to_log=warnings + infos,
                    message=f"自動修復 {len(auto_fixable_critical)} 個錯誤"
                )
            else:
                # 非專家模式 → 詢問確認
                return ErrorHandlingResult(
                    action=ErrorAction.PAUSE_FOR_REVIEW,
                    errors_to_fix=auto_fixable_critical,
                    errors_to_log=warnings + infos,
                    message=f"發現 {len(auto_fixable_critical)} 個可自動修復的錯誤，是否執行？"
                )
        
        if warnings:
            # 只有警告 → 記錄但繼續
            return ErrorHandlingResult(
                action=ErrorAction.CONTINUE_WITH_LOG,
                errors_to_fix=[],
                errors_to_log=warnings + infos,
                message=f"發現 {len(warnings)} 個警告，已記錄"
            )
        
        # 只有 info → 繼續
        return ErrorHandlingResult(
            action=ErrorAction.CONTINUE_WITH_LOG,
            errors_to_fix=[],
            errors_to_log=infos,
            message="無嚴重問題"
        )

# 錯誤工廠函數
def connection_error(component_id: str, target_id: str, param: str) -> GHError:
    return GHError(
        severity=ErrorSeverity.CRITICAL,
        category=ErrorCategory.CONNECTION,
        component_id=component_id,
        message=f"無法連接到 {target_id} 的 {param} 參數",
        auto_fixable=True,
        suggested_fix=f"嘗試連接到 {target_id} 的替代參數",
        fix_confidence=0.7
    )

def missing_component_error(component_type: str) -> GHError:
    return GHError(
        severity=ErrorSeverity.CRITICAL,
        category=ErrorCategory.COMPONENT,
        component_id="unknown",
        message=f"組件類型 '{component_type}' 不存在",
        auto_fixable=False
    )

def parameter_warning(component_id: str, param: str, value: float, suggested: tuple) -> GHError:
    return GHError(
        severity=ErrorSeverity.WARNING,
        category=ErrorCategory.PARAMETER,
        component_id=component_id,
        message=f"參數 {param}={value} 超出建議範圍 {suggested}",
        auto_fixable=True,
        suggested_fix=f"調整為 {sum(suggested)/2}",
        fix_confidence=0.9
    )
```

---

## 6. core/dual_ai.py

```python
"""Claude + Gemini 雙 AI 協作系統"""

from dataclasses import dataclass
from typing import Any, Protocol
import json
import os

from .fallback import FallbackChain, FallbackResult, create_default_review_chain

class AIReviewer(Protocol):
    async def review(self, proposal: dict) -> dict: ...

@dataclass
class ReviewResult:
    score: float              # 0-100
    issues: list[str]
    suggestions: list[str]
    raw_response: dict

@dataclass
class DualAIResult:
    claude_proposal: dict
    review_result: ReviewResult
    fallback_info: FallbackResult
    consensus_score: float    # Claude 和 Gemini 的一致性
    final_recommendation: dict

class GeminiReviewer:
    """Gemini API 評審器"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client = None
    
    async def review(self, proposal: dict, context: str = "") -> ReviewResult:
        if not self._client:
            await self._init_client()
        
        prompt = self._build_review_prompt(proposal, context)
        response = await self._client.generate_content_async(prompt)
        
        return self._parse_response(response.text)
    
    async def _init_client(self):
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel('gemini-1.5-pro')
        except ImportError:
            raise ImportError("請安裝 google-generativeai: pip install google-generativeai")
    
    def _build_review_prompt(self, proposal: dict, context: str) -> str:
        return f"""作為 Grasshopper 參數化設計專家，評審以下設計提案：

背景：{context}

提案內容：
{json.dumps(proposal, ensure_ascii=False, indent=2)}

請評估：
1. 幾何邏輯正確性 (組件連接是否合理)
2. 參數化程度適當性 (哪些應該是參數、哪些應該固定)
3. 可擴展性 (是否容易修改和擴展)
4. 效能考量 (是否有不必要的複雜度)

請以 JSON 格式回覆：
{{
    "score": 0-100 的整數,
    "issues": ["問題1", "問題2", ...],
    "suggestions": ["建議1", "建議2", ...],
    "confidence": 0-1 的浮點數表示評審信心度
}}"""
    
    def _parse_response(self, text: str) -> ReviewResult:
        # 清理可能的 markdown 標記
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        
        try:
            data = json.loads(text)
            return ReviewResult(
                score=data.get("score", 50),
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                raw_response=data
            )
        except json.JSONDecodeError:
            # Fallback: 嘗試從文本提取信息
            return ReviewResult(
                score=50,
                issues=["無法解析 Gemini 回應"],
                suggestions=[],
                raw_response={"raw_text": text}
            )

class ClaudeSelfReviewer:
    """Claude 自我評審 (Fallback)"""
    
    async def review(self, proposal: dict, context: str = "") -> ReviewResult:
        # 這裡會透過 MCP 或直接 API 調用 Claude
        # 使用不同的 system prompt 來模擬「評審者」角色
        
        # Placeholder - 實際實現需要 Claude API
        return ReviewResult(
            score=70,
            issues=["(自我評審) 需要進一步驗證"],
            suggestions=["建議人工確認關鍵連接"],
            raw_response={"mode": "self_review"}
        )

class RuleBasedValidator:
    """純規則驗證 (最後 Fallback)"""
    
    RULES = {
        "has_output": lambda p: "outputs" in p and len(p["outputs"]) > 0,
        "has_connections": lambda p: "connections" in p and len(p["connections"]) > 0,
        "no_orphans": lambda p: True,  # 簡化：實際需要圖分析
    }
    
    async def review(self, proposal: dict, context: str = "") -> ReviewResult:
        issues = []
        passed = 0
        
        for rule_name, check in self.RULES.items():
            try:
                if check(proposal):
                    passed += 1
                else:
                    issues.append(f"規則 '{rule_name}' 未通過")
            except Exception as e:
                issues.append(f"規則 '{rule_name}' 檢查失敗: {e}")
        
        score = (passed / len(self.RULES)) * 100
        
        return ReviewResult(
            score=score,
            issues=issues,
            suggestions=["建議啟用 AI 評審以獲得更詳細的分析"],
            raw_response={"mode": "rule_based", "rules_passed": passed}
        )

class DualAIOptimizer:
    """整合 Claude 提案 + Gemini/Fallback 評審"""
    
    def __init__(self, gemini_api_key: str = None):
        self.gemini = GeminiReviewer(gemini_api_key)
        self.claude_fallback = ClaudeSelfReviewer()
        self.rule_validator = RuleBasedValidator()
        
        self.review_chain = create_default_review_chain(
            gemini_reviewer=self.gemini.review,
            claude_self_reviewer=self.claude_fallback.review,
            rule_validator=self.rule_validator.review
        )
    
    async def optimize(
        self,
        claude_proposal: dict,
        context: str = "",
        timeout: float = 30
    ) -> DualAIResult:
        """執行雙 AI 優化流程"""
        
        # 執行帶 Fallback 的評審
        fallback_result = await self.review_chain.execute(
            claude_proposal,
            context,
            timeout=timeout
        )
        
        review = fallback_result.result
        if review is None:
            review = ReviewResult(
                score=0,
                issues=["所有評審機制都失敗"],
                suggestions=["請檢查 API 配置"],
                raw_response={}
            )
        
        # 計算共識分數 (如果是降級模式，共識較低)
        consensus = self._calculate_consensus(
            claude_proposal,
            review,
            fallback_result.degradation_level
        )
        
        # 生成最終建議
        final = self._generate_recommendation(claude_proposal, review)
        
        return DualAIResult(
            claude_proposal=claude_proposal,
            review_result=review,
            fallback_info=fallback_result,
            consensus_score=consensus,
            final_recommendation=final
        )
    
    def _calculate_consensus(
        self,
        proposal: dict,
        review: ReviewResult,
        degradation_level: int
    ) -> float:
        """計算共識分數"""
        base_consensus = review.score / 100
        
        # 降級會降低共識信心
        degradation_penalty = degradation_level * 0.15
        
        return max(0, base_consensus - degradation_penalty)
    
    def _generate_recommendation(
        self,
        proposal: dict,
        review: ReviewResult
    ) -> dict:
        """根據評審結果生成最終建議"""
        if review.score >= 80:
            action = "accept"
            message = "提案品質良好，建議採納"
        elif review.score >= 60:
            action = "revise"
            message = f"提案需要修改: {', '.join(review.issues[:2])}"
        else:
            action = "reject"
            message = "提案品質不足，建議重新設計"
        
        return {
            "action": action,
            "message": message,
            "priority_fixes": review.issues[:3],
            "suggestions": review.suggestions[:3],
        }
```

---

## 7. core/__init__.py

```python
"""LangGraph Core Module - 核心系統組件"""

from .convergence import (
    ConvergenceConfig,
    ConvergenceChecker,
    ConvergenceResult,
    ConvergenceReason,
)
from .fallback import (
    FallbackChain,
    FallbackResult,
    DegradationLevel,
    create_default_review_chain,
)
from .state_manager import (
    StateManager,
    StateManagerConfig,
    StateArchive,
)
from .trust import (
    TrustLevel,
    TrustConfig,
    AdaptiveTrustSystem,
    InteractionEvent,
)
from .errors import (
    GHError,
    ErrorSeverity,
    ErrorCategory,
    ErrorAction,
    ErrorHandler,
    ErrorHandlingResult,
    connection_error,
    missing_component_error,
    parameter_warning,
)
from .dual_ai import (
    DualAIOptimizer,
    DualAIResult,
    GeminiReviewer,
    ReviewResult,
)

__all__ = [
    # Convergence
    "ConvergenceConfig",
    "ConvergenceChecker", 
    "ConvergenceResult",
    "ConvergenceReason",
    # Fallback
    "FallbackChain",
    "FallbackResult",
    "DegradationLevel",
    "create_default_review_chain",
    # State
    "StateManager",
    "StateManagerConfig",
    "StateArchive",
    # Trust
    "TrustLevel",
    "TrustConfig",
    "AdaptiveTrustSystem",
    "InteractionEvent",
    # Errors
    "GHError",
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorAction",
    "ErrorHandler",
    "ErrorHandlingResult",
    "connection_error",
    "missing_component_error",
    "parameter_warning",
    # Dual AI
    "DualAIOptimizer",
    "DualAIResult",
    "GeminiReviewer",
    "ReviewResult",
]
```

---

## 使用範例

```python
# optimization.py 整合範例
from langgraph.core import (
    DualAIOptimizer,
    ConvergenceChecker,
    ConvergenceConfig,
    StateManager,
    AdaptiveTrustSystem,
    ErrorHandler,
    TrustLevel,
)

async def optimize_parameters_node(state: dict) -> dict:
    # 初始化系統
    optimizer = DualAIOptimizer()
    convergence = ConvergenceChecker(ConvergenceConfig.for_complexity(state["complexity"]))
    state_mgr = StateManager()
    trust = AdaptiveTrustSystem()
    error_handler = ErrorHandler()
    
    # 1. Claude 提案 (假設已有)
    claude_proposal = state["current_proposal"]
    
    # 2. 雙 AI 評審
    result = await optimizer.optimize(claude_proposal, context=state["topic"])
    
    # 3. 錯誤處理
    if result.review_result.issues:
        errors = [...]  # 轉換為 GHError
        handling = error_handler.handle(errors, trust.level)
        if handling.action == ErrorAction.PAUSE_FOR_REVIEW:
            return {"awaiting_confirmation": True, "errors": errors}
    
    # 4. 檢查收斂
    state["convergence_scores"].append(result.consensus_score)
    state["quality_scores"].append(result.review_result.score / 100)
    
    conv_result = convergence.check(
        state["convergence_scores"],
        state["quality_scores"]
    )
    
    # 5. 狀態修剪
    state = state_mgr.prune(state)
    
    # 6. 返回結果
    if conv_result.converged:
        return {
            **state,
            "awaiting_confirmation": trust.should_pause("final_review"),
            "convergence_reason": conv_result.reason.value,
        }
    
    return {**state, "continue_optimization": True}
```
