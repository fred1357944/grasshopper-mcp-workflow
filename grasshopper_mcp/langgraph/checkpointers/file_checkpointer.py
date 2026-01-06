"""
File-based State Checkpointer

Persists workflow state to the filesystem for:
- Resume after interruption
- Session history tracking
- State rollback capabilities
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Any
from ..state import DesignState


class FileCheckpointer:
    """
    File-based checkpointer for LangGraph workflows

    Saves state to JSON files in a structured directory:
    ```
    base_path/
    ├── sessions/
    │   ├── {session_id}/
    │   │   ├── state.json          # Current state
    │   │   ├── history/            # State history
    │   │   │   ├── 001_state.json
    │   │   │   ├── 002_state.json
    │   │   │   └── ...
    │   │   └── proposals/          # Individual proposals
    │   │       ├── 001_claude.md
    │   │       └── 002_gemini.md
    │   └── ...
    └── index.json                  # Session index
    ```
    """

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize the checkpointer

        Args:
            base_path: Base directory for checkpoints.
                      Defaults to GH_WIP/optimization_session/
        """
        if base_path is None:
            base_path = os.path.join(os.getcwd(), "GH_WIP", "optimization_session")

        self.base_path = Path(base_path)
        self.sessions_path = self.base_path / "sessions"
        self.index_path = self.base_path / "index.json"

        # Ensure directories exist
        self.sessions_path.mkdir(parents=True, exist_ok=True)

        # Initialize index if needed
        if not self.index_path.exists():
            self._save_index({"sessions": [], "last_updated": datetime.now().isoformat()})

    def save(self, state: DesignState) -> str:
        """
        Save current state

        Args:
            state: The state to save

        Returns:
            Session ID
        """
        session_id = state["session_id"]
        session_path = self.sessions_path / session_id

        # Create session directory
        session_path.mkdir(parents=True, exist_ok=True)
        (session_path / "history").mkdir(exist_ok=True)
        (session_path / "proposals").mkdir(exist_ok=True)

        # Save current state
        state_file = session_path / "state.json"
        self._save_json(state_file, dict(state))

        # Save to history
        history_count = len(list((session_path / "history").glob("*.json")))
        history_file = session_path / "history" / f"{history_count + 1:03d}_state.json"
        self._save_json(history_file, dict(state))

        # Save proposals
        self._save_proposals(session_path / "proposals", state.get("proposals", []))

        # Update index
        self._update_index(session_id, state)

        return session_id

    def load(self, session_id: str) -> Optional[DesignState]:
        """
        Load state for a session

        Args:
            session_id: The session to load

        Returns:
            The state, or None if not found
        """
        state_file = self.sessions_path / session_id / "state.json"

        if not state_file.exists():
            return None

        return self._load_json(state_file)

    def load_latest(self) -> Optional[DesignState]:
        """
        Load the most recent session

        Returns:
            The latest state, or None if no sessions exist
        """
        index = self._load_index()
        sessions = index.get("sessions", [])

        if not sessions:
            return None

        # Sort by last updated
        sessions.sort(key=lambda s: s.get("last_updated", ""), reverse=True)
        return self.load(sessions[0]["session_id"])

    def list_sessions(self) -> list[dict]:
        """
        List all sessions

        Returns:
            List of session summaries
        """
        index = self._load_index()
        return index.get("sessions", [])

    def get_history(self, session_id: str) -> list[DesignState]:
        """
        Get state history for a session

        Args:
            session_id: The session

        Returns:
            List of historical states
        """
        history_path = self.sessions_path / session_id / "history"

        if not history_path.exists():
            return []

        history = []
        for state_file in sorted(history_path.glob("*.json")):
            state = self._load_json(state_file)
            if state:
                history.append(state)

        return history

    def rollback(self, session_id: str, history_index: int) -> Optional[DesignState]:
        """
        Rollback to a previous state

        Args:
            session_id: The session
            history_index: The history index to rollback to (1-based)

        Returns:
            The rolled-back state, or None if failed
        """
        history = self.get_history(session_id)

        if not history or history_index < 1 or history_index > len(history):
            return None

        # Get the state at the specified index
        state = history[history_index - 1]

        # Save as current state
        self.save(state)

        return state

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session

        Args:
            session_id: The session to delete

        Returns:
            True if deleted, False if not found
        """
        session_path = self.sessions_path / session_id

        if not session_path.exists():
            return False

        import shutil
        shutil.rmtree(session_path)

        # Update index
        index = self._load_index()
        index["sessions"] = [
            s for s in index["sessions"]
            if s["session_id"] != session_id
        ]
        self._save_index(index)

        return True

    def generate_report(self, session_id: str) -> str:
        """
        Generate a markdown report for a session

        Args:
            session_id: The session

        Returns:
            Markdown report string
        """
        state = self.load(session_id)
        if not state:
            return f"Session {session_id} not found."

        history = self.get_history(session_id)

        report = f"""# Optimization Session Report

## Session Info
- **ID**: {state['session_id']}
- **Topic**: {state['topic']}
- **Mode**: {state['mode']}
- **Created**: {state['created_at']}
- **Stage**: {state['current_stage']}

## Progress
- **Iterations**: {state['current_iteration']} / {state['max_iterations']}
- **Convergence**: {state['convergence_score']:.2f}
- **Converged**: {'Yes' if state['is_converged'] else 'No'}

## Proposals ({len(state.get('proposals', []))})
"""
        for i, prop in enumerate(state.get('proposals', [])[:10]):
            report += f"\n### {i+1}. {prop['ai'].title()} - Iteration {prop['iteration']}\n"
            report += f"*{prop['timestamp']}*\n"
            report += f"\n{prop['content'][:500]}...\n" if len(prop.get('content', '')) > 500 else f"\n{prop.get('content', 'N/A')}\n"

        if state.get('variants'):
            report += f"\n## Variants ({len(state['variants'])})\n"
            for v in state['variants']:
                report += f"- **{v['variant_id']}**: Score {v['quality_score']:.2f}\n"

        if state.get('errors'):
            report += f"\n## Errors ({len(state['errors'])})\n"
            for e in state['errors'][:5]:
                report += f"- {e}\n"

        if state.get('decisions_made'):
            report += f"\n## Decisions Made\n"
            for d in state['decisions_made']:
                report += f"- **{d['question']}**: {d['chosen_option']}\n"

        report += f"\n## History\n- {len(history)} state snapshots saved\n"

        return report

    # === Private Methods ===

    def _save_json(self, path: Path, data: Any) -> None:
        """Save data as JSON"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def _load_json(self, path: Path) -> Optional[dict]:
        """Load JSON data"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _save_index(self, index: dict) -> None:
        """Save the session index"""
        self._save_json(self.index_path, index)

    def _load_index(self) -> dict:
        """Load the session index"""
        return self._load_json(self.index_path) or {"sessions": []}

    def _update_index(self, session_id: str, state: DesignState) -> None:
        """Update the session index"""
        index = self._load_index()

        # Find or create session entry
        session_entry = None
        for s in index["sessions"]:
            if s["session_id"] == session_id:
                session_entry = s
                break

        if session_entry is None:
            session_entry = {"session_id": session_id}
            index["sessions"].append(session_entry)

        # Update entry
        session_entry.update({
            "topic": state["topic"],
            "mode": state["mode"],
            "stage": state["current_stage"],
            "iteration": state["current_iteration"],
            "convergence": state["convergence_score"],
            "last_updated": datetime.now().isoformat(),
        })

        index["last_updated"] = datetime.now().isoformat()
        self._save_index(index)

    def _save_proposals(self, proposals_path: Path, proposals: list) -> None:
        """Save individual proposals as markdown files"""
        for i, prop in enumerate(proposals):
            filename = f"{i+1:03d}_{prop['ai']}.md"
            filepath = proposals_path / filename

            content = f"""# {prop['ai'].title()} Proposal - Iteration {prop['iteration']}

*Timestamp: {prop['timestamp']}*

---

{prop['content']}
"""
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
