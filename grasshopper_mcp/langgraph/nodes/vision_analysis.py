"""
Vision Analysis Node for Grasshopper LangGraph Workflow

Analyzes canvas screenshots using Vision models (Claude/Gemini)
to detect errors, verify connections, and understand component state.
"""

import base64
import os
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from ..state import DesignState


class VisionModel(str, Enum):
    """Available vision models"""
    CLAUDE = "claude"
    GEMINI = "gemini"


@dataclass
class ErrorDetection:
    """Result of error detection analysis"""
    has_errors: bool
    red_components: List[str]  # Component IDs or descriptions
    orange_warnings: List[str]
    disconnected_wires: List[Dict[str, str]]
    error_messages: List[str]
    confidence: float
    raw_analysis: str


@dataclass
class CanvasUnderstanding:
    """Understanding of canvas state"""
    component_count: int
    identified_components: List[Dict[str, Any]]
    connection_graph: List[Dict[str, str]]
    layout_quality: str  # "good", "messy", "overlapping"
    suggestions: List[str]


class VisionAnalyzer:
    """
    Analyze Grasshopper canvas images using Vision models

    Supports both Claude (for detailed analysis) and Gemini (for fast scanning)
    """

    def __init__(self, model: VisionModel = VisionModel.CLAUDE):
        self.model = model
        self._setup_client()

    def _setup_client(self):
        """Setup API client based on selected model"""
        if self.model == VisionModel.CLAUDE:
            try:
                import anthropic
                self.client = anthropic.Anthropic()
            except ImportError:
                raise ImportError("anthropic package required: pip install anthropic")
        else:
            try:
                import google.generativeai as genai
                genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
                self.client = genai.GenerativeModel("gemini-1.5-flash")
            except ImportError:
                raise ImportError("google-generativeai package required: pip install google-generativeai")

    def _analyze_with_claude(self, image_base64: str, prompt: str) -> str:
        """Analyze image using Claude Vision"""
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        return response.content[0].text

    def _analyze_with_gemini(self, image_base64: str, prompt: str) -> str:
        """Analyze image using Gemini Vision"""
        import PIL.Image
        import io

        # Convert base64 to PIL Image
        image_bytes = base64.b64decode(image_base64)
        image = PIL.Image.open(io.BytesIO(image_bytes))

        response = self.client.generate_content([prompt, image])
        return response.text

    def analyze(self, image_base64: str, prompt: str) -> str:
        """Analyze image with configured model"""
        if self.model == VisionModel.CLAUDE:
            return self._analyze_with_claude(image_base64, prompt)
        else:
            return self._analyze_with_gemini(image_base64, prompt)

    def detect_errors(self, canvas_image: str) -> ErrorDetection:
        """
        Detect errors in Grasshopper canvas

        Looks for:
        - Red components (errors)
        - Orange components (warnings)
        - Disconnected wires
        - Error bubbles/messages
        """
        prompt = """Analyze this Grasshopper canvas screenshot for errors.

Look for:
1. RED components - these indicate errors
2. ORANGE components - these indicate warnings
3. Disconnected wires (lines that don't connect to anything)
4. Error message bubbles (small text boxes near components)

Respond in JSON format:
{
    "has_errors": true/false,
    "red_components": ["description of each red component"],
    "orange_warnings": ["description of each orange component"],
    "disconnected_wires": [{"from": "component name", "description": "what's wrong"}],
    "error_messages": ["any visible error text"],
    "confidence": 0.0-1.0,
    "analysis": "brief description of overall canvas state"
}"""

        try:
            response = self.analyze(canvas_image, prompt)

            # Parse JSON from response
            # Handle case where model wraps JSON in markdown
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())

            return ErrorDetection(
                has_errors=data.get("has_errors", False),
                red_components=data.get("red_components", []),
                orange_warnings=data.get("orange_warnings", []),
                disconnected_wires=data.get("disconnected_wires", []),
                error_messages=data.get("error_messages", []),
                confidence=data.get("confidence", 0.5),
                raw_analysis=data.get("analysis", "")
            )
        except Exception as e:
            return ErrorDetection(
                has_errors=False,
                red_components=[],
                orange_warnings=[],
                disconnected_wires=[],
                error_messages=[f"Analysis failed: {str(e)}"],
                confidence=0.0,
                raw_analysis=str(e)
            )

    def understand_canvas(self, canvas_image: str) -> CanvasUnderstanding:
        """
        Understand the overall canvas structure

        Identifies components, connections, and layout quality
        """
        prompt = """Analyze this Grasshopper canvas to understand its structure.

Identify:
1. What components are visible (sliders, panels, geometry components, etc.)
2. How they are connected (data flow)
3. Layout quality (is it organized or messy?)

Respond in JSON format:
{
    "component_count": 0,
    "identified_components": [
        {"type": "Number Slider", "nickname": "if visible", "position": "left/center/right"},
    ],
    "connection_graph": [
        {"from": "component A", "to": "component B", "description": "what data flows"}
    ],
    "layout_quality": "good/messy/overlapping",
    "suggestions": ["any improvements"]
}"""

        try:
            response = self.analyze(canvas_image, prompt)

            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            data = json.loads(json_str.strip())

            return CanvasUnderstanding(
                component_count=data.get("component_count", 0),
                identified_components=data.get("identified_components", []),
                connection_graph=data.get("connection_graph", []),
                layout_quality=data.get("layout_quality", "unknown"),
                suggestions=data.get("suggestions", [])
            )
        except Exception as e:
            return CanvasUnderstanding(
                component_count=0,
                identified_components=[],
                connection_graph=[],
                layout_quality="unknown",
                suggestions=[f"Analysis failed: {str(e)}"]
            )

    def verify_geometry(self, viewport_image: str, expected: str) -> Dict[str, Any]:
        """
        Verify 3D geometry matches expectations

        Args:
            viewport_image: Base64 Rhino viewport screenshot
            expected: Description of what geometry should look like

        Returns:
            Verification result with match score and description
        """
        prompt = f"""Analyze this Rhino 3D viewport.

Expected geometry: {expected}

Questions:
1. Does the visible geometry match the expected description?
2. Are there any obvious errors (missing parts, wrong scale, etc.)?
3. What is the overall quality of the geometry?

Respond in JSON format:
{{
    "matches_expected": true/false,
    "match_score": 0.0-1.0,
    "visible_geometry": "description of what you see",
    "errors": ["any visible problems"],
    "quality": "good/acceptable/poor"
}}"""

        try:
            response = self.analyze(viewport_image, prompt)

            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]

            return json.loads(json_str.strip())
        except Exception as e:
            return {
                "matches_expected": False,
                "match_score": 0.0,
                "visible_geometry": "Analysis failed",
                "errors": [str(e)],
                "quality": "unknown"
            }


def vision_analysis_node(state: DesignState) -> Dict[str, Any]:
    """
    LangGraph node: Analyze captured images

    Requires vision_capture_node to have run first.
    """
    current_snapshot = state.get("current_snapshot")

    if not current_snapshot:
        return {
            "error_detection": None,
            "errors": state.get("errors", []) + ["No vision snapshot available for analysis"]
        }

    canvas_image = current_snapshot.get("canvas_image")
    if not canvas_image:
        return {
            "error_detection": None,
            "errors": state.get("errors", []) + ["No canvas image in snapshot"]
        }

    # Use Gemini for fast scanning, Claude for detailed analysis
    try:
        analyzer = VisionAnalyzer(model=VisionModel.GEMINI)
    except Exception:
        # Fallback to Claude if Gemini not available
        try:
            analyzer = VisionAnalyzer(model=VisionModel.CLAUDE)
        except Exception as e:
            return {
                "error_detection": None,
                "errors": state.get("errors", []) + [f"No vision model available: {str(e)}"]
            }

    # Detect errors
    error_detection = analyzer.detect_errors(canvas_image)

    # Build error detection dict for state
    error_dict = {
        "has_red_components": error_detection.has_errors,
        "red_component_ids": error_detection.red_components,
        "error_messages": error_detection.error_messages,
        "disconnected_wires": error_detection.disconnected_wires,
        "confidence": error_detection.confidence
    }

    # Add errors to state if detected
    new_errors = state.get("errors", [])
    if error_detection.has_errors:
        for msg in error_detection.error_messages:
            if msg not in new_errors:
                new_errors.append(msg)

    return {
        "error_detection": error_dict,
        "errors": new_errors
    }


# Test function
def test_analysis():
    """Test vision analysis with a sample image"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python vision_analysis.py <image_path>")
        return

    image_path = sys.argv[1]

    with open(image_path, 'rb') as f:
        image_base64 = base64.b64encode(f.read()).decode()

    print("Testing error detection...")
    analyzer = VisionAnalyzer(model=VisionModel.GEMINI)
    result = analyzer.detect_errors(image_base64)

    print(f"Has errors: {result.has_errors}")
    print(f"Red components: {result.red_components}")
    print(f"Warnings: {result.orange_warnings}")
    print(f"Confidence: {result.confidence}")
    print(f"Analysis: {result.raw_analysis}")


if __name__ == "__main__":
    test_analysis()
