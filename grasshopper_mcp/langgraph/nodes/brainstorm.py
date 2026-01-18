"""
Brainstorm Node - 腦力激盪節點

實現 Superpowers 的三階段腦力激盪方法：
1. Understanding: 釐清問題空間、約束、成功標準
2. Exploring: 發散思維，生成 2-3 個方案並分析取捨
3. Presenting: 收斂，分段呈現設計 (200-300字/段)

核心原則：
- 單一問題原則
- 漸進驗證 (每段後確認)
- YAGNI (You Aren't Gonna Need It)
- 推薦首選方案並解釋原因
- 文檔輸出到 docs/plans/
"""

from datetime import datetime
from typing import Dict, Any, List
import uuid

from ..state import (
    DesignState,
    BrainstormIdea,
    BrainstormPhase,
)


def brainstorm_node(state: DesignState) -> Dict[str, Any]:
    """
    Brainstorm main node

    Routes to appropriate phase based on state.
    Superpowers philosophy: "Systematic over ad-hoc"

    Args:
        state: Current DesignState

    Returns:
        State updates
    """
    phase = state.get("brainstorm_phase") or BrainstormPhase.UNDERSTANDING.value

    if phase == BrainstormPhase.UNDERSTANDING.value:
        return _understanding_phase(state)
    elif phase == BrainstormPhase.EXPLORING.value:
        return _exploring_phase(state)
    elif phase == BrainstormPhase.PRESENTING.value:
        return _presenting_phase(state)
    else:
        return _complete_phase(state)


def _understanding_phase(state: DesignState) -> Dict[str, Any]:
    """
    Phase 1: Understanding the Problem Space

    Clarify:
    - Purpose (what and why)
    - Constraints (technical, business, user)
    - Success criteria (how to measure success)
    """
    topic = state.get("topic", "")
    requirements = state.get("requirements", "")
    constraints = state.get("brainstorm_constraints", [])
    success_criteria = state.get("brainstorm_success_criteria", [])

    # Generate understanding questions
    questions = _generate_understanding_questions(topic, requirements, constraints)

    # Select the next question to ask (single question principle)
    if not constraints:
        question = questions["constraints"]
        question_type = "constraints"
    elif not success_criteria:
        question = questions["success"]
        question_type = "success"
    else:
        # Ready to move to exploring
        return {
            "brainstorm_phase": BrainstormPhase.EXPLORING.value,
            "errors": state.get("errors", []) + [
                "Brainstorm: Understanding phase complete, moving to exploring"
            ],
        }

    return {
        "brainstorm_phase": BrainstormPhase.UNDERSTANDING.value,
        "awaiting_confirmation": True,
        "confirmation_reason": "brainstorm_understanding",
        "pending_decisions": state.get("pending_decisions", []) + [{
            "id": str(uuid.uuid4()),
            "question": question,
            "options": ["Provide answer", "Skip this question", "Move to next phase"],
            "importance": "high",
            "context": f"Brainstorm understanding: {question_type}",
            "resolved": False,
            "chosen_option": None,
        }],
    }


def _exploring_phase(state: DesignState) -> Dict[str, Any]:
    """
    Phase 2: Exploring Approaches

    Generate 2-3 different approaches with:
    - Trade-off analysis
    - Feasibility assessment
    - Recommended option (lead with why)
    """
    topic = state.get("topic", "")
    requirements = state.get("requirements", "")
    constraints = state.get("brainstorm_constraints", [])
    success_criteria = state.get("brainstorm_success_criteria", [])
    existing_ideas = state.get("brainstorm_ideas", [])

    # Generate approaches if not already done
    if len(existing_ideas) < 2:
        ideas = _generate_approaches(topic, requirements, constraints, success_criteria)

        # Score and rank
        scored_ideas = _score_ideas(ideas, constraints, success_criteria)

        # Mark recommended
        if scored_ideas:
            scored_ideas[0]["is_recommended"] = True

        return {
            "brainstorm_ideas": scored_ideas,
            "brainstorm_phase": BrainstormPhase.EXPLORING.value,
            "awaiting_confirmation": True,
            "confirmation_reason": "brainstorm_approaches",
            "pending_decisions": state.get("pending_decisions", []) + [{
                "id": str(uuid.uuid4()),
                "question": _format_approaches_question(scored_ideas),
                "options": [
                    f"Select approach {i+1}" for i in range(len(scored_ideas))
                ] + ["Explore more options", "Provide custom approach"],
                "importance": "high",
                "context": "Brainstorm approach selection",
                "resolved": False,
                "chosen_option": None,
            }],
        }

    # Ideas already generated, move to presenting
    return {
        "brainstorm_phase": BrainstormPhase.PRESENTING.value,
        "errors": state.get("errors", []) + [
            "Brainstorm: Exploring phase complete, moving to presenting"
        ],
    }


def _presenting_phase(state: DesignState) -> Dict[str, Any]:
    """
    Phase 3: Presenting the Design

    Present in digestible sections (200-300 words each):
    - Architecture overview
    - Key components
    - Data/parameter flow
    - Error handling considerations
    - Testing approach

    Validate after each section.
    """
    topic = state.get("topic", "")
    ideas = state.get("brainstorm_ideas", [])

    # Get the selected/recommended idea
    selected_idea = next(
        (idea for idea in ideas if idea.get("is_recommended")),
        ideas[0] if ideas else None
    )

    if not selected_idea:
        return {
            "brainstorm_phase": BrainstormPhase.COMPLETE.value,
            "errors": state.get("errors", []) + ["No idea selected for presentation"],
        }

    # Generate design sections
    sections = _generate_design_sections(topic, selected_idea)

    # Format for presentation
    presentation = _format_presentation(topic, selected_idea, sections)

    return {
        "brainstorm_phase": BrainstormPhase.COMPLETE.value,
        "final_proposal": presentation,
        "requirements": _extract_requirements_from_idea(selected_idea),
        "awaiting_confirmation": True,
        "confirmation_reason": "brainstorm_design_approval",
        "pending_decisions": state.get("pending_decisions", []) + [{
            "id": str(uuid.uuid4()),
            "question": "Please review the proposed design. Do you want to proceed?",
            "options": ["Approve and proceed", "Request modifications", "Start over"],
            "importance": "high",
            "context": "Brainstorm design approval",
            "resolved": False,
            "chosen_option": None,
        }],
    }


def _complete_phase(state: DesignState) -> Dict[str, Any]:
    """
    Complete brainstorming and transition to workflow
    """
    return {
        "brainstorm_phase": None,
        "intent_type": "workflow",
        "current_stage": "decomposition",
        "errors": state.get("errors", []) + [
            "Brainstorm: Complete, transitioning to workflow"
        ],
    }


# === Helper Functions ===

def _generate_understanding_questions(
    topic: str,
    requirements: str,
    existing_constraints: List[str]
) -> Dict[str, str]:
    """Generate questions for understanding phase"""
    return {
        "purpose": f"What is the primary purpose of '{topic}'? What problem does it solve?",
        "constraints": (
            "What constraints should I be aware of?\n"
            "Consider:\n"
            "- Technical constraints (materials, dimensions, compatibility)\n"
            "- User constraints (who uses it, how)\n"
            "- Business constraints (time, cost, resources)"
        ),
        "success": (
            "How would you define success for this design?\n"
            "What criteria should I use to evaluate approaches?"
        ),
        "context": f"Is there any existing design or pattern in the codebase I should reference?",
    }


def _generate_approaches(
    topic: str,
    requirements: str,
    constraints: List[str],
    success_criteria: List[str]
) -> List[BrainstormIdea]:
    """Generate 2-3 design approaches"""
    # In full implementation, this would use LLM to generate diverse approaches
    # For now, generate template approaches

    approaches = [
        BrainstormIdea(
            id=str(uuid.uuid4()),
            content=f"Approach 1: Minimal Design for '{topic}'\n\n"
                    f"Focus on simplicity and core functionality. "
                    f"Use basic Grasshopper components with clear parameter flow. "
                    f"Prioritize maintainability over features.",
            feasibility=0.9,
            novelty=0.3,
            alignment=0.7,
            source_phase="exploring",
            is_recommended=False,
            trade_offs=[
                "Pro: Easy to implement and maintain",
                "Pro: Lower risk of errors",
                "Con: May lack advanced features",
                "Con: Limited flexibility",
            ],
        ),
        BrainstormIdea(
            id=str(uuid.uuid4()),
            content=f"Approach 2: Parametric Design for '{topic}'\n\n"
                    f"Highly configurable with extensive slider controls. "
                    f"Use Division, Mass Addition for calculations. "
                    f"Support for variants through parameter adjustment.",
            feasibility=0.7,
            novelty=0.6,
            alignment=0.8,
            source_phase="exploring",
            is_recommended=False,
            trade_offs=[
                "Pro: Highly flexible and customizable",
                "Pro: Supports design exploration",
                "Con: More complex to set up",
                "Con: More potential points of failure",
            ],
        ),
        BrainstormIdea(
            id=str(uuid.uuid4()),
            content=f"Approach 3: Modular Design for '{topic}'\n\n"
                    f"Break into reusable components/joseki. "
                    f"Each module handles one aspect. "
                    f"Easy to extend and modify individual parts.",
            feasibility=0.6,
            novelty=0.8,
            alignment=0.75,
            source_phase="exploring",
            is_recommended=False,
            trade_offs=[
                "Pro: Highly reusable components",
                "Pro: Easy to test and debug",
                "Con: Higher initial setup cost",
                "Con: May be overkill for simple designs",
            ],
        ),
    ]

    return approaches


def _score_ideas(
    ideas: List[BrainstormIdea],
    constraints: List[str],
    success_criteria: List[str]
) -> List[BrainstormIdea]:
    """Score and sort ideas"""
    # Calculate composite score
    for idea in ideas:
        # Weighted scoring
        composite = (
            idea["feasibility"] * 0.4 +
            idea["alignment"] * 0.4 +
            idea["novelty"] * 0.2
        )
        # Store in alignment field for sorting
        idea["alignment"] = composite

    # Sort by composite score (descending)
    return sorted(ideas, key=lambda x: x["alignment"], reverse=True)


def _format_approaches_question(ideas: List[BrainstormIdea]) -> str:
    """Format approaches for user selection"""
    lines = ["I've generated the following approaches:\n"]

    for i, idea in enumerate(ideas, 1):
        recommended = " (Recommended)" if idea.get("is_recommended") else ""
        lines.append(f"**Approach {i}{recommended}**")
        lines.append(idea["content"][:200] + "...")
        lines.append("\nTrade-offs:")
        for trade in idea.get("trade_offs", [])[:3]:
            lines.append(f"  - {trade}")
        lines.append("")

    lines.append("\nWhich approach would you like to pursue?")
    return "\n".join(lines)


def _generate_design_sections(
    topic: str,
    idea: BrainstormIdea
) -> Dict[str, str]:
    """Generate design sections (200-300 words each)"""
    return {
        "architecture": (
            f"## Architecture Overview\n\n"
            f"The design for '{topic}' follows a layered approach:\n"
            f"1. Input Layer: Parameter sliders and controls\n"
            f"2. Calculation Layer: Division, Addition for derived values\n"
            f"3. Geometry Layer: Primitives and transformations\n"
            f"4. Output Layer: Final solid union or assembly"
        ),
        "components": (
            f"## Key Components\n\n"
            f"- Number Sliders: Primary parameters (dimensions, counts)\n"
            f"- Division/Negative: Derived calculations\n"
            f"- Construct Point: Position definitions\n"
            f"- XY Plane: Orientation planes\n"
            f"- Center Box/Cylinder: Geometry primitives\n"
            f"- Solid Union: Final assembly"
        ),
        "data_flow": (
            f"## Parameter Flow\n\n"
            f"Sliders → Calculations → Points → Planes → Geometry → Union\n\n"
            f"Each parameter should have clear naming and range constraints."
        ),
        "error_handling": (
            f"## Error Handling\n\n"
            f"- Validate slider ranges (min/max)\n"
            f"- Check connection compatibility\n"
            f"- Handle null geometry gracefully\n"
            f"- Log connection failures for debugging"
        ),
        "testing": (
            f"## Testing Approach\n\n"
            f"- Test with default parameter values\n"
            f"- Test edge cases (min/max values)\n"
            f"- Verify all connections succeed\n"
            f"- Visual inspection in Rhino viewport"
        ),
    }


def _format_presentation(
    topic: str,
    idea: BrainstormIdea,
    sections: Dict[str, str]
) -> str:
    """Format the complete design presentation"""
    lines = [
        f"# Design Proposal: {topic}",
        f"*Generated: {datetime.now().isoformat()}*",
        "",
        "## Summary",
        idea["content"],
        "",
    ]

    for section_name, section_content in sections.items():
        lines.append(section_content)
        lines.append("")

    lines.extend([
        "## Trade-offs",
        "",
    ])
    for trade in idea.get("trade_offs", []):
        lines.append(f"- {trade}")

    return "\n".join(lines)


def _extract_requirements_from_idea(idea: BrainstormIdea) -> str:
    """Extract requirements from selected idea"""
    return idea["content"]


# === Entry/Exit Utilities ===

def enter_brainstorm_mode(state: DesignState) -> Dict[str, Any]:
    """Initialize Brainstorm mode"""
    return {
        "brainstorm_phase": BrainstormPhase.UNDERSTANDING.value,
        "brainstorm_ideas": [],
        "brainstorm_constraints": [],
        "brainstorm_success_criteria": [],
        "intent_type": "brainstorm",
    }


def exit_brainstorm_mode(state: DesignState) -> Dict[str, Any]:
    """Clean exit from Brainstorm mode"""
    return {
        "brainstorm_phase": None,
        "current_stage": "decomposition",
    }


def add_constraint(state: DesignState, constraint: str) -> Dict[str, Any]:
    """Add a constraint identified during understanding"""
    constraints = state.get("brainstorm_constraints", [])
    return {
        "brainstorm_constraints": constraints + [constraint],
    }


def add_success_criterion(state: DesignState, criterion: str) -> Dict[str, Any]:
    """Add a success criterion identified during understanding"""
    criteria = state.get("brainstorm_success_criteria", [])
    return {
        "brainstorm_success_criteria": criteria + [criterion],
    }


def select_approach(state: DesignState, approach_index: int) -> Dict[str, Any]:
    """Select an approach to pursue"""
    ideas = state.get("brainstorm_ideas", [])

    if 0 <= approach_index < len(ideas):
        # Mark selected as recommended
        updated_ideas = []
        for i, idea in enumerate(ideas):
            idea_copy = dict(idea)
            idea_copy["is_recommended"] = (i == approach_index)
            updated_ideas.append(idea_copy)

        return {
            "brainstorm_ideas": updated_ideas,
            "brainstorm_phase": BrainstormPhase.PRESENTING.value,
        }

    return {}
