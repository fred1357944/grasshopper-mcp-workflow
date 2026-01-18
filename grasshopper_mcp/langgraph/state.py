"""
State definitions for LangGraph Grasshopper Workflow

Defines the core state schema for:
- Design optimization iterations
- Multi-variant exploration
- Human-in-the-loop decision points
- Superpower integration (Think-Partner, Brainstorm, Meta-Agent)
"""

from typing import TypedDict, Literal, Optional, Annotated, List, Dict, Any
from datetime import datetime
from enum import Enum
import operator


class OptimizationMode(str, Enum):
    """Workflow mode selection"""
    ITERATIVE = "iterative"      # Option A: Iterative Design Optimization
    MULTI_VARIANT = "multi_variant"  # Option B: Multi-Variant Exploration


class IntentType(str, Enum):
    """High-level intent classification for Superpower routing"""
    WORKFLOW = "workflow"           # Standard 4-stage pipeline
    META_AGENT = "meta_agent"       # Dynamic tool/agent creation
    THINK_PARTNER = "think_partner" # Socratic exploration (Claudesidian)
    BRAINSTORM = "brainstorm"       # 3-phase creative exploration (Superpowers)


class BrainstormPhase(str, Enum):
    """Brainstorm phases from Superpowers methodology"""
    UNDERSTANDING = "understanding"  # Phase 1: Clarify problem space
    EXPLORING = "exploring"          # Phase 2: Divergent ideation
    PRESENTING = "presenting"        # Phase 3: Convergent prioritization
    COMPLETE = "complete"


class ThinkingMode(str, Enum):
    """Think-Partner modes from Claudesidian"""
    THINKING = "thinking"  # Generate questions, explore assumptions
    WRITING = "writing"    # Synthesize insights into actionable outputs


class WorkflowStage(str, Enum):
    """4-stage Workflow Pipeline stages"""
    DECOMPOSITION = "decomposition"      # Stage 1: Intent decomposition
    TOOL_RETRIEVAL = "tool_retrieval"    # Stage 2: Tool/Joseki retrieval
    PROMPT_GENERATION = "prompt_generation"  # Stage 3: Prompt generation
    CONFIG_ASSEMBLY = "config_assembly"  # Stage 4: Config assembly
    COMPLETE = "complete"


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


# === Superpower TypedDicts ===

class ThinkingEntry(TypedDict):
    """A single entry in the Think-Partner thinking log"""
    question: str
    reflection: str
    insights: List[str]
    connections: List[str]  # Links to other ideas/knowledge
    timestamp: str


class BrainstormIdea(TypedDict):
    """A brainstorm idea with evaluation scores"""
    id: str
    content: str
    feasibility: float      # 0-1: How practical to implement
    novelty: float          # 0-1: How creative/innovative
    alignment: float        # 0-1: How well it meets requirements
    source_phase: str       # Which phase generated this
    is_recommended: bool
    trade_offs: List[str]


class GeneratedTool(TypedDict):
    """A dynamically generated tool by Meta-Agent"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    implementation: str     # Python code or MCP command template
    joseki_id: Optional[str]  # If stored in Joseki library
    created_at: str


class AgentConfig(TypedDict):
    """Configuration for a dynamically created agent"""
    name: str
    description: str
    tools: List[str]
    system_prompt: str
    confidence_threshold: float


class SubTask(TypedDict):
    """A subtask in the Workflow Pipeline"""
    id: str
    name: str
    description: str
    dependencies: List[str]      # Names of dependent subtasks
    status: Literal["pending", "in_progress", "completed", "failed"]
    component_type: str          # workflow, joseki, custom
    parameters: Dict[str, Any]


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

    # === Superpower: Intent Classification ===
    intent_type: Optional[str]           # IntentType value
    intent_confidence: float             # 0-1 confidence in classification
    intent_keywords: List[str]           # Matched keywords

    # === Superpower: Think-Partner Mode (Claudesidian) ===
    thinking_mode: Optional[str]         # ThinkingMode value
    thinking_log: List[ThinkingEntry]    # Captured thoughts and questions
    thinking_insights: List[str]         # Synthesized insights

    # === Superpower: Brainstorm Mode (Superpowers) ===
    brainstorm_phase: Optional[str]      # BrainstormPhase value
    brainstorm_ideas: List[BrainstormIdea]
    brainstorm_constraints: List[str]    # Identified constraints
    brainstorm_success_criteria: List[str]

    # === Superpower: Meta-Agent Mode ===
    meta_agent_active: bool
    meta_agent_operation: Optional[str]  # search_tool/create_tool/ask_user/create_agent_config
    generated_tools: List[GeneratedTool]
    agent_configs: List[AgentConfig]

    # === Superpower: Workflow Pipeline (4-stage) ===
    subtasks: List[SubTask]                  # Decomposed subtasks (typed)
    workflow_subtasks: List[Dict[str, Any]]  # Decomposed subtasks (legacy)
    retrieved_tools: List[Dict[str, Any]]    # Retrieved tools/joseki
    execution_prompts: List[Dict[str, Any]]  # Generated execution prompts
    execution_plan: Optional[str]            # Overall execution plan
    component_id_map: Dict[str, str]         # Logical name → GUID map
    workflow_stage_outputs: Dict[str, Dict[str, Any]]  # Stage outputs
    joseki_patterns: List[Dict[str, Any]]    # Matched joseki patterns
    final_output: Optional[Dict[str, Any]]   # Final assembled output


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

        # Superpower: Intent
        intent_type=None,
        intent_confidence=0.0,
        intent_keywords=[],

        # Superpower: Think-Partner
        thinking_mode=None,
        thinking_log=[],
        thinking_insights=[],

        # Superpower: Brainstorm
        brainstorm_phase=None,
        brainstorm_ideas=[],
        brainstorm_constraints=[],
        brainstorm_success_criteria=[],

        # Superpower: Meta-Agent
        meta_agent_active=False,
        meta_agent_operation=None,
        generated_tools=[],
        agent_configs=[],

        # Superpower: Workflow Pipeline
        subtasks=[],
        workflow_subtasks=[],
        retrieved_tools=[],
        execution_prompts=[],
        execution_plan=None,
        component_id_map={},
        workflow_stage_outputs={},
        joseki_patterns=[],
        final_output=None,
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
