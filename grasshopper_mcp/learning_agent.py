from typing import Dict, Any, List
from pathlib import Path
import json
from .knowledge_base import ConnectionKnowledgeBase

class LearningAgent:
    """
    Agent responsible for learning from successful Grasshopper executions.
    Extracts connection patterns and updates the Knowledge Base.
    """
    
    def __init__(self, knowledge_base: ConnectionKnowledgeBase):
        self.kb = knowledge_base

    def learn_from_execution(self, workflow_json: Dict[str, Any], execution_report: Dict[str, Any]):
        """
        Processes a successful execution report to learn patterns.
        
        Args:
            workflow_json: The workflow configuration that was executed.
            execution_report: The report returned by the GH/WASP execution (must indicate success).
        """
        # 1. Verify Success
        if execution_report.get("status") != "success":
            return

        print("🧠 Learning Agent: analyzing successful workflow...")
        
        # 2. Extract Connections
        connections = workflow_json.get("connections", [])
        components = workflow_json.get("components", [])
        
        # Build ID lookup map
        comp_lookup = {c["id"]: c for c in components}

        learned_count = 0
        
        for conn in connections:
            source_id = conn.get("from") or conn.get("source", {}).get("id")
            target_id = conn.get("to") or conn.get("target", {}).get("id")
            
            # Extract port names
            # Handle different JSON formats (some use fromParam, some use source.port)
            source_port = conn.get("fromParam") or conn.get("source", {}).get("port")
            target_port = conn.get("toParam") or conn.get("target", {}).get("port")

            if not (source_id and target_id and source_port and target_port):
                continue

            source_comp = comp_lookup.get(source_id)
            target_comp = comp_lookup.get(target_id)

            if not source_comp or not target_comp:
                continue
                
            # Use Component Type (Name) for generalization
            # Ideally use GUID, but Name is more readable for now and mapped in KB
            source_type = source_comp.get("type", "Unknown")
            target_type = target_comp.get("type", "Unknown")

            # 3. Update Knowledge Base
            self.kb.record_connection(source_type, source_port, target_type, target_port)
            learned_count += 1

        print(f"✅ Learned {learned_count} connection patterns.")
        
        # 4. Save to Disk (Optional, handled by caller or periodically)
        # self.kb.save_knowledge(...) 
