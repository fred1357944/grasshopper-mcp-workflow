import json
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Any
from pathlib import Path

@dataclass
class PortInfo:
    name: str
    nickname: str
    description: str = ""
    type_hint_id: str = "unknown"  # e.g., "gh_int", "gh_curve", "gh_brep"
    access: str = "item"           # "item", "list", "tree"

@dataclass
class ComponentSignature:
    guid: str
    name: str
    nickname: str
    category: str = "General"
    inputs: Dict[str, PortInfo] = field(default_factory=dict)
    outputs: Dict[str, PortInfo] = field(default_factory=dict)

class ConnectionKnowledgeBase:
    """
    Central Knowledge Base for Component Connections and Types.
    Stores:
    1. Component Signatures (Inputs/Outputs/Types)
    2. Connection Triplets (Source.Out -> Target.In statistics)
    3. Type Compatibility Matrix
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        self.signatures: Dict[str, ComponentSignature] = {} # Key: Component Name (or GUID if available)
        self.connection_triplets: Dict[str, int] = {} # Key: "Source.Out->Target.In", Value: Frequency
        self.guid_map: Dict[str, str] = {} # Key: GUID, Value: Component Name
        
        # Heuristic map for parameter nicknames to likely types
        self.param_type_heuristics = {
            "C": "gh_curve", "crv": "gh_curve", "Curve": "gh_curve",
            "P": "gh_point", "Pt": "gh_point", "Point": "gh_point",
            "V": "gh_vector", "Vec": "gh_vector",
            "I": "gh_integer", "N": "gh_number", "val": "gh_number",
            "B": "gh_brep", "Brep": "gh_brep", "S": "gh_surface",
            "M": "gh_mesh", "Mesh": "gh_mesh",
            "Pln": "gh_plane", "F": "gh_plane", # Frame
            "T": "gh_boolean", "Bool": "gh_boolean",
            "D": "gh_domain",
            "Col": "gh_colour",
            "Box": "gh_box",
            "Str": "gh_string", "Txt": "gh_string"
        }

        # Compatible types (Parent -> Child is valid)
        self.compatible_types = {
            ("gh_integer", "gh_number"),
            ("gh_number", "gh_string"), # Auto-convert
            ("gh_integer", "gh_string"),
            ("gh_point", "gh_vector"), # Often interchangeable
            ("gh_vector", "gh_point"),
            ("gh_line", "gh_curve"),
            ("gh_circle", "gh_curve"),
            ("gh_arc", "gh_curve"),
            ("gh_polyline", "gh_curve"),
            ("gh_curve", "gh_geometry"),
            ("gh_surface", "gh_geometry"),
            ("gh_brep", "gh_geometry"),
            ("gh_mesh", "gh_geometry"),
            ("gh_box", "gh_brep"), # Box can cast to Brep
            ("gh_box", "gh_mesh"), # Box can cast to Mesh
            ("gh_surface", "gh_brep") # Surface is a single-face Brep
        }

        if storage_dir:
            self.load_knowledge(storage_dir)

    def load_knowledge(self, directory: Path):
        """Loads learned data from JSON files."""
        triplet_file = directory / "connection_triplets.json"
        if triplet_file.exists():
            try:
                with open(triplet_file, 'r', encoding='utf-8') as f:
                    self.connection_triplets = json.load(f)
            except Exception as e:
                print(f"Error loading triplets: {e}")

        # Load signatures from wasp_component_params.json or similar if available
        # This is a placeholder for loading specific library definitions
        pass

    def save_knowledge(self, directory: Path):
        """Saves learned data to JSON files."""
        directory.mkdir(parents=True, exist_ok=True)
        with open(directory / "connection_triplets.json", 'w', encoding='utf-8') as f:
            json.dump(self.connection_triplets, f, indent=2, sort_keys=True)

    def register_component_from_json(self, name: str, data: Dict):
        """Registers a component from the wasp_component_params.json format."""
        sig = ComponentSignature(
            guid=data.get("guid", ""), # Often missing in current JSON
            name=name,
            nickname=name, # Default to name if no nickname
        )

        for inp in data.get("inputs", []):
            p_name = inp.get("name", "")
            p_nick = inp.get("nickname", "")
            p_type = self._guess_type(p_name, p_nick, inp.get("description", ""))
            sig.inputs[p_name] = PortInfo(name=p_name, nickname=p_nick, description=inp.get("description", ""), type_hint_id=p_type)

        for out in data.get("outputs", []):
            p_name = out.get("name", "")
            p_nick = out.get("nickname", "")
            p_type = self._guess_type(p_name, p_nick, out.get("description", ""))
            sig.outputs[p_name] = PortInfo(name=p_name, nickname=p_nick, description=out.get("description", ""), type_hint_id=p_type)
        
        self.signatures[name] = sig

    def _guess_type(self, name: str, nickname: str, desc: str) -> str:
        """Heuristic to guess type from parameter info."""
        # 1. Check direct nickname match
        if nickname in self.param_type_heuristics:
            return self.param_type_heuristics[nickname]
        
        # 2. Check keywords in description
        desc_lower = desc.lower()
        if "curve" in desc_lower: return "gh_curve"
        if "point" in desc_lower: return "gh_point"
        if "plane" in desc_lower: return "gh_plane"
        if "vector" in desc_lower: return "gh_vector"
        if "mesh" in desc_lower: return "gh_mesh"
        if "brep" in desc_lower: return "gh_brep"
        if "boolean" in desc_lower or "true" in desc_lower: return "gh_boolean"
        if "integer" in desc_lower: return "gh_integer"
        if "number" in desc_lower: return "gh_number"
        
        return "unknown"

    def record_connection(self, source_comp: str, source_port: str, target_comp: str, target_port: str):
        """Records a successful connection (Learning)."""
        key = f"{source_comp}.{source_port}->{target_comp}.{target_port}"
        self.connection_triplets[key] = self.connection_triplets.get(key, 0) + 1

    def get_connection_confidence(self, source_comp: str, source_port: str, target_comp: str, target_port: str) -> float:
        """Returns a confidence score (0.0 to 1.0) for a connection."""
        key = f"{source_comp}.{source_port}->{target_comp}.{target_port}"
        count = self.connection_triplets.get(key, 0)
        
        # Simple sigmoid-like confidence
        if count >= 10: return 1.0
        if count >= 5: return 0.9
        if count >= 1: return 0.7
        return 0.0

    def is_type_compatible(self, source_type: str, target_type: str) -> bool:
        """Checks if types are compatible."""
        if source_type == "unknown" or target_type == "unknown":
            return True # Benefit of doubt
        if source_type == target_type:
            return True
        if (source_type, target_type) in self.compatible_types:
            return True
        return False