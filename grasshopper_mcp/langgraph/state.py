"""
State definitions for LangGraph Grasshopper Workflow

Defines the core state schema for:
- Design optimization iterations
- Multi-variant exploration
- Human-in-the-loop decision points
"""

from typing import TypedDict, Literal, Optional, Annotated
from datetime import datetime
from enum import Enum
import operator


class OptimizationMode(str, Enum):
    """Workflow mode selection"""
    ITERATIVE = "iterative"      # Option A: Iterative Design Optimization
    MULTI_VARIANT = "multi_variant"  # Option B: Multi-Variant Exploration


class Proposal(TypedDict):
    """A single design proposal from an AI"""
    ai: Literal["claude", "gemini"]
    content: str
    timestamp: str
    iteration: int
    score: Optional[float]


class Decision(TypedDict):
    """A decision point requiring human input"""
    id: str
    question: str
    options: list[str]
    importance: Literal["high", "medium", "low"]
    context: str
    resolved: bool
    chosen_option: Optional[str]


class DesignVariant(TypedDict):
    """A design variant for multi-variant exploration"""
    variant_id: str
    parameters: dict
    placement_info: Optional[dict]
    execution_result: Optional[dict]
    quality_score: float
    errors: list[str]


class DesignState(TypedDict):
    """
    Core state for Grasshopper design workflow

    Supports both:
    - Option A: Iterative optimization (single design, multiple refinements)
    - Option B: Multi-variant exploration (multiple designs, parallel evaluation)
    """

    # === Session Info ===
    session_id: str
    topic: str
    created_at: str
    mode: OptimizationMode

    # === Workflow Stage ===
    current_stage: Literal[
        "requirements",      # Step 1: Clarify requirements
        "decomposition",     # Step 2: Geometric decomposition
        "connectivity",      # Step 3: Component connectivity
        "guid_resolution",   # Step 4: GUID resolution & layout
        "execution",         # Step 5: Execute placement
        "evaluation",        # Step 6: Evaluate & cleanup
        "optimization",      # Optimization loop
        "complete"           # Workflow complete
    ]

    # === Iteration Control ===
    current_iteration: int
    max_iterations: int

    # === Design Artifacts ===
    requirements: str
    part_info_mmd: str
    component_info_mmd: str
    placement_info: Optional[dict]

    # === Option A: Iterative Optimization ===
    proposals: Annotated[list[Proposal], operator.add]
    convergence_score: float
    is_converged: bool

    # === Option B: Multi-Variant Exploration ===
    variants: list[DesignVariant]
    selected_variant_id: Optional[str]

    # === Execution Results ===
    execution_result: Optional[dict]
    errors: Annotated[list[str], operator.add]

    # === Human-in-the-loop ===
    pending_decisions: list[Decision]
    decisions_made: Annotated[list[Decision], operator.add]
    awaiting_confirmation: bool
    confirmation_reason: Optional[str]

    # === Final Output ===
    final_proposal: Optional[str]
    user_approved: bool


def create_initial_state(
    topic: str,
    mode: OptimizationMode = OptimizationMode.ITERATIVE,
    max_iterations: int = 5
) -> DesignState:
    """Create initial state for a new design session"""
    import uuid

    return DesignState(
        # Session
        session_id=str(uuid.uuid4()),
        topic=topic,
        created_at=datetime.now().isoformat(),
        mode=mode,

        # Stage
        current_stage="requirements",

        # Iteration
        current_iteration=0,
        max_iterations=max_iterations,

        # Artifacts
        requirements="",
        part_info_mmd="",
        component_info_mmd="",
        placement_info=None,

        # Iterative
        proposals=[],
        convergence_score=0.0,
        is_converged=False,

        # Multi-variant
        variants=[],
        selected_variant_id=None,

        # Execution
        execution_result=None,
        errors=[],

        # Human-in-the-loop
        pending_decisions=[],
        decisions_made=[],
        awaiting_confirmation=False,
        confirmation_reason=None,

        # Output
        final_proposal=None,
        user_approved=False,
    )


def should_pause_for_confirmation(state: DesignState) -> tuple[bool, str]:
    """
    Determine if workflow should pause for human confirmation

    Returns:
        (should_pause, reason)
    """
    # 1. Critical decisions pending
    high_importance = [
        d for d in state["pending_decisions"]
        if d["importance"] == "high" and not d["resolved"]
    ]
    if high_importance:
        return True, "critical_decision"

    # 2. Convergence reached
    if state["is_converged"] and state["convergence_score"] > 0.85:
        return True, "convergence_reached"

    # 3. Max iterations reached
    if state["current_iteration"] >= state["max_iterations"]:
        return True, "max_iterations_reached"

    return False, "continue"


def calculate_convergence(proposals: list[Proposal]) -> float:
    """
    Calculate convergence score based on proposal similarity

    Higher score = proposals are converging (AI opinions aligning)
    """
    if len(proposals) < 2:
        return 0.0

    # Simple heuristic: compare last two proposals
    # In production, use semantic similarity
    last_two = proposals[-2:]

    # Placeholder: check if same AI or different
    if last_two[0]["ai"] != last_two[1]["ai"]:
        # Different AIs agreeing = high convergence signal
        # Would compare content similarity in production
        return 0.7

    return 0.5
