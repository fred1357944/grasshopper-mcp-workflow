#!/usr/bin/env python3
"""
HITL Collaborator - 人機協作互動
================================

功能：
1. AskUserQuestion - 詢問用戶（利用用戶專業）
2. Web Search - 按需搜尋（遇到未知再查）
3. Confirm - 確認操作
4. Knowledge Collection - 收集並結構化用戶提供的知識

設計原則：
- 利用用戶專業知識，而非試圖取代
- 按需搜尋，而非預建龐大知識庫
- 結構化收集，便於後續學習
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Awaitable, Union


class QuestionType(Enum):
    """問題類型"""
    CONFIRM = "confirm"                  # 確認 (Yes/No)
    SELECT = "select"                    # 選擇 (從選項中選)
    INPUT = "input"                      # 輸入 (自由文字)
    KNOWLEDGE = "knowledge"              # 知識收集 (結構化)
    SEARCH_OR_INPUT = "search_or_input"  # 輸入或搜尋


@dataclass
class Question:
    """問題定義"""
    question_type: QuestionType
    prompt: str
    options: List[str] = field(default_factory=list)
    default: Optional[str] = None
    context: str = ""                    # 相關上下文
    knowledge_key: Optional[str] = None  # 知識鍵（用於結構化儲存）


@dataclass
class Answer:
    """回答"""
    value: str
    source: str = "user_input"           # user_input, selection, web_search
    confidence: float = 1.0
    raw_response: str = ""


@dataclass
class CollectedKnowledge:
    """收集的知識"""
    key: str
    value: str
    source: str
    context: str = ""


class HITLCollaborator:
    """
    人機協作器

    支援兩種模式：
    1. 同步模式 - 使用回調函數（適合 CLI）
    2. 異步模式 - 返回問題，等待外部回答（適合 Web/API）
    """

    def __init__(
        self,
        user_callback: Optional[Callable[[str], Awaitable[str]]] = None,
        web_search_callback: Optional[Callable[[str], Awaitable[str]]] = None,
        auto_mode: bool = False
    ):
        """
        Args:
            user_callback: 用戶互動回調（async）
            web_search_callback: 網頁搜尋回調（async）
            auto_mode: 自動模式（使用預設值，不詢問）
        """
        self.user_callback = user_callback
        self.web_search_callback = web_search_callback
        self.auto_mode = auto_mode

        # 收集的知識
        self.collected_knowledge: List[CollectedKnowledge] = []

        # 對話歷史（用於上下文）
        self.conversation_history: List[Dict] = []

    # =========================================================================
    # 核心 API
    # =========================================================================

    async def ask(
        self,
        prompt: str,
        question_type: QuestionType = QuestionType.INPUT,
        options: Optional[List[str]] = None,
        default: Optional[str] = None,
        knowledge_key: Optional[str] = None,
        context: str = ""
    ) -> Answer:
        """
        詢問用戶

        Args:
            prompt: 問題提示
            question_type: 問題類型
            options: 選項（SELECT 類型）
            default: 預設值
            knowledge_key: 知識鍵（如果需要結構化儲存）
            context: 相關上下文

        Returns:
            Answer
        """
        question = Question(
            question_type=question_type,
            prompt=prompt,
            options=options or [],
            default=default,
            context=context,
            knowledge_key=knowledge_key
        )

        # 自動模式
        if self.auto_mode:
            return self._auto_answer(question)

        # 格式化提示
        formatted_prompt = self._format_prompt(question)

        # 獲取回答
        if self.user_callback:
            raw_response = await self.user_callback(formatted_prompt)
        else:
            # 無回調，使用預設或拋出
            if default is not None:
                return Answer(value=default, source="default")
            raise RuntimeError("No user callback configured and no default value")

        # 處理回答
        answer = self._process_response(raw_response, question)

        # 記錄對話
        self.conversation_history.append({
            "role": "assistant",
            "content": formatted_prompt
        })
        self.conversation_history.append({
            "role": "user",
            "content": raw_response
        })

        # 如果是知識收集，結構化儲存
        if knowledge_key:
            self.collected_knowledge.append(CollectedKnowledge(
                key=knowledge_key,
                value=answer.value,
                source=answer.source,
                context=context
            ))

        return answer

    async def confirm(
        self,
        prompt: str,
        default: bool = True
    ) -> bool:
        """
        確認操作

        Args:
            prompt: 確認提示
            default: 預設值

        Returns:
            bool
        """
        answer = await self.ask(
            prompt=prompt,
            question_type=QuestionType.CONFIRM,
            default="y" if default else "n"
        )

        return answer.value.lower() in ['y', 'yes', '是', '確認', 'true', '1', '']

    async def select(
        self,
        prompt: str,
        options: List[str],
        allow_other: bool = True,
        default: Optional[int] = None
    ) -> Answer:
        """
        選擇（從選項中選）

        Args:
            prompt: 選擇提示
            options: 選項列表
            allow_other: 允許輸入其他
            default: 預設選項索引

        Returns:
            Answer
        """
        if allow_other:
            options = list(options) + ["其他（請輸入）"]

        default_value = str(default + 1) if default is not None else None

        return await self.ask(
            prompt=prompt,
            question_type=QuestionType.SELECT,
            options=options,
            default=default_value
        )

    async def collect_knowledge(
        self,
        topic: str,
        context: str = "",
        existing_knowledge: Optional[str] = None,
        allow_search: bool = True
    ) -> CollectedKnowledge:
        """
        收集領域知識

        Args:
            topic: 知識主題
            context: 相關上下文
            existing_knowledge: 已有的相關知識
            allow_search: 允許搜尋

        Returns:
            CollectedKnowledge
        """
        # 構建提示
        if existing_knowledge:
            prompt = (
                f"關於「{topic}」，之前的案例使用：\n"
                f"  {existing_knowledge}\n\n"
                f"這次也適用嗎？或需要調整？"
            )
        else:
            if allow_search:
                prompt = (
                    f"關於「{topic}」，請提供相關資訊或規範。\n"
                    f"（您也可以輸入 'search: 關鍵字' 讓我幫您搜尋）"
                )
            else:
                prompt = f"關於「{topic}」，請提供相關資訊或規範。"

        answer = await self.ask(
            prompt=prompt,
            question_type=QuestionType.SEARCH_OR_INPUT,
            knowledge_key=self._normalize_key(topic),
            context=context
        )

        # 處理搜尋請求
        if answer.value.lower().startswith("search:") and allow_search:
            search_query = answer.value[7:].strip()
            search_result = await self._web_search(search_query)

            # 讓用戶確認搜尋結果
            confirm_answer = await self.ask(
                prompt=f"搜尋結果：\n{search_result}\n\n請確認要使用的資訊（可以調整）：",
                question_type=QuestionType.INPUT,
                knowledge_key=self._normalize_key(topic),
                context=f"search_query: {search_query}"
            )

            return CollectedKnowledge(
                key=self._normalize_key(topic),
                value=confirm_answer.value,
                source="web_search",
                context=context
            )

        return CollectedKnowledge(
            key=self._normalize_key(topic),
            value=answer.value,
            source=answer.source,
            context=context
        )

    # =========================================================================
    # 協作式設計流程
    # =========================================================================

    async def collaborate_on_unclear_points(
        self,
        unclear_points: List[str],
        existing_knowledge: Optional[Dict[str, str]] = None
    ) -> Dict[str, CollectedKnowledge]:
        """
        協作式處理不明確的點

        Args:
            unclear_points: 需要澄清的點列表
            existing_knowledge: 已有的相關知識

        Returns:
            Dict[point, CollectedKnowledge]
        """
        existing_knowledge = existing_knowledge or {}
        results = {}

        for point in unclear_points:
            existing = existing_knowledge.get(point)

            knowledge = await self.collect_knowledge(
                topic=point,
                existing_knowledge=existing,
                allow_search=True
            )

            results[point] = knowledge

        return results

    async def confirm_workflow(
        self,
        workflow_description: str,
        patterns_used: List[str],
        estimated_components: int,
        user_inputs_needed: List[str]
    ) -> bool:
        """
        確認工作流程

        Args:
            workflow_description: 工作流程描述
            patterns_used: 使用的模式
            estimated_components: 預估組件數
            user_inputs_needed: 需要用戶提供的輸入

        Returns:
            bool
        """
        prompt = f"""
╔═══════════════════════════════════════════════════════════════════════╗
║  📋 工作流程確認                                                       ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  描述: {workflow_description:<57} ║
║                                                                       ║
║  使用模式:                                                            ║
{self._format_list(patterns_used, indent=4, max_width=60)}
║                                                                       ║
║  預估組件數: {estimated_components:<50} ║
║                                                                       ║
║  需要您提供:                                                          ║
{self._format_list(user_inputs_needed, indent=4, max_width=60)}
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝

確認執行此工作流程？[Y/n]
"""
        return await self.confirm(prompt, default=True)

    # =========================================================================
    # 內部方法
    # =========================================================================

    def _format_prompt(self, question: Question) -> str:
        """格式化提示"""
        prompt = question.prompt

        if question.context:
            prompt = f"[上下文] {question.context}\n\n{prompt}"

        if question.question_type == QuestionType.SELECT and question.options:
            prompt += "\n"
            for i, opt in enumerate(question.options, 1):
                prompt += f"  [{i}] {opt}\n"

        if question.question_type == QuestionType.CONFIRM:
            default_hint = "[Y/n]" if question.default == "y" else "[y/N]"
            if not prompt.rstrip().endswith(default_hint):
                prompt += f" {default_hint}"

        if question.default and question.question_type == QuestionType.INPUT:
            prompt += f"\n  (預設: {question.default})"

        return prompt

    def _process_response(self, response: str, question: Question) -> Answer:
        """處理回答"""
        response = response.strip()

        # 空回答使用預設
        if not response and question.default:
            return Answer(
                value=question.default,
                source="default",
                raw_response=response
            )

        # SELECT 類型
        if question.question_type == QuestionType.SELECT:
            if response.isdigit():
                idx = int(response) - 1
                if 0 <= idx < len(question.options):
                    # 檢查是否是「其他」選項
                    if question.options[idx] == "其他（請輸入）":
                        return Answer(
                            value=response,
                            source="user_input",
                            raw_response=response
                        )
                    return Answer(
                        value=question.options[idx],
                        source="selection",
                        raw_response=response
                    )

        return Answer(
            value=response,
            source="user_input",
            raw_response=response
        )

    def _auto_answer(self, question: Question) -> Answer:
        """自動模式回答"""
        if question.default:
            return Answer(
                value=question.default,
                source="auto_default",
                confidence=0.5
            )

        if question.question_type == QuestionType.CONFIRM:
            return Answer(value="y", source="auto_confirm", confidence=0.5)

        if question.question_type == QuestionType.SELECT and question.options:
            return Answer(
                value=question.options[0],
                source="auto_first_option",
                confidence=0.5
            )

        return Answer(value="", source="auto_empty", confidence=0.0)

    async def _web_search(self, query: str) -> str:
        """執行網頁搜尋"""
        if self.web_search_callback:
            return await self.web_search_callback(query)

        # 無搜尋回調，返回提示
        return f"[搜尋功能未配置] 請手動搜尋: {query}"

    def _normalize_key(self, topic: str) -> str:
        """正規化知識鍵"""
        # 移除特殊字符，轉換為 snake_case
        key = re.sub(r'[^\w\s]', '', topic)
        key = re.sub(r'\s+', '_', key)
        return key.lower()

    def _format_list(self, items: List[str], indent: int = 2, max_width: int = 60) -> str:
        """格式化列表"""
        if not items:
            return f"║{'(無)':^{max_width + indent}}║\n"

        result = ""
        for item in items[:5]:  # 最多顯示 5 項
            line = f"{'  ' * indent}• {item}"
            if len(line) > max_width:
                line = line[:max_width-3] + "..."
            result += f"║  {line:<{max_width + indent - 2}}║\n"

        if len(items) > 5:
            result += f"║  {'... 還有 ' + str(len(items) - 5) + ' 項':^{max_width + indent - 2}}║\n"

        return result

    def get_collected_knowledge_dict(self) -> Dict[str, str]:
        """獲取收集的知識（字典格式）"""
        return {k.key: k.value for k in self.collected_knowledge}

    def get_collected_knowledge_list(self) -> List[Dict]:
        """獲取收集的知識（列表格式，便於儲存）"""
        return [
            {
                "key": k.key,
                "value": k.value,
                "source": k.source,
                "context": k.context
            }
            for k in self.collected_knowledge
        ]

    def clear_collected_knowledge(self):
        """清除收集的知識"""
        self.collected_knowledge = []
        self.conversation_history = []


# =============================================================================
# CLI 輔助
# =============================================================================

async def cli_user_callback(prompt: str) -> str:
    """CLI 用戶回調"""
    print(prompt)
    try:
        return input("> ").strip()
    except EOFError:
        return ""


async def mock_web_search(query: str) -> str:
    """模擬網頁搜尋"""
    return f"""
搜尋結果 for "{query}":

1. [台灣建築技術規則] 日照陰影規範
   建築物高度 H ≤ 3.6 × (Sw + D)
   其中 Sw = 道路寬度, D = 退縮距離

2. [建築法規解釋] 建蔽率計算
   建蔽率 = 建築面積 / 基地面積 × 100%
"""


# =============================================================================
# Test
# =============================================================================

if __name__ == "__main__":
    import asyncio

    async def test():
        print("HITL Collaborator 測試")
        print("=" * 60)

        # 使用 CLI 回調
        collaborator = HITLCollaborator(
            user_callback=cli_user_callback,
            web_search_callback=mock_web_search
        )

        # 測試確認
        print("\n1. 測試確認...")
        confirmed = await collaborator.confirm("使用 WASP 立方體聚集模式？")
        print(f"  確認結果: {confirmed}")

        # 測試選擇
        print("\n2. 測試選擇...")
        answer = await collaborator.select(
            "選擇結構類型：",
            options=["鋼骨 (S)", "鋼筋混凝土 (RC)", "鋼骨鋼筋混凝土 (SRC)"]
        )
        print(f"  選擇結果: {answer.value}")

        # 測試知識收集
        print("\n3. 測試知識收集...")
        knowledge = await collaborator.collect_knowledge(
            topic="日照法規公式",
            context="用於建築高度計算"
        )
        print(f"  收集到: {knowledge.key} = {knowledge.value}")

        # 顯示收集的知識
        print("\n收集的知識：")
        for k in collaborator.collected_knowledge:
            print(f"  {k.key}: {k.value} (來源: {k.source})")

    asyncio.run(test())
