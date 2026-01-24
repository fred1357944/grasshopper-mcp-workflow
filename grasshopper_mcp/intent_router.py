#!/usr/bin/env python3
"""
Intent Router - 意圖路由器
==========================

分析用戶請求，判斷信心度，選擇處理模式：
- Workflow Mode: 高信心度，有已知模式可循
- Meta-Agent Mode: 低信心度，需要探索或澄清

Usage:
    from grasshopper_mcp.intent_router import IntentRouter, ProcessingMode

    router = IntentRouter()
    result = router.route("做一個 WASP 離散聚集")

    if result.mode == ProcessingMode.WORKFLOW:
        # 走確定性管線
        workflow.run(result.intent)
    else:
        # 走 Meta-Agent 探索
        meta_agent.explore(result.intent, result.questions)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path
import json


class ProcessingMode(Enum):
    """處理模式"""
    WORKFLOW = "workflow"           # 確定性管線
    META_AGENT = "meta_agent"       # 彈性探索
    HYBRID = "hybrid"               # 混合模式


class IntentType(Enum):
    """意圖類型"""
    CREATE = "create"               # 創建新設計
    MODIFY = "modify"               # 修改現有設計
    ANALYZE = "analyze"             # 分析設計
    DEBUG = "debug"                 # 除錯
    EXPLORE = "explore"             # 探索/學習
    UNKNOWN = "unknown"             # 無法判斷


@dataclass
class RoutingResult:
    """路由結果"""
    mode: ProcessingMode
    intent_type: IntentType
    confidence: float               # 0.0 - 1.0

    # 解析出的資訊
    keywords: List[str] = field(default_factory=list)
    target_plugins: List[str] = field(default_factory=list)
    matched_patterns: List[str] = field(default_factory=list)

    # Meta-Agent 需要的資訊
    questions: List[str] = field(default_factory=list)
    suggested_tools: List[str] = field(default_factory=list)

    # 原始請求
    raw_request: str = ""

    def to_dict(self) -> Dict:
        return {
            'mode': self.mode.value,
            'intent_type': self.intent_type.value,
            'confidence': self.confidence,
            'keywords': self.keywords,
            'target_plugins': self.target_plugins,
            'matched_patterns': self.matched_patterns,
            'questions': self.questions,
            'suggested_tools': self.suggested_tools
        }


class IntentRouter:
    """
    意圖路由器

    根據用戶請求分析：
    1. 意圖類型（創建/修改/分析/除錯）
    2. 信心度（是否有已知模式）
    3. 處理模式（Workflow / Meta-Agent）
    """

    # ========== 知識庫 ==========

    # 插件關鍵字映射
    PLUGIN_KEYWORDS: Dict[str, List[str]] = {
        "Ladybug": ["日照", "太陽", "solar", "sun", "shading", "遮陽", "氣候", "climate", "EPW"],
        "Honeybee": ["能源", "energy", "模擬", "simulation", "房間", "room", "daylight", "日光"],
        "Karamba3D": ["結構", "structural", "beam", "樑", "力學", "FEA", "有限元"],
        "Kangaroo2": ["找形", "form finding", "physics", "物理", "張力", "tensile", "膜", "membrane"],
        "WASP": ["離散", "discrete", "聚集", "aggregation", "模組", "module", "wasp"],
        "Galapagos": ["優化", "optimization", "genetic", "基因", "演化", "evolve"],
        "Octopus": ["多目標", "multi-objective", "pareto", "octopus"],
        "Lunchbox": ["面板", "panel", "六角", "hex", "網格", "grid"],
        "Weaverbird": ["細分", "subdivision", "mesh", "網格處理"],
        "Pufferfish": ["變形", "morph", "漸變", "tween"],
        "Anemone": ["迴圈", "loop", "迭代", "iteration"],
        "Human UI": ["介面", "UI", "按鈕", "button", "滑桿"],
        "Metahopper": ["meta", "文檔", "document", "組件操作"],
    }

    # 意圖動詞映射
    INTENT_VERBS: Dict[IntentType, List[str]] = {
        IntentType.CREATE: ["做", "建", "創", "設計", "create", "make", "build", "design", "生成"],
        IntentType.MODIFY: ["改", "修", "加", "換", "modify", "change", "add", "replace", "調整", "更新"],
        IntentType.ANALYZE: ["分析", "檢查", "看", "analyze", "check", "inspect", "評估"],
        IntentType.DEBUG: ["錯", "問題", "修復", "debug", "fix", "error", "issue", "失敗", "不動"],
        IntentType.EXPLORE: ["怎麼", "如何", "什麼", "可以", "how", "what", "can", "學", "教"],
    }

    # 模式觸發條件
    CONFIDENCE_THRESHOLD = 0.6  # 低於此值觸發 Meta-Agent

    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化路由器

        Args:
            config_dir: 配置目錄，包含 connection_patterns.json
        """
        if config_dir is None:
            self.config_dir = Path("config")
        elif isinstance(config_dir, str):
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = config_dir
        self.patterns: Dict[str, Dict] = {}
        self._load_patterns()

    def _load_patterns(self):
        """載入連接模式"""
        patterns_path = self.config_dir / "connection_patterns.json"
        if patterns_path.exists():
            try:
                with open(patterns_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.patterns = data.get("patterns", {})
            except Exception as e:
                print(f"Warning: Failed to load patterns: {e}")

    def route(self, request: str) -> RoutingResult:
        """
        分析請求並路由

        Args:
            request: 用戶請求

        Returns:
            RoutingResult 包含路由決策
        """
        result = RoutingResult(
            mode=ProcessingMode.WORKFLOW,
            intent_type=IntentType.UNKNOWN,
            confidence=0.0,
            raw_request=request
        )

        # 1. 提取關鍵字和插件
        result.keywords = self._extract_keywords(request)
        result.target_plugins = self._identify_plugins(request)

        # 2. 判斷意圖類型
        result.intent_type = self._classify_intent(request)

        # 3. 匹配已知模式
        result.matched_patterns = self._match_patterns(request, result.target_plugins)

        # 4. 計算信心度
        result.confidence = self._calculate_confidence(result)

        # 5. 決定處理模式
        result.mode = self._decide_mode(result)

        # 6. 如果是 Meta-Agent，生成問題和工具建議
        if result.mode in [ProcessingMode.META_AGENT, ProcessingMode.HYBRID]:
            result.questions = self._generate_questions(result)
            result.suggested_tools = self._suggest_tools(result)

        return result

    def _extract_keywords(self, request: str) -> List[str]:
        """提取關鍵字"""
        keywords = []
        request_lower = request.lower()

        # 從所有插件關鍵字中匹配
        for plugin, kw_list in self.PLUGIN_KEYWORDS.items():
            for kw in kw_list:
                if kw.lower() in request_lower:
                    keywords.append(kw)

        return list(set(keywords))

    def _identify_plugins(self, request: str) -> List[str]:
        """識別目標插件"""
        plugins = []
        request_lower = request.lower()

        for plugin_name, keywords in self.PLUGIN_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in request_lower:
                    if plugin_name not in plugins:
                        plugins.append(plugin_name)
                    break

        return plugins

    def _classify_intent(self, request: str) -> IntentType:
        """分類意圖"""
        request_lower = request.lower()

        # 計算每種意圖的匹配分數
        scores = {}
        for intent_type, verbs in self.INTENT_VERBS.items():
            score = sum(1 for v in verbs if v in request_lower)
            scores[intent_type] = score

        # 選擇最高分的意圖
        if max(scores.values()) > 0:
            return max(scores.keys(), key=lambda k: scores[k])

        return IntentType.UNKNOWN

    def _match_patterns(self, request: str, plugins: List[str]) -> List[str]:
        """匹配已知連接模式"""
        matched = []
        request_lower = request.lower()

        for pattern_name, pattern_info in self.patterns.items():
            # 檢查插件匹配
            pattern_plugins = pattern_info.get("plugins", [])
            if any(p in plugins for p in pattern_plugins):
                matched.append(pattern_name)
                continue

            # 檢查關鍵字匹配
            keywords = pattern_info.get("keywords", [])
            if any(kw.lower() in request_lower for kw in keywords):
                matched.append(pattern_name)

        return matched

    def _calculate_confidence(self, result: RoutingResult) -> float:
        """
        計算信心度

        因素：
        - 是否識別出插件 (+0.3)
        - 是否匹配到模式 (+0.4)
        - 意圖是否明確 (+0.2)
        - 關鍵字數量 (+0.1)
        """
        confidence = 0.0

        # 插件識別
        if result.target_plugins:
            confidence += 0.3
            if len(result.target_plugins) == 1:
                confidence += 0.1  # 單一插件更確定

        # 模式匹配
        if result.matched_patterns:
            confidence += 0.4
            if len(result.matched_patterns) == 1:
                confidence += 0.1  # 唯一匹配更確定

        # 意圖明確
        if result.intent_type != IntentType.UNKNOWN:
            confidence += 0.2
            if result.intent_type == IntentType.CREATE:
                confidence += 0.05  # 創建意圖最常見

        # 關鍵字數量
        kw_bonus = min(len(result.keywords) * 0.05, 0.1)
        confidence += kw_bonus

        return min(confidence, 1.0)

    def _decide_mode(self, result: RoutingResult) -> ProcessingMode:
        """決定處理模式"""

        # 低信心度 → Meta-Agent
        if result.confidence < self.CONFIDENCE_THRESHOLD:
            return ProcessingMode.META_AGENT

        # 探索/除錯意圖 → Meta-Agent
        if result.intent_type in [IntentType.EXPLORE, IntentType.DEBUG]:
            return ProcessingMode.META_AGENT

        # 多個插件且無明確模式 → Hybrid
        if len(result.target_plugins) > 2 and not result.matched_patterns:
            return ProcessingMode.HYBRID

        # 其他情況 → Workflow
        return ProcessingMode.WORKFLOW

    def _generate_questions(self, result: RoutingResult) -> List[str]:
        """生成澄清問題"""
        questions = []

        # 沒有識別出插件
        if not result.target_plugins:
            questions.append("你想使用哪些 Grasshopper 插件？(例如: WASP, Ladybug, Karamba)")

        # 意圖不明
        if result.intent_type == IntentType.UNKNOWN:
            questions.append("你想要創建新設計、修改現有設計、還是分析/除錯？")

        # 多個模式匹配
        if len(result.matched_patterns) > 2:
            patterns_str = ", ".join(result.matched_patterns[:3])
            questions.append(f"找到多個可能的模式: {patterns_str}。你想用哪一個？")

        # 除錯意圖
        if result.intent_type == IntentType.DEBUG:
            questions.append("可以描述一下錯誤訊息或不正常的行為嗎？")

        # 修改意圖但沒有來源
        if result.intent_type == IntentType.MODIFY:
            questions.append("你有現有的 .ghx 檔案嗎？或者要從哪個範例開始修改？")

        # 限制問題數量（每次最多 2 個）
        return questions[:2]

    def _suggest_tools(self, result: RoutingResult) -> List[str]:
        """建議 Meta-Agent 工具"""
        tools = []

        # 沒有模式匹配 → 需要搜尋
        if not result.matched_patterns:
            tools.append("search_tool")

        # 探索意圖 → 需要搜尋
        if result.intent_type == IntentType.EXPLORE:
            tools.append("search_tool")

        # 除錯意圖 → 需要詢問
        if result.intent_type == IntentType.DEBUG:
            tools.append("ask_user")

        # 意圖不明 → 需要詢問
        if result.intent_type == IntentType.UNKNOWN:
            tools.append("ask_user")

        # 多插件組合 → 可能需要合成
        if len(result.target_plugins) > 2:
            tools.append("synthesize")

        return list(set(tools))


# ============================================================================
# 便捷函數
# ============================================================================

def create_router(config_dir: Optional[str] = None) -> IntentRouter:
    """創建路由器實例"""
    path = Path(config_dir) if config_dir else None
    return IntentRouter(config_dir=path)


def route_request(request: str, config_dir: Optional[str] = None) -> RoutingResult:
    """快速路由請求"""
    router = create_router(config_dir)
    return router.route(request)


# ============================================================================
# CLI
# ============================================================================

def main():
    """命令行測試"""
    import sys

    test_requests = [
        "做一個 WASP 離散聚集",
        "幫我分析這個日照設計",
        "這個 Karamba 結構有錯誤",
        "怎麼做一個參數化立面",
        "結合 Ladybug 日照和 WASP 聚集做一個設計",
        "幫我改一下這個設計，加上結構分析",
        "做個東西",
    ]

    if len(sys.argv) > 1:
        test_requests = [" ".join(sys.argv[1:])]

    router = IntentRouter()

    print("=" * 60)
    print("Intent Router 測試")
    print("=" * 60)

    for request in test_requests:
        print(f"\n請求: {request}")
        print("-" * 40)

        result = router.route(request)

        print(f"  模式: {result.mode.value}")
        print(f"  意圖: {result.intent_type.value}")
        print(f"  信心度: {result.confidence:.2f}")
        print(f"  插件: {result.target_plugins}")
        print(f"  模式匹配: {result.matched_patterns}")

        if result.questions:
            print(f"  問題: {result.questions}")
        if result.suggested_tools:
            print(f"  建議工具: {result.suggested_tools}")


if __name__ == "__main__":
    main()
