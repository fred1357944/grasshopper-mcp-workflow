"""
Integration Module for Grasshopper MCP Workflow

Connects LangGraph workflows with existing Grasshopper tools:
- PlacementExecutor
- ComponentManager
- ConnectionManager
- ParameterSetter
- Parser utilities
"""

import os
import sys
from pathlib import Path
from typing import Optional, Any
from datetime import datetime

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .state import DesignState, OptimizationMode, create_initial_state
from .graphs.workflow_selector import (
    create_workflow,
    WorkflowType,
    GrasshopperWorkflowRunner
)
from .checkpointers.file_checkpointer import FileCheckpointer


class GrasshopperLangGraphIntegration:
    """
    High-level integration between LangGraph workflows and Grasshopper tools

    Provides:
    - Unified interface for design optimization
    - Integration with existing parser utilities
    - Execution through PlacementExecutor
    - State persistence with FileCheckpointer
    """

    def __init__(
        self,
        work_dir: Optional[str] = None,
        grasshopper_host: str = "localhost",
        grasshopper_port: int = 8080
    ):
        """
        Initialize the integration

        Args:
            work_dir: Working directory (defaults to GH_WIP)
            grasshopper_host: Grasshopper MCP server host
            grasshopper_port: Grasshopper MCP server port
        """
        self.work_dir = Path(work_dir or os.path.join(os.getcwd(), "GH_WIP"))
        self.work_dir.mkdir(parents=True, exist_ok=True)

        self.grasshopper_host = grasshopper_host
        self.grasshopper_port = grasshopper_port

        # Initialize checkpointer
        self.checkpointer = FileCheckpointer(
            base_path=str(self.work_dir / "optimization_session")
        )

        # Workflow runner
        self.runner: Optional[GrasshopperWorkflowRunner] = None

        # Try to import Grasshopper tools
        self._init_grasshopper_tools()

    def _init_grasshopper_tools(self):
        """Initialize Grasshopper tool connections"""
        try:
            from grasshopper_tools.client import GrasshopperClient
            from grasshopper_tools.placement_executor import PlacementExecutor
            from grasshopper_tools.parser_utils import MMDParser, JSONGenerator

            self.client = GrasshopperClient(
                host=self.grasshopper_host,
                port=self.grasshopper_port
            )
            self.executor = PlacementExecutor(client=self.client)
            self.parser = MMDParser()
            self.generator = JSONGenerator()
            self._tools_available = True

        except ImportError as e:
            print(f"Warning: Grasshopper tools not available: {e}")
            self.client = None
            self.executor = None
            self.parser = None
            self.generator = None
            self._tools_available = False

    def start_optimization(
        self,
        topic: str,
        mode: str = "auto",
        max_iterations: int = 5
    ) -> DesignState:
        """
        Start a new design optimization workflow

        Args:
            topic: Design topic/requirement
            mode: "iterative", "variants", or "auto"
            max_iterations: Maximum iterations or variants

        Returns:
            Initial state
        """
        # Map mode string to WorkflowType
        workflow_type = {
            "iterative": WorkflowType.ITERATIVE,
            "variants": WorkflowType.MULTI_VARIANT,
            "auto": WorkflowType.AUTO
        }.get(mode, WorkflowType.AUTO)

        # Create runner
        self.runner = GrasshopperWorkflowRunner(
            workflow_type=workflow_type,
            max_iterations=max_iterations
        )

        # Start workflow
        state = self.runner.start(topic)

        # Save initial state
        self.checkpointer.save(state)

        return state

    def run_step(self) -> DesignState:
        """
        Run one step of the workflow

        Returns:
            Updated state
        """
        if not self.runner:
            raise ValueError("No active workflow. Call start_optimization first.")

        state = self.runner.run()
        self.checkpointer.save(state)
        return state

    def provide_input(self, user_input: dict) -> DesignState:
        """
        Provide user input and continue workflow

        Args:
            user_input: User decisions/approvals
                - {"approved": True/False}
                - {"decision": {"id": str, "choice": str}}

        Returns:
            Updated state
        """
        if not self.runner:
            raise ValueError("No active workflow.")

        state = self.runner.resume(user_input)
        self.checkpointer.save(state)
        return state

    def get_status(self) -> dict:
        """Get current workflow status"""
        if not self.runner:
            return {"status": "not_started"}
        return self.runner.get_status()

    def resume_session(self, session_id: Optional[str] = None) -> DesignState:
        """
        Resume a previous session

        Args:
            session_id: Session to resume (or latest if None)

        Returns:
            Loaded state
        """
        if session_id:
            state = self.checkpointer.load(session_id)
        else:
            state = self.checkpointer.load_latest()

        if not state:
            raise ValueError("No session found to resume")

        # Recreate runner with loaded state
        workflow_type = (
            WorkflowType.ITERATIVE
            if state["mode"] == OptimizationMode.ITERATIVE
            else WorkflowType.MULTI_VARIANT
        )

        self.runner = GrasshopperWorkflowRunner(
            workflow_type=workflow_type,
            max_iterations=state["max_iterations"]
        )
        self.runner.state = state
        self.runner.workflow = create_workflow(workflow_type)

        return state

    def execute_placement(self, placement_info: Optional[dict] = None) -> dict:
        """
        Execute placement using Grasshopper tools

        Args:
            placement_info: Placement data (or use from current state)

        Returns:
            Execution result
        """
        if not self._tools_available:
            return {"success": False, "error": "Grasshopper tools not available"}

        if placement_info is None and self.runner:
            placement_info = self.runner.state.get("placement_info")

        if not placement_info:
            return {"success": False, "error": "No placement_info provided"}

        # Save placement_info to file
        placement_path = self.work_dir / "placement_info.json"
        import json
        with open(placement_path, "w") as f:
            json.dump(placement_info, f, indent=2)

        # Execute
        try:
            result = self.executor.execute_placement_info(str(placement_path))
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    def parse_component_info(self, mmd_path: Optional[str] = None) -> tuple:
        """
        Parse component_info.mmd file

        Args:
            mmd_path: Path to MMD file (or use default)

        Returns:
            (components, connections) tuple
        """
        if not self._tools_available:
            raise RuntimeError("Grasshopper tools not available")

        if mmd_path is None:
            mmd_path = str(self.work_dir / "component_info.mmd")

        return self.parser.parse_component_info_mmd(mmd_path)

    def generate_placement_info(
        self,
        components: list,
        connections: list
    ) -> dict:
        """
        Generate placement_info.json from parsed components

        Args:
            components: Parsed components
            connections: Parsed connections

        Returns:
            placement_info dict
        """
        if not self._tools_available:
            raise RuntimeError("Grasshopper tools not available")

        return self.generator.generate_placement_info(components, connections)

    def get_report(self, session_id: Optional[str] = None) -> str:
        """
        Generate optimization report

        Args:
            session_id: Session to report (or current)

        Returns:
            Markdown report
        """
        if session_id is None and self.runner:
            session_id = self.runner.state.get("session_id")

        if not session_id:
            return "No session available for report."

        return self.checkpointer.generate_report(session_id)


# === Convenience Functions ===

def optimize_design(
    topic: str,
    mode: str = "auto",
    max_iterations: int = 5,
    work_dir: Optional[str] = None
) -> dict:
    """
    Convenience function to run design optimization

    Args:
        topic: Design topic
        mode: Optimization mode
        max_iterations: Maximum iterations
        work_dir: Working directory

    Returns:
        Final state and report
    """
    integration = GrasshopperLangGraphIntegration(work_dir=work_dir)

    # Start optimization
    state = integration.start_optimization(topic, mode, max_iterations)

    # Run until needs input
    state = integration.run_step()

    # Return current status
    return {
        "state": state,
        "status": integration.get_status(),
        "report": integration.get_report()
    }


def resume_and_approve(session_id: Optional[str] = None) -> dict:
    """
    Resume a session and approve the current state

    Args:
        session_id: Session to resume

    Returns:
        Updated state and status
    """
    integration = GrasshopperLangGraphIntegration()

    state = integration.resume_session(session_id)
    state = integration.provide_input({"approved": True})

    return {
        "state": state,
        "status": integration.get_status(),
        "report": integration.get_report()
    }


if __name__ == "__main__":
    # Test the integration
    print("Testing GrasshopperLangGraphIntegration...")

    integration = GrasshopperLangGraphIntegration()

    # Start a test optimization
    state = integration.start_optimization(
        topic="Test: Optimize table component connections",
        mode="iterative",
        max_iterations=3
    )

    print(f"Started session: {state['session_id']}")
    print(f"Mode: {state['mode']}")
    print(f"Stage: {state['current_stage']}")

    # Run a step
    state = integration.run_step()
    print(f"After step - Stage: {state['current_stage']}")

    # Get status
    status = integration.get_status()
    print(f"Status: {status}")

    # Get report
    report = integration.get_report()
    print("\n--- Report Preview ---")
    print(report[:500])
