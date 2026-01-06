"""
Human-in-the-Loop Review Node

Handles decision points that require human confirmation
"""

from typing import Any
from ..state import DesignState, Decision


def human_decision_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Human decision point

    This node:
    1. Presents pending decisions to user
    2. Waits for user input
    3. Records decisions
    4. Determines next stage based on decisions

    In practice, this integrates with Claude to:
    - Present options clearly
    - Collect user choice
    - Apply the decision

    Note: In LangGraph, this would use interrupt_before or
    a human-in-the-loop pattern with checkpointing.
    """
    pending = state.get("pending_decisions", [])
    unresolved = [d for d in pending if not d["resolved"]]

    if not unresolved:
        # No decisions needed, continue
        return _determine_next_stage(state)

    # In production, this would:
    # 1. Use LangGraph's interrupt mechanism
    # 2. Present choices to user via Claude
    # 3. Wait for and process response

    # For now, mark awaiting confirmation
    return {
        "awaiting_confirmation": True,
        "confirmation_reason": "pending_decisions",
    }


def apply_decision(state: DesignState, decision_id: str, chosen_option: str) -> dict[str, Any]:
    """
    Apply a human decision

    Args:
        state: Current state
        decision_id: ID of the decision
        chosen_option: The option chosen by the user

    Returns:
        State updates
    """
    pending = state.get("pending_decisions", [])
    decisions_made = state.get("decisions_made", [])

    # Find and update the decision
    updated_pending = []
    new_decisions_made = []

    for decision in pending:
        if decision["id"] == decision_id:
            # Mark as resolved
            resolved_decision = Decision(
                id=decision["id"],
                question=decision["question"],
                options=decision["options"],
                importance=decision["importance"],
                context=decision["context"],
                resolved=True,
                chosen_option=chosen_option
            )
            new_decisions_made.append(resolved_decision)
        else:
            updated_pending.append(decision)

    # Check if all high-priority decisions are resolved
    remaining_high = [
        d for d in updated_pending
        if d["importance"] == "high" and not d["resolved"]
    ]

    return {
        "pending_decisions": updated_pending,
        "decisions_made": new_decisions_made,
        "awaiting_confirmation": len(remaining_high) > 0,
    }


def _determine_next_stage(state: DesignState) -> dict[str, Any]:
    """
    Determine next stage after decisions are made

    Based on:
    - Current stage
    - Decisions made
    - Errors present
    """
    current_stage = state.get("current_stage", "requirements")
    errors = state.get("errors", [])

    # Stage progression logic
    stage_order = [
        "requirements",
        "decomposition",
        "connectivity",
        "guid_resolution",
        "execution",
        "evaluation",
        "optimization",
        "complete"
    ]

    try:
        current_index = stage_order.index(current_stage)
    except ValueError:
        current_index = 0

    # If there are errors, stay in current stage or go to optimization
    if errors:
        return {
            "current_stage": "optimization",
            "awaiting_confirmation": False,
        }

    # Otherwise, advance to next stage
    next_index = min(current_index + 1, len(stage_order) - 1)
    return {
        "current_stage": stage_order[next_index],
        "awaiting_confirmation": False,
    }


def format_decision_for_display(decision: Decision) -> str:
    """
    Format a decision for display to user

    Returns formatted markdown string
    """
    importance_emoji = {
        "high": "🔴",
        "medium": "🟡",
        "low": "🟢"
    }

    options_formatted = "\n".join([
        f"  {i+1}. {opt}"
        for i, opt in enumerate(decision["options"])
    ])

    return f"""
{importance_emoji.get(decision['importance'], '⚪')} **{decision['question']}**

Context: {decision['context']}

Options:
{options_formatted}
"""


def format_all_pending_decisions(state: DesignState) -> str:
    """
    Format all pending decisions for display

    Returns formatted markdown string
    """
    pending = state.get("pending_decisions", [])
    unresolved = [d for d in pending if not d["resolved"]]

    if not unresolved:
        return "No pending decisions."

    formatted = ["# Pending Decisions\n"]

    # Group by importance
    high = [d for d in unresolved if d["importance"] == "high"]
    medium = [d for d in unresolved if d["importance"] == "medium"]
    low = [d for d in unresolved if d["importance"] == "low"]

    if high:
        formatted.append("## Critical Decisions (must resolve)\n")
        for d in high:
            formatted.append(format_decision_for_display(d))

    if medium:
        formatted.append("## Important Decisions\n")
        for d in medium:
            formatted.append(format_decision_for_display(d))

    if low:
        formatted.append("## Optional Decisions\n")
        for d in low:
            formatted.append(format_decision_for_display(d))

    return "\n".join(formatted)
