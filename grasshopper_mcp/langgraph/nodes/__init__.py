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
from .vision_capture import vision_capture_node, VisionCapture
from .vision_analysis import vision_analysis_node, VisionAnalyzer, ErrorDetection
from .auto_fix import auto_fix_node, joseki_lookup_node, AutoFixAgent

# Superpower nodes (v3.0)
from .think_partner import (
    think_partner_node,
    enter_think_partner_mode,
    exit_think_partner_mode,
    add_user_response,
)
from .brainstorm import (
    brainstorm_node,
    enter_brainstorm_mode,
    exit_brainstorm_mode,
    add_constraint,
    add_success_criterion,
    select_approach,
)
from .meta_agent import (
    meta_agent_node,
    enter_meta_agent_mode,
    exit_meta_agent_mode,
    MetaAgentOperation,
)
from .workflow_pipeline import (
    intent_decomposition_node,
    tool_retrieval_node,
    prompt_generation_node,
    config_assembly_node,
    enter_workflow_mode,
    exit_workflow_mode,
    get_current_stage_node,
)

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

    # Vision nodes (v2.1)
    "vision_capture_node",
    "vision_analysis_node",
    "VisionCapture",
    "VisionAnalyzer",
    "ErrorDetection",

    # Auto-fix nodes (v2.1)
    "auto_fix_node",
    "joseki_lookup_node",
    "AutoFixAgent",

    # Superpower nodes (v3.0) - Think-Partner
    "think_partner_node",
    "enter_think_partner_mode",
    "exit_think_partner_mode",
    "add_user_response",

    # Superpower nodes (v3.0) - Brainstorm
    "brainstorm_node",
    "enter_brainstorm_mode",
    "exit_brainstorm_mode",
    "add_constraint",
    "add_success_criterion",
    "select_approach",

    # Superpower nodes (v3.0) - Meta-Agent
    "meta_agent_node",
    "enter_meta_agent_mode",
    "exit_meta_agent_mode",
    "MetaAgentOperation",

    # Superpower nodes (v3.0) - Workflow Pipeline
    "intent_decomposition_node",
    "tool_retrieval_node",
    "prompt_generation_node",
    "config_assembly_node",
    "enter_workflow_mode",
    "exit_workflow_mode",
    "get_current_stage_node",
]
