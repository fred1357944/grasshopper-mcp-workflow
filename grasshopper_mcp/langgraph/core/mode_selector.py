"""
Mode Selector - 模式選擇器

結合 IntentRouter 和 ConfidenceEvaluator 選擇最佳處理模式。

決策邏輯：
- 高信心 + 已知模式 → Workflow Mode
- 低信心 + 模糊請求 → Think-Partner Mode
- 創意/探索請求 → Brainstorm Mode
- 工具/代理創建請求 → Meta-Agent Mode
"""

from dataclasses import dataclass
from typing import Dict, Optional, Any
from enum import Enum

from .intent_router import IntentRouter, IntentType, IntentClassification
from .confidence import ConfidenceEvaluator, ConfidenceResult


class ProcessingStrategy(str, Enum):
    """How to process the task"""
    DIRECT = "direct"           # Execute immediately
    EXPLORE_FIRST = "explore"   # Explore before executing
    PARALLEL = "parallel"       # Multiple approaches in parallel
    ITERATIVE = "iterative"     # Refine through iterations


@dataclass
class ModeSelection:
    """Result of mode selection"""
    intent_type: IntentType
    strategy: ProcessingStrategy
    confidence: float
    should_ask_clarification: bool
    clarification_question: Optional[str]
    reasoning: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_type": self.intent_type.value,
            "strategy": self.strategy.value,
            "confidence": self.confidence,
            "should_ask_clarification": self.should_ask_clarification,
            "clarification_question": self.clarification_question,
            "reasoning": self.reasoning,
        }


@dataclass
class ModeThresholds:
    """Configurable thresholds for mode selection"""
    # Confidence thresholds
    high_confidence: float = 0.8    # Skip clarification, direct execution
    medium_confidence: float = 0.5  # Proceed with caution
    low_confidence: float = 0.3     # Need clarification

    # Strategy thresholds
    explore_threshold: float = 0.6  # Below this, explore first
    parallel_threshold: float = 0.4 # Below this, try parallel approaches


class ModeSelector:
    """
    Selects processing mode based on intent and confidence

    Combines:
    - IntentRouter: High-level intent classification
    - ConfidenceEvaluator: Task-level confidence scoring

    Usage:
        selector = ModeSelector()
        result = selector.select("brainstorm ideas for a chair", state)
        print(f"Mode: {result.intent_type}, Strategy: {result.strategy}")
    """

    def __init__(
        self,
        confidence_evaluator: Optional[ConfidenceEvaluator] = None,
        intent_router: Optional[IntentRouter] = None,
        thresholds: Optional[ModeThresholds] = None
    ):
        self.confidence_evaluator = confidence_evaluator or ConfidenceEvaluator()
        self.intent_router = intent_router or IntentRouter()
        self.thresholds = thresholds or ModeThresholds()

    def select(
        self,
        task: str,
        state: Optional[Dict] = None
    ) -> ModeSelection:
        """
        Select the optimal processing mode

        Args:
            task: User's task description
            state: Current workflow state (DesignState)

        Returns:
            ModeSelection with mode, strategy, and reasoning
        """
        state = state or {}

        # 1. Classify intent
        intent_result = self.intent_router.classify(task, state)

        # 2. Evaluate confidence (if applicable)
        confidence_result = self._evaluate_confidence(task, state)

        # 3. Combine results to select mode
        return self._combine_and_select(intent_result, confidence_result, task, state)

    def _evaluate_confidence(
        self,
        task: str,
        state: Dict
    ) -> Optional[ConfidenceResult]:
        """Evaluate confidence for the task"""
        # Extract component type if mentioned
        component_type = self._extract_component_type(task)

        if component_type:
            return self.confidence_evaluator.evaluate(
                component_type=component_type,
                context={"task": task, **state}
            )

        return None

    def _extract_component_type(self, task: str) -> Optional[str]:
        """Extract component type from task description"""
        # Common Grasshopper component keywords
        components = [
            "slider", "box", "sphere", "cylinder", "plane",
            "point", "curve", "surface", "brep", "mesh",
            "division", "addition", "multiplication", "negative",
        ]

        task_lower = task.lower()
        for comp in components:
            if comp in task_lower:
                return comp.title()

        return None

    def _combine_and_select(
        self,
        intent_result: IntentClassification,
        confidence_result: Optional[ConfidenceResult],
        task: str,
        state: Dict
    ) -> ModeSelection:
        """Combine intent and confidence to make final selection"""

        # Get base confidence from intent classification
        base_confidence = intent_result.confidence

        # Adjust with component confidence if available
        if confidence_result:
            combined_confidence = (base_confidence + confidence_result.total_score) / 2
        else:
            combined_confidence = base_confidence

        # Determine strategy based on confidence and intent
        strategy = self._determine_strategy(
            intent_result.intent_type,
            combined_confidence,
            state
        )

        # Check if clarification is needed
        should_ask, question = self._check_clarification_needed(
            intent_result,
            combined_confidence,
            task
        )

        # Generate reasoning
        reasoning = self._generate_reasoning(
            intent_result,
            confidence_result,
            strategy,
            combined_confidence
        )

        return ModeSelection(
            intent_type=intent_result.intent_type,
            strategy=strategy,
            confidence=combined_confidence,
            should_ask_clarification=should_ask,
            clarification_question=question,
            reasoning=reasoning
        )

    def _determine_strategy(
        self,
        intent_type: IntentType,
        confidence: float,
        state: Dict
    ) -> ProcessingStrategy:
        """Determine processing strategy based on intent and confidence"""

        # Manual triggers get direct processing
        if intent_type == IntentType.THINK_PARTNER:
            return ProcessingStrategy.ITERATIVE

        if intent_type == IntentType.BRAINSTORM:
            return ProcessingStrategy.PARALLEL

        if intent_type == IntentType.META_AGENT:
            return ProcessingStrategy.EXPLORE_FIRST

        # For WORKFLOW, decide based on confidence
        if confidence >= self.thresholds.high_confidence:
            return ProcessingStrategy.DIRECT
        elif confidence >= self.thresholds.explore_threshold:
            return ProcessingStrategy.ITERATIVE
        elif confidence >= self.thresholds.parallel_threshold:
            return ProcessingStrategy.PARALLEL
        else:
            return ProcessingStrategy.EXPLORE_FIRST

    def _check_clarification_needed(
        self,
        intent_result: IntentClassification,
        confidence: float,
        task: str
    ) -> tuple[bool, Optional[str]]:
        """Check if clarification is needed"""

        # Manual triggers don't need clarification
        if intent_result.is_manual_trigger:
            return False, None

        # Low confidence needs clarification
        if confidence < self.thresholds.low_confidence:
            return True, self._generate_clarification_question(intent_result, task)

        # Unknown intent needs clarification
        if intent_result.intent_type == IntentType.UNKNOWN:
            return True, "I'm not sure what you'd like to do. Could you clarify your goal?"

        return False, None

    def _generate_clarification_question(
        self,
        intent_result: IntentClassification,
        task: str
    ) -> str:
        """Generate a clarification question"""

        if intent_result.intent_type == IntentType.BRAINSTORM:
            return (
                "I'll help you brainstorm. Before we start:\n"
                "1. What are the key constraints I should know about?\n"
                "2. How would you define success for this design?"
            )

        if intent_result.intent_type == IntentType.THINK_PARTNER:
            return (
                "I'd like to explore this with you. "
                "What's the most important aspect you want to understand better?"
            )

        if intent_result.intent_type == IntentType.META_AGENT:
            return (
                "It sounds like you might need a custom tool. "
                "Could you describe what operation you want to perform?"
            )

        # Default clarification
        return (
            f"I understood your request as: '{task[:50]}...'\n"
            "Is this correct? What specific outcome are you looking for?"
        )

    def _generate_reasoning(
        self,
        intent_result: IntentClassification,
        confidence_result: Optional[ConfidenceResult],
        strategy: ProcessingStrategy,
        combined_confidence: float
    ) -> str:
        """Generate reasoning for the mode selection"""
        parts = []

        # Intent reasoning
        parts.append(f"Intent: {intent_result.intent_type.value} ({intent_result.reasoning})")

        # Confidence reasoning
        if confidence_result:
            parts.append(f"Component confidence: {confidence_result.total_score:.2f}")

        parts.append(f"Combined confidence: {combined_confidence:.2f}")
        parts.append(f"Strategy: {strategy.value}")

        return " | ".join(parts)

    def get_recommended_mode(
        self,
        task: str,
        available_modes: Optional[list[IntentType]] = None
    ) -> IntentType:
        """
        Quick method to get recommended mode without full analysis

        Args:
            task: User's task description
            available_modes: Limit to specific modes

        Returns:
            Recommended IntentType
        """
        result = self.select(task, {})

        if available_modes and result.intent_type not in available_modes:
            # Fall back to first available
            return available_modes[0] if available_modes else IntentType.WORKFLOW

        return result.intent_type


# Convenience function
def select_mode(
    task: str,
    state: Optional[Dict] = None
) -> ModeSelection:
    """Quick mode selection without instantiating selector"""
    selector = ModeSelector()
    return selector.select(task, state)
