"""
Grasshopper 資料模型定義
========================
定義 GHX 解析與模式庫所需的所有資料結構
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import json


class DataType(Enum):
    """Grasshopper 資料類型"""
    UNKNOWN = "unknown"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    TEXT = "text"
    POINT = "point"
    VECTOR = "vector"
    PLANE = "plane"
    CURVE = "curve"
    SURFACE = "surface"
    BREP = "brep"
    MESH = "mesh"
    GEOMETRY = "geometry"
    COLOR = "color"
    DOMAIN = "domain"
    INTERVAL = "interval"
    TRANSFORM = "transform"
    DATA_TREE = "datatree"


class ComponentCategory(Enum):
    """元件分類"""
    PARAMS = "Params"           # 參數元件 (Slider, Panel, etc.)
    MATHS = "Maths"             # 數學運算
    SETS = "Sets"               # 集合操作
    VECTOR = "Vector"           # 向量操作
    CURVE = "Curve"             # 曲線操作
    SURFACE = "Surface"         # 曲面操作
    MESH = "Mesh"               # 網格操作
    INTERSECT = "Intersect"     # 交集操作
    TRANSFORM = "Transform"     # 變換操作
    DISPLAY = "Display"         # 顯示元件
    UNKNOWN = "Unknown"


@dataclass
class Parameter:
    """元件參數（輸入或輸出）"""
    name: str
    nickname: str
    index: int
    data_type: DataType = DataType.UNKNOWN
    is_principal: bool = True  # 是否為主要參數
    default_value: Optional[Any] = None
    
    # 連接資訊 (在解析後填充)
    connected_sources: List[str] = field(default_factory=list)  # 來源 component_id:output_index
    connected_targets: List[str] = field(default_factory=list)  # 目標 component_id:input_index

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "nickname": self.nickname,
            "index": self.index,
            "data_type": self.data_type.value,
            "is_principal": self.is_principal,
            "default_value": self.default_value,
            "connected_sources": self.connected_sources,
            "connected_targets": self.connected_targets
        }


@dataclass
class GHComponent:
    """Grasshopper 元件"""
    instance_guid: str          # 此實例的唯一 ID
    component_guid: str         # 元件類型的 GUID (用於識別元件種類)
    name: str                   # 元件全名
    nickname: str               # 元件暱稱
    category: ComponentCategory = ComponentCategory.UNKNOWN
    subcategory: str = ""
    
    # 位置資訊
    position: Tuple[float, float] = (0.0, 0.0)
    pivot: Tuple[float, float] = (0.0, 0.0)
    
    # 參數
    inputs: List[Parameter] = field(default_factory=list)
    outputs: List[Parameter] = field(default_factory=list)
    
    # 元件特定資料
    properties: Dict[str, Any] = field(default_factory=dict)
    
    # 元資料
    is_cluster: bool = False
    is_disabled: bool = False
    
    def get_input_by_name(self, name: str) -> Optional[Parameter]:
        """根據名稱取得輸入參數"""
        for inp in self.inputs:
            if inp.name == name or inp.nickname == name:
                return inp
        return None
    
    def get_output_by_name(self, name: str) -> Optional[Parameter]:
        """根據名稱取得輸出參數"""
        for out in self.outputs:
            if out.name == name or out.nickname == name:
                return out
        return None

    def to_dict(self) -> dict:
        return {
            "instance_guid": self.instance_guid,
            "component_guid": self.component_guid,
            "name": self.name,
            "nickname": self.nickname,
            "category": self.category.value,
            "subcategory": self.subcategory,
            "position": self.position,
            "pivot": self.pivot,
            "inputs": [inp.to_dict() for inp in self.inputs],
            "outputs": [out.to_dict() for out in self.outputs],
            "properties": self.properties,
            "is_cluster": self.is_cluster,
            "is_disabled": self.is_disabled
        }


@dataclass
class GHConnection:
    """元件之間的連接"""
    source_component_id: str    # 來源元件 GUID
    source_output_index: int    # 來源輸出參數索引
    source_output_name: str     # 來源輸出參數名稱
    
    target_component_id: str    # 目標元件 GUID
    target_input_index: int     # 目標輸入參數索引
    target_input_name: str      # 目標輸入參數名稱
    
    def to_dict(self) -> dict:
        return {
            "source_component_id": self.source_component_id,
            "source_output_index": self.source_output_index,
            "source_output_name": self.source_output_name,
            "target_component_id": self.target_component_id,
            "target_input_index": self.target_input_index,
            "target_input_name": self.target_input_name
        }
    
    @property
    def source_key(self) -> str:
        """來源的唯一識別"""
        return f"{self.source_component_id}:{self.source_output_index}"
    
    @property
    def target_key(self) -> str:
        """目標的唯一識別"""
        return f"{self.target_component_id}:{self.target_input_index}"


@dataclass
class GHGroup:
    """元件群組"""
    guid: str
    name: str
    nickname: str
    color: Optional[Tuple[int, int, int, int]] = None  # ARGB
    component_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "guid": self.guid,
            "name": self.name,
            "nickname": self.nickname,
            "color": self.color,
            "component_ids": self.component_ids
        }


@dataclass
class GHDocument:
    """完整的 Grasshopper 文件"""
    filepath: str = ""
    
    # 文件元資料
    grasshopper_version: str = ""
    plugin_version: str = ""
    document_id: str = ""
    
    # 核心內容
    components: Dict[str, GHComponent] = field(default_factory=dict)  # key: instance_guid
    connections: List[GHConnection] = field(default_factory=list)
    groups: List[GHGroup] = field(default_factory=list)
    
    # 統計資訊
    @property
    def component_count(self) -> int:
        return len(self.components)
    
    @property
    def connection_count(self) -> int:
        return len(self.connections)
    
    def get_component_by_guid(self, guid: str) -> Optional[GHComponent]:
        """根據 GUID 取得元件"""
        return self.components.get(guid)
    
    def get_components_by_name(self, name: str) -> List[GHComponent]:
        """根據名稱取得所有匹配的元件"""
        return [c for c in self.components.values() 
                if c.name == name or c.nickname == name]
    
    def get_connected_inputs(self, component_id: str) -> List[GHConnection]:
        """取得連接到指定元件輸入的所有連接"""
        return [c for c in self.connections if c.target_component_id == component_id]
    
    def get_connected_outputs(self, component_id: str) -> List[GHConnection]:
        """取得從指定元件輸出的所有連接"""
        return [c for c in self.connections if c.source_component_id == component_id]
    
    def get_upstream_components(self, component_id: str) -> List[str]:
        """取得上游元件（提供輸入的元件）"""
        connections = self.get_connected_inputs(component_id)
        return list(set(c.source_component_id for c in connections))
    
    def get_downstream_components(self, component_id: str) -> List[str]:
        """取得下游元件（接收輸出的元件）"""
        connections = self.get_connected_outputs(component_id)
        return list(set(c.target_component_id for c in connections))
    
    def get_source_components(self) -> List[GHComponent]:
        """取得沒有輸入連接的元件（通常是 Slider、Panel 等）"""
        components_with_inputs = set(c.target_component_id for c in self.connections)
        return [c for guid, c in self.components.items() 
                if guid not in components_with_inputs]
    
    def get_sink_components(self) -> List[GHComponent]:
        """取得沒有輸出連接的元件（通常是顯示元件）"""
        components_with_outputs = set(c.source_component_id for c in self.connections)
        return [c for guid, c in self.components.items() 
                if guid not in components_with_outputs]
    
    def to_dict(self) -> dict:
        return {
            "filepath": self.filepath,
            "grasshopper_version": self.grasshopper_version,
            "plugin_version": self.plugin_version,
            "document_id": self.document_id,
            "component_count": self.component_count,
            "connection_count": self.connection_count,
            "components": {k: v.to_dict() for k, v in self.components.items()},
            "connections": [c.to_dict() for c in self.connections],
            "groups": [g.to_dict() for g in self.groups]
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def summary(self) -> str:
        """產生文件摘要"""
        lines = [
            f"=== GH Document Summary ===",
            f"File: {self.filepath}",
            f"GH Version: {self.grasshopper_version}",
            f"Components: {self.component_count}",
            f"Connections: {self.connection_count}",
            f"Groups: {len(self.groups)}",
            "",
            "--- Component Types ---"
        ]
        
        # 統計元件類型
        type_counts: Dict[str, int] = {}
        for comp in self.components.values():
            type_counts[comp.name] = type_counts.get(comp.name, 0) + 1
        
        for name, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {name}: {count}")
        
        return "\n".join(lines)


# ============================================================
# 模式庫相關資料結構
# ============================================================

@dataclass
class ComponentVocabulary:
    """Level 1: 元件詞彙表條目"""
    component_guid: str
    name: str
    nickname: str
    category: ComponentCategory
    subcategory: str
    
    input_specs: List[Dict[str, Any]] = field(default_factory=list)
    output_specs: List[Dict[str, Any]] = field(default_factory=list)
    
    pattern_tags: List[str] = field(default_factory=list)
    elegance_score: float = 3.0  # 1-5 scale
    
    common_predecessors: List[str] = field(default_factory=list)
    common_successors: List[str] = field(default_factory=list)
    
    notes: str = ""


@dataclass
class ConnectionPattern:
    """Level 2: 連接模式"""
    pattern_id: str
    description: str
    elegance_level: int  # 1-5
    
    # 模式結構 (簡化版，用列表表示流程)
    component_sequence: List[str] = field(default_factory=list)
    connection_rules: List[Dict[str, str]] = field(default_factory=list)
    
    # 變體
    alternatives: List['ConnectionPattern'] = field(default_factory=list)
    
    # 識別關鍵字
    keywords: List[str] = field(default_factory=list)
    
    # 優化建議
    optimization_tips: List[str] = field(default_factory=list)


@dataclass
class IntentPattern:
    """Level 3: 設計意圖模式"""
    intent_id: str
    intent_name: str
    description: str
    
    # 語義關鍵字 (用於 NLU 匹配)
    keywords: List[str] = field(default_factory=list)
    semantic_variants: List[str] = field(default_factory=list)  # 自然語言變體
    
    # 標準實作方式
    canonical_patterns: List[str] = field(default_factory=list)  # 連接模式 ID
    
    # 參數化需求
    typical_parameters: List[Dict[str, Any]] = field(default_factory=list)
    
    # 反模式
    anti_patterns: List[Dict[str, str]] = field(default_factory=list)


# ============================================================
# LangGraph 狀態相關
# ============================================================

@dataclass
class EleganceScore:
    """優雅度評分細節"""
    total: float = 0.0
    slider_count_score: float = 0.0
    data_tree_score: float = 0.0
    component_ratio_score: float = 0.0
    pattern_match_score: float = 0.0
    geometric_coupling_score: float = 0.0
    
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "breakdown": {
                "slider_count": self.slider_count_score,
                "data_tree": self.data_tree_score,
                "component_ratio": self.component_ratio_score,
                "pattern_match": self.pattern_match_score,
                "geometric_coupling": self.geometric_coupling_score
            },
            "issues": self.issues,
            "suggestions": self.suggestions
        }
