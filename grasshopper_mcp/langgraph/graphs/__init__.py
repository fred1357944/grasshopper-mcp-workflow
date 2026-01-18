"""
LangGraph Workflow Graphs

Defines the state machine graphs for:
- Option A: Iterative Design Optimization
- Option B: Multi-Variant Design Exploration
- Combined workflow with mode selection
"""

from .iterative_workflow import create_iterative_workflow
from .multivariant_workflow import create_multivariant_workflow
from .workflow_selector import create_workflow, WorkflowType

# Superpower graphs (v3.0)
from .multi_mode_workflow import (
    create_multi_mode_workflow,
    run_multi_mode_workflow,
    get_workflow_graph,
    MultiModeWorkflowRunner,
)

# Compiled LangGraph (v4.0) - 真正的 StateGraph 實作
from .compiled_workflow import (
    build_multi_mode_graph,
    compile_workflow,
    CompiledWorkflowRunner,
    run_compiled_workflow,
    stream_compiled_workflow,
    get_workflow_mermaid,
)

__all__ = [
    "create_iterative_workflow",
    "create_multivariant_workflow",
    "create_workflow",
    "WorkflowType",
    # Superpower (v3.0) - 模擬版
    "create_multi_mode_workflow",
    "run_multi_mode_workflow",
    "get_workflow_graph",
    "MultiModeWorkflowRunner",
    # Compiled (v4.0) - 真正 LangGraph
    "build_multi_mode_graph",
    "compile_workflow",
    "CompiledWorkflowRunner",
    "run_compiled_workflow",
    "stream_compiled_workflow",
    "get_workflow_mermaid",
]
