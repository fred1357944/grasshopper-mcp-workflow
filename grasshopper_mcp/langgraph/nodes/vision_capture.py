"""
Vision Capture Node for Grasshopper LangGraph Workflow

Provides canvas and viewport capture capabilities via GH_MCP.
Returns base64 images for vision model analysis.
"""

import base64
import json
import socket
from typing import Optional, Dict, Any
from dataclasses import dataclass
from ..state import DesignState


@dataclass
class CaptureResult:
    """Result from a capture operation"""
    success: bool
    image_base64: Optional[str] = None
    width: int = 0
    height: int = 0
    bounds: Optional[Dict[str, float]] = None
    error: Optional[str] = None


class VisionCapture:
    """
    Vision capture client for GH_MCP

    Provides methods to capture:
    - Grasshopper canvas (2D node graph)
    - Rhino viewport (3D geometry preview)
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8080, timeout: float = 30.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def _send_command(self, command_type: str, parameters: Optional[Dict] = None) -> Dict:
        """Send command to GH_MCP server"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)

        try:
            sock.connect((self.host, self.port))

            command = {"type": command_type}
            if parameters:
                command["parameters"] = parameters

            message = json.dumps(command) + "\n"
            sock.sendall(message.encode())

            # Receive response (may be large for images)
            chunks = []
            while True:
                try:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    # Check if we have complete JSON
                    try:
                        data = b''.join(chunks).decode('utf-8-sig')
                        json.loads(data.strip())
                        break  # Valid JSON, we're done
                    except json.JSONDecodeError:
                        continue  # Need more data
                except socket.timeout:
                    break

            response_text = b''.join(chunks).decode('utf-8-sig').strip()
            return json.loads(response_text)

        finally:
            sock.close()

    def capture_canvas(self, bounds: Optional[Dict[str, float]] = None) -> CaptureResult:
        """
        Capture Grasshopper canvas as PNG image

        Args:
            bounds: Optional dict with x, y, width, height to capture specific region
                   If None, captures entire document

        Returns:
            CaptureResult with base64 image data
        """
        params = {}
        if bounds:
            params["bounds"] = bounds

        try:
            response = self._send_command("capture_canvas", params if params else None)

            if response.get("success"):
                data = response.get("data", {})
                return CaptureResult(
                    success=True,
                    image_base64=data.get("image"),
                    width=data.get("width", 0),
                    height=data.get("height", 0),
                    bounds=data.get("bounds")
                )
            else:
                return CaptureResult(
                    success=False,
                    error=response.get("error", "Unknown error")
                )
        except Exception as e:
            return CaptureResult(success=False, error=str(e))

    def capture_rhino_view(self, width: int = 1920, height: int = 1080) -> CaptureResult:
        """
        Capture Rhino 3D viewport as PNG image

        Args:
            width: Output image width
            height: Output image height

        Returns:
            CaptureResult with base64 image data
        """
        try:
            response = self._send_command("capture_rhino_view", {
                "width": width,
                "height": height
            })

            if response.get("success"):
                data = response.get("data", {})
                return CaptureResult(
                    success=True,
                    image_base64=data.get("image"),
                    width=data.get("width", 0),
                    height=data.get("height", 0)
                )
            else:
                return CaptureResult(
                    success=False,
                    error=response.get("error", "Unknown error")
                )
        except Exception as e:
            return CaptureResult(success=False, error=str(e))

    def zoom_to_components(self, component_ids: list[str]) -> Dict:
        """
        Zoom canvas to specific components

        Args:
            component_ids: List of component GUIDs to focus on

        Returns:
            Response dict from MCP
        """
        try:
            return self._send_command("zoom_to_components", {
                "componentIds": component_ids
            })
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_image(self, base64_data: str, filepath: str) -> bool:
        """Save base64 image to file"""
        try:
            image_bytes = base64.b64decode(base64_data)
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            return True
        except Exception:
            return False


def vision_capture_node(state: DesignState) -> Dict[str, Any]:
    """
    LangGraph node: Capture canvas and viewport images

    Adds vision snapshots to state for subsequent analysis.
    """
    from datetime import datetime

    capture = VisionCapture()
    snapshots = state.get("vision_snapshots", [])

    # Capture canvas
    canvas_result = capture.capture_canvas()
    viewport_result = capture.capture_rhino_view(width=1280, height=720)

    snapshot = {
        "timestamp": datetime.now().isoformat(),
        "canvas_image": canvas_result.image_base64 if canvas_result.success else None,
        "canvas_bounds": canvas_result.bounds,
        "viewport_image": viewport_result.image_base64 if viewport_result.success else None,
        "canvas_success": canvas_result.success,
        "viewport_success": viewport_result.success,
        "errors": []
    }

    if not canvas_result.success:
        snapshot["errors"].append(f"Canvas capture failed: {canvas_result.error}")
    if not viewport_result.success:
        snapshot["errors"].append(f"Viewport capture failed: {viewport_result.error}")

    snapshots.append(snapshot)

    return {
        "vision_snapshots": snapshots,
        "current_snapshot": snapshot
    }


# Convenience function for testing
def test_capture():
    """Test capture functionality"""
    capture = VisionCapture()

    print("Testing canvas capture...")
    result = capture.capture_canvas()
    print(f"  Success: {result.success}")
    if result.success:
        print(f"  Size: {result.width}x{result.height}")
        print(f"  Image data length: {len(result.image_base64) if result.image_base64 else 0}")
    else:
        print(f"  Error: {result.error}")

    print("\nTesting viewport capture...")
    result = capture.capture_rhino_view()
    print(f"  Success: {result.success}")
    if result.success:
        print(f"  Size: {result.width}x{result.height}")
    else:
        print(f"  Error: {result.error}")


if __name__ == "__main__":
    test_capture()
