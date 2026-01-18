"""
Auto-Fix Node for Grasshopper LangGraph Workflow

Implements the self-correction loop:
1. Detect errors via vision analysis
2. Query Joseki library for solutions
3. Apply fixes via MCP
4. Verify fix success
5. Record results for learning
"""

import json
import socket
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from ..state import DesignState


@dataclass
class FixAttempt:
    """Record of a fix attempt"""
    timestamp: str
    error_type: str
    error_description: str
    fix_applied: str
    success: bool
    details: str


class AutoFixAgent:
    """
    Self-correction agent for Grasshopper automation

    Implements the vision-feedback loop:
    - Detect errors from canvas screenshots
    - Look up solutions from Joseki library
    - Apply fixes via MCP commands
    - Verify results and learn from outcomes
    """

    def __init__(self, mcp_host: str = "127.0.0.1", mcp_port: int = 8080):
        self.mcp_host = mcp_host
        self.mcp_port = mcp_port
        self.fix_history: List[FixAttempt] = []
        self.max_fix_attempts = 5

    def _send_mcp_command(self, command_type: str, parameters: Optional[Dict] = None) -> Dict:
        """Send command to GH_MCP server"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30.0)

        try:
            sock.connect((self.mcp_host, self.mcp_port))

            command = {"type": command_type}
            if parameters:
                command["parameters"] = parameters

            message = json.dumps(command) + "\n"
            sock.sendall(message.encode())

            response = sock.recv(65536).decode('utf-8-sig').strip()
            return json.loads(response)
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            sock.close()

    def get_document_errors(self) -> List[Dict]:
        """Get all errors from current Grasshopper document"""
        response = self._send_mcp_command("get_document_errors")
        if response.get("success"):
            return response.get("data", {}).get("errors", [])
        return []

    def analyze_error(self, error: Dict) -> Dict[str, Any]:
        """
        Analyze an error and suggest fixes

        Returns:
            dict with:
            - error_type: categorized error type
            - likely_cause: probable cause
            - suggested_fixes: list of potential fixes
        """
        error_msg = error.get("message", "").lower()
        component_type = error.get("componentType", "")

        analysis = {
            "error_type": "unknown",
            "likely_cause": "Unknown cause",
            "suggested_fixes": []
        }

        # Categorize error types
        if "null" in error_msg or "no data" in error_msg:
            analysis["error_type"] = "missing_input"
            analysis["likely_cause"] = "Input parameter is not connected or has no data"
            analysis["suggested_fixes"] = [
                "Check if all required inputs are connected",
                "Verify upstream components are producing output",
                "Add default value to input parameter"
            ]

        elif "type" in error_msg and ("mismatch" in error_msg or "convert" in error_msg):
            analysis["error_type"] = "type_mismatch"
            analysis["likely_cause"] = "Data type incompatibility between connected components"
            analysis["suggested_fixes"] = [
                "Add type conversion component (e.g., Number to Integer)",
                "Check connection is to correct port",
                "Verify data structure (list vs single item)"
            ]

        elif "index" in error_msg or "out of range" in error_msg:
            analysis["error_type"] = "index_error"
            analysis["likely_cause"] = "Trying to access data at invalid index"
            analysis["suggested_fixes"] = [
                "Add List Item component with bounds checking",
                "Verify list has expected number of items",
                "Add Cull Null to remove empty items"
            ]

        elif "geometry" in error_msg or "invalid" in error_msg:
            analysis["error_type"] = "geometry_error"
            analysis["likely_cause"] = "Invalid or degenerate geometry"
            analysis["suggested_fixes"] = [
                "Check input geometry is valid",
                "Add geometry validation component",
                "Verify scale and dimensions are non-zero"
            ]

        elif "slider" in component_type.lower():
            analysis["error_type"] = "slider_config"
            analysis["likely_cause"] = "Slider value or range issue"
            analysis["suggested_fixes"] = [
                "Set appropriate min/max values",
                "Ensure value is within range",
                "Check decimal places setting"
            ]

        return analysis

    def apply_fix(self, error: Dict, fix_type: str) -> bool:
        """
        Apply a fix for a specific error

        Args:
            error: The error dict from get_document_errors
            fix_type: Type of fix to apply

        Returns:
            True if fix was applied successfully
        """
        component_id = error.get("componentId")
        if not component_id:
            return False

        try:
            if fix_type == "reconnect":
                # Get component info to understand its connections
                info_response = self._send_mcp_command("get_component_info", {"id": component_id})
                if not info_response.get("success"):
                    return False
                # Would need more logic to determine what to reconnect
                return False

            elif fix_type == "set_default":
                # Try to set a default value
                response = self._send_mcp_command("set_component_value", {
                    "id": component_id,
                    "value": "0"  # Default value
                })
                return response.get("success", False)

            elif fix_type == "delete_and_replace":
                # Delete problematic component
                response = self._send_mcp_command("delete_component", {
                    "componentId": component_id
                })
                return response.get("success", False)

        except Exception as e:
            print(f"Fix failed: {e}")
            return False

        return False

    def run_fix_loop(self, max_iterations: int = None) -> Dict[str, Any]:
        """
        Run the self-correction loop

        Returns:
            Summary of fix attempts and results
        """
        if max_iterations is None:
            max_iterations = self.max_fix_attempts

        results = {
            "iterations": 0,
            "errors_fixed": 0,
            "errors_remaining": 0,
            "fix_attempts": []
        }

        for iteration in range(max_iterations):
            results["iterations"] = iteration + 1

            # Get current errors
            errors = self.get_document_errors()
            if not errors:
                print(f"No errors remaining after {iteration} iterations")
                break

            print(f"Iteration {iteration + 1}: Found {len(errors)} error(s)")

            # Try to fix each error
            for error in errors:
                analysis = self.analyze_error(error)

                attempt = FixAttempt(
                    timestamp=datetime.now().isoformat(),
                    error_type=analysis["error_type"],
                    error_description=error.get("message", ""),
                    fix_applied="",
                    success=False,
                    details=""
                )

                # Try suggested fixes
                for fix in analysis["suggested_fixes"]:
                    # Map suggestion to fix type
                    fix_type = self._suggestion_to_fix_type(fix)
                    if fix_type:
                        success = self.apply_fix(error, fix_type)
                        attempt.fix_applied = fix
                        attempt.success = success
                        if success:
                            results["errors_fixed"] += 1
                            break

                self.fix_history.append(attempt)
                results["fix_attempts"].append({
                    "error": error.get("message"),
                    "fix": attempt.fix_applied,
                    "success": attempt.success
                })

        # Final error count
        final_errors = self.get_document_errors()
        results["errors_remaining"] = len(final_errors)

        return results

    def _suggestion_to_fix_type(self, suggestion: str) -> Optional[str]:
        """Map a suggestion text to a fix type"""
        suggestion_lower = suggestion.lower()

        if "connect" in suggestion_lower:
            return "reconnect"
        elif "default" in suggestion_lower or "value" in suggestion_lower:
            return "set_default"
        elif "remove" in suggestion_lower or "delete" in suggestion_lower:
            return "delete_and_replace"

        return None


def auto_fix_node(state: DesignState) -> Dict[str, Any]:
    """
    LangGraph node: Auto-fix detected errors

    Requires vision_analysis_node to have run first.
    Uses error detection results to apply fixes.
    """
    error_detection = state.get("error_detection")

    if not error_detection or not error_detection.get("has_red_components"):
        return {
            "applied_fixes": [],
            "fix_summary": "No errors to fix"
        }

    agent = AutoFixAgent()

    # Run fix loop
    results = agent.run_fix_loop(max_iterations=3)

    # Update state
    return {
        "applied_fixes": results.get("fix_attempts", []),
        "fix_summary": f"Fixed {results['errors_fixed']}/{results['iterations']} errors, {results['errors_remaining']} remaining",
        "errors": state.get("errors", []) if results["errors_remaining"] == 0 else state.get("errors", [])
    }


def joseki_lookup_node(state: DesignState) -> Dict[str, Any]:
    """
    LangGraph node: Look up Joseki solutions for errors

    Searches the Joseki library for patterns that might help
    resolve current errors or improve the design.
    """
    from ...joseki import JosekiLibrary
    import os

    # Get Joseki library path
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    library_path = os.path.join(base_path, "joseki", "library")

    try:
        library = JosekiLibrary(library_path)
    except Exception as e:
        return {
            "matched_joseki": None,
            "joseki_error": f"Failed to load Joseki library: {e}"
        }

    # Get current errors
    errors = state.get("errors", [])
    error_detection = state.get("error_detection", {})

    # Search for relevant Joseki based on error types
    search_tags = []

    if error_detection.get("disconnected_wires"):
        search_tags.append("connection")

    # Also search based on current design intent
    requirements = state.get("requirements", "")
    if "voronoi" in requirements.lower():
        search_tags.append("voronoi")
    if "grid" in requirements.lower() or "array" in requirements.lower():
        search_tags.append("array")
    if "box" in requirements.lower():
        search_tags.append("box")

    # Find matching Joseki
    matches = []
    if search_tags:
        matches = library.search_by_tags(search_tags)

    if matches:
        best_match = matches[0]
        return {
            "matched_joseki": {
                "id": best_match.id,
                "name": best_match.name,
                "description": best_match.description,
                "pseudo_code": best_match.pseudo_code,
                "prompt_context": best_match.to_prompt_context()
            }
        }

    return {
        "matched_joseki": None
    }


# Test function
def test_auto_fix():
    """Test auto-fix functionality"""
    agent = AutoFixAgent()

    print("Getting document errors...")
    errors = agent.get_document_errors()
    print(f"Found {len(errors)} error(s)")

    for error in errors:
        print(f"\n  - {error.get('componentName')}: {error.get('message')}")
        analysis = agent.analyze_error(error)
        print(f"    Type: {analysis['error_type']}")
        print(f"    Cause: {analysis['likely_cause']}")
        print(f"    Fixes: {analysis['suggested_fixes']}")


if __name__ == "__main__":
    test_auto_fix()
