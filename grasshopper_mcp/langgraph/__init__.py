"""
LangGraph Integration for Grasshopper MCP Workflow

This module provides state machine-based workflow orchestration for
iterative design optimization and multi-variant exploration.

Workflow Options:
- Option A: Iterative Design Optimization Loop
- Option B: Multi-Variant Design Exploration
"""

from .state import DesignState, OptimizationMode
from .graphs.workflow_selector import create_workflow, WorkflowType

__all__ = [
    "DesignState",
    "OptimizationMode",
    "create_workflow",
    "WorkflowType",
]

__version__ = "0.1.0"
