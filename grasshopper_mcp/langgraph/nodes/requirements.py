"""
Requirements Clarification Node

Step 1 of the Grasshopper workflow: Clarify design requirements
"""

from typing import Any
from ..state import DesignState, Decision
import uuid


def clarify_requirements_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Clarify design requirements

    This node:
    1. Analyzes the topic/requirements
    2. Identifies ambiguities
    3. Creates decision points for unclear requirements
    4. Outputs structured requirements

    In practice, this would integrate with Claude to:
    - Ask clarifying questions
    - Parse user responses
    - Build a requirements specification
    """
    topic = state["topic"]
    current_requirements = state.get("requirements", "")

    # Analyze for ambiguities (placeholder logic)
    # In production, use LLM to identify unclear points
    ambiguities = _identify_ambiguities(topic, current_requirements)

    # Create decisions for critical ambiguities
    new_decisions = []
    for amb in ambiguities:
        if amb["importance"] == "high":
            new_decisions.append(Decision(
                id=str(uuid.uuid4()),
                question=amb["question"],
                options=amb["options"],
                importance="high",
                context=f"Clarifying requirement: {amb['aspect']}",
                resolved=False,
                chosen_option=None
            ))

    # Build structured requirements
    structured_requirements = _build_requirements(topic, current_requirements)

    return {
        "requirements": structured_requirements,
        "pending_decisions": state["pending_decisions"] + new_decisions,
        "current_stage": "decomposition" if not new_decisions else "requirements",
    }


def _identify_ambiguities(topic: str, requirements: str) -> list[dict]:
    """
    Identify ambiguous aspects of the requirements

    Returns list of:
    {
        "aspect": str,
        "question": str,
        "options": list[str],
        "importance": "high" | "medium" | "low"
    }
    """
    # Placeholder: In production, use LLM analysis
    ambiguities = []

    # Check for common ambiguities in parametric design
    keywords_needing_clarification = {
        "桌子": {
            "aspect": "table_type",
            "question": "請確認桌子類型",
            "options": ["書桌", "餐桌", "茶几", "工作台"],
            "importance": "high"
        },
        "參數化": {
            "aspect": "parametric_aspects",
            "question": "哪些尺寸需要參數化？",
            "options": ["長寬高", "腿部角度", "桌面曲率", "全部"],
            "importance": "medium"
        }
    }

    for keyword, amb in keywords_needing_clarification.items():
        if keyword in topic and keyword not in requirements:
            ambiguities.append(amb)

    return ambiguities


def _build_requirements(topic: str, existing: str) -> str:
    """
    Build structured requirements document

    Format:
    # Design Requirements

    ## Overview
    [topic summary]

    ## Specifications
    - Dimension constraints
    - Material requirements
    - Parametric variables

    ## Constraints
    - Manufacturing constraints
    - Assembly requirements
    """
    if existing:
        return existing

    # Generate initial requirements structure
    template = f"""# Design Requirements

## Overview
{topic}

## Specifications
- 尺寸約束: [待定義]
- 材料需求: [待定義]
- 參數化變數: [待定義]

## Constraints
- 製造約束: [待定義]
- 組裝需求: [待定義]

## Notes
- Created from topic: {topic}
- Status: Initial draft, pending clarification
"""
    return template
