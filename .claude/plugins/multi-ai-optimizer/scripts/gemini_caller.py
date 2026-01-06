#!/usr/bin/env python3
"""
Gemini CLI Caller for Multi-AI Optimizer

Provides a Python interface to call Gemini CLI for AI collaboration.
Supports both synchronous and asynchronous calling patterns.
"""

import subprocess
import json
import asyncio
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class GeminiResponse:
    """Response from Gemini CLI"""
    content: str
    success: bool
    error: Optional[str]
    timestamp: str
    duration_seconds: float


class GeminiCaller:
    """
    Wrapper for Gemini CLI calls

    Usage:
        caller = GeminiCaller()
        response = caller.call("Analyze this design proposal...")
        print(response.content)
    """

    def __init__(
        self,
        timeout: int = 60,
        model: Optional[str] = None
    ):
        """
        Initialize Gemini caller

        Args:
            timeout: Maximum seconds to wait for response
            model: Optional model override (e.g., "gemini-pro")
        """
        self.timeout = timeout
        self.model = model
        self._verify_installation()

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
        Call Gemini CLI synchronously

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

            # Execute
            result = subprocess.run(
                cmd,
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
                    duration_seconds=duration
                )
            else:
                return GeminiResponse(
                    content="",
                    success=False,
                    error=result.stderr.strip() or "Unknown error",
                    timestamp=datetime.now().isoformat(),
                    duration_seconds=duration
                )

        except subprocess.TimeoutExpired:
            duration = (datetime.now() - start_time).total_seconds()
            return GeminiResponse(
                content="",
                success=False,
                error=f"Timeout after {self.timeout} seconds",
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
