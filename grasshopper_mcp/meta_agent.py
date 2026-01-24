#!/usr/bin/env python3
"""
Meta-Agent - 彈性探索代理
==========================

當 Workflow Mode 無法處理時，Meta-Agent 提供彈性探索能力：
- search_tool: 語義搜尋知識庫
- ask_user: 結構化提問
- synthesize: 合成新模式

Usage:
    from grasshopper_mcp.meta_agent import MetaAgent

    agent = MetaAgent(ghx_skill_db="course.db")

    # 搜尋
    results = await agent.search("日照分析 WASP")

    # 提問
    question = agent.ask_user(intent_type=IntentType.DEBUG)

    # 合成
    new_pattern = agent.synthesize(source_patterns=["Ladybug_Solar", "WASP_Aggregation"])
"""

import json
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    pass  # For future type hints


class ToolType(Enum):
    """工具類型"""
    SEARCH = "search_tool"
    ASK = "ask_user"
    SYNTHESIZE = "synthesize"
    CREATE_CONFIG = "create_agent_config"


@dataclass
class SearchResult:
    """搜尋結果"""
    source: str                     # 來源（ghx_skill, patterns, guids）
    item: str                       # 項目名稱
    score: float                    # 相關性分數
    details: Dict = field(default_factory=dict)


@dataclass
class Question:
    """結構化問題"""
    text: str
    category: str                   # clarify, confirm, debug, explore
    options: Optional[List[str]] = None
    required: bool = True
    follow_up: Optional[str] = None


@dataclass
class SynthesizedPattern:
    """合成的模式"""
    name: str
    description: str
    source_patterns: List[str]
    components: List[str]
    connections: List[Dict]
    confidence: float


class MetaAgent:
    """
    Meta-Agent - 彈性探索代理

    在 Workflow Mode 無法處理時提供：
    1. 語義搜尋 - 從 GHX Skill 和 Pattern Library 找相關資訊
    2. 結構化提問 - 根據情境生成精準問題
    3. 模式合成 - 從多個已知模式組合新模式
    """

    def __init__(
        self,
        ghx_skill_db: Optional[str] = None,
        config_dir: Optional[str] = None
    ):
        """
        初始化 Meta-Agent

        Args:
            ghx_skill_db: GHX Skill 資料庫路徑
            config_dir: 配置目錄
        """
        self.ghx_skill_db = Path(ghx_skill_db) if ghx_skill_db else None
        self.config_dir = Path(config_dir) if config_dir else Path("config")

        # 載入配置
        self.patterns: Dict = {}
        self.trusted_guids: Dict = {}
        self._load_configs()

        # GHX Skill (lazy load)
        self._ghx_skill = None

        # 對話歷史
        self.conversation: List[Dict] = []

    def _load_configs(self):
        """載入配置文件"""
        # 載入 patterns
        patterns_path = self.config_dir / "connection_patterns.json"
        if patterns_path.exists():
            with open(patterns_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.patterns = data.get("patterns", {})

        # 載入 trusted_guids
        guids_path = self.config_dir / "trusted_guids.json"
        if guids_path.exists():
            with open(guids_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.trusted_guids = data.get("components", {})

    @property
    def ghx_skill(self):
        """Lazy load GHX Skill"""
        if self._ghx_skill is None and self.ghx_skill_db:
            try:
                from ghx_skill.main import GHXSkill
                self._ghx_skill = GHXSkill(
                    str(self.ghx_skill_db),
                    use_semantic=True
                )
            except ImportError:
                pass  # GHX Skill 未安裝
        return self._ghx_skill

    # ========== search_tool ==========

    async def search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        語義搜尋知識庫

        Args:
            query: 搜尋查詢
            sources: 搜尋來源 ["ghx_skill", "patterns", "guids"]
            top_k: 返回數量

        Returns:
            搜尋結果列表
        """
        sources = sources or ["patterns", "guids", "ghx_skill"]
        results = []

        # 1. 搜尋 Patterns
        if "patterns" in sources:
            pattern_results = self._search_patterns(query)
            results.extend(pattern_results)

        # 2. 搜尋 Trusted GUIDs
        if "guids" in sources:
            guid_results = self._search_guids(query)
            results.extend(guid_results)

        # 3. 搜尋 GHX Skill（如果可用）
        if "ghx_skill" in sources and self.ghx_skill:
            try:
                ghx_results = await self._search_ghx_skill(query, top_k)
                results.extend(ghx_results)
            except Exception:
                pass

        # 按分數排序
        results.sort(key=lambda r: r.score, reverse=True)

        return results[:top_k]

    def _search_patterns(self, query: str) -> List[SearchResult]:
        """搜尋連接模式"""
        results = []
        query_lower = query.lower()

        for name, info in self.patterns.items():
            score = 0.0

            # 名稱匹配
            if query_lower in name.lower():
                score += 0.5

            # 關鍵字匹配
            keywords = info.get("keywords", [])
            for kw in keywords:
                if kw.lower() in query_lower or query_lower in kw.lower():
                    score += 0.3

            # 描述匹配
            description = info.get("description", "")
            if query_lower in description.lower():
                score += 0.2

            # 插件匹配
            plugins = info.get("plugins", [])
            for plugin in plugins:
                if plugin.lower() in query_lower:
                    score += 0.4

            if score > 0:
                results.append(SearchResult(
                    source="patterns",
                    item=name,
                    score=min(score, 1.0),
                    details={
                        "description": description,
                        "plugins": plugins,
                        "components": info.get("components", [])
                    }
                ))

        return results

    def _search_guids(self, query: str) -> List[SearchResult]:
        """搜尋組件 GUID"""
        results = []
        query_lower = query.lower()

        for name, info in self.trusted_guids.items():
            score = 0.0

            # 名稱匹配
            if query_lower in name.lower():
                score += 0.6

            # 類別匹配
            category = info.get("category", "")
            if query_lower in category.lower():
                score += 0.3

            # 別名匹配
            aliases = info.get("aliases", [])
            for alias in aliases:
                if query_lower in alias.lower():
                    score += 0.4

            if score > 0:
                results.append(SearchResult(
                    source="guids",
                    item=name,
                    score=min(score, 1.0),
                    details={
                        "guid": info.get("guid"),
                        "category": category,
                        "inputs": info.get("inputs", []),
                        "outputs": info.get("outputs", [])
                    }
                ))

        return results

    async def _search_ghx_skill(self, query: str, top_k: int) -> List[SearchResult]:
        """搜尋 GHX Skill 資料庫"""
        if not self.ghx_skill:
            return []

        try:
            ghx_results = self.ghx_skill.search_semantic(query, top_k=top_k)

            return [
                SearchResult(
                    source="ghx_skill",
                    item=r.get("filename", r.get("filepath", "")),
                    score=r.get("similarity", 0.5),
                    details={
                        "components": r.get("components", []),
                        "plugins": r.get("plugins", []),
                        "complexity": r.get("complexity_score", 0)
                    }
                )
                for r in ghx_results
            ]
        except Exception:
            return []

    # ========== ask_user ==========

    def ask_user(
        self,
        intent_type: Optional[str] = None,
        context: Optional[Dict] = None,
        previous_answers: Optional[List[str]] = None
    ) -> Question:
        """
        生成結構化問題

        Args:
            intent_type: 意圖類型
            context: 上下文資訊
            previous_answers: 之前的回答

        Returns:
            結構化問題
        """
        context = context or {}
        previous_answers = previous_answers or []

        # 根據意圖類型生成問題
        if intent_type == "unknown":
            return Question(
                text="你想要做什麼？",
                category="clarify",
                options=[
                    "創建新的 Grasshopper 設計",
                    "修改現有的設計",
                    "分析或除錯設計",
                    "學習如何使用某個功能"
                ]
            )

        elif intent_type == "create":
            # 檢查是否已知插件
            if not context.get("target_plugins"):
                return Question(
                    text="你想使用哪些 Grasshopper 插件？",
                    category="clarify",
                    options=[
                        "WASP (離散聚集)",
                        "Ladybug/Honeybee (環境分析)",
                        "Karamba (結構分析)",
                        "Kangaroo (找形)",
                        "其他 (請說明)"
                    ]
                )

            # 檢查是否有參考
            if not context.get("reference"):
                return Question(
                    text="你有參考範例嗎？",
                    category="clarify",
                    options=[
                        "有，我會上傳 .ghx 檔案",
                        "沒有，從頭開始",
                        "想參考課程範例"
                    ],
                    required=False
                )

        elif intent_type == "debug":
            return Question(
                text="可以描述一下遇到的問題嗎？",
                category="debug",
                follow_up="請提供錯誤訊息或不正常的行為描述"
            )

        elif intent_type == "modify":
            return Question(
                text="你想修改什麼？",
                category="clarify",
                options=[
                    "加入新的功能/插件",
                    "改變參數或數值",
                    "優化現有流程",
                    "修復錯誤"
                ]
            )

        elif intent_type == "explore":
            return Question(
                text="你想學習什麼？",
                category="explore",
                options=[
                    "特定插件的使用方法",
                    "如何達成某個設計效果",
                    "最佳實踐和技巧",
                    "錯誤排除方法"
                ]
            )

        # 預設問題
        return Question(
            text="可以提供更多細節嗎？",
            category="clarify"
        )

    def process_answer(self, question: Question, answer: str) -> Dict:
        """
        處理用戶回答

        Args:
            question: 問題
            answer: 用戶回答

        Returns:
            解析後的資訊
        """
        # 記錄對話
        self.conversation.append({
            "question": question.text,
            "answer": answer,
            "category": question.category
        })

        # 解析回答
        result = {
            "category": question.category,
            "raw_answer": answer
        }

        # 如果有選項，匹配選項
        if question.options:
            for i, opt in enumerate(question.options):
                if answer.strip() == str(i + 1) or answer.lower() in opt.lower():
                    result["selected_option"] = i
                    result["selected_text"] = opt
                    break

        return result

    # ========== synthesize ==========

    def synthesize(
        self,
        source_patterns: List[str],
        connection_strategy: str = "sequential"
    ) -> Optional[SynthesizedPattern]:
        """
        合成新模式

        Args:
            source_patterns: 來源模式名稱
            connection_strategy: 連接策略 (sequential, parallel, custom)

        Returns:
            合成的模式
        """
        # 收集來源模式資訊
        sources = []
        for name in source_patterns:
            if name in self.patterns:
                sources.append({
                    "name": name,
                    "info": self.patterns[name]
                })

        if len(sources) < 2:
            return None

        # 合併組件
        all_components = []
        all_plugins = []
        for src in sources:
            all_components.extend(src["info"].get("components", []))
            all_plugins.extend(src["info"].get("plugins", []))

        # 去重
        all_components = list(dict.fromkeys(all_components))
        all_plugins = list(dict.fromkeys(all_plugins))

        # 合併連接
        all_connections = []
        for src in sources:
            wiring = src["info"].get("wiring", [])
            all_connections.extend(wiring)

        # 找連接點（如果是 sequential）
        if connection_strategy == "sequential":
            bridge_connections = self._find_bridge_connections(sources)
            all_connections.extend(bridge_connections)

        # 生成名稱
        pattern_names = [s["name"] for s in sources]
        new_name = "_".join([n.split("_")[0] for n in pattern_names]) + "_Combined"

        # 計算信心度
        confidence = 0.7 if connection_strategy == "sequential" else 0.5

        return SynthesizedPattern(
            name=new_name,
            description=f"合成自: {', '.join(pattern_names)}",
            source_patterns=pattern_names,
            components=all_components,
            connections=all_connections,
            confidence=confidence
        )

    def _find_bridge_connections(self, sources: List[Dict]) -> List[Dict]:
        """找出模式間的橋接連接"""
        bridges = []

        # 簡單策略：找第一個模式的輸出 → 第二個模式的輸入
        if len(sources) >= 2:
            src1 = sources[0]["info"]
            src2 = sources[1]["info"]

            # 假設最後一個組件的輸出 → 第一個組件的輸入
            comps1 = src1.get("components", [])
            comps2 = src2.get("components", [])

            if comps1 and comps2:
                bridges.append({
                    "from": comps1[-1],
                    "to": comps2[0],
                    "fromParam": 0,
                    "toParam": 0,
                    "note": "bridge_connection"
                })

        return bridges

    # ========== 主要入口 ==========

    async def explore(
        self,
        request: str,
        routing_result: Optional[Dict] = None
    ) -> Dict:
        """
        探索模式 - Meta-Agent 主入口

        Args:
            request: 用戶請求
            routing_result: Router 的分析結果

        Returns:
            探索結果
        """
        result = {
            "status": "exploring",
            "steps": [],
            "recommendations": [],
            "questions": [],
            "synthesized_pattern": None
        }

        routing = routing_result or {}

        # Step 1: 搜尋相關資訊
        result["steps"].append("搜尋知識庫...")
        search_results = await self.search(request)

        if search_results:
            result["steps"].append(f"找到 {len(search_results)} 個相關結果")
            result["recommendations"] = [
                {
                    "source": r.source,
                    "item": r.item,
                    "score": r.score,
                    "details": r.details
                }
                for r in search_results[:3]
            ]

        # Step 2: 如果有多個匹配，嘗試合成
        matched_patterns = routing.get("matched_patterns", [])
        if len(matched_patterns) >= 2:
            result["steps"].append("嘗試合成新模式...")
            synthesized = self.synthesize(matched_patterns[:2])
            if synthesized:
                result["synthesized_pattern"] = {
                    "name": synthesized.name,
                    "description": synthesized.description,
                    "components": synthesized.components,
                    "confidence": synthesized.confidence
                }

        # Step 3: 生成澄清問題
        intent_type = routing.get("intent_type", "unknown")
        question = self.ask_user(
            intent_type=intent_type,
            context={
                "target_plugins": routing.get("target_plugins", []),
                "search_results": len(search_results)
            }
        )
        result["questions"].append({
            "text": question.text,
            "options": question.options,
            "category": question.category
        })

        result["status"] = "awaiting_input"
        return result


# ============================================================================
# 便捷函數
# ============================================================================

def create_meta_agent(
    ghx_skill_db: Optional[str] = None,
    config_dir: Optional[str] = None
) -> MetaAgent:
    """創建 Meta-Agent 實例"""
    return MetaAgent(ghx_skill_db=ghx_skill_db, config_dir=config_dir)


# ============================================================================
# CLI
# ============================================================================

async def main():
    """命令行測試"""
    agent = MetaAgent()

    print("=" * 60)
    print("Meta-Agent 測試")
    print("=" * 60)

    # 測試搜尋
    print("\n【搜尋測試】")
    results = await agent.search("日照分析 WASP")
    for r in results:
        print(f"  [{r.source}] {r.item} (score: {r.score:.2f})")

    # 測試提問
    print("\n【提問測試】")
    question = agent.ask_user(intent_type="create", context={})
    print(f"  問題: {question.text}")
    if question.options:
        for i, opt in enumerate(question.options):
            print(f"    {i+1}. {opt}")

    # 測試合成
    print("\n【合成測試】")
    synthesized = agent.synthesize(["Ladybug_Solar", "WASP_Aggregation"])
    if synthesized:
        print(f"  名稱: {synthesized.name}")
        print(f"  組件: {synthesized.components[:5]}...")
        print(f"  信心度: {synthesized.confidence}")

    # 測試完整探索
    print("\n【完整探索測試】")
    explore_result = await agent.explore(
        "做一個結合日照分析和 WASP 聚集的設計",
        routing_result={
            "intent_type": "create",
            "target_plugins": ["Ladybug", "WASP"],
            "matched_patterns": ["Ladybug_Solar", "WASP_Aggregation"]
        }
    )
    print(f"  狀態: {explore_result['status']}")
    print(f"  步驟: {explore_result['steps']}")
    if explore_result['synthesized_pattern']:
        print(f"  合成模式: {explore_result['synthesized_pattern']['name']}")


if __name__ == "__main__":
    asyncio.run(main())
