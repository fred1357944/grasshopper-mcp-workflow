"""
Option B: Multi-Variant Design Exploration Workflow

Implements parallel variant generation and evaluation:
1. Requirements → 2. Decomposition → 3. Connectivity → 4. Generate Variants → 5. Evaluate All → 6. Select Best → 7. Complete

With optional follow-up optimization of the selected variant.
"""

from typing import Literal
from ..state import DesignState


def create_multivariant_workflow():
    """
    Create the multi-variant exploration workflow

    Graph Structure:
    ```
    [START]
        │
        ▼
    [clarify_requirements]
        │
        ▼
    [decompose_geometry]
        │
        ▼
    [plan_connectivity]
        │
        ▼
    [generate_variants]
        │
        ▼
    [evaluate_variants] ◄──────────────────────┐
        │                                       │
        ▼                                       │
    [select_best_variant]                       │
        │                                       │
        ├─── all_failed ────────────────────────┘
        │
        ├─── needs_review ──→ [human_decision]
        │                           │
        │                           ├─── optimize_more ──→ [optimize_variant] ──→ [evaluate_variants]
        │                           │
        │                           └─── approved ──→ [END]
        │
        └─── auto_approved ──→ [END]
    ```

    Returns:
        Compiled LangGraph workflow
    """
    graph_definition = {
        "nodes": [
            "clarify_requirements",
            "decompose_geometry",
            "plan_connectivity",
            "generate_variants",
            "evaluate_variants",
            "select_best_variant",
            "human_decision",
            "optimize_variant",
        ],
        "edges": [
            # Main flow
            ("START", "clarify_requirements"),
            ("clarify_requirements", "decompose_geometry"),
            ("decompose_geometry", "plan_connectivity"),
            ("plan_connectivity", "generate_variants"),
            ("generate_variants", "evaluate_variants"),
            ("evaluate_variants", "select_best_variant"),

            # Selection routing
            ("select_best_variant", "human_decision", "needs_review"),
            ("select_best_variant", "generate_variants", "all_failed"),
            ("select_best_variant", "END", "auto_approved"),

            # After human decision
            ("human_decision", "optimize_variant", "optimize_more"),
            ("human_decision", "END", "approved"),
            ("optimize_variant", "evaluate_variants", "continue"),
        ],
        "conditional_edges": {
            "select_best_variant": _route_after_selection,
            "human_decision": _route_after_decision,
        }
    }

    return MultiVariantWorkflow(graph_definition)


class MultiVariantWorkflow:
    """
    Multi-variant workflow runner

    In production, this would be a compiled LangGraph StateGraph.
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
            plan_connectivity_node,
            generate_variants_node,
            evaluate_variants_node,
            select_best_variant_node,
            human_decision_node,
            optimize_parameters_node,  # Reuse for variant optimization
        )

        node_functions = {
            "clarify_requirements": clarify_requirements_node,
            "decompose_geometry": decompose_geometry_node,
            "plan_connectivity": plan_connectivity_node,
            "generate_variants": generate_variants_node,
            "evaluate_variants": evaluate_variants_node,
            "select_best_variant": select_best_variant_node,
            "human_decision": human_decision_node,
            "optimize_variant": optimize_parameters_node,
        }

        # Stage to node mapping for multi-variant mode
        stage_to_node = {
            "requirements": "clarify_requirements",
            "decomposition": "decompose_geometry",
            "connectivity": "plan_connectivity",
            "guid_resolution": "generate_variants",
            "execution": "evaluate_variants",
            "evaluation": "select_best_variant",
            "optimization": "optimize_variant",
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
            node_name = stage_to_node.get(current_stage, "clarify_requirements")

            if node_name not in node_functions:
                break

            # Execute node
            node_fn = node_functions[node_name]
            updates = node_fn(state)

            # Apply updates
            state = {**state, **updates}

        return state


# === Routing Functions ===

def _route_after_selection(state: DesignState) -> Literal["review", "retry", "done"]:
    """Route after variant selection"""
    selected = state.get("selected_variant_id")
    variants = state.get("variants", [])

    if not selected:
        # All failed
        valid_variants = [v for v in variants if v["quality_score"] > 0]
        if not valid_variants:
            return "retry"

    # Has selection, need review
    return "review"


def _route_after_decision(state: DesignState) -> Literal["optimize", "done"]:
    """Route after human decision"""
    if state.get("user_approved"):
        return "done"

    # Check if user wants more optimization
    decisions = state.get("decisions_made", [])
    for d in decisions:
        if d.get("chosen_option") == "optimize_more":
            return "optimize"

    return "done"


def create_parallel_evaluation_subgraph():
    """
    Create a subgraph for parallel variant evaluation

    This would use LangGraph's map-reduce pattern:
    - Map: Evaluate each variant independently
    - Reduce: Collect all results

    ```
    [variants]
        │
        ├──→ [evaluate_variant_1]
        ├──→ [evaluate_variant_2]
        ├──→ [evaluate_variant_3]
        ...
        │
        ▼
    [collect_results]
    ```
    """
    # Placeholder for parallel evaluation
    # In production, use LangGraph's map operation

    return {
        "type": "parallel_map",
        "map_node": "evaluate_single_variant",
        "reduce_node": "collect_variant_results",
        "input_key": "variants",
        "output_key": "evaluated_variants",
    }
