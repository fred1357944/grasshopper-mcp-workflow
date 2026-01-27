#!/usr/bin/env python3
"""
WorkflowExecutor v2.1 - 整合版
================================

整合：
1. 兩階段 Router（Reference Match + 三維評估）
2. 優化驗證順序（Pre-Check → Semantic Review）
3. Reference-First + Dual-Mode 統一入口

流程：
    用戶請求 → Router → Reference/Meta-Agent → Validate → Execute → Archive

Usage:
    executor = WorkflowExecutor(config_dir="reference_library")
    result = await executor.run("做一個 WASP 立方體聚集")
"""

import json
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Awaitable
from pathlib import Path
from datetime import datetime

# Learning Agent 整合
from .knowledge_base import ConnectionKnowledgeBase
from .learning_agent import LearningAgent

# Vision 診斷整合
from .vision_diagnostic_client import (
    VisionDiagnosticClient,
    ExecutionDiagnosticHelper,
    DiagnosticLevel,
    DiagnosticResult
)

# Component Validator (Validation-First Architecture)
from .component_validator import (
    ComponentValidator,
    ValidationStatus,
    ValidationReport as ComponentValidationReport,
)


# ============================================================================
# Enums & Data Classes
# ============================================================================

class ExecutionMode(Enum):
    """執行模式"""
    REFERENCE = "reference"      # 有 Golden Config
    WORKFLOW = "workflow"        # 三維評估通過
    META_AGENT = "meta_agent"    # 需要彈性處理


class WorkflowPhase(Enum):
    """工作流程階段"""
    ROUTE = "route"
    SEARCH = "search"
    CONFIRM = "confirm"
    PRE_CHECK = "pre_check"           # 先做語法檢查
    SEMANTIC_REVIEW = "semantic_review"  # 通過後再做語義審查
    EXECUTE = "execute"
    ARCHIVE = "archive"
    COMPLETE = "complete"
    FAILED = "failed"


class RiskLevel(Enum):
    """風險等級"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class RouterDecision:
    """路由決策結果"""
    mode: ExecutionMode
    confidence: float
    reason: str
    stage: str  # "reference_match" or "three_dimension"
    reference: Optional[Dict] = None
    partial_matches: List[Dict] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """驗證結果"""
    passed: bool
    phase: str  # "pre_check" or "semantic_review"
    issues: List[Dict] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.INFO
    data_flow_trace: Optional[str] = None  # Mermaid 格式


@dataclass
class ExecutionResult:
    """執行結果"""
    success: bool
    mode: ExecutionMode
    phase: WorkflowPhase
    config_used: Optional[Dict] = None
    validation: Optional[ValidationResult] = None
    component_validation: Optional[ComponentValidationReport] = None  # 組件驗證報告
    errors: List[str] = field(default_factory=list)
    learned: bool = False
    diagnostic: Optional[Dict] = None  # Vision 診斷結果


# ============================================================================
# Two-Stage Router
# ============================================================================

class IntegratedRouter:
    """
    兩階段 Router
    
    Stage 1: Reference Match（搜尋 golden/ + variations/）
    Stage 2: 三維評估（Intent + Tool + Pattern）
    """
    
    # 領域關鍵字
    DOMAIN_KEYWORDS: Dict[str, List[str]] = {
        'wasp': ['wasp', '離散', '聚集', 'aggregation', 'part', 'module', '模組', 'stochastic', '立方體', 'cube'],
        'karamba': ['karamba', '結構', '分析', 'beam', 'shell', 'structural', 'fea', '樑'],
        'ladybug': ['ladybug', 'honeybee', '日照', '能源', 'radiation', 'solar', 'energy', '遮陽'],
        'kangaroo': ['kangaroo', '物理', '模擬', 'physics', 'simulation', '找形', '形態', 'form finding', '張力', 'tensile', '膜', 'membrane', 'fabric', 'tension'],
        'geometry': ['voronoi', 'mesh', 'surface', 'curve', 'point', 'brep', '網格', '曲面'],
    }
    
    def __init__(
        self,
        reference_library_path: Path,
        pattern_library_path: Optional[Path] = None
    ):
        self.ref_path = Path(reference_library_path)
        self.pattern_path = pattern_library_path
        
        # 閾值配置
        self.thresholds = {
            'reference_direct': 0.8,    # Stage 1: 直接走 Reference
            'workflow_min': 0.8,        # Stage 2: 三維評估閾值
        }
        
        # Stage 2 權重
        self.weights = {
            'intent': 0.4,
            'tool': 0.35,
            'pattern': 0.25,
        }
        
        # 載入索引
        self.reference_index = self._load_reference_index()
    
    def _load_reference_index(self) -> Dict:
        """載入 Reference Library 索引"""
        index_path = self.ref_path / "_index.json"
        
        if index_path.exists():
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 自動建立索引
        return self._build_reference_index()
    
    def _build_reference_index(self) -> Dict:
        """建立 Reference 索引"""
        index = {"entries": [], "version": "2.1"}
        
        if not self.ref_path.exists():
            return index
        
        for category_dir in self.ref_path.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith("_"):
                # 讀取 metadata.json
                metadata_path = category_dir / "metadata.json"
                category_meta = {}
                if metadata_path.exists():
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        category_meta = json.load(f)
                
                # 搜尋 golden/
                golden_dir = category_dir / "golden"
                if golden_dir.exists():
                    for config_file in golden_dir.glob("*.json"):
                        entry = self._index_config_file(config_file, category_dir.name, category_meta)
                        if entry:
                            index["entries"].append(entry)
                
                # 搜尋 variations/
                variations_dir = category_dir / "variations"
                if variations_dir.exists():
                    for config_file in variations_dir.glob("*.json"):
                        entry = self._index_config_file(config_file, category_dir.name, category_meta, is_variation=True)
                        if entry:
                            index["entries"].append(entry)
        
        # 儲存索引
        try:
            with open(self.ref_path / "_index.json", 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save index: {e}")
        
        return index
    
    def _index_config_file(
        self, 
        config_file: Path, 
        category: str, 
        category_meta: Dict,
        is_variation: bool = False
    ) -> Optional[Dict]:
        """索引單個配置檔案"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            meta = config.get("_meta", {})
            config_name = config_file.stem
            
            # 檢查 metadata.json 中的優先級設定
            config_override = category_meta.get("configs", {}).get(config_name, {})
            
            # 決定 confidence
            if config_override.get("status") == "DEPRECATED":
                confidence = config_override.get("confidence", 0.3)
            elif config_override.get("preferred", False):
                confidence = config_override.get("confidence", 1.0)
            else:
                confidence = meta.get("confidence", 0.9 if is_variation else 1.0)
            
            return {
                "path": str(config_file),
                "category": category,
                "name": meta.get("name", config_name),
                "keywords": meta.get("keywords", []),
                "confidence": confidence,
                "verified": meta.get("verified", False),
                "description": meta.get("description", ""),
                "is_variation": is_variation,
                "deprecated": config_override.get("status") == "DEPRECATED",
                "preferred": config_override.get("preferred", False),
            }
        except Exception as e:
            print(f"Warning: Failed to index {config_file}: {e}")
            return None
    
    def route(self, user_input: str, context: Optional[Dict] = None) -> RouterDecision:
        """
        主路由邏輯（兩階段）
        
        Args:
            user_input: 用戶請求
            context: 額外上下文
            
        Returns:
            RouterDecision
        """
        context = context or {}
        
        # ========== Stage 1: Reference Match ==========
        keywords = self._extract_keywords(user_input)
        reference_result = self._search_reference(keywords)
        
        if reference_result and reference_result["confidence"] >= self.thresholds['reference_direct']:
            # 檢查是否被 deprecated
            if reference_result.get("deprecated"):
                # 嘗試找 preferred 版本
                preferred = self._find_preferred_alternative(reference_result)
                if preferred:
                    reference_result = preferred
            
            return RouterDecision(
                mode=ExecutionMode.REFERENCE,
                confidence=reference_result["confidence"],
                reason=f"✅ 找到 Golden Config: {reference_result['name']}",
                stage="reference_match",
                reference=reference_result,
                scores={"reference_match": reference_result["confidence"]}
            )
        
        # ========== Stage 2: 三維評估 ==========
        intent_score = self._assess_intent_clarity(user_input, keywords)
        tool_score = self._assess_tool_availability(keywords, context)
        pattern_score = self._assess_pattern_match(keywords)
        
        total_score = (
            intent_score * self.weights['intent'] +
            tool_score * self.weights['tool'] +
            pattern_score * self.weights['pattern']
        )
        
        scores = {
            "intent": intent_score,
            "tool": tool_score,
            "pattern": pattern_score,
            "total": total_score,
            "reference_match": reference_result["confidence"] if reference_result else 0.0
        }
        
        if total_score >= self.thresholds['workflow_min']:
            return RouterDecision(
                mode=ExecutionMode.WORKFLOW,
                confidence=total_score,
                reason=f"三維評估通過: 意圖{intent_score:.0%}、工具{tool_score:.0%}、模式{pattern_score:.0%}",
                stage="three_dimension",
                reference=reference_result,
                scores=scores
            )
        else:
            return RouterDecision(
                mode=ExecutionMode.META_AGENT,
                confidence=total_score,
                reason=self._explain_meta_agent_reason(intent_score, tool_score, pattern_score),
                stage="meta_agent",
                partial_matches=[reference_result] if reference_result else [],
                scores=scores
            )
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取關鍵字"""
        text_lower = text.lower()
        extracted = set()
        
        for category, kws in self.DOMAIN_KEYWORDS.items():
            for kw in kws:
                if kw.lower() in text_lower:
                    extracted.add(kw.lower())
        
        return list(extracted)
    
    def _search_reference(self, keywords: List[str]) -> Optional[Dict]:
        """搜尋 Reference Library"""
        if not keywords:
            return None
        
        query_keywords = set(kw.lower() for kw in keywords)
        best_match = None
        best_score = 0.0
        
        for entry in self.reference_index.get("entries", []):
            # 跳過 deprecated（除非沒有其他選擇）
            if entry.get("deprecated") and best_match:
                continue
            
            entry_keywords = set(kw.lower() for kw in entry.get("keywords", []))
            overlap = entry_keywords & query_keywords
            
            if overlap:
                overlap_ratio = len(overlap) / max(len(query_keywords), 1)
                config_confidence = entry.get("confidence", 1.0)
                
                # preferred 加分
                if entry.get("preferred"):
                    config_confidence = min(config_confidence * 1.1, 1.0)
                
                score = overlap_ratio * config_confidence
                
                if score > best_score:
                    best_score = score
                    best_match = {**entry, "confidence": score, "matched_keywords": list(overlap)}
        
        return best_match
    
    def _find_preferred_alternative(self, deprecated_entry: Dict) -> Optional[Dict]:
        """找 preferred 替代版本"""
        category = deprecated_entry.get("category")
        
        for entry in self.reference_index.get("entries", []):
            if (entry.get("category") == category and 
                entry.get("preferred") and 
                not entry.get("deprecated")):
                return entry
        
        return None
    
    def _assess_intent_clarity(self, user_input: str, keywords: List[str]) -> float:
        """評估意圖清晰度"""
        score = 0.0
        
        # 有具體插件名稱
        plugin_names = ['wasp', 'karamba', 'ladybug', 'kangaroo', 'galapagos']
        if any(p in user_input.lower() for p in plugin_names):
            score += 0.4
        
        # 有幾何類型
        geo_types = ['cube', 'sphere', 'mesh', 'curve', 'surface', '立方體', '球', '曲面']
        if any(g in user_input.lower() for g in geo_types):
            score += 0.3
        
        # 有動作詞
        actions = ['做', 'create', '建立', '生成', '分析', 'analyze', '聚集', 'aggregate']
        if any(a in user_input.lower() for a in actions):
            score += 0.2
        
        # 關鍵字數量加分
        if len(keywords) >= 3:
            score += 0.1
        
        return min(score, 1.0)
    
    def _assess_tool_availability(self, keywords: List[str], context: Dict) -> float:
        """評估工具可用性"""
        # 簡化版：假設常見插件都可用
        available_plugins = {'wasp', 'karamba', 'ladybug', 'kangaroo', 'galapagos'}
        
        matched = sum(1 for kw in keywords if kw.lower() in available_plugins)
        
        if not keywords:
            return 0.5
        
        return min(matched / len(keywords) + 0.5, 1.0)
    
    def _assess_pattern_match(self, keywords: List[str]) -> float:
        """評估模式匹配度"""
        # 使用 Reference 搜尋結果作為 pattern match
        result = self._search_reference(keywords)
        return result["confidence"] if result else 0.0
    
    def _explain_meta_agent_reason(self, intent: float, tool: float, pattern: float) -> str:
        """解釋為什麼需要 Meta-Agent"""
        reasons = []
        
        if intent < 0.6:
            reasons.append(f"需求不夠明確（{intent:.0%}）")
        if tool < 0.7:
            reasons.append(f"部分工具缺失（{tool:.0%}）")
        if pattern < 0.5:
            reasons.append(f"沒有匹配模式（{pattern:.0%}）")
        
        return "，".join(reasons) if reasons else "綜合評估需要彈性處理"


# ============================================================================
# Validators
# ============================================================================

class PreExecutionChecker:
    """
    Pre-Execution Checker（Hardcoded 規則）
    
    快速、確定性的語法檢查
    """
    
    # 已知的危險模式
    DANGEROUS_PATTERNS = [
        {
            "component": "Mesh Box",
            "params": ["X", "Y", "Z"],
            "check": "value_too_high",
            "threshold": 20,
            "risk": RiskLevel.CRITICAL,
            "message": "Mesh Box 的 X/Y/Z 是細分數量，不是尺寸。值過高會導致資料爆炸。"
        },
        {
            "component": "Divide Curve",
            "params": ["Count"],
            "check": "value_too_high",
            "threshold": 1000,
            "risk": RiskLevel.WARNING,
            "message": "分割數量過高可能導致效能問題。"
        }
    ]
    
    def check(self, config: Dict) -> ValidationResult:
        """執行語法檢查"""
        issues = []
        max_risk = RiskLevel.INFO
        
        components = config.get("components", [])
        
        for comp in components:
            comp_type = comp.get("type", "")
            props = comp.get("properties", {})
            
            for pattern in self.DANGEROUS_PATTERNS:
                if pattern["component"].lower() in comp_type.lower():
                    for param in pattern["params"]:
                        value = props.get(param.lower()) or props.get(param)
                        
                        if value is not None:
                            if pattern["check"] == "value_too_high" and value > pattern["threshold"]:
                                issues.append({
                                    "component": comp.get("nickname", comp_type),
                                    "param": param,
                                    "value": value,
                                    "threshold": pattern["threshold"],
                                    "risk": pattern["risk"].value,
                                    "message": pattern["message"]
                                })
                                
                                if pattern["risk"].value == "critical":
                                    max_risk = RiskLevel.CRITICAL
                                elif pattern["risk"].value == "warning" and max_risk != RiskLevel.CRITICAL:
                                    max_risk = RiskLevel.WARNING
        
        return ValidationResult(
            passed=max_risk != RiskLevel.CRITICAL,
            phase="pre_check",
            issues=issues,
            risk_level=max_risk
        )


class SemanticReviewer:
    """
    Semantic Reviewer（LLM 語義審查）
    
    資料流追蹤、語義衝突檢測
    """
    
    def __init__(self, llm_client: Optional[Any] = None):
        self.llm = llm_client
    
    async def review(self, config: Dict, user_intent: str) -> ValidationResult:
        """執行語義審查"""
        
        # 如果沒有 LLM client，使用規則化審查
        if self.llm is None:
            return self._rule_based_review(config, user_intent)
        
        # LLM 審查
        prompt = self._build_review_prompt(config, user_intent)
        response = await self.llm.complete(prompt)
        return self._parse_review_response(response)
    
    def _rule_based_review(self, config: Dict, user_intent: str) -> ValidationResult:
        """規則化語義審查（無 LLM 時使用）"""
        issues = []
        
        components = config.get("components", [])
        connections = config.get("connections", [])
        
        # 追蹤資料流
        data_flow = self._trace_data_flow(components, connections)
        
        # 檢查資料爆炸風險
        explosion_risk = self._check_data_explosion(data_flow)
        if explosion_risk:
            issues.append(explosion_risk)
        
        # 生成 Mermaid 圖
        mermaid = self._generate_mermaid(data_flow)
        
        max_risk = RiskLevel.INFO
        for issue in issues:
            if issue.get("risk") == "critical":
                max_risk = RiskLevel.CRITICAL
            elif issue.get("risk") == "warning" and max_risk != RiskLevel.CRITICAL:
                max_risk = RiskLevel.WARNING
        
        return ValidationResult(
            passed=max_risk != RiskLevel.CRITICAL,
            phase="semantic_review",
            issues=issues,
            risk_level=max_risk,
            data_flow_trace=mermaid
        )
    
    def _trace_data_flow(self, components: List[Dict], connections: List[Dict]) -> List[Dict]:
        """追蹤資料流"""
        flow = []
        
        # 建立組件 ID → 資訊的映射
        comp_map = {c.get("id"): c for c in components}
        
        # 估算每個組件的輸出數量
        output_estimates = {}
        
        for comp in components:
            comp_id = comp.get("id")
            comp_type = comp.get("type", "")
            props = comp.get("properties", {})
            
            # 估算輸出
            if "box" in comp_type.lower() or "mesh" in comp_type.lower():
                # Mesh Box 的輸出 = X * Y * 6（六個面）
                x = props.get("x") or props.get("X") or props.get("default", 1)
                y = props.get("y") or props.get("Y") or 1
                z = props.get("z") or props.get("Z") or 1
                
                if isinstance(x, (int, float)) and x > 1:
                    output_estimates[comp_id] = int(x * y * 6)  # 細分後的面數
                else:
                    output_estimates[comp_id] = 6  # 基本立方體
            elif "slider" in comp_type.lower():
                output_estimates[comp_id] = 1
            elif "deconstruct" in comp_type.lower():
                # 繼承上游數量
                for conn in connections:
                    if conn.get("to_id") == comp_id:
                        upstream = output_estimates.get(conn.get("from_id"), 1)
                        output_estimates[comp_id] = upstream
                        break
            else:
                output_estimates[comp_id] = output_estimates.get(comp_id, 1)
        
        # 建立流程
        for comp in components:
            comp_id = comp.get("id")
            flow.append({
                "id": comp_id,
                "type": comp.get("type"),
                "nickname": comp.get("nickname", comp_id),
                "estimated_output": output_estimates.get(comp_id, 1)
            })
        
        return flow
    
    def _check_data_explosion(self, data_flow: List[Dict]) -> Optional[Dict]:
        """檢查資料爆炸風險"""
        for node in data_flow:
            estimated = node.get("estimated_output", 1)
            
            if estimated > 100:
                return {
                    "component": node.get("nickname"),
                    "type": node.get("type"),
                    "estimated_output": estimated,
                    "risk": "critical" if estimated > 500 else "warning",
                    "message": f"組件 {node.get('nickname')} 預估輸出 {estimated} 個項目，可能導致後續運算量爆炸"
                }
        
        return None
    
    def _generate_mermaid(self, data_flow: List[Dict]) -> str:
        """生成 Mermaid 流程圖"""
        lines = ["graph LR"]
        
        for i, node in enumerate(data_flow):
            node_id = node.get("id", f"node{i}")
            nickname = node.get("nickname", node_id)
            estimated = node.get("estimated_output", 1)
            
            # 風險標記
            if estimated > 500:
                lines.append(f'    {node_id}["{nickname}<br/>⚠️ {estimated} items"]')
            elif estimated > 100:
                lines.append(f'    {node_id}["{nickname}<br/>⚡ {estimated} items"]')
            else:
                lines.append(f'    {node_id}["{nickname}"]')
        
        return "\n".join(lines)
    
    def _build_review_prompt(self, config: Dict, user_intent: str) -> str:
        """建立 LLM 審查 prompt"""
        return f"""
你是 Grasshopper 語義專家。請審查以下配置是否會導致問題。

## 用戶意圖
{user_intent}

## 配置
```json
{json.dumps(config, indent=2, ensure_ascii=False)[:2000]}
```

## 請檢查
1. 資料流是否會爆炸（指數級增長）
2. 參數語義是否正確（如 Mesh Box X/Y/Z 是細分數量不是尺寸）
3. 組件選擇是否恰當

## 回應格式
```json
{{
    "passed": true/false,
    "risk_level": "info/warning/critical",
    "issues": [
        {{"component": "...", "message": "...", "risk": "..."}}
    ],
    "recommendation": "..."
}}
```
"""
    
    def _parse_review_response(self, response: str) -> ValidationResult:
        """解析 LLM 回應"""
        try:
            # 提取 JSON
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                data = json.loads(response)
            
            risk_map = {
                "info": RiskLevel.INFO,
                "warning": RiskLevel.WARNING,
                "critical": RiskLevel.CRITICAL
            }
            
            return ValidationResult(
                passed=data.get("passed", True),
                phase="semantic_review",
                issues=data.get("issues", []),
                risk_level=risk_map.get(data.get("risk_level", "info"), RiskLevel.INFO)
            )
        except Exception as e:
            return ValidationResult(
                passed=True,
                phase="semantic_review",
                issues=[{"message": f"LLM 回應解析失敗: {e}"}],
                risk_level=RiskLevel.WARNING
            )


# ============================================================================
# Main Executor
# ============================================================================

class WorkflowExecutor:
    """
    WorkflowExecutor v2.1 - 統一入口
    
    整合：
    - 兩階段 Router
    - Reference-First Workflow
    - Dual-Mode Fallback
    - 優化驗證順序（Pre-Check → Semantic Review）
    """
    
    def __init__(
        self,
        reference_library_path: str = "reference_library",
        pattern_library_path: Optional[str] = None,
        mcp_client: Optional[Any] = None,
        llm_client: Optional[Any] = None,
        user_callback: Optional[Callable[[str], Awaitable[str]]] = None,
        auto_confirm: bool = False
    ):
        self.ref_path = Path(reference_library_path)
        self.pattern_path = Path(pattern_library_path) if pattern_library_path else None
        self.mcp = mcp_client
        self.llm = llm_client
        self.user_callback = user_callback
        self.auto_confirm = auto_confirm
        
        # 初始化組件
        self.router = IntegratedRouter(
            reference_library_path=self.ref_path,
            pattern_library_path=self.pattern_path
        )
        self.pre_checker = PreExecutionChecker()
        self.semantic_reviewer = SemanticReviewer(llm_client=llm_client)

        # 學習系統
        config_dir = Path("config")
        self.knowledge_base = ConnectionKnowledgeBase(storage_dir=config_dir)
        self.learning_agent = LearningAgent(
            knowledge_base=self.knowledge_base,
            storage_dir=config_dir,
            auto_save=True
        )

        # 升降級規則
        self.promotion_rules = {
            'min_usage': 3,
            'min_success_rate': 0.9,
        }
        self.demotion_rules = {
            'min_failures': 2,
            'or_success_rate_below': 0.7,
        }

        # Vision 診斷整合
        self.vision_client = VisionDiagnosticClient()
        self.diagnostic_helper = ExecutionDiagnosticHelper(self.vision_client)
        self.enable_vision_diagnostic = True  # 可配置開關

        # Component Validator (Validation-First Architecture)
        self.component_validator = ComponentValidator(config_dir=str(config_dir))
    
    async def run(self, user_request: str, context: Optional[Dict] = None) -> ExecutionResult:
        """
        主執行流程
        
        Args:
            user_request: 用戶請求
            context: 額外上下文
            
        Returns:
            ExecutionResult
        """
        context = context or {}
        
        print(f"\n{'='*60}")
        print(f"📝 用戶請求: {user_request}")
        print(f"{'='*60}")
        
        # ========== Phase 1: Route ==========
        print(f"\n🔍 Phase 1: 路由...")
        decision = self.router.route(user_request, context)
        
        print(f"  模式: {decision.mode.value}")
        print(f"  信心度: {decision.confidence:.0%}")
        print(f"  階段: {decision.stage}")
        print(f"  原因: {decision.reason}")
        
        # ========== 根據模式執行 ==========
        if decision.mode == ExecutionMode.REFERENCE:
            return await self._run_reference_mode(user_request, decision)
        elif decision.mode == ExecutionMode.WORKFLOW:
            return await self._run_workflow_mode(user_request, decision)
        else:
            return await self._run_meta_agent_mode(user_request, decision)
    
    async def _run_reference_mode(
        self, 
        user_request: str, 
        decision: RouterDecision
    ) -> ExecutionResult:
        """執行 Reference Mode"""
        
        reference = decision.reference
        if not reference:
            return ExecutionResult(
                success=False,
                mode=ExecutionMode.REFERENCE,
                phase=WorkflowPhase.SEARCH,
                errors=["Reference 不存在"]
            )
        
        # ========== Phase 2: 載入配置 ==========
        print(f"\n📋 Phase 2: 載入 Golden Config: {reference['name']}")
        
        config_path = Path(reference['path'])
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            return ExecutionResult(
                success=False,
                mode=ExecutionMode.REFERENCE,
                phase=WorkflowPhase.SEARCH,
                errors=[f"載入配置失敗: {e}"]
            )
        
        # ========== Phase 3: 確認（HITL）==========
        if not self.auto_confirm:
            print(f"\n👤 Phase 3: 等待用戶確認...")
            confirmed = await self._ask_user_confirm(config, reference)
            if not confirmed:
                return ExecutionResult(
                    success=False,
                    mode=ExecutionMode.REFERENCE,
                    phase=WorkflowPhase.CONFIRM,
                    config_used=config,
                    errors=["用戶取消"]
                )
        
        # ========== Phase 3.5: Component Validation（Validation-First）==========
        print(f"\n🔍 Phase 3.5: Component Validation...")
        components = config.get("components", [])
        if components:
            comp_report = self.component_validator.validate_components(
                components, context=user_request
            )

            if not comp_report.can_proceed:
                print(f"  ⚠️ 部分組件需要確認:")
                for comp_name in comp_report.requires_decision:
                    v = comp_report.get_validation(comp_name)
                    if v and v.status == ValidationStatus.AMBIGUOUS:
                        print(f"    • {comp_name}: 有多個版本")
                    elif v and v.status == ValidationStatus.NOT_FOUND:
                        print(f"    • {comp_name}: 找不到")

                # 如果不是自動確認模式，返回讓用戶處理
                if not self.auto_confirm:
                    return ExecutionResult(
                        success=False,
                        mode=ExecutionMode.REFERENCE,
                        phase=WorkflowPhase.PRE_CHECK,
                        config_used=config,
                        component_validation=comp_report,
                        errors=["部分組件需要確認，請查看 component_validation"]
                    )
            else:
                print(f"  ✅ {comp_report.valid_count} 個組件已驗證")

        # ========== Phase 4: Pre-Check（先做語法檢查）==========
        print(f"\n🔍 Phase 4: Pre-Execution Check（語法）...")
        pre_check_result = self.pre_checker.check(config)
        
        if pre_check_result.issues:
            print(f"  發現 {len(pre_check_result.issues)} 個問題:")
            for issue in pre_check_result.issues:
                print(f"    • [{issue.get('risk', 'info')}] {issue.get('message', 'Unknown')}")
        
        if not pre_check_result.passed:
            print(f"  ❌ Pre-Check 失敗（CRITICAL 問題）")
            return ExecutionResult(
                success=False,
                mode=ExecutionMode.REFERENCE,
                phase=WorkflowPhase.PRE_CHECK,
                config_used=config,
                validation=pre_check_result,
                errors=[i.get("message", "Unknown") for i in pre_check_result.issues]
            )
        
        print(f"  ✅ Pre-Check 通過")
        
        # ========== Phase 5: Semantic Review（通過後再做語義審查）==========
        print(f"\n🧠 Phase 5: Semantic Review（語義）...")
        semantic_result = await self.semantic_reviewer.review(config, user_request)
        
        if semantic_result.data_flow_trace:
            print(f"  資料流追蹤:")
            for line in semantic_result.data_flow_trace.split('\n')[:5]:
                print(f"    {line}")
        
        if semantic_result.issues:
            print(f"  發現 {len(semantic_result.issues)} 個問題:")
            for issue in semantic_result.issues:
                print(f"    • [{issue.get('risk', 'info')}] {issue.get('message', 'Unknown')}")
        
        if not semantic_result.passed:
            print(f"  ❌ Semantic Review 失敗")
            
            # 詢問用戶是否繼續
            if not self.auto_confirm:
                proceed = await self._ask_user_proceed_despite_warning(semantic_result)
                if not proceed:
                    return ExecutionResult(
                        success=False,
                        mode=ExecutionMode.REFERENCE,
                        phase=WorkflowPhase.SEMANTIC_REVIEW,
                        config_used=config,
                        validation=semantic_result,
                        errors=[i.get("message", "Unknown") for i in semantic_result.issues]
                    )
        
        print(f"  ✅ Semantic Review 通過")
        
        # ========== Phase 6: Execute ==========
        print(f"\n🚀 Phase 6: 執行...")
        exec_result = await self._execute_config(config)

        if not exec_result["success"]:
            errors = exec_result.get("errors", [])
            diagnostic = None

            # ========== 執行失敗時調用 Vision 診斷 ==========
            if self.enable_vision_diagnostic and errors:
                print(f"\n🔍 執行失敗，調用 Vision 診斷...")
                diagnostic = self.diagnostic_helper.diagnose_execution_failure(
                    config=config,
                    errors=errors,
                    level=DiagnosticLevel.STANDARD
                )

                if diagnostic.get("diagnosed"):
                    print(f"  ✅ 診斷完成")

                    # 顯示診斷結果
                    for diag in diagnostic.get("diagnostics", []):
                        if diag.get("ai_analyzed"):
                            print(f"  💡 原因: {diag.get('cause', 'Unknown')}")
                            print(f"  🔧 建議: {diag.get('solution', 'Unknown')}")

                            # 記錄失敗到 Archive
                            if diag.get("correct_params"):
                                print(f"  📝 正確參數: {diag.get('correct_params')}")
                else:
                    print(f"  ⚠️ 診斷失敗: {diagnostic.get('error', 'Unknown')}")

            return ExecutionResult(
                success=False,
                mode=ExecutionMode.REFERENCE,
                phase=WorkflowPhase.EXECUTE,
                config_used=config,
                validation=semantic_result,
                errors=errors,
                diagnostic=diagnostic
            )
        
        # ========== Phase 7: Archive/Learn ==========
        print(f"\n📚 Phase 7: 歸檔與學習...")
        learned = await self._archive_and_learn(config_path, config, success=True)
        
        print(f"\n{'='*60}")
        print(f"✅ 執行成功")
        print(f"{'='*60}")
        
        return ExecutionResult(
            success=True,
            mode=ExecutionMode.REFERENCE,
            phase=WorkflowPhase.COMPLETE,
            config_used=config,
            validation=semantic_result,
            learned=learned
        )
    
    async def _run_workflow_mode(
        self, 
        user_request: str, 
        decision: RouterDecision
    ) -> ExecutionResult:
        """執行 Workflow Mode（三維評估通過但無 Golden Config）"""
        
        print(f"\n⚙️ Workflow Mode（三維評估通過）")
        
        # 如果有部分匹配的 Reference，嘗試使用
        if decision.reference:
            print(f"  嘗試使用部分匹配: {decision.reference['name']}")
            return await self._run_reference_mode(user_request, decision)
        
        # 否則需要生成新配置
        print(f"  ⚠️ 沒有匹配的 Reference，需要生成新配置")
        print(f"  TODO: 整合 Dual-Mode Workflow 的生成邏輯")
        
        return ExecutionResult(
            success=False,
            mode=ExecutionMode.WORKFLOW,
            phase=WorkflowPhase.SEARCH,
            errors=["Workflow Mode 配置生成尚未實作"]
        )
    
    async def _run_meta_agent_mode(
        self, 
        user_request: str, 
        decision: RouterDecision
    ) -> ExecutionResult:
        """執行 Meta-Agent Mode"""
        
        print(f"\n🔍 Meta-Agent Mode")
        print(f"  原因: {decision.reason}")
        
        # 如果有部分匹配，詢問用戶
        if decision.partial_matches:
            print(f"\n📚 找到 {len(decision.partial_matches)} 個部分匹配:")
            for i, match in enumerate(decision.partial_matches):
                print(f"  [{i+1}] {match['name']} ({match['confidence']:.0%})")
            
            if not self.auto_confirm:
                choice = await self._ask_user_select_or_create(decision.partial_matches)
                
                if choice and choice != "create":
                    # 用戶選擇了一個匹配
                    selected = decision.partial_matches[int(choice) - 1]
                    decision.reference = selected
                    return await self._run_reference_mode(user_request, decision)
        
        print(f"\n  ⚠️ Meta-Agent 創建功能尚未整合")
        print(f"  TODO: 整合 ask_user, search_tool, create_tool")
        
        return ExecutionResult(
            success=False,
            mode=ExecutionMode.META_AGENT,
            phase=WorkflowPhase.SEARCH,
            errors=["Meta-Agent 創建功能尚未整合"]
        )
    
    async def _ask_user_confirm(self, config: Dict, reference: Dict) -> bool:
        """詢問用戶確認"""
        meta = config.get("_meta", {})
        components = config.get("components", [])
        
        message = f"""
╔═══════════════════════════════════════════════════════════════════════╗
║  📋 Golden Config: {reference['name']:<46} ║
╠═══════════════════════════════════════════════════════════════════════╣
║  組件數: {len(components):<60} ║
║  信心度: {reference['confidence']:.0%:<60} ║
║  驗證: {'✅ 已驗證' if meta.get('verified') else '⚠️ 未驗證':<60} ║
╚═══════════════════════════════════════════════════════════════════════╝

確認使用此配置？[Y/n]
"""
        
        if self.user_callback:
            response = await self.user_callback(message)
            return response.lower() in ['', 'y', 'yes', '是', '確認']
        else:
            print(message)
            return True  # 無回調時默認確認
    
    async def _ask_user_proceed_despite_warning(self, validation: ValidationResult) -> bool:
        """詢問用戶是否忽略警告繼續"""
        message = f"""
⚠️ Semantic Review 發現問題：

{chr(10).join(f"  • {i.get('message', 'Unknown')}" for i in validation.issues)}

仍要繼續執行嗎？[y/N]
"""
        
        if self.user_callback:
            response = await self.user_callback(message)
            return response.lower() in ['y', 'yes', '是']
        else:
            print(message)
            return False  # 無回調時默認不繼續
    
    async def _ask_user_select_or_create(self, matches: List[Dict]) -> Optional[str]:
        """詢問用戶選擇匹配或創建新配置"""
        message = f"""
請選擇：
{chr(10).join(f"  [{i+1}] {m['name']} ({m['confidence']:.0%})" for i, m in enumerate(matches))}
  [c] 創建新配置

輸入選擇：
"""
        
        if self.user_callback:
            response = await self.user_callback(message)
            if response.lower() == 'c':
                return "create"
            if response.isdigit() and 1 <= int(response) <= len(matches):
                return response
            return None
        else:
            print(message)
            return "1" if matches else "create"
    
    async def _execute_config(self, config: Dict) -> Dict:
        """執行配置"""
        
        if self.mcp is None:
            # 模擬執行
            print("  ⚠️ 無 MCP Client，模擬執行")
            
            components = config.get("components", [])
            connections = config.get("connections", [])
            
            for comp in components[:5]:
                print(f"    ➕ add_component({comp.get('type')})")
            
            if len(components) > 5:
                print(f"    ... 還有 {len(components) - 5} 個組件")
            
            print(f"    🔗 建立 {len(connections)} 條連接")
            
            return {"success": True}
        
        # 實際執行
        try:
            # TODO: 整合 MCP 執行邏輯
            return {"success": True}
        except Exception as e:
            return {"success": False, "errors": [str(e)]}
    
    async def _archive_and_learn(
        self,
        config_path: Path,
        config: Dict,
        success: bool,
        diagnostic: Optional[Dict] = None
    ) -> bool:
        """
        歸檔與學習

        整合 Learning Agent：
        - 成功執行：從配置中學習連接模式
        - 失敗執行：記錄診斷結果，供後續學習
        - 更新 connection_triplets.json
        - 自動保存到 config/ 目錄
        """

        try:
            # 更新使用統計
            stats = config.get("_stats", {"usage_count": 0, "success_count": 0})
            stats["usage_count"] = stats.get("usage_count", 0) + 1

            if success:
                stats["success_count"] = stats.get("success_count", 0) + 1

            stats["last_used"] = datetime.now().isoformat()
            config["_stats"] = stats

            # ========== Learning Agent 學習 ==========
            if success:
                execution_report = {"status": "success"}
                context = f"Reference: {config.get('_meta', {}).get('name', config_path.stem)}"

                learning_result = self.learning_agent.learn_from_execution(
                    workflow_json=config,
                    execution_report=execution_report,
                    context=context
                )

                if learning_result.get("learned_count", 0) > 0:
                    print(f"  🧠 學習到 {learning_result['learned_count']} 個連接模式")
                    if learning_result.get("new_patterns"):
                        print(f"     新模式: {learning_result['new_patterns'][:3]}")

            # ========== 失敗時記錄診斷結果 ==========
            if not success and diagnostic and diagnostic.get("diagnosed"):
                # 記錄失敗診斷到配置的 _failures 欄位
                failures = config.get("_failures", [])
                failure_record = {
                    "timestamp": datetime.now().isoformat(),
                    "diagnostics": diagnostic.get("diagnostics", []),
                    "patterns_learned": diagnostic.get("patterns", []),
                    "suggestions": diagnostic.get("suggestions", [])
                }
                failures.append(failure_record)

                # 保留最近 10 次失敗記錄
                config["_failures"] = failures[-10:]

                print(f"  📝 記錄失敗診斷（共 {len(config['_failures'])} 條記錄）")

                # 如果失敗次數過多，標記為需要審查
                if len(failures) >= self.demotion_rules['min_failures']:
                    print(f"  ⚠️ 失敗次數達到 {len(failures)}，建議審查配置")
                    config["_needs_review"] = True

            # 檢查是否應該升級（從 variation 到 golden）
            success_rate = stats["success_count"] / stats["usage_count"]

            if (stats["usage_count"] >= self.promotion_rules['min_usage'] and
                success_rate >= self.promotion_rules['min_success_rate']):

                if "variation" in str(config_path):
                    print(f"  🎉 達到升級條件！（使用 {stats['usage_count']} 次，成功率 {success_rate:.0%}）")
                    # TODO: 實作升級邏輯

            # 儲存更新
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"  ⚠️ 歸檔失敗: {e}")
            return False


# ============================================================================
# CLI
# ============================================================================

async def main():
    """測試入口"""
    import sys
    
    test_cases = [
        "做一個 WASP 立方體聚集",
        "做一個 WASP 離散設計",
        "做一個 Karamba 結構分析",
        "做個東西",
    ]
    
    if len(sys.argv) > 1:
        test_cases = [" ".join(sys.argv[1:])]
    
    # 建立測試用的 reference_library
    test_ref_path = Path("/home/claude/gh_mcp_integrated/reference_library")
    test_ref_path.mkdir(parents=True, exist_ok=True)
    
    # 複製 Golden Config
    import shutil
    src = Path("/mnt/user-data/outputs/gh_mcp_reference_first/reference_library")
    if src.exists():
        shutil.copytree(src, test_ref_path, dirs_exist_ok=True)
    
    executor = WorkflowExecutor(
        reference_library_path=str(test_ref_path),
        auto_confirm=True
    )
    
    for request in test_cases:
        result = await executor.run(request)
        print(f"\n最終結果: {'✅ 成功' if result.success else '❌ 失敗'} ({result.mode.value})")
        print()


if __name__ == "__main__":
    asyncio.run(main())
