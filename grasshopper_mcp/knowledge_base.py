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

    @staticmethod
    def _get_default_config_dir() -> Path:
        """Get the default config directory (project root/config)."""
        # Try to find config relative to this module
        module_dir = Path(__file__).parent.parent
        config_dir = module_dir / "config"
        if config_dir.exists():
            return config_dir
        # Fallback to current working directory
        return Path("config")

    def __init__(self, storage_dir: Optional[Path] = None):
        self.signatures: Dict[str, ComponentSignature] = {} # Key: Component Name (or GUID if available)
        self.connection_triplets: Dict[str, int] = {} # Key: "Source.Out->Target.In", Value: Frequency
        self.guid_map: Dict[str, str] = {} # Key: GUID, Value: Component Name

        # Store config directory for pattern lookups
        self.config_dir = Path(storage_dir) if storage_dir else self._get_default_config_dir()
        
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
                    data = json.load(f)
                    # Handle structured format from connection_analyzer.py
                    if isinstance(data, dict) and "triplets" in data:
                        # Convert triplets list to dict format
                        for triplet in data.get("triplets", []):
                            key = f"{triplet['source_component']}.{triplet['source_param']}->{triplet['target_component']}.{triplet['target_param']}"
                            self.connection_triplets[key] = triplet.get("frequency", 1)
                    else:
                        # Legacy format: direct dict
                        self.connection_triplets = data
            except Exception as e:
                print(f"Error loading triplets: {e}")

        # Load wasp_component_params.json for component signatures
        wasp_params_file = directory / "wasp_component_params.json"
        if wasp_params_file.exists():
            try:
                with open(wasp_params_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for name, comp_data in data.get("components", {}).items():
                        self.register_component_from_json(name, comp_data)
            except Exception as e:
                print(f"Error loading wasp_component_params: {e}")

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

    def search_patterns(self, query: str) -> List[Dict[str, Any]]:
        """
        搜尋連接模式

        Args:
            query: 搜尋關鍵字 (例如 "wasp", "structural", "solar", "wasp cube")
                   支援多詞查詢，任一詞匹配即返回

        Returns:
            匹配的模式列表，每個包含 name, description, category, keywords, wiring
            按匹配詞數排序（匹配越多排越前）
        """
        patterns_file = self.config_dir / "connection_patterns.json"
        if not patterns_file.exists():
            return []

        try:
            with open(patterns_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error loading connection_patterns.json: {e}")
            return []

        # 分詞處理：支援多詞查詢
        query_tokens = [t.strip().lower() for t in query.split() if t.strip()]
        if not query_tokens:
            return []

        results = []
        seen_names = set()

        for name, pattern in data.get("patterns", {}).items():
            name_lower = name.lower()
            keywords = pattern.get("keywords", [])
            keywords_lower = [k.lower() for k in keywords]
            category = pattern.get("category", "").lower()
            description = pattern.get("description", "").lower()

            # 計算匹配詞數
            match_count = 0
            matched_tokens = []

            for token in query_tokens:
                # 檢查名稱
                if token in name_lower:
                    match_count += 2  # 名稱匹配權重更高
                    matched_tokens.append(f"name:{token}")
                    continue

                # 檢查關鍵字
                for kw in keywords_lower:
                    if token in kw:
                        match_count += 1
                        matched_tokens.append(f"keyword:{token}")
                        break
                else:
                    # 檢查類別
                    if token in category:
                        match_count += 1
                        matched_tokens.append(f"category:{token}")
                    # 檢查描述
                    elif token in description:
                        match_count += 0.5
                        matched_tokens.append(f"description:{token}")

            # 只要有匹配就加入結果
            if match_count > 0 and name not in seen_names:
                seen_names.add(name)
                results.append({
                    "name": name,
                    "description": pattern.get("description", ""),
                    "category": pattern.get("category", ""),
                    "keywords": keywords,
                    "wiring": pattern.get("wiring", []),
                    "notes": pattern.get("notes", []),
                    "match_score": match_count,
                    "matched_tokens": matched_tokens
                })

        # 按匹配分數排序
        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results

    def get_pattern(self, pattern_name: str) -> Optional[Dict[str, Any]]:
        """
        獲取特定連接模式

        Args:
            pattern_name: 模式名稱 (例如 "WASP_Stochastic")

        Returns:
            模式詳情，或 None 如果不存在
        """
        patterns_file = self.config_dir / "connection_patterns.json"
        if not patterns_file.exists():
            return None

        try:
            with open(patterns_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("patterns", {}).get(pattern_name)
        except Exception as e:
            print(f"Error loading pattern {pattern_name}: {e}")
            return None


# ============================================================================
# 便利函數 (Module-level helpers)
# ============================================================================

# 全域單例
_default_kb: Optional[ConnectionKnowledgeBase] = None


def _get_default_kb() -> ConnectionKnowledgeBase:
    """取得預設 Knowledge Base（懶載入單例）"""
    global _default_kb
    if _default_kb is None:
        _default_kb = ConnectionKnowledgeBase(storage_dir=Path("config"))
    return _default_kb


def lookup(query: str) -> Dict[str, Any]:
    """
    快速查詢（自動判斷類型）

    Examples:
        lookup("Face Normals")     # → 組件信息
        lookup("WASP_Stochastic")  # → 連接模式
        lookup("clear_canvas")     # → 命令可用性

    Returns:
        {"type": "component|pattern|command", "result": ...}
    """
    kb = _get_default_kb()

    # 1. 嘗試查詢組件
    if query in kb.signatures:
        sig = kb.signatures[query]
        return {
            "type": "component",
            "result": {
                "name": sig.name,
                "guid": sig.guid,
                "inputs": {k: v.nickname for k, v in sig.inputs.items()},
                "outputs": {k: v.nickname for k, v in sig.outputs.items()},
            }
        }

    # 2. 嘗試查詢連接模式
    for key in kb.connection_triplets:
        if query.lower() in key.lower():
            return {
                "type": "triplet",
                "result": {
                    "pattern": key,
                    "frequency": kb.connection_triplets[key]
                }
            }

    return {"type": "not_found", "query": query}


def get_guid(component_name: str) -> Optional[str]:
    """
    快速獲取組件 GUID

    Examples:
        get_guid("Rotate")  # → "19c70daf-600f-4697-ace2-567f6702144d"
    """
    kb = _get_default_kb()
    sig = kb.signatures.get(component_name)
    return sig.guid if sig else None


def is_cmd_ok(command: str) -> bool:
    """
    檢查 MCP 命令是否可用

    Examples:
        is_cmd_ok("clear_document")  # → True
        is_cmd_ok("clear_canvas")    # → False
    """
    # 從 mcp_commands.json 載入
    mcp_file = Path("config/mcp_commands.json")
    if mcp_file.exists():
        try:
            with open(mcp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                available = data.get("available", {})
                unavailable = data.get("unavailable", [])

                if command in unavailable:
                    return False
                if command in available:
                    return True
        except Exception:
            pass

    # 預設常見命令
    KNOWN_COMMANDS = {
        "add_component", "connect_components", "clear_document",
        "set_slider_properties", "set_component_value",
        "get_component_candidates", "get_errors", "get_document_info"
    }
    BLOCKED_COMMANDS = {
        "clear_canvas", "new_document", "get_all_components", "select_all"
    }

    if command in BLOCKED_COMMANDS:
        return False
    return command in KNOWN_COMMANDS


def get_wasp_param(component: str, param_role: str) -> Optional[str]:
    """
    獲取 WASP 組件的標準參數名稱

    這是一個專用函數，確保 WASP 連接使用正確的參數名稱。

    Examples:
        get_wasp_param("Connection From Direction", "geometry")  # → "GEO"
        get_wasp_param("Basic Part", "name")  # → "NAME"
        get_wasp_param("Stochastic Aggregation", "count")  # → "N"

    Args:
        component: 組件名稱
        param_role: 參數角色 (geometry, name, connection, rules, count, seed, etc.)

    Returns:
        標準參數名稱，如果找不到則返回 None
    """
    # WASP 參數對照表 - 從 trusted_guids.json 提取並標準化
    WASP_PARAMS = {
        "Connection From Direction": {
            "geometry": "GEO",
            "center": "CEN",
            "up": "UP",
            "type": "T",
            "connection": "CONN",
            "plane_out": "PLN_OUT"
        },
        "Basic Part": {
            "name": "NAME",
            "geometry": "GEO",
            "connection": "CONN",
            "collision": "COLL",
            "attribute": "ATTR",
            "part": "PART"
        },
        "Rules Generator": {
            "part": "PART",
            "self_part": "SELF_P",
            "self_conn": "SELF_C",
            "type": "TYP",
            "grammar": "GR",
            "rules": "R"
        },
        "Stochastic Aggregation": {
            "part": "PART",
            "previous": "PREV",
            "count": "N",
            "rules": "RULES",
            "seed": "SEED",
            "category": "CAT",
            "mode": "MODE",
            "global_constraints": "GC",
            "id": "ID",
            "reset": "RESET",
            "aggregation": "AGGR",
            "part_out": "PART_OUT"
        },
        "Get Part Geometry": {
            "part": "PART",
            "geometry": "GEO",
            "mesh": "M"
        }
    }

    comp_params = WASP_PARAMS.get(component)
    if comp_params:
        return comp_params.get(param_role.lower())
    return None


def get_standard_param(component_type: str, param_hint: str) -> str:
    """
    獲取 Grasshopper 組件的標準參數名稱

    確保連接使用正確的參數名稱，避免索引錯誤。

    Examples:
        get_standard_param("Center Box", "x_size")  # → "X"
        get_standard_param("Number Slider", "output")  # → "N"
        get_standard_param("Mesh Brep", "mesh")  # → "M"

    Args:
        component_type: 組件類型
        param_hint: 參數提示 (x_size, output, mesh, etc.)

    Returns:
        標準參數名稱
    """
    # 標準 GH 組件參數對照表
    STANDARD_PARAMS = {
        "Number Slider": {
            "output": "N",
            "number": "N"
        },
        "Panel": {
            "output": "out",
            "text": "out"
        },
        "Center Box": {
            "base": "B",
            "x_size": "X",
            "y_size": "Y",
            "z_size": "Z",
            "box": "B"
        },
        "Solid Union": {
            "breps": "B",
            "result": "R"
        },
        "Mesh Brep": {
            "brep": "B",
            "mesh": "M"
        },
        "Deconstruct Brep": {
            "brep": "B",
            "faces": "F",
            "edges": "E",
            "vertices": "V"
        },
        "List Item": {
            "list": "L",
            "index": "i",
            "item": "i"
        },
        "Area": {
            "geometry": "G",
            "centroid": "C",
            "area": "A"
        },
        "Line SDL": {
            "start": "S",
            "direction": "D",
            "length": "L",
            "line": "L"
        },
        "Unit Z": {
            "vector": "V",
            "factor": "F"
        },
        "Custom Preview": {
            "geometry": "G",
            "material": "M"
        }
    }

    comp_params = STANDARD_PARAMS.get(component_type)
    if comp_params:
        return comp_params.get(param_hint.lower(), param_hint)

    # 如果找不到，返回原始提示（可能已經是正確的參數名）
    return param_hint