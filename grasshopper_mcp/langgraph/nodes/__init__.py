"""
LangGraph Nodes for Grasshopper Workflow

Each node represents a step in the design workflow:
- Requirements clarification
- Geometric decomposition
- Component connectivity planning
- GUID resolution
- Execution
- Evaluation and optimization
"""

from .requirements import clarify_requirements_node
from .decomposition import decompose_geometry_node, validate_decomposition_node
from .connectivity import plan_connectivity_node, detect_conflicts_node
from .execution import execute_placement_node, analyze_errors_node
from .optimization import optimize_parameters_node, check_convergence_node
from .human_review import human_decision_node
from .variants import generate_variants_node, evaluate_variants_node, select_best_variant_node

__all__ = [
    # Core workflow nodes
    "clarify_requirements_node",
    "decompose_geometry_node",
    "validate_decomposition_node",
    "plan_connectivity_node",
    "detect_conflicts_node",
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
