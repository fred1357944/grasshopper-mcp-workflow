"""
Multi-Mode Workflow - 多模式工作流程圖

整合所有 Superpower 模式：
- Intent Router: 入口分類
- Think-Partner: 蘇格拉底式探索
- Brainstorm: 三階段腦力激盪
- Meta-Agent: 動態工具創建
- Workflow Pipeline: 確定性四階段管線

核心架構：
1. 入口節點分類意圖
2. 根據分類分發到對應模式
3. 每個模式有自己的子圖
4. 共享 Human Review 和 Quality Gates
"""

from typing import Literal, Dict, Any, Optional
from dataclasses import dataclass

from ..state import (
    DesignState,
    create_initial_state,
    IntentType,
    BrainstormPhase,
    ThinkingMode,
    WorkflowStage,
)

from ..core.intent_router import IntentRouter, classify_intent
from ..core.mode_selector import ModeSelector, select_mode

from ..nodes.think_partner import (
    think_partner_node,
    enter_think_partner_mode,
    exit_think_partner_mode,
)
from ..nodes.brainstorm import (
    brainstorm_node,
    enter_brainstorm_mode,
    exit_brainstorm_mode,
)
from ..nodes.meta_agent import (
    meta_agent_node,
    enter_meta_agent_mode,
    exit_meta_agent_mode,
    MetaAgentOperation,
)
from ..nodes.workflow_pipeline import (
    intent_decomposition_node,
    tool_retrieval_node,
    prompt_generation_node,
    config_assembly_node,
    enter_workflow_mode,
)
from ..nodes.human_review import human_decision_node


# === Graph Definition Types ===

@dataclass
class GraphNode:
    """A node in the workflow graph"""
    name: str
    handler: str  # Function name
    description: str


@dataclass
class GraphEdge:
    """An edge in the workflow graph"""
    source: str
    target: str
    condition: Optional[str] = None  # Condition function name


# === Router Nodes ===

def intent_router_node(state: DesignState) -> Dict[str, Any]:
    """
    Entry point: Classify intent and route to appropriate mode

    This is the first node in the multi-mode workflow.
    """
    topic = state.get("topic", "")
    requirements = state.get("requirements", "")
    task = f"{topic} {requirements}".strip()

    # Classify intent
    classification = classify_intent(task, dict(state))

    return {
        "intent_type": classification.intent_type.value,
        "intent_confidence": classification.confidence,
        "intent_keywords": classification.matched_keywords,
        "errors": state.get("errors", []) + [
            f"Intent classified: {classification.intent_type.value} "
            f"(confidence: {classification.confidence:.2f})"
        ],
    }


def mode_router_node(state: DesignState) -> str:
    """
    Routing function: Determine which mode subgraph to enter

    Returns the name of the target node.
    """
    intent_type = state.get("intent_type")

    if intent_type == IntentType.THINK_PARTNER.value:
        return "enter_think_partner"
    elif intent_type == IntentType.BRAINSTORM.value:
        return "enter_brainstorm"
    elif intent_type == IntentType.META_AGENT.value:
        return "enter_meta_agent"
    elif intent_type == IntentType.WORKFLOW.value:
        return "enter_workflow"
    else:
        # Default to workflow
        return "enter_workflow"


# === Think-Partner Subgraph ===

def think_partner_router(state: DesignState) -> str:
    """Route within Think-Partner mode"""
    mode = state.get("thinking_mode")

    if mode == ThinkingMode.THINKING.value:
        if state.get("awaiting_confirmation"):
            return "human_decision"
        return "think_partner_process"
    elif mode == ThinkingMode.WRITING.value:
        return "think_partner_exit"
    else:
        return "think_partner_exit"


# === Brainstorm Subgraph ===

def brainstorm_router(state: DesignState) -> str:
    """Route within Brainstorm mode"""
    phase = state.get("brainstorm_phase")

    if phase == BrainstormPhase.UNDERSTANDING.value:
        if state.get("awaiting_confirmation"):
            return "human_decision"
        return "brainstorm_process"
    elif phase == BrainstormPhase.EXPLORING.value:
        if state.get("awaiting_confirmation"):
            return "human_decision"
        return "brainstorm_process"
    elif phase == BrainstormPhase.PRESENTING.value:
        if state.get("awaiting_confirmation"):
            return "human_decision"
        return "brainstorm_process"
    elif phase == BrainstormPhase.COMPLETE.value:
        return "brainstorm_exit"
    else:
        return "brainstorm_exit"


# === Meta-Agent Subgraph ===

def meta_agent_router(state: DesignState) -> str:
    """Route within Meta-Agent mode"""
    if not state.get("meta_agent_active"):
        return "meta_agent_exit"

    operation = state.get("meta_agent_operation")

    if state.get("awaiting_confirmation"):
        return "human_decision"

    if operation == MetaAgentOperation.IDLE:
        return "meta_agent_exit"

    return "meta_agent_process"


# === Workflow Subgraph ===

def workflow_router(state: DesignState) -> str:
    """Route within Workflow mode"""
    stage = state.get("current_stage")

    if stage == WorkflowStage.DECOMPOSITION.value:
        return "workflow_decompose"
    elif stage == WorkflowStage.TOOL_RETRIEVAL.value:
        return "workflow_retrieve"
    elif stage == WorkflowStage.PROMPT_GENERATION.value:
        return "workflow_prompt"
    elif stage == WorkflowStage.CONFIG_ASSEMBLY.value:
        return "workflow_assemble"
    elif stage == WorkflowStage.COMPLETE.value:
        return "workflow_exit"
    else:
        return "workflow_exit"


# === Exit Conditions ===

def should_exit(state: DesignState) -> bool:
    """Check if workflow should exit"""
    # Approved by human
    if state.get("user_approved"):
        return True

    # All modes completed
    intent_type = state.get("intent_type")
    if intent_type == IntentType.WORKFLOW.value:
        return state.get("current_stage") == WorkflowStage.COMPLETE.value
    elif intent_type == IntentType.BRAINSTORM.value:
        return state.get("brainstorm_phase") == BrainstormPhase.COMPLETE.value
    elif intent_type == IntentType.THINK_PARTNER.value:
        return state.get("thinking_mode") is None
    elif intent_type == IntentType.META_AGENT.value:
        return not state.get("meta_agent_active")

    return False


# === Graph Definition ===

def create_multi_mode_workflow():
    """
    Create the multi-mode workflow graph

    Graph Structure:
    ```
    [START]
        │
        ▼
    [intent_router] ─── classify intent
        │
        ▼
    [mode_router] ─── route to subgraph
        │
        ├──► [Think-Partner Subgraph]
        │    └─ thinking ↔ writing → exit
        │
        ├──► [Brainstorm Subgraph]
        │    └─ understanding → exploring → presenting → exit
        │
        ├──► [Meta-Agent Subgraph]
        │    └─ search → create → ask → config → exit
        │
        └──► [Workflow Subgraph]
             └─ decompose → retrieve → prompt → assemble → exit
        │
        ▼
    [human_decision] ◄─── shared human review
        │
        ▼
    [final_output]
        │
        ▼
    [END]
    ```

    Returns:
        Graph definition (dict)
    """
    # In production, this would use LangGraph StateGraph
    # For now, return a graph definition dict

    graph_definition = {
        "name": "multi_mode_workflow",
        "version": "3.0",
        "description": "Superpower-integrated multi-mode workflow",

        # === Nodes ===
        "nodes": {
            # Entry nodes
            "intent_router": {
                "handler": "intent_router_node",
                "description": "Classify user intent",
            },

            # Think-Partner nodes
            "enter_think_partner": {
                "handler": "enter_think_partner_mode",
                "description": "Initialize Think-Partner mode",
            },
            "think_partner_process": {
                "handler": "think_partner_node",
                "description": "Process Think-Partner step",
            },
            "think_partner_exit": {
                "handler": "exit_think_partner_mode",
                "description": "Exit Think-Partner mode",
            },

            # Brainstorm nodes
            "enter_brainstorm": {
                "handler": "enter_brainstorm_mode",
                "description": "Initialize Brainstorm mode",
            },
            "brainstorm_process": {
                "handler": "brainstorm_node",
                "description": "Process Brainstorm step",
            },
            "brainstorm_exit": {
                "handler": "exit_brainstorm_mode",
                "description": "Exit Brainstorm mode",
            },

            # Meta-Agent nodes
            "enter_meta_agent": {
                "handler": "enter_meta_agent_mode",
                "description": "Initialize Meta-Agent mode",
            },
            "meta_agent_process": {
                "handler": "meta_agent_node",
                "description": "Process Meta-Agent step",
            },
            "meta_agent_exit": {
                "handler": "exit_meta_agent_mode",
                "description": "Exit Meta-Agent mode",
            },

            # Workflow Pipeline nodes
            "enter_workflow": {
                "handler": "enter_workflow_mode",
                "description": "Initialize Workflow mode",
            },
            "workflow_decompose": {
                "handler": "intent_decomposition_node",
                "description": "Stage 1: Decompose intent",
            },
            "workflow_retrieve": {
                "handler": "tool_retrieval_node",
                "description": "Stage 2: Retrieve tools",
            },
            "workflow_prompt": {
                "handler": "prompt_generation_node",
                "description": "Stage 3: Generate prompts",
            },
            "workflow_assemble": {
                "handler": "config_assembly_node",
                "description": "Stage 4: Assemble config",
            },
            "workflow_exit": {
                "handler": "exit_workflow_mode",
                "description": "Exit Workflow mode",
            },

            # Shared nodes
            "human_decision": {
                "handler": "human_decision_node",
                "description": "Human review checkpoint",
            },
            "final_output": {
                "handler": "generate_final_output",
                "description": "Generate final output",
            },
        },

        # === Edges ===
        "edges": [
            # Entry
            {"source": "START", "target": "intent_router"},
            {"source": "intent_router", "target": "mode_router", "type": "conditional"},

            # Think-Partner subgraph
            {"source": "enter_think_partner", "target": "think_partner_process"},
            {"source": "think_partner_process", "target": "think_partner_router", "type": "conditional"},
            {"source": "think_partner_exit", "target": "final_output"},

            # Brainstorm subgraph
            {"source": "enter_brainstorm", "target": "brainstorm_process"},
            {"source": "brainstorm_process", "target": "brainstorm_router", "type": "conditional"},
            {"source": "brainstorm_exit", "target": "final_output"},

            # Meta-Agent subgraph
            {"source": "enter_meta_agent", "target": "meta_agent_process"},
            {"source": "meta_agent_process", "target": "meta_agent_router", "type": "conditional"},
            {"source": "meta_agent_exit", "target": "final_output"},

            # Workflow subgraph
            {"source": "enter_workflow", "target": "workflow_decompose"},
            {"source": "workflow_decompose", "target": "workflow_retrieve"},
            {"source": "workflow_retrieve", "target": "workflow_prompt"},
            {"source": "workflow_prompt", "target": "workflow_assemble"},
            {"source": "workflow_assemble", "target": "workflow_exit"},
            {"source": "workflow_exit", "target": "final_output"},

            # Human decision (shared)
            {"source": "human_decision", "target": "mode_router", "type": "conditional"},

            # Exit
            {"source": "final_output", "target": "END"},
        ],

        # === Conditional Functions ===
        "conditionals": {
            "mode_router": "mode_router_node",
            "think_partner_router": "think_partner_router",
            "brainstorm_router": "brainstorm_router",
            "meta_agent_router": "meta_agent_router",
            "workflow_router": "workflow_router",
        },
    }

    return graph_definition


def generate_final_output(state: DesignState) -> Dict[str, Any]:
    """Generate final output from completed workflow"""
    intent_type = state.get("intent_type")
    topic = state.get("topic", "")

    output_parts = [
        f"# Workflow Complete: {topic}",
        f"Mode: {intent_type}",
        "",
    ]

    # Add mode-specific output
    if intent_type == IntentType.THINK_PARTNER.value:
        insights = state.get("thinking_insights", [])
        output_parts.append("## Think-Partner Insights")
        for insight in insights:
            output_parts.append(f"- {insight}")

    elif intent_type == IntentType.BRAINSTORM.value:
        ideas = state.get("brainstorm_ideas", [])
        output_parts.append("## Brainstorm Ideas")
        for idea in ideas:
            recommended = " (Recommended)" if idea.get("is_recommended") else ""
            output_parts.append(f"- {idea.get('content', '')[:100]}{recommended}")

    elif intent_type == IntentType.META_AGENT.value:
        tools = state.get("generated_tools", [])
        output_parts.append("## Generated Tools")
        for tool in tools:
            output_parts.append(f"- {tool.get('name', 'Unknown')}: {tool.get('description', '')}")

    elif intent_type == IntentType.WORKFLOW.value:
        placement_info = state.get("placement_info")
        if placement_info:
            output_parts.append("## Workflow Output")
            output_parts.append(f"Components: {len(placement_info.get('components', []))}")
            output_parts.append(f"Connections: {len(placement_info.get('connections', []))}")

    # Add errors
    errors = state.get("errors", [])
    if errors:
        output_parts.append("")
        output_parts.append("## Processing Log")
        for error in errors[-10:]:  # Last 10 messages
            output_parts.append(f"- {error}")

    final_output = "\n".join(output_parts)

    return {
        "final_proposal": final_output,
        "errors": state.get("errors", []) + ["Workflow complete, final output generated"],
    }


# === Graph Execution (Simulation) ===

class MultiModeWorkflowRunner:
    """
    Runner for the multi-mode workflow

    In production, this would use LangGraph's compiled graph.
    For now, simulates the graph execution.
    """

    def __init__(self):
        self.graph = create_multi_mode_workflow()
        self.handlers = {
            "intent_router_node": intent_router_node,
            "enter_think_partner_mode": enter_think_partner_mode,
            "think_partner_node": think_partner_node,
            "exit_think_partner_mode": exit_think_partner_mode,
            "enter_brainstorm_mode": enter_brainstorm_mode,
            "brainstorm_node": brainstorm_node,
            "exit_brainstorm_mode": exit_brainstorm_mode,
            "enter_meta_agent_mode": enter_meta_agent_mode,
            "meta_agent_node": meta_agent_node,
            "exit_meta_agent_mode": exit_meta_agent_mode,
            "enter_workflow_mode": enter_workflow_mode,
            "intent_decomposition_node": intent_decomposition_node,
            "tool_retrieval_node": tool_retrieval_node,
            "prompt_generation_node": prompt_generation_node,
            "config_assembly_node": config_assembly_node,
            "human_decision_node": human_decision_node,
            "generate_final_output": generate_final_output,
        }

    def run(
        self,
        topic: str,
        requirements: str = "",
        max_steps: int = 20
    ) -> DesignState:
        """
        Run the workflow

        Args:
            topic: The design topic
            requirements: Optional requirements
            max_steps: Maximum steps to prevent infinite loops

        Returns:
            Final state
        """
        # Initialize state
        state = create_initial_state(topic)
        state["requirements"] = requirements

        # Run intent router
        intent_result = intent_router_node(state)
        state = {**state, **intent_result}

        # Route to mode
        target_node = mode_router_node(state)

        # Execute mode-specific workflow
        step = 0
        current_node = target_node

        while step < max_steps:
            step += 1

            # Get handler
            node_def = self.graph["nodes"].get(current_node)
            if not node_def:
                break

            handler_name = node_def["handler"]
            handler = self.handlers.get(handler_name)

            if not handler:
                break

            # Execute handler
            result = handler(state)
            state = {**state, **result}

            # Check exit condition
            if should_exit(state):
                # Generate final output
                final_result = generate_final_output(state)
                state = {**state, **final_result}
                break

            # Route to next node
            current_node = self._route_next(state, current_node)

            if current_node == "END":
                break

        return state

    def _route_next(self, state: Dict[str, Any], current_node: str) -> str:
        """Determine next node based on current state"""
        intent_type = state.get("intent_type")

        # Handle awaiting confirmation
        if state.get("awaiting_confirmation"):
            return "human_decision"

        # Mode-specific routing
        if "think_partner" in current_node:
            return think_partner_router(state)
        elif "brainstorm" in current_node:
            return brainstorm_router(state)
        elif "meta_agent" in current_node:
            return meta_agent_router(state)
        elif "workflow" in current_node:
            return workflow_router(state)

        return "final_output"


# === Convenience Functions ===

def run_multi_mode_workflow(
    topic: str,
    requirements: str = ""
) -> DesignState:
    """Quick function to run the multi-mode workflow"""
    runner = MultiModeWorkflowRunner()
    return runner.run(topic, requirements)


def get_workflow_graph() -> Dict[str, Any]:
    """Get the workflow graph definition"""
    return create_multi_mode_workflow()
