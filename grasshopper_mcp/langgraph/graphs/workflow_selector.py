"""
Workflow Selector

Provides a unified interface to create and run either:
- Option A: Iterative Design Optimization
- Option B: Multi-Variant Design Exploration

Allows dynamic selection based on user preference or task requirements.
"""

from enum import Enum
from typing import Optional, Union
from ..state import DesignState, OptimizationMode, create_initial_state
from .iterative_workflow import create_iterative_workflow, IterativeWorkflow
from .multivariant_workflow import create_multivariant_workflow, MultiVariantWorkflow


class WorkflowType(str, Enum):
    """Available workflow types"""
    ITERATIVE = "iterative"  # Option A
    MULTI_VARIANT = "multi_variant"  # Option B
    AUTO = "auto"  # Automatically select based on context


def create_workflow(
    workflow_type: WorkflowType = WorkflowType.AUTO,
    topic: Optional[str] = None,
    max_iterations: int = 5,
) -> Union[IterativeWorkflow, MultiVariantWorkflow]:
    """
    Create a workflow based on the specified type

    Args:
        workflow_type: Which workflow to create
        topic: Optional topic for auto-selection heuristics
        max_iterations: Maximum iterations (for iterative) or variants (for multi-variant)

    Returns:
        Configured workflow instance
    """
    if workflow_type == WorkflowType.AUTO:
        workflow_type = _auto_select_workflow(topic)

    if workflow_type == WorkflowType.ITERATIVE:
        return create_iterative_workflow()
    else:
        return create_multivariant_workflow()


def _auto_select_workflow(topic: Optional[str]) -> WorkflowType:
    """
    Automatically select workflow based on topic/context

    Heuristics:
    - Keywords suggesting exploration → Multi-variant
    - Keywords suggesting refinement → Iterative
    - Default → Iterative
    """
    if not topic:
        return WorkflowType.ITERATIVE

    topic_lower = topic.lower()

    # Multi-variant indicators
    multi_variant_keywords = [
        "explore", "探索",
        "variants", "變體",
        "options", "選項",
        "compare", "比較",
        "alternatives", "替代",
        "try different", "嘗試不同",
        "generate", "生成多個",
    ]

    # Iterative indicators
    iterative_keywords = [
        "optimize", "優化",
        "improve", "改進",
        "refine", "精煉",
        "fix", "修正",
        "adjust", "調整",
        "tune", "調優",
    ]

    for kw in multi_variant_keywords:
        if kw in topic_lower:
            return WorkflowType.MULTI_VARIANT

    for kw in iterative_keywords:
        if kw in topic_lower:
            return WorkflowType.ITERATIVE

    # Default to iterative
    return WorkflowType.ITERATIVE


class GrasshopperWorkflowRunner:
    """
    High-level workflow runner for Grasshopper design optimization

    Provides:
    - Workflow selection (Option A or B)
    - State management
    - Human-in-the-loop integration
    - Result persistence
    """

    def __init__(
        self,
        workflow_type: WorkflowType = WorkflowType.AUTO,
        max_iterations: int = 5,
    ):
        """
        Initialize the workflow runner

        Args:
            workflow_type: Which workflow to use (or auto-select)
            max_iterations: Maximum iterations/variants
        """
        self.workflow_type = workflow_type
        self.max_iterations = max_iterations
        self.workflow = None
        self.state = None

    def start(self, topic: str) -> DesignState:
        """
        Start a new design workflow

        Args:
            topic: The design topic/requirement

        Returns:
            Initial state
        """
        # Determine workflow type
        if self.workflow_type == WorkflowType.AUTO:
            selected_type = _auto_select_workflow(topic)
        else:
            selected_type = self.workflow_type

        # Create workflow
        self.workflow = create_workflow(
            workflow_type=selected_type,
            topic=topic,
            max_iterations=self.max_iterations
        )

        # Create initial state
        mode = (
            OptimizationMode.ITERATIVE
            if selected_type == WorkflowType.ITERATIVE
            else OptimizationMode.MULTI_VARIANT
        )
        self.state = create_initial_state(
            topic=topic,
            mode=mode,
            max_iterations=self.max_iterations
        )

        return self.state

    def run(self) -> DesignState:
        """
        Run the workflow until completion or human input needed

        Returns:
            Updated state
        """
        if not self.workflow or not self.state:
            raise ValueError("Workflow not started. Call start() first.")

        self.state = self.workflow.invoke(self.state)
        return self.state

    def resume(self, user_input: Optional[dict] = None) -> DesignState:
        """
        Resume workflow after human input

        Args:
            user_input: User decisions/approvals

        Returns:
            Updated state
        """
        if not self.workflow or not self.state:
            raise ValueError("Workflow not started. Call start() first.")

        if user_input:
            # Apply user input to state
            if "approved" in user_input:
                self.state["user_approved"] = user_input["approved"]
                self.state["awaiting_confirmation"] = False

            if "decision" in user_input:
                # Apply decision
                from ..nodes.human_review import apply_decision
                decision_updates = apply_decision(
                    self.state,
                    user_input["decision"]["id"],
                    user_input["decision"]["choice"]
                )
                self.state = {**self.state, **decision_updates}

        # Continue running
        return self.run()

    def get_status(self) -> dict:
        """
        Get current workflow status

        Returns:
            Status information
        """
        if not self.state:
            return {"status": "not_started"}

        return {
            "status": "running" if not self.state.get("awaiting_confirmation") else "waiting",
            "stage": self.state.get("current_stage"),
            "iteration": self.state.get("current_iteration"),
            "max_iterations": self.state.get("max_iterations"),
            "mode": self.state.get("mode"),
            "convergence": self.state.get("convergence_score"),
            "awaiting": self.state.get("confirmation_reason"),
            "errors": len(self.state.get("errors", [])),
            "variants": len(self.state.get("variants", [])),
        }


def run_design_optimization(
    topic: str,
    workflow_type: WorkflowType = WorkflowType.AUTO,
    max_iterations: int = 5,
    auto_approve: bool = False
) -> DesignState:
    """
    Convenience function to run a complete design optimization

    Args:
        topic: Design topic/requirement
        workflow_type: Workflow to use
        max_iterations: Maximum iterations
        auto_approve: If True, auto-approve all decisions (for testing)

    Returns:
        Final state
    """
    runner = GrasshopperWorkflowRunner(
        workflow_type=workflow_type,
        max_iterations=max_iterations
    )

    state = runner.start(topic)
    state = runner.run()

    # Handle decision points if auto_approve
    max_resumes = 10
    resumes = 0

    while state.get("awaiting_confirmation") and resumes < max_resumes:
        resumes += 1

        if auto_approve:
            state = runner.resume({"approved": True})
        else:
            # In production, this would interact with user
            break

    return state
