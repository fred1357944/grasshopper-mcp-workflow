"""
Think-Partner Node - 思考夥伴節點

實現 Claudesidian 的 Think-Partner 模式：
- Thinking Phase: 生成問題、探索假設、搜索知識
- Writing Phase: 綜合洞見、產出內容

核心原則：
- 單一問題原則 (每次只問一個問題)
- 搜索現有知識庫 (Joseki patterns)
- 記錄洞見到 thinking_log
- 識別想法間的連結
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

from ..state import (
    DesignState,
    ThinkingEntry,
    ThinkingMode,
)


def think_partner_node(state: DesignState) -> Dict[str, Any]:
    """
    Think-Partner main node

    Routes to thinking or writing phase based on state.
    Claudesidian philosophy: "AI amplifies thinking, not just writing"

    Args:
        state: Current DesignState

    Returns:
        State updates
    """
    mode = state.get("thinking_mode") or ThinkingMode.THINKING.value

    if mode == ThinkingMode.THINKING.value:
        return _thinking_phase(state)
    else:
        return _writing_phase(state)


def _thinking_phase(state: DesignState) -> Dict[str, Any]:
    """
    Thinking Phase - Socratic exploration

    Generate probing questions to understand the problem deeply.
    Follow single-question principle: one question per interaction.
    """
    topic = state.get("topic", "")
    requirements = state.get("requirements", "")
    thinking_log = state.get("thinking_log", [])
    thinking_insights = state.get("thinking_insights", [])

    # Determine which question to ask based on what we know
    question, question_type = _select_next_question(
        topic, requirements, thinking_log
    )

    # Search for relevant knowledge (Joseki patterns)
    connections = _search_knowledge_connections(topic, requirements)

    # Create new thinking entry
    new_entry = ThinkingEntry(
        question=question,
        reflection="",  # Will be filled when user responds
        insights=[],
        connections=connections,
        timestamp=datetime.now().isoformat()
    )

    # Check if we have enough insights to move to writing
    should_transition = _should_transition_to_writing(thinking_log, thinking_insights)

    return {
        "thinking_log": thinking_log + [new_entry],
        "thinking_mode": ThinkingMode.WRITING.value if should_transition else ThinkingMode.THINKING.value,
        "awaiting_confirmation": True,
        "confirmation_reason": "think_partner_question",
        "pending_decisions": state.get("pending_decisions", []) + [{
            "id": str(uuid.uuid4()),
            "question": question,
            "options": ["Answer and continue thinking", "Move to writing phase", "End exploration"],
            "importance": "medium",
            "context": f"Think-Partner exploration: {question_type}",
            "resolved": False,
            "chosen_option": None,
        }],
    }


def _writing_phase(state: DesignState) -> Dict[str, Any]:
    """
    Writing Phase - Synthesize insights

    Transform thinking phase insights into actionable outputs.
    """
    topic = state.get("topic", "")
    thinking_log = state.get("thinking_log", [])
    thinking_insights = state.get("thinking_insights", [])

    # Synthesize all insights from thinking log
    synthesized = _synthesize_insights(thinking_log, thinking_insights)

    # Generate actionable output
    output = _generate_output(topic, synthesized)

    return {
        "thinking_insights": synthesized,
        "final_proposal": output,
        "thinking_mode": None,  # End think-partner mode
        "current_stage": "requirements",  # Ready to proceed with workflow
        "errors": state.get("errors", []) + [
            f"Think-Partner completed: {len(synthesized)} insights synthesized"
        ],
    }


def _select_next_question(
    topic: str,
    requirements: str,
    thinking_log: List[ThinkingEntry]
) -> tuple[str, str]:
    """
    Select the next question to ask

    Follows Socratic method progression:
    1. Clarification questions (what, who)
    2. Assumption questions (why assume)
    3. Reason/evidence questions (how do we know)
    4. Implication questions (what follows)
    5. Meta questions (why this question matters)
    """
    num_questions = len(thinking_log)

    # Question progression
    question_templates = [
        # Phase 1: Clarification
        (f"What is the core problem you're trying to solve with '{topic}'?", "clarification"),
        (f"Who will be using or benefiting from this design?", "clarification"),

        # Phase 2: Assumptions
        ("What assumptions are we making about the constraints?", "assumption"),
        ("What implicit requirements haven't been stated?", "assumption"),

        # Phase 3: Evidence
        ("What similar designs have worked well in the past?", "evidence"),
        ("What patterns from our knowledge base might apply here?", "evidence"),

        # Phase 4: Implications
        ("What are the potential edge cases we should consider?", "implication"),
        ("How might this design need to evolve over time?", "implication"),

        # Phase 5: Meta
        ("What's the most important aspect we haven't discussed yet?", "meta"),
        ("What question should I be asking that I haven't?", "meta"),
    ]

    # Select based on progress
    idx = min(num_questions, len(question_templates) - 1)
    return question_templates[idx]


def _search_knowledge_connections(topic: str, requirements: str) -> List[str]:
    """
    Search for connections to existing knowledge

    In full implementation, this would search:
    - Joseki pattern library
    - Component registry
    - Previous successful designs
    """
    connections = []

    # Keywords that might connect to known patterns
    keywords = [
        ("table", "furniture-joseki"),
        ("chair", "furniture-joseki"),
        ("box", "primitive-patterns"),
        ("parametric", "parameter-patterns"),
        ("modular", "modular-patterns"),
    ]

    combined = f"{topic} {requirements}".lower()

    for keyword, pattern_id in keywords:
        if keyword in combined:
            connections.append(f"Potential connection: {pattern_id}")

    return connections


def _should_transition_to_writing(
    thinking_log: List[ThinkingEntry],
    thinking_insights: List[str]
) -> bool:
    """
    Determine if ready to transition to writing phase

    Criteria:
    - At least 3 questions asked
    - OR explicit insights gathered
    - OR specific types of questions answered
    """
    if len(thinking_log) >= 5:
        return True

    if len(thinking_insights) >= 3:
        return True

    # Check if we have key question types answered
    question_types_needed = {"clarification", "assumption", "evidence"}
    types_answered = set()

    for entry in thinking_log:
        # In real implementation, track question type per entry
        if entry.get("reflection"):  # Has been answered
            types_answered.add("answered")

    return len(types_answered) >= 2


def _synthesize_insights(
    thinking_log: List[ThinkingEntry],
    existing_insights: List[str]
) -> List[str]:
    """
    Synthesize insights from thinking log

    Extract key learnings from the Q&A process
    """
    insights = list(existing_insights)

    for entry in thinking_log:
        # Extract insights from reflections
        if entry.get("insights"):
            insights.extend(entry["insights"])

        # Extract insights from connections
        if entry.get("connections"):
            for conn in entry["connections"]:
                if conn not in insights:
                    insights.append(f"Connection discovered: {conn}")

    return insights


def _generate_output(topic: str, insights: List[str]) -> str:
    """
    Generate actionable output from insights

    Creates a summary that can feed into the workflow
    """
    if not insights:
        return f"Topic: {topic}\n\nNo specific insights gathered. Ready to proceed with standard workflow."

    output_parts = [
        f"# Think-Partner Summary: {topic}",
        "",
        "## Key Insights",
    ]

    for i, insight in enumerate(insights, 1):
        output_parts.append(f"{i}. {insight}")

    output_parts.extend([
        "",
        "## Recommended Next Steps",
        "1. Proceed with design decomposition",
        "2. Consider the identified constraints",
        "3. Apply relevant patterns from knowledge base",
    ])

    return "\n".join(output_parts)


# === Entry/Exit Utilities ===

def enter_think_partner_mode(state: DesignState) -> Dict[str, Any]:
    """Initialize Think-Partner mode"""
    return {
        "thinking_mode": ThinkingMode.THINKING.value,
        "thinking_log": [],
        "thinking_insights": [],
        "intent_type": "think_partner",
    }


def exit_think_partner_mode(state: DesignState) -> Dict[str, Any]:
    """Clean exit from Think-Partner mode"""
    return {
        "thinking_mode": None,
        "current_stage": "requirements",
    }


def add_user_response(
    state: DesignState,
    response: str
) -> Dict[str, Any]:
    """
    Process user's response to a thinking question

    Updates the latest thinking entry with the response
    """
    thinking_log = state.get("thinking_log", [])

    if not thinking_log:
        return {}

    # Update the last entry with reflection
    last_entry = thinking_log[-1].copy()
    last_entry["reflection"] = response

    # Extract any insights from the response
    # In full implementation, this could use NLP
    new_insights = []
    if len(response) > 50:  # Substantial response
        new_insights.append(f"User insight: {response[:100]}...")

    last_entry["insights"] = last_entry.get("insights", []) + new_insights

    # Replace last entry
    updated_log = thinking_log[:-1] + [last_entry]

    return {
        "thinking_log": updated_log,
        "thinking_insights": state.get("thinking_insights", []) + new_insights,
    }
