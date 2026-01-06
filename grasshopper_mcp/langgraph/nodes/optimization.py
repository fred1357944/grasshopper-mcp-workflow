"""
Optimization Nodes

Implements iterative design optimization loop (Option A)
"""

from typing import Any
from ..state import DesignState, Proposal, calculate_convergence
from datetime import datetime
import subprocess
import json


def optimize_parameters_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Optimize design parameters

    This node:
    1. Analyzes current design state
    2. Generates improvement proposal (Claude)
    3. Gets alternative/review from Gemini
    4. Updates proposals list
    5. Calculates convergence

    Implements the Claude-Gemini alternating pattern
    """
    current_iteration = state["current_iteration"]
    max_iterations = state["max_iterations"]
    proposals = state.get("proposals", [])

    # Check if we should continue
    if current_iteration >= max_iterations:
        return {
            "awaiting_confirmation": True,
            "confirmation_reason": "max_iterations_reached",
            "current_stage": "evaluation",
        }

    # Generate Claude proposal
    claude_proposal = _generate_claude_proposal(state)

    # Get Gemini review/alternative
    gemini_response = _get_gemini_review(claude_proposal, state)

    # Create proposal records
    new_proposals = [
        Proposal(
            ai="claude",
            content=claude_proposal,
            timestamp=datetime.now().isoformat(),
            iteration=current_iteration + 1,
            score=None
        )
    ]

    if gemini_response:
        new_proposals.append(Proposal(
            ai="gemini",
            content=gemini_response,
            timestamp=datetime.now().isoformat(),
            iteration=current_iteration + 1,
            score=None
        ))

    # Calculate convergence
    all_proposals = proposals + new_proposals
    convergence = calculate_convergence(all_proposals)
    is_converged = convergence > 0.85

    return {
        "proposals": new_proposals,
        "current_iteration": current_iteration + 1,
        "convergence_score": convergence,
        "is_converged": is_converged,
        "current_stage": "optimization",
    }


def check_convergence_node(state: DesignState) -> dict[str, Any]:
    """
    Node: Check if optimization has converged

    Determines whether to:
    1. Continue iterating
    2. Pause for human confirmation
    3. Complete optimization

    Returns routing decision
    """
    convergence_score = state["convergence_score"]
    is_converged = state["is_converged"]
    current_iteration = state["current_iteration"]
    max_iterations = state["max_iterations"]

    # Check convergence
    if is_converged:
        return {
            "awaiting_confirmation": True,
            "confirmation_reason": "convergence_reached",
            "final_proposal": _synthesize_final_proposal(state),
            "current_stage": "evaluation",
        }

    # Check max iterations
    if current_iteration >= max_iterations:
        return {
            "awaiting_confirmation": True,
            "confirmation_reason": "max_iterations_reached",
            "final_proposal": _synthesize_final_proposal(state),
            "current_stage": "evaluation",
        }

    # Continue optimization
    return {
        "current_stage": "optimization",
    }


def _generate_claude_proposal(state: DesignState) -> str:
    """
    Generate improvement proposal from Claude

    Analyzes:
    - Current design state
    - Previous proposals
    - Execution errors
    - User requirements

    Returns: Proposal text
    """
    requirements = state.get("requirements", "")
    component_info = state.get("component_info_mmd", "")
    errors = state.get("errors", [])
    proposals = state.get("proposals", [])

    # Build context
    context = f"""
Design Requirements:
{requirements[:500] if requirements else "Not specified"}

Current Component Design:
{component_info[:500] if component_info else "Not specified"}

Previous Errors:
{json.dumps(errors[:5]) if errors else "None"}

Previous Proposals:
{len(proposals)} proposals generated so far
"""

    # In production, this would call Claude API
    # For now, return a template proposal
    proposal = f"""
## Optimization Proposal - Iteration {state['current_iteration'] + 1}

### Analysis
Based on the current design state, I propose the following improvements:

### Proposed Changes
1. [Improvement 1 based on context]
2. [Improvement 2 based on errors]
3. [Optimization suggestion]

### Expected Benefits
- Improved reliability
- Better performance
- Cleaner component layout

### Implementation Notes
- Context analyzed: {len(context)} chars
- Errors addressed: {len(errors)}
"""
    return proposal


def _get_gemini_review(claude_proposal: str, state: DesignState) -> str:
    """
    Get Gemini's review/alternative proposal

    Calls Gemini CLI to:
    1. Review Claude's proposal
    2. Identify strengths and weaknesses
    3. Propose alternatives or improvements

    Returns: Gemini response text
    """
    prompt = f"""Please review the following design optimization proposal and provide:
1. Strengths of the proposal
2. Potential issues or improvements
3. An alternative or enhanced proposal

Context:
- Topic: {state.get('topic', 'Design optimization')}
- Iteration: {state['current_iteration'] + 1}
- Previous convergence: {state.get('convergence_score', 0):.2f}

Proposal to review:
{claude_proposal}

Respond concisely with your analysis and alternative proposal."""

    try:
        # Call Gemini CLI
        result = subprocess.run(
            ["gemini", prompt],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"[Gemini review unavailable: {result.stderr}]"

    except subprocess.TimeoutExpired:
        return "[Gemini review timed out]"
    except FileNotFoundError:
        return "[Gemini CLI not available]"
    except Exception as e:
        return f"[Gemini error: {str(e)}]"


def _synthesize_final_proposal(state: DesignState) -> str:
    """
    Synthesize final proposal from all iterations

    Combines:
    - Best aspects from each proposal
    - Resolved issues
    - Final recommendations
    """
    proposals = state.get("proposals", [])

    if not proposals:
        return "No proposals generated."

    # Get last Claude and Gemini proposals
    claude_proposals = [p for p in proposals if p["ai"] == "claude"]
    gemini_proposals = [p for p in proposals if p["ai"] == "gemini"]

    last_claude = claude_proposals[-1]["content"] if claude_proposals else ""
    last_gemini = gemini_proposals[-1]["content"] if gemini_proposals else ""

    synthesis = f"""
# Final Optimization Proposal

## Summary
After {state['current_iteration']} iterations, the design has reached
{'convergence' if state['is_converged'] else 'maximum iterations'}.

## Convergence Score: {state['convergence_score']:.2f}

## Final Claude Proposal
{last_claude[:1000] if last_claude else "None"}

## Final Gemini Input
{last_gemini[:1000] if last_gemini else "None"}

## Recommended Actions
1. Review the final proposal above
2. Apply changes to component_info.mmd if approved
3. Re-execute placement with updated design

## Statistics
- Total iterations: {state['current_iteration']}
- Total proposals: {len(proposals)}
- Claude proposals: {len(claude_proposals)}
- Gemini proposals: {len(gemini_proposals)}
"""
    return synthesis
