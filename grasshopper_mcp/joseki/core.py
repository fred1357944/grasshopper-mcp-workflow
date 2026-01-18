"""
Grasshopper Joseki (定式) Core Data Structures

Provides data models for storing and retrieving reusable Grasshopper patterns.
Optimized for RAG retrieval and precise topology reconstruction.
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path


@dataclass
class PortConstraint:
    """Parameter constraints for validation and UI hints"""
    node_id: str            # Corresponding node ID
    port_name: str          # Port name (e.g., "Count", "Radius")
    type_hint: str          # Type hint: "Integer", "Float", "Interval", "Boolean"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    options: List[Any] = field(default_factory=list)  # For Value Lists
    description: str = ""


@dataclass
class JosekiNode:
    """A node (component) in the graph"""
    id: str                 # Unique ID within the graph
    name: str               # Component display name (e.g., "Voronoi")
    component_guid: str     # Grasshopper Component GUID
    nickname: Optional[str] = None
    input_values: Dict[str, Any] = field(default_factory=dict)  # Static input values
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})


@dataclass
class JosekiConnection:
    """A connection (wire) between nodes"""
    from_node_id: str
    from_port: str          # Output port name
    to_node_id: str
    to_port: str            # Input port name


@dataclass
class JosekiStats:
    """Usage statistics for retrieval optimization"""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: str = field(default_factory=lambda: datetime.now().isoformat())
    success_count: int = 0
    failure_count: int = 0
    author: str = "System"


@dataclass
class GrasshopperJoseki:
    """
    Grasshopper Joseki (定式) Standard Format

    Design goals:
    - RAG retrieval friendly
    - Precise topology reconstruction
    - Few-shot prompting support
    """
    id: str
    name: str               # Joseki name
    description: str        # Human-readable description
    category: str           # Category (e.g., "Pattern", "Structure")
    tags: List[str]         # Keywords

    # RAG fields
    pseudo_code: str        # Step-by-step logic for LLM understanding
    embedding_text: str = ""  # Vector embedding source text

    # Topology
    nodes: List[JosekiNode] = field(default_factory=list)
    connections: List[JosekiConnection] = field(default_factory=list)
    constraints: List[PortConstraint] = field(default_factory=list)

    # Metadata
    preview_image: Optional[str] = None
    stats: JosekiStats = field(default_factory=JosekiStats)

    def __post_init__(self):
        if not self.embedding_text:
            self.embedding_text = self._generate_rag_text()

    def _generate_rag_text(self) -> str:
        """Generate optimized text for vector embedding"""
        return (
            f"[{self.category}] {self.name}: {self.description}\n"
            f"Tags: {', '.join(self.tags)}\n"
            f"Logic Steps:\n{self.pseudo_code}"
        )

    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_json(cls, json_str: str) -> 'GrasshopperJoseki':
        """Deserialize from JSON string"""
        data = json.loads(json_str)
        return cls._from_dict(data)

    @classmethod
    def from_file(cls, filepath: str) -> 'GrasshopperJoseki':
        """Load from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: Dict) -> 'GrasshopperJoseki':
        """Convert dictionary to GrasshopperJoseki"""
        # Convert nested dataclasses
        nodes = [JosekiNode(**n) if isinstance(n, dict) else n for n in data.get('nodes', [])]
        connections = [JosekiConnection(**c) if isinstance(c, dict) else c for c in data.get('connections', [])]
        constraints = [PortConstraint(**c) if isinstance(c, dict) else c for c in data.get('constraints', [])]
        stats = JosekiStats(**data.get('stats', {})) if isinstance(data.get('stats'), dict) else JosekiStats()

        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            category=data['category'],
            tags=data['tags'],
            pseudo_code=data['pseudo_code'],
            embedding_text=data.get('embedding_text', ''),
            nodes=nodes,
            connections=connections,
            constraints=constraints,
            preview_image=data.get('preview_image'),
            stats=stats
        )

    def save(self, directory: str) -> str:
        """Save to JSON file in directory"""
        filepath = Path(directory) / f"{self.id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
        return str(filepath)

    def generate_mcp_commands(self) -> List[Dict]:
        """
        Generate MCP commands to recreate this Joseki

        Returns list of commands to:
        1. Add all components
        2. Set input values
        3. Create connections
        """
        commands = []

        # Add components
        for node in self.nodes:
            commands.append({
                "type": "add_component",
                "parameters": {
                    "guid": node.component_guid,
                    "x": node.position["x"],
                    "y": node.position["y"]
                },
                "_node_id": node.id,
                "_description": f"Add {node.name}"
            })

        # Note: Connection commands would need actual instance GUIDs
        # which are only available after components are created

        return commands

    def to_prompt_context(self) -> str:
        """
        Generate context for LLM few-shot prompting

        Returns formatted string suitable for including in prompts
        """
        nodes_str = "\n".join([
            f"  - {n.name} (id: {n.id})" +
            (f" with inputs: {n.input_values}" if n.input_values else "")
            for n in self.nodes
        ])

        conns_str = "\n".join([
            f"  - {c.from_node_id}.{c.from_port} -> {c.to_node_id}.{c.to_port}"
            for c in self.connections
        ])

        return f"""### Joseki: {self.name}
Category: {self.category}
Description: {self.description}

Steps:
{self.pseudo_code}

Components:
{nodes_str}

Connections:
{conns_str}
"""


class JosekiLibrary:
    """
    Manager for Joseki collection

    Handles loading, saving, and searching Joseki patterns
    """

    def __init__(self, library_path: str):
        self.library_path = Path(library_path)
        self.library_path.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, GrasshopperJoseki] = {}
        self._load_all()

    def _load_all(self):
        """Load all Joseki from library directory"""
        for filepath in self.library_path.glob("*.json"):
            try:
                joseki = GrasshopperJoseki.from_file(str(filepath))
                self._cache[joseki.id] = joseki
            except Exception as e:
                print(f"Warning: Failed to load {filepath}: {e}")

    def get(self, joseki_id: str) -> Optional[GrasshopperJoseki]:
        """Get Joseki by ID"""
        return self._cache.get(joseki_id)

    def search_by_name(self, query: str) -> List[GrasshopperJoseki]:
        """Simple name-based search"""
        query_lower = query.lower()
        return [
            j for j in self._cache.values()
            if query_lower in j.name.lower() or query_lower in j.description.lower()
        ]

    def search_by_tags(self, tags: List[str]) -> List[GrasshopperJoseki]:
        """Search by tags"""
        return [
            j for j in self._cache.values()
            if any(tag in j.tags for tag in tags)
        ]

    def search_by_category(self, category: str) -> List[GrasshopperJoseki]:
        """Search by category"""
        return [j for j in self._cache.values() if j.category == category]

    def add(self, joseki: GrasshopperJoseki) -> str:
        """Add new Joseki to library"""
        filepath = joseki.save(str(self.library_path))
        self._cache[joseki.id] = joseki
        return filepath

    def list_all(self) -> List[GrasshopperJoseki]:
        """List all Joseki"""
        return list(self._cache.values())

    def get_categories(self) -> List[str]:
        """Get all unique categories"""
        return list(set(j.category for j in self._cache.values()))

    def get_all_tags(self) -> List[str]:
        """Get all unique tags"""
        tags = set()
        for j in self._cache.values():
            tags.update(j.tags)
        return list(tags)


def create_sample_joseki():
    """Create sample Joseki patterns for testing"""

    # Voronoi pattern
    voronoi = GrasshopperJoseki(
        id=str(uuid.uuid4()),
        name="Basic 2D Voronoi",
        description="Generates a Voronoi diagram within a rectangular boundary using random points.",
        category="Pattern Generation",
        tags=["voronoi", "2d", "random", "tessellation", "cellular", "pattern"],
        pseudo_code="""1. Define a Rectangle as the boundary region.
2. Populate the region with N random 2D points.
3. Compute Voronoi diagram using these points.
4. Clip the Voronoi cells to the original Rectangle boundary.""",
        nodes=[
            JosekiNode(
                id="n1",
                name="Rectangle",
                component_guid="87f3-rectangle-guid",
                nickname="Bounds",
                input_values={"X": 100, "Y": 100},
                position={"x": 0, "y": 0}
            ),
            JosekiNode(
                id="n2",
                name="Populate2D",
                component_guid="98a2-populate-guid",
                nickname="RandomPoints",
                input_values={"Count": 50, "Seed": 1},
                position={"x": 150, "y": 0}
            ),
            JosekiNode(
                id="n3",
                name="Voronoi",
                component_guid="12b4-voronoi-guid",
                position={"x": 300, "y": 0}
            )
        ],
        connections=[
            JosekiConnection("n1", "R", "n2", "R"),
            JosekiConnection("n2", "P", "n3", "P"),
            JosekiConnection("n1", "R", "n3", "B")
        ],
        constraints=[
            PortConstraint(
                node_id="n2",
                port_name="Count",
                type_hint="Integer",
                min_value=1,
                max_value=1000,
                description="Number of Voronoi cells"
            )
        ]
    )

    # Box Array pattern
    box_array = GrasshopperJoseki(
        id=str(uuid.uuid4()),
        name="Simple Box Grid",
        description="Creates a 3D grid of boxes using rectangular array transformation.",
        category="Structure",
        tags=["array", "grid", "3d", "box", "structure", "repetition"],
        pseudo_code="""1. Create a CenterBox with specified dimensions.
2. Apply RectangularArray to create a grid pattern.
3. Adjust spacing and count for X, Y, Z directions.""",
        nodes=[
            JosekiNode(
                id="n1",
                name="Center Box",
                component_guid="4e874a4e-95cd-46d0-904d-19cca8fd962c",
                input_values={"X": 10, "Y": 10, "Z": 10},
                position={"x": 0, "y": 0}
            ),
            JosekiNode(
                id="n2",
                name="Rectangular Array",
                component_guid="arr-rect-guid",
                input_values={"Nx": 5, "Ny": 5, "Nz": 1},
                position={"x": 200, "y": 0}
            )
        ],
        connections=[
            JosekiConnection("n1", "B", "n2", "G")
        ]
    )

    return [voronoi, box_array]


if __name__ == "__main__":
    # Generate sample Joseki
    samples = create_sample_joseki()
    for joseki in samples:
        print(f"\n{'='*50}")
        print(joseki.to_prompt_context())
        print(f"\nJSON:\n{joseki.to_json()[:500]}...")
