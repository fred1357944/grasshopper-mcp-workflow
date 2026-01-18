"""
CLI Commands - 命令處理器

支援的 Slash Commands:
- /think <topic>: 啟動 Think-Partner 蘇格拉底式探索
- /brainstorm <topic>: 啟動三階段腦力激盪
- /workflow <topic>: 啟動確定性四階段管線
- /meta <topic>: 啟動 Meta-Agent 工具創建
- /status: 查看當前狀態
- /continue: 繼續當前對話
- /reset: 重置會話

整合 EnhancedGHOrchestrator 和 IntentRouter。
"""

import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..langgraph.core.intent_router import IntentType, is_manual_trigger
from ..langgraph.core.integration import EnhancedGHOrchestrator
from ..langgraph.state import DesignState


class CommandType(str, Enum):
    """Command types"""
    THINK = "think"
    BRAINSTORM = "brainstorm"
    WORKFLOW = "workflow"
    META = "meta"
    STATUS = "status"
    CONTINUE = "continue"
    RESET = "reset"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class CommandResult:
    """Result of command execution"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    awaiting_input: bool = False
    prompt: Optional[str] = None


class CommandHandler:
    """
    Command handler for slash commands

    Usage:
        handler = CommandHandler()
        result = await handler.execute("/think parametric chair design")

        if result.awaiting_input:
            # Show prompt to user
            print(result.prompt)
            user_input = input("> ")
            result = await handler.continue_conversation(user_input)
    """

    def __init__(self):
        self.orchestrator: Optional[EnhancedGHOrchestrator] = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of orchestrator"""
        if not self._initialized:
            self.orchestrator = EnhancedGHOrchestrator.create()
            self._initialized = True

    async def execute(self, command: str) -> CommandResult:
        """
        Execute a slash command

        Args:
            command: Full command string (e.g., "/think parametric chair")

        Returns:
            CommandResult with execution outcome
        """
        self._ensure_initialized()

        # Parse command
        cmd_type, topic = self._parse_command(command)

        # Handle built-in commands
        if cmd_type == CommandType.HELP:
            return self._show_help()
        elif cmd_type == CommandType.STATUS:
            return self._show_status()
        elif cmd_type == CommandType.RESET:
            return self._reset_session()
        elif cmd_type == CommandType.CONTINUE:
            return CommandResult(
                success=True,
                message="Use continue_conversation() with user input",
                awaiting_input=True,
                prompt="Enter your response: "
            )

        # Map to IntentType
        intent_map = {
            CommandType.THINK: IntentType.THINK_PARTNER,
            CommandType.BRAINSTORM: IntentType.BRAINSTORM,
            CommandType.WORKFLOW: IntentType.WORKFLOW,
            CommandType.META: IntentType.META_AGENT,
        }

        intent_type = intent_map.get(cmd_type)

        if intent_type is None:
            return CommandResult(
                success=False,
                message=f"Unknown command: {command}",
            )

        # Execute with forced mode
        try:
            result = await self.orchestrator.execute_with_mode_selection(
                task=topic,
                context={},
                force_mode=intent_type
            )

            # Check if awaiting user input
            state_updates = result.get("state_updates", {})
            awaiting = state_updates.get("awaiting_confirmation", False)
            prompt = None

            if awaiting:
                decisions = state_updates.get("pending_decisions", [])
                if decisions:
                    last_decision = decisions[-1]
                    prompt = self._format_decision_prompt(last_decision)

            return CommandResult(
                success=True,
                message=f"Mode: {result['mode']} | Strategy: {result['strategy']}",
                data=result,
                awaiting_input=awaiting,
                prompt=prompt,
            )

        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Error executing command: {str(e)}",
            )

    async def continue_conversation(self, user_input: str) -> CommandResult:
        """
        Continue conversation with user input

        Args:
            user_input: User's response to previous prompt

        Returns:
            CommandResult with next step
        """
        self._ensure_initialized()

        if self.orchestrator is None:
            return CommandResult(
                success=False,
                message="No active session. Use a command first.",
            )

        try:
            result = self.orchestrator.continue_conversation(user_input)

            # Check if still awaiting
            awaiting = result.get("awaiting_confirmation", False)
            prompt = None

            if awaiting:
                decisions = result.get("pending_decisions", [])
                if decisions:
                    last_decision = decisions[-1]
                    prompt = self._format_decision_prompt(last_decision)

            return CommandResult(
                success=True,
                message="Conversation continued",
                data=result,
                awaiting_input=awaiting,
                prompt=prompt,
            )

        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Error continuing conversation: {str(e)}",
            )

    def _parse_command(self, command: str) -> tuple[CommandType, str]:
        """Parse command string into type and topic"""
        command = command.strip()

        if not command.startswith("/"):
            return CommandType.UNKNOWN, command

        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        topic = parts[1] if len(parts) > 1 else ""

        cmd_map = {
            "/think": CommandType.THINK,
            "/brainstorm": CommandType.BRAINSTORM,
            "/workflow": CommandType.WORKFLOW,
            "/meta": CommandType.META,
            "/status": CommandType.STATUS,
            "/continue": CommandType.CONTINUE,
            "/reset": CommandType.RESET,
            "/help": CommandType.HELP,
        }

        return cmd_map.get(cmd, CommandType.UNKNOWN), topic

    def _format_decision_prompt(self, decision: Dict) -> str:
        """Format a decision into a user prompt"""
        lines = [
            decision.get("question", "Please make a decision:"),
            "",
            "Options:",
        ]

        options = decision.get("options", [])
        for i, opt in enumerate(options, 1):
            lines.append(f"  {i}. {opt}")

        lines.extend([
            "",
            "Enter your choice (number or text):",
        ])

        return "\n".join(lines)

    def _show_help(self) -> CommandResult:
        """Show help information"""
        help_text = """
Superpower Commands
===================

Mode Commands:
  /think <topic>      - Start Think-Partner exploration (Socratic method)
  /brainstorm <topic> - Start 3-phase brainstorming (Superpowers)
  /workflow <topic>   - Start 4-stage deterministic pipeline
  /meta <topic>       - Start Meta-Agent for tool creation

Session Commands:
  /status             - Show current session status
  /continue           - Continue conversation with input
  /reset              - Reset the current session
  /help               - Show this help

Examples:
  /think what makes a good chair design
  /brainstorm ideas for a parametric table
  /workflow create a simple box
  /meta create a spiral pattern tool
"""
        return CommandResult(
            success=True,
            message=help_text.strip(),
        )

    def _show_status(self) -> CommandResult:
        """Show current session status"""
        self._ensure_initialized()

        state = self.orchestrator.get_current_state()

        if state is None:
            return CommandResult(
                success=True,
                message="No active session. Use a command to start.",
            )

        status_lines = [
            "Session Status",
            "==============",
            f"Topic: {state.get('topic', 'N/A')}",
            f"Mode: {state.get('intent_type', 'N/A')}",
            f"Stage: {state.get('current_stage', 'N/A')}",
            f"Iteration: {state.get('current_iteration', 0)}",
            "",
        ]

        # Mode-specific status
        intent = state.get("intent_type")

        if intent == IntentType.THINK_PARTNER.value:
            status_lines.append(f"Thinking Mode: {state.get('thinking_mode', 'N/A')}")
            status_lines.append(f"Questions Asked: {len(state.get('thinking_log', []))}")
            status_lines.append(f"Insights: {len(state.get('thinking_insights', []))}")

        elif intent == IntentType.BRAINSTORM.value:
            status_lines.append(f"Brainstorm Phase: {state.get('brainstorm_phase', 'N/A')}")
            status_lines.append(f"Ideas: {len(state.get('brainstorm_ideas', []))}")
            status_lines.append(f"Constraints: {len(state.get('brainstorm_constraints', []))}")

        elif intent == IntentType.META_AGENT.value:
            status_lines.append(f"Meta-Agent Active: {state.get('meta_agent_active', False)}")
            status_lines.append(f"Generated Tools: {len(state.get('generated_tools', []))}")

        elif intent == IntentType.WORKFLOW.value:
            status_lines.append(f"Subtasks: {len(state.get('subtasks', []))}")
            status_lines.append(f"Retrieved Tools: {len(state.get('retrieved_tools', []))}")

        # Errors/log
        errors = state.get("errors", [])
        if errors:
            status_lines.append("")
            status_lines.append(f"Log entries: {len(errors)}")
            status_lines.append(f"Last: {errors[-1][:60]}..." if errors else "")

        return CommandResult(
            success=True,
            message="\n".join(status_lines),
            data={"state": dict(state)} if state else None,
        )

    def _reset_session(self) -> CommandResult:
        """Reset the current session"""
        self._ensure_initialized()
        self.orchestrator.reset_session()

        return CommandResult(
            success=True,
            message="Session reset. Ready for new commands.",
        )


# === CLI Entry Point ===

async def run_cli():
    """Simple CLI interface for testing"""
    handler = CommandHandler()

    print("Superpower CLI")
    print("Type /help for available commands, or 'quit' to exit")
    print()

    while True:
        try:
            user_input = input("> ").strip()

            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                result = await handler.execute(user_input)
            else:
                # Continue conversation
                result = await handler.continue_conversation(user_input)

            print(result.message)

            if result.data:
                # Show summary of data
                if "state_updates" in result.data:
                    updates = result.data["state_updates"]
                    if updates.get("errors"):
                        print(f"\nLog: {updates['errors'][-1]}")

            if result.awaiting_input and result.prompt:
                print()
                print(result.prompt)

            print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Main entry point"""
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
