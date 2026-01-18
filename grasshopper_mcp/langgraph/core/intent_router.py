"""
Intent Router - 意圖路由器

分類用戶請求的高層意圖，決定進入哪種處理模式：
- WORKFLOW: 確定性四階段管線
- META_AGENT: 動態工具/代理創建
- THINK_PARTNER: 蘇格拉底式探索 (Claudesidian)
- BRAINSTORM: 三階段創意探索 (Superpowers)

支援：
- 自動偵測 (基於關鍵字和上下文)
- 手動觸發 (/think, /brainstorm)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import re


class IntentType(str, Enum):
    """High-level intent classification"""
    WORKFLOW = "workflow"           # Standard 4-stage pipeline
    META_AGENT = "meta_agent"       # Dynamic tool/agent creation
    THINK_PARTNER = "think_partner" # Socratic exploration
    BRAINSTORM = "brainstorm"       # 3-phase creative exploration
    UNKNOWN = "unknown"             # Needs clarification


@dataclass
class IntentClassification:
    """Result of intent classification"""
    intent_type: IntentType
    confidence: float           # 0-1
    matched_keywords: List[str]
    is_manual_trigger: bool     # User used /think or /brainstorm
    reasoning: str              # Explanation of classification


@dataclass
class IntentPatterns:
    """Configurable intent patterns"""
    workflow_keywords: List[str] = field(default_factory=lambda: [
        "build", "create", "make", "design", "construct",
        "add", "implement", "generate", "produce",
        "建構", "創建", "製作", "設計", "做", "加", "實作",
    ])

    meta_agent_keywords: List[str] = field(default_factory=lambda: [
        "create tool", "new tool", "custom tool", "build agent",
        "create agent", "dynamic", "synthesize", "generate tool",
        "創建工具", "新工具", "自定義", "合成",
    ])

    think_partner_keywords: List[str] = field(default_factory=lambda: [
        "think about", "explore", "what if", "consider",
        "reflect", "analyze deeply", "understand", "why",
        "思考", "探索", "如果", "考慮", "反思", "為什麼",
    ])

    brainstorm_keywords: List[str] = field(default_factory=lambda: [
        "brainstorm", "ideas for", "possibilities", "alternatives",
        "options", "creative", "innovate", "explore options",
        "腦力激盪", "想法", "可能性", "替代方案", "選項", "創意",
    ])

    # Manual trigger commands
    manual_triggers: Dict[str, IntentType] = field(default_factory=lambda: {
        "/think": IntentType.THINK_PARTNER,
        "/brainstorm": IntentType.BRAINSTORM,
        "/workflow": IntentType.WORKFLOW,
        "/meta": IntentType.META_AGENT,
    })


class IntentRouter:
    """
    Routes user intent to appropriate processing mode

    Works alongside ExpertRouter for task-level routing.
    IntentRouter handles high-level mode selection,
    ExpertRouter handles task-type specific expert selection.

    Usage:
        router = IntentRouter()
        result = router.classify("brainstorm ideas for a parametric chair", {})
        print(f"Intent: {result.intent_type}, Confidence: {result.confidence}")
    """

    def __init__(self, patterns: Optional[IntentPatterns] = None):
        self.patterns = patterns or IntentPatterns()

    def classify(
        self,
        task: str,
        context: Optional[Dict] = None
    ) -> IntentClassification:
        """
        Classify user intent

        Args:
            task: User's task description
            context: Optional context (previous state, history)

        Returns:
            IntentClassification with type, confidence, and reasoning
        """
        context = context or {}
        task_lower = task.lower().strip()

        # 1. Check for manual triggers first
        manual_result = self._check_manual_triggers(task_lower)
        if manual_result:
            return manual_result

        # 2. Keyword-based classification
        scores = self._calculate_keyword_scores(task_lower)

        # 3. Context-based adjustments
        scores = self._adjust_by_context(scores, context)

        # 4. Select best intent
        return self._select_best_intent(scores, task_lower)

    def _check_manual_triggers(self, task: str) -> Optional[IntentClassification]:
        """Check for manual trigger commands like /think, /brainstorm"""
        for trigger, intent_type in self.patterns.manual_triggers.items():
            if task.startswith(trigger):
                return IntentClassification(
                    intent_type=intent_type,
                    confidence=1.0,
                    matched_keywords=[trigger],
                    is_manual_trigger=True,
                    reasoning=f"Manual trigger: {trigger}"
                )
        return None

    def _calculate_keyword_scores(self, task: str) -> Dict[IntentType, Tuple[float, List[str]]]:
        """Calculate scores based on keyword matching"""
        scores: Dict[IntentType, Tuple[float, List[str]]] = {
            IntentType.WORKFLOW: (0.0, []),
            IntentType.META_AGENT: (0.0, []),
            IntentType.THINK_PARTNER: (0.0, []),
            IntentType.BRAINSTORM: (0.0, []),
        }

        # Check each pattern set
        pattern_map = {
            IntentType.WORKFLOW: self.patterns.workflow_keywords,
            IntentType.META_AGENT: self.patterns.meta_agent_keywords,
            IntentType.THINK_PARTNER: self.patterns.think_partner_keywords,
            IntentType.BRAINSTORM: self.patterns.brainstorm_keywords,
        }

        for intent_type, keywords in pattern_map.items():
            matched = []
            for keyword in keywords:
                if keyword.lower() in task:
                    matched.append(keyword)

            if matched:
                # Score based on number and specificity of matches
                # Multi-word matches are more specific
                score = sum(
                    0.3 if ' ' in kw else 0.2
                    for kw in matched
                )
                # Cap at 0.9 for keyword-only classification
                score = min(0.9, score)
                scores[intent_type] = (score, matched)

        return scores

    def _adjust_by_context(
        self,
        scores: Dict[IntentType, Tuple[float, List[str]]],
        context: Dict
    ) -> Dict[IntentType, Tuple[float, List[str]]]:
        """Adjust scores based on context"""
        # If already in a specific mode, boost that mode
        current_intent = context.get("intent_type")
        if current_intent and current_intent in [e.value for e in IntentType]:
            intent = IntentType(current_intent)
            if intent in scores:
                current_score, keywords = scores[intent]
                scores[intent] = (min(1.0, current_score + 0.1), keywords)

        # If there are unresolved questions, boost Think-Partner
        if context.get("pending_decisions"):
            current_score, keywords = scores[IntentType.THINK_PARTNER]
            scores[IntentType.THINK_PARTNER] = (min(1.0, current_score + 0.15), keywords)

        # If low confidence in previous operations, boost Brainstorm
        if context.get("intent_confidence", 1.0) < 0.5:
            current_score, keywords = scores[IntentType.BRAINSTORM]
            scores[IntentType.BRAINSTORM] = (min(1.0, current_score + 0.1), keywords)

        return scores

    def _select_best_intent(
        self,
        scores: Dict[IntentType, Tuple[float, List[str]]],
        task: str
    ) -> IntentClassification:
        """Select the best intent based on scores"""
        # Find highest scoring intent
        best_intent = IntentType.WORKFLOW  # Default
        best_score = 0.0
        best_keywords: List[str] = []

        for intent_type, (score, keywords) in scores.items():
            if score > best_score:
                best_score = score
                best_intent = intent_type
                best_keywords = keywords

        # If no clear winner, default to WORKFLOW for action-oriented tasks
        if best_score < 0.2:
            # Check if it looks like a build/create task
            action_words = ["create", "make", "build", "add", "做", "建", "加"]
            if any(word in task.lower() for word in action_words):
                best_intent = IntentType.WORKFLOW
                best_score = 0.5
                best_keywords = [w for w in action_words if w in task.lower()]

        # Generate reasoning
        reasoning = self._generate_reasoning(best_intent, best_score, best_keywords, task)

        return IntentClassification(
            intent_type=best_intent,
            confidence=best_score,
            matched_keywords=best_keywords,
            is_manual_trigger=False,
            reasoning=reasoning
        )

    def _generate_reasoning(
        self,
        intent: IntentType,
        score: float,
        keywords: List[str],
        task: str
    ) -> str:
        """Generate human-readable reasoning for classification"""
        if score >= 0.7:
            certainty = "High confidence"
        elif score >= 0.4:
            certainty = "Medium confidence"
        else:
            certainty = "Low confidence"

        if keywords:
            keyword_str = ", ".join(keywords[:3])
            return f"{certainty} ({score:.2f}): Matched keywords [{keyword_str}] → {intent.value}"
        else:
            return f"{certainty} ({score:.2f}): Default classification → {intent.value}"

    def get_mode_description(self, intent_type: IntentType) -> str:
        """Get description of what each mode does"""
        descriptions = {
            IntentType.WORKFLOW: (
                "Workflow Mode: 4-stage deterministic pipeline\n"
                "  1. Intent Decomposition - Break down into subtasks\n"
                "  2. Tool Retrieval - Find relevant tools/joseki\n"
                "  3. Prompt Generation - Generate execution prompts\n"
                "  4. Config Assembly - Assemble final configuration"
            ),
            IntentType.META_AGENT: (
                "Meta-Agent Mode: Dynamic tool and agent creation\n"
                "  - search_tool: Find existing tools\n"
                "  - create_tool: Generate new tools\n"
                "  - ask_user: Request clarification\n"
                "  - create_agent_config: Assemble agent configuration"
            ),
            IntentType.THINK_PARTNER: (
                "Think-Partner Mode: Socratic exploration (Claudesidian)\n"
                "  - Thinking Phase: Generate questions, explore assumptions\n"
                "  - Writing Phase: Synthesize insights into outputs\n"
                "  - Single question principle: One question per message"
            ),
            IntentType.BRAINSTORM: (
                "Brainstorm Mode: 3-phase creative exploration (Superpowers)\n"
                "  1. Understanding: Clarify problem, constraints, success criteria\n"
                "  2. Exploring: Generate 2-3 approaches with trade-off analysis\n"
                "  3. Presenting: Present design in 200-300 word sections"
            ),
            IntentType.UNKNOWN: (
                "Unknown intent - needs clarification"
            ),
        }
        return descriptions.get(intent_type, "Unknown mode")


# Convenience functions
def classify_intent(task: str, context: Optional[Dict] = None) -> IntentClassification:
    """Quick classification without instantiating router"""
    router = IntentRouter()
    return router.classify(task, context)


def is_manual_trigger(task: str) -> bool:
    """Check if task starts with a manual trigger"""
    triggers = ["/think", "/brainstorm", "/workflow", "/meta"]
    return any(task.lower().strip().startswith(t) for t in triggers)
