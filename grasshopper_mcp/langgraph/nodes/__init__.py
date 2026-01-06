"""
LangGraph Nodes for Grasshopper Workflow

Each node represents a step in the design workflow:
- Requirements clarification
- Geometric decomposition (with Mermaid file generation)
- Component connectivity planning (with Mermaid file generation)
- GUID resolution
- Execution
- Evaluation and optimization

Enhanced v2.0:
- File-first approach: generates .mmd files before state updates
- Human confirmation checkpoints at each stage
- Gemini integration for validation
"""

from .requirements import clarify_requirements_node
from .decomposition import (
    decompose_geometry_node,
    confirm_decomposition_node,
    validate_decomposition_node,
)
from .connectivity import (
    plan_connectivity_node,
    confirm_connectivity_node,
    detect_conflicts_node,
)
from .execution import execute_placement_node, analyze_errors_node
from .optimization import optimize_parameters_node, check_convergence_node
from .human_review import human_decision_node
from .variants import generate_variants_node, evaluate_variants_node, select_best_variant_node

__all__ = [
    # Core workflow nodes
    "clarify_requirements_node",

    # Step 2: Decomposition (writes part_info.mmd)
    "decompose_geometry_node",
    "confirm_decomposition_node",
    "validate_decomposition_node",

    # Step 3: Connectivity (writes component_info.mmd)
    "plan_connectivity_node",
    "confirm_connectivity_node",
    "detect_conflicts_node",

    # Step 4-5: Execution
    "execute_placement_node",
    "analyze_errors_node",

    # Optimization nodes
    "optimize_parameters_node",
    "check_convergence_node",

    # Human-in-the-loop
    "human_decision_node",

    # Multi-variant nodes
    "generate_variants_node",
    "evaluate_variants_node",
    "select_best_variant_node",
]
