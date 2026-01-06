"""
Option A: Iterative Design Optimization Workflow

Implements the Claude-Gemini alternating optimization loop:
1. Requirements → 2. Decomposition → 3. Connectivity → 4. Execution → 5. Optimization Loop → 6. Complete

With validation loops and human decision points at each stage.
"""

from typing import Literal
from ..state import DesignState, should_pause_for_confirmation

# Note: In production, import from langgraph
# from langgraph.graph import StateGraph, END


def create_iterative_workflow():
    """
    Create the iterative design optimization workflow

    Graph Structure:
    ```
    [START]
        │
        ▼
    [clarify_requirements]
        │
        ├─── needs_clarification ──→ [human_decision] ──→ [clarify_requirements]
        │
        ▼
    [decompose_geometry]
        │
        ├─── validation_failed ──→ [validate_decomposition] ──→ [decompose_geometry]
        │
        ▼
    [plan_connectivity]
        │
        ├─── conflicts_found ──→ [detect_conflicts] ──→ [plan_connectivity]
        │
        ▼
    [execute_placement]
        │
        ├─── errors ──→ [analyze_errors] ──→ [optimize_parameters]
        │
        ▼
    [optimize_parameters] ◄─────────────────────────────┐
        │                                                │
        ▼                                                │
    [check_convergence]                                  │
        │                                                │
        ├─── not_converged ──────────────────────────────┘
        │
        ├─── converged ──→ [human_decision] ──→ [END]
        │
        └─── max_iterations ──→ [human_decision] ──→ [END]
    ```

    Returns:
        Compiled LangGraph workflow
    """
    # Placeholder: In production, use actual LangGraph
    # from langgraph.graph import StateGraph, END

    # Define the graph structure
    graph_definition = {
        "nodes": [
            "clarify_requirements",
            "decompose_geometry",
            "validate_decomposition",
            "plan_connectivity",
            "detect_conflicts",
            "execute_placement",
            "analyze_errors",
            "optimize_parameters",
            "check_convergence",
            "human_decision",
        ],
        "edges": [
            # Main flow
            ("START", "clarify_requirements"),
            ("clarify_requirements", "decompose_geometry"),
            ("decompose_geometry", "plan_connectivity"),
            ("plan_connectivity", "execute_placement"),
            ("execute_placement", "optimize_parameters"),
            ("optimize_parameters", "check_convergence"),

            # Validation loops
            ("clarify_requirements", "human_decision", "needs_clarification"),
            ("human_decision", "clarify_requirements", "resume_requirements"),

            ("decompose_geometry", "validate_decomposition", "needs_validation"),
            ("validate_decomposition", "decompose_geometry", "fix_decomposition"),
            ("validate_decomposition", "plan_connectivity", "valid"),

            ("plan_connectivity", "detect_conflicts", "check_conflicts"),
            ("detect_conflicts", "plan_connectivity", "has_conflicts"),
            ("detect_conflicts", "execute_placement", "no_conflicts"),

            ("execute_placement", "analyze_errors", "has_errors"),
            ("analyze_errors", "optimize_parameters", "proceed"),
            ("analyze_errors", "human_decision", "needs_decision"),

            # Optimization loop
            ("check_convergence", "optimize_parameters", "not_converged"),
            ("check_convergence", "human_decision", "converged"),
            ("check_convergence", "human_decision", "max_iterations"),

            # Final
            ("human_decision", "END", "approved"),
        ],
        "conditional_edges": {
            "clarify_requirements": _route_after_requirements,
            "decompose_geometry": _route_after_decomposition,
            "plan_connectivity": _route_after_connectivity,
            "execute_placement": _route_after_execution,
            "check_convergence": _route_after_convergence,
            "human_decision": _route_after_decision,
        }
    }

    return IterativeWorkflow(graph_definition)


class IterativeWorkflow:
    """
    Iterative workflow runner

    In production, this would be a compiled LangGraph StateGraph.
    This class provides a compatible interface for testing.
    """

    def __init__(self, graph_definition: dict):
        self.graph = graph_definition
        self.current_node = "START"

    def invoke(self, state: DesignState) -> DesignState:
        """
        Run the workflow to completion or until human input needed

        Args:
            state: Initial or current state

        Returns:
            Updated state
        """
        from ..nodes import (
            clarify_requirements_node,
            decompose_geometry_node,
            validate_decomposition_node,
            plan_connectivity_node,
            detect_conflicts_node,
            execute_placement_node,
            analyze_errors_node,
            optimize_parameters_node,
            check_convergence_node,
            human_decision_node,
        )

        node_functions = {
            "clarify_requirements": clarify_requirements_node,
            "decompose_geometry": decompose_geometry_node,
            "validate_decomposition": validate_decomposition_node,
            "plan_connectivity": plan_connectivity_node,
            "detect_conflicts": detect_conflicts_node,
            "execute_placement": execute_placement_node,
            "analyze_errors": analyze_errors_node,
            "optimize_parameters": optimize_parameters_node,
            "check_convergence": check_convergence_node,
            "human_decision": human_decision_node,
        }

        max_steps = 100
        step = 0

        while step < max_steps:
            step += 1

            # Check if we need human input
            if state.get("awaiting_confirmation"):
                break

            # Check if complete
            if state.get("current_stage") == "complete":
                break

            # Get next node based on current stage
            current_stage = state.get("current_stage", "requirements")
            node_name = self._stage_to_node(current_stage)

            if node_name not in node_functions:
                break

            # Execute node
            node_fn = node_functions[node_name]
            updates = node_fn(state)

            # Apply updates
            state = {**state, **updates}

        return state

    def _stage_to_node(self, stage: str) -> str:
        """Map stage to node name"""
        stage_to_node = {
            "requirements": "clarify_requirements",
            "decomposition": "decompose_geometry",
            "connectivity": "plan_connectivity",
            "guid_resolution": "execute_placement",
            "execution": "execute_placement",
            "evaluation": "check_convergence",
            "optimization": "optimize_parameters",
        }
        return stage_to_node.get(stage, "clarify_requirements")


# === Routing Functions ===

def _route_after_requirements(state: DesignState) -> Literal["decompose", "human"]:
    """Route after requirements clarification"""
    if state.get("pending_decisions"):
        unresolved = [d for d in state["pending_decisions"] if not d["resolved"]]
        if unresolved:
            return "human"
    return "decompose"


def _route_after_decomposition(state: DesignState) -> Literal["validate", "connectivity"]:
    """Route after geometry decomposition"""
    if not state.get("part_info_mmd"):
        return "validate"
    return "connectivity"


def _route_after_connectivity(state: DesignState) -> Literal["check_conflicts", "execute"]:
    """Route after connectivity planning"""
    # Always check for conflicts
    return "check_conflicts"


def _route_after_execution(state: DesignState) -> Literal["errors", "optimize"]:
    """Route after execution"""
    if state.get("errors"):
        return "errors"
    return "optimize"


def _route_after_convergence(state: DesignState) -> Literal["continue", "converged", "max_iter"]:
    """Route after convergence check"""
    if state.get("is_converged"):
        return "converged"
    if state["current_iteration"] >= state["max_iterations"]:
        return "max_iter"
    return "continue"


def _route_after_decision(state: DesignState) -> Literal["continue", "end"]:
    """Route after human decision"""
    if state.get("user_approved"):
        return "end"
    return "continue"
