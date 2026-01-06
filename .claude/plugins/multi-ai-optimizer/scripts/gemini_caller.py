#!/usr/bin/env python3
"""
Gemini Caller for Multi-AI Optimizer

Supports two modes:
1. CLI Mode - Uses Gemini CLI (simple, no API key needed)
2. API Mode - Uses Gemini API (more features, requires API key)

API Mode enables:
- Semantic similarity for convergence detection
- Structured JSON outputs
- Design quality scoring
- Intelligent variant generation
"""

import subprocess
import json
import os
import asyncio
from typing import Optional, Literal
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Try to load environment variables from .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # dotenv not installed, use os.environ directly


@dataclass
class GeminiResponse:
    """Response from Gemini"""
    content: str
    success: bool
    error: Optional[str]
    timestamp: str
    duration_seconds: float
    mode: Literal["cli", "api"] = "cli"
    tokens_used: Optional[int] = None


class GeminiCaller:
    """
    Unified Gemini caller supporting both CLI and API modes

    Usage:
        # Auto-detect mode (API if key available, else CLI)
        caller = GeminiCaller()

        # Force specific mode
        caller = GeminiCaller(mode="api")
        caller = GeminiCaller(mode="cli")

        # Call
        response = caller.call("Analyze this design...")
    """

    def __init__(
        self,
        mode: Literal["auto", "cli", "api"] = "auto",
        api_key: Optional[str] = None,
        timeout: int = 60,
        model: str = "gemini-2.0-flash-exp"
    ):
        """
        Initialize Gemini caller

        Args:
            mode: "auto", "cli", or "api"
            api_key: Gemini API key (or from GEMINI_API_KEY env var)
            timeout: Request timeout in seconds
            model: Model to use for API mode
        """
        self.timeout = timeout
        self.model = model
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

        # Determine mode
        if mode == "auto":
            self.mode = "api" if self.api_key else "cli"
        else:
            self.mode = mode

        # Validate
        if self.mode == "api" and not self.api_key:
            logger.warning("API mode requested but no API key found. Falling back to CLI.")
            self.mode = "cli"

        # Initialize API client if needed
        self._api_client = None
        self._genai = None
        if self.mode == "api":
            self._init_api_client()

        logger.info(f"GeminiCaller initialized in {self.mode} mode")

    def _init_api_client(self):
        """Initialize the Gemini API client"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._api_client = genai.GenerativeModel(self.model)
            self._genai = genai
        except ImportError:
            logger.error("google-generativeai not installed. Run: pip install google-generativeai")
            self.mode = "cli"

    def _verify_installation(self) -> bool:
        """Verify Gemini CLI is installed"""
        try:
            result = subprocess.run(
                ["which", "gemini"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                logger.warning("Gemini CLI not found in PATH")
                return False
            return True
        except Exception as e:
            logger.error(f"Error checking Gemini installation: {e}")
            return False

    def call(self, prompt: str) -> GeminiResponse:
        """
        Call Gemini with the given prompt

        Args:
            prompt: The prompt to send

        Returns:
            GeminiResponse with content and metadata
        """
        if self.mode == "api":
            return self._call_api(prompt)
        else:
            return self._call_cli(prompt)

    def _call_api(self, prompt: str) -> GeminiResponse:
        """Call using Gemini API"""
        start_time = datetime.now()

        try:
            response = self._api_client.generate_content(prompt)
            duration = (datetime.now() - start_time).total_seconds()

            tokens = None
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                tokens = getattr(response.usage_metadata, 'total_token_count', None)

            return GeminiResponse(
                content=response.text,
                success=True,
                error=None,
                timestamp=datetime.now().isoformat(),
                duration_seconds=duration,
                mode="api",
                tokens_used=tokens
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return GeminiResponse(
                content="",
                success=False,
                error=str(e),
                timestamp=datetime.now().isoformat(),
                duration_seconds=duration,
                mode="api"
            )

    def _call_cli(self, prompt: str) -> GeminiResponse:
        """Call using Gemini CLI"""
        start_time = datetime.now()

        try:
            result = subprocess.run(
                ["gemini", prompt],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            duration = (datetime.now() - start_time).total_seconds()

            if result.returncode == 0:
                return GeminiResponse(
                    content=result.stdout.strip(),
                    success=True,
                    error=None,
                    timestamp=datetime.now().isoformat(),
                    duration_seconds=duration,
                    mode="cli"
                )
            else:
                return GeminiResponse(
                    content="",
                    success=False,
                    error=result.stderr.strip() or "Unknown error",
                    timestamp=datetime.now().isoformat(),
                    duration_seconds=duration,
                    mode="cli"
                )

        except subprocess.TimeoutExpired:
            duration = (datetime.now() - start_time).total_seconds()
            return GeminiResponse(
                content="",
                success=False,
                error=f"Timeout after {self.timeout} seconds",
                timestamp=datetime.now().isoformat(),
                duration_seconds=duration,
                mode="cli"
            )
        except FileNotFoundError:
            return GeminiResponse(
                content="",
                success=False,
                error="Gemini CLI not found",
                timestamp=datetime.now().isoformat(),
                duration_seconds=0,
                mode="cli"
            )
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return GeminiResponse(
                content="",
                success=False,
                error=str(e),
                timestamp=datetime.now().isoformat(),
                duration_seconds=duration,
                mode="cli"
            )

    # === Advanced API Features ===

    def analyze_design(self, design: str, criteria: Optional[list] = None) -> dict:
        """
        Analyze a design and return structured evaluation (API mode only)

        Returns: {"overall_score": float, "criteria_scores": dict, "strengths": list, "suggestions": list}
        """
        if self.mode != "api":
            return {"error": "API mode required", "mode": self.mode}

        criteria = criteria or ["structure", "efficiency", "manufacturability"]
        prompt = f"""Analyze this design. Evaluate on: {', '.join(criteria)}

Design: {design}

Respond in JSON: {{"overall_score": 0-100, "criteria_scores": {{}}, "strengths": [], "suggestions": []}}"""

        try:
            response = self._api_client.generate_content(
                prompt,
                generation_config=self._genai.GenerationConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except Exception as e:
            return {"error": str(e)}

    def calculate_convergence(self, proposals: list[dict]) -> dict:
        """Calculate convergence between proposals"""
        if len(proposals) < 2:
            return {"convergence_score": 0.0}

        recent = proposals[-3:] if len(proposals) >= 3 else proposals
        proposals_text = "\n---\n".join([
            f"Proposal ({p.get('ai', '?')}): {p.get('content', '')[:500]}"
            for p in recent
        ])

        prompt = f"""Analyze convergence of these proposals:

{proposals_text}

Respond in JSON: {{"convergence_score": 0.0-1.0, "agreement_points": [], "recommendation": "continue|finalize|need human"}}"""

        response = self.call(prompt)
        if response.success:
            try:
                return json.loads(response.content)
            except json.JSONDecodeError:
                return {"convergence_score": 0.5, "raw": response.content}
        return {"convergence_score": 0.5, "error": response.error}

    def review_proposal(self, proposal: str, context: str = "") -> dict:
        """Review a proposal and provide feedback"""
        prompt = f"""Review this design proposal.

Context: {context or 'Design optimization'}
Proposal: {proposal}

Respond in JSON: {{"assessment": "", "strengths": [], "concerns": [], "confidence": 0.0-1.0}}"""

        response = self.call(prompt)
        if response.success:
            try:
                return json.loads(response.content)
            except json.JSONDecodeError:
                return {"assessment": response.content, "confidence": 0.5}
        return {"error": response.error}

    async def call_async(self, prompt: str) -> GeminiResponse:
        """
        Call Gemini CLI asynchronously

        Args:
            prompt: The prompt to send to Gemini

        Returns:
            GeminiResponse with content and metadata
        """
        start_time = datetime.now()

        try:
            # Build command
            cmd = ["gemini"]
            if self.model:
                cmd.extend(["-m", self.model])
            cmd.append(prompt)

            # Execute asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                duration = (datetime.now() - start_time).total_seconds()
                return GeminiResponse(
                    content="",
                    success=False,
                    error=f"Timeout after {self.timeout} seconds",
                    timestamp=datetime.now().isoformat(),
                    duration_seconds=duration
                )

            duration = (datetime.now() - start_time).total_seconds()

            if process.returncode == 0:
                return GeminiResponse(
                    content=stdout.decode().strip(),
                    success=True,
                    error=None,
                    timestamp=datetime.now().isoformat(),
                    duration_seconds=duration
                )
            else:
                return GeminiResponse(
                    content="",
                    success=False,
                    error=stderr.decode().strip() or "Unknown error",
                    timestamp=datetime.now().isoformat(),
                    duration_seconds=duration
                )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return GeminiResponse(
                content="",
                success=False,
                error=str(e),
                timestamp=datetime.now().isoformat(),
                duration_seconds=duration
            )


# === Prompt Templates ===

def create_review_prompt(proposal: str, context: str = "") -> str:
    """Create a prompt for Gemini to review a proposal"""
    return f"""Please review the following design proposal and provide:
1. Strengths of the proposal
2. Potential issues or improvements
3. An alternative or enhanced proposal

Context: {context}

Proposal:
{proposal}

Please respond in a structured format."""


def create_alternative_prompt(original: str, feedback: str) -> str:
    """Create a prompt for Gemini to generate an alternative"""
    return f"""Based on the following original proposal and feedback,
generate an improved alternative design.

Original Proposal:
{original}

Feedback:
{feedback}

Please provide a complete alternative proposal that addresses the feedback."""


def create_convergence_check_prompt(proposals: list[dict]) -> str:
    """Create a prompt to check if proposals are converging"""
    proposals_text = "\n\n".join([
        f"Proposal {i+1} ({p['ai']}):\n{p['content']}"
        for i, p in enumerate(proposals[-3:])  # Last 3 proposals
    ])

    return f"""Analyze whether the following proposals are converging
towards a consensus. Rate convergence from 0.0 to 1.0.

{proposals_text}

Respond with JSON: {{"convergence_score": float, "analysis": string}}"""


# === Convenience Functions ===

def get_gemini_review(proposal: str, context: str = "") -> Optional[str]:
    """Quick function to get a Gemini review"""
    caller = GeminiCaller()
    prompt = create_review_prompt(proposal, context)
    response = caller.call(prompt)
    return response.content if response.success else None


def get_gemini_alternative(original: str, feedback: str) -> Optional[str]:
    """Quick function to get a Gemini alternative"""
    caller = GeminiCaller()
    prompt = create_alternative_prompt(original, feedback)
    response = caller.call(prompt)
    return response.content if response.success else None


if __name__ == "__main__":
    # Test the caller
    caller = GeminiCaller()

    print("Testing Gemini CLI caller...")
    response = caller.call("Say 'Hello from Gemini!' in one line.")

    if response.success:
        print(f"Success: {response.content}")
        print(f"Duration: {response.duration_seconds:.2f}s")
    else:
        print(f"Error: {response.error}")
