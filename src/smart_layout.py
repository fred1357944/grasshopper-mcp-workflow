"""
Smart Layout - 智能佈局模組
============================
實現分層佈局算法，避免「蜘蛛網」問題

策略：
1. 將元件分為輸入層、處理層、輸出層
2. 每層內部分組排列
3. 層間保持合理間距
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Set, Optional, Any
from collections import defaultdict
from enum import Enum


class ComponentLayer(Enum):
    """元件層級"""
    INPUT = "input"       # 輸入層（Slider, Point, Curve 輸入等）
    PROCESS = "process"   # 處理層（數學運算、幾何操作等）
    OUTPUT = "output"     # 輸出層（最終幾何、顯示元件等）


# 元件類型到層級的映射
LAYER_MAPPING = {
    ComponentLayer.INPUT: [
        "Number Slider", "Integer Slider", "Boolean Toggle",
        "Point", "Curve", "Surface", "Brep", "Geometry",
        "Panel", "Text Panel", "Param Viewer",
        "Gene Pool", "Galapagos",
        "MD Slider", "Gradient Control",
    ],
    ComponentLayer.OUTPUT: [
        "Custom Preview", "Preview",
        "Bake Geometry", "Bake",
        "Surface", "Mesh", "Brep",  # 當它們是終點時
        "Colour Swatch", "Gradient",
        "Data Output", "Stream Gate",
    ],
    # 其他元件默認為 PROCESS 層
}


@dataclass
class LayoutConfig:
    """佈局配置"""
    # 層間距離
    layer_spacing: int = 250
    
    # 元件間距
    component_spacing_x: int = 150
    component_spacing_y: int = 80
    
    # 起始位置
    start_x: int = 50
    start_y: int = 50
    
    # 最大寬度（每層）
    max_layer_width: int = 1200
    
    # 分組間距
    group_spacing: int = 100


@dataclass
class LayoutComponent:
    """佈局用元件資訊"""
    id: str
    type: str
    nickname: str
    layer: ComponentLayer = ComponentLayer.PROCESS
    group: int = 0
    position: Tuple[float, float] = (0, 0)
    
    # 連接資訊
    inputs_from: List[str] = field(default_factory=list)
    outputs_to: List[str] = field(default_factory=list)
    
    @property
    def depth(self) -> int:
        """計算元件深度（從輸入端開始的最長路徑）"""
        # 這會在佈局時計算
        return 0


class SmartLayoutEngine:
    """
    智能佈局引擎
    
    用法：
        engine = SmartLayoutEngine()
        positioned = engine.layout(components, connections)
    """
    
    def __init__(self, config: LayoutConfig = None):
        self.config = config or LayoutConfig()
    
    def layout(
        self,
        components: List[Dict[str, Any]],
        connections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        執行佈局
        
        Args:
            components: 元件列表 [{"id": ..., "type": ..., "nickname": ...}, ...]
            connections: 連接列表 [{"from": {"component": ..., "output": ...}, "to": {...}}, ...]
            
        Returns:
            帶位置資訊的元件列表
        """
        if not components:
            return []
        
        # 1. 轉換為內部格式並建立連接圖
        layout_comps = self._prepare_components(components, connections)
        
        # 2. 分類元件到各層
        layers = self._classify_layers(layout_comps, connections)
        
        # 3. 計算深度（拓撲排序）
        depths = self._compute_depths(layout_comps)
        
        # 4. 在各層內分組
        grouped = self._group_within_layers(layers, depths)
        
        # 5. 計算位置
        self._assign_positions(grouped)
        
        # 6. 轉回原始格式
        return self._export_positions(components, layout_comps)
    
    def _prepare_components(
        self,
        components: List[Dict],
        connections: List[Dict]
    ) -> Dict[str, LayoutComponent]:
        """準備元件資料"""
        layout_comps = {}
        
        for comp in components:
            comp_id = comp.get("id", "")
            layout_comps[comp_id] = LayoutComponent(
                id=comp_id,
                type=comp.get("type", comp.get("name", "")),
                nickname=comp.get("nickname", "")
            )
        
        # 建立連接關係
        for conn in connections:
            from_info = conn.get("from", {})
            to_info = conn.get("to", {})
            
            from_id = from_info.get("component", "")
            to_id = to_info.get("component", "")
            
            if from_id in layout_comps:
                layout_comps[from_id].outputs_to.append(to_id)
            if to_id in layout_comps:
                layout_comps[to_id].inputs_from.append(from_id)
        
        return layout_comps
    
    def _classify_layers(
        self,
        layout_comps: Dict[str, LayoutComponent],
        connections: List[Dict]
    ) -> Dict[ComponentLayer, List[str]]:
        """將元件分類到各層"""
        layers = {
            ComponentLayer.INPUT: [],
            ComponentLayer.PROCESS: [],
            ComponentLayer.OUTPUT: []
        }
        
        # 找出沒有輸入連接的元件（輸入層候選）
        target_ids = set()
        source_ids = set()
        
        for conn in connections:
            source_ids.add(conn.get("from", {}).get("component", ""))
            target_ids.add(conn.get("to", {}).get("component", ""))
        
        no_inputs = source_ids - target_ids
        no_outputs = target_ids - source_ids
        
        for comp_id, comp in layout_comps.items():
            comp_type = comp.type
            
            # 檢查是否明確屬於某層
            layer_found = False
            for layer, types in LAYER_MAPPING.items():
                if any(t.lower() in comp_type.lower() for t in types):
                    # 但如果是幾何類型，需要額外判斷
                    if comp_type in ["Surface", "Mesh", "Brep", "Curve", "Point"]:
                        # 如果沒有輸入，當作輸入層
                        if comp_id in no_inputs or not comp.inputs_from:
                            layers[ComponentLayer.INPUT].append(comp_id)
                        # 如果沒有輸出，當作輸出層
                        elif comp_id in no_outputs or not comp.outputs_to:
                            layers[ComponentLayer.OUTPUT].append(comp_id)
                        else:
                            layers[ComponentLayer.PROCESS].append(comp_id)
                    else:
                        layers[layer].append(comp_id)
                    
                    comp.layer = layer
                    layer_found = True
                    break
            
            if not layer_found:
                # 根據連接情況決定
                if comp_id in no_inputs or not comp.inputs_from:
                    layers[ComponentLayer.INPUT].append(comp_id)
                    comp.layer = ComponentLayer.INPUT
                elif comp_id in no_outputs or not comp.outputs_to:
                    layers[ComponentLayer.OUTPUT].append(comp_id)
                    comp.layer = ComponentLayer.OUTPUT
                else:
                    layers[ComponentLayer.PROCESS].append(comp_id)
                    comp.layer = ComponentLayer.PROCESS
        
        return layers
    
    def _compute_depths(self, layout_comps: Dict[str, LayoutComponent]) -> Dict[str, int]:
        """計算每個元件的深度（從輸入端的距離）"""
        depths = {}
        
        def dfs(comp_id: str, visited: Set[str]) -> int:
            if comp_id in depths:
                return depths[comp_id]
            
            if comp_id in visited:
                return 0  # 避免循環
            
            visited.add(comp_id)
            comp = layout_comps.get(comp_id)
            
            if not comp or not comp.inputs_from:
                depths[comp_id] = 0
                return 0
            
            max_input_depth = max(
                dfs(input_id, visited)
                for input_id in comp.inputs_from
                if input_id in layout_comps
            )
            
            depths[comp_id] = max_input_depth + 1
            return depths[comp_id]
        
        for comp_id in layout_comps:
            dfs(comp_id, set())
        
        return depths
    
    def _group_within_layers(
        self,
        layers: Dict[ComponentLayer, List[str]],
        depths: Dict[str, int]
    ) -> Dict[ComponentLayer, List[List[str]]]:
        """在各層內根據深度分組"""
        grouped = {}
        
        for layer, comp_ids in layers.items():
            if not comp_ids:
                grouped[layer] = []
                continue
            
            # 按深度分組
            depth_groups = defaultdict(list)
            for comp_id in comp_ids:
                depth = depths.get(comp_id, 0)
                depth_groups[depth].append(comp_id)
            
            # 按深度排序
            sorted_groups = [
                depth_groups[d]
                for d in sorted(depth_groups.keys())
            ]
            
            grouped[layer] = sorted_groups
        
        return grouped
    
    def _assign_positions(
        self,
        grouped: Dict[ComponentLayer, List[List[str]]]
    ):
        """分配位置"""
        current_x = self.config.start_x
        
        # 按層順序處理
        layer_order = [ComponentLayer.INPUT, ComponentLayer.PROCESS, ComponentLayer.OUTPUT]
        
        for layer in layer_order:
            groups = grouped.get(layer, [])
            if not groups:
                continue
            
            # 計算此層的總寬度
            max_group_height = 0
            group_x = current_x
            
            for group in groups:
                y = self.config.start_y
                
                for comp_id in group:
                    # 這裡需要訪問 layout_comps，所以這個方法需要重構
                    pass
                
                max_group_height = max(max_group_height, y)
                group_x += self.config.component_spacing_x
            
            current_x = group_x + self.config.layer_spacing
    
    def _export_positions(
        self,
        original: List[Dict],
        layout_comps: Dict[str, LayoutComponent]
    ) -> List[Dict]:
        """匯出位置到原始格式"""
        result = []
        
        for comp in original:
            comp_copy = dict(comp)
            comp_id = comp.get("id", "")
            
            if comp_id in layout_comps:
                lc = layout_comps[comp_id]
                comp_copy["position"] = list(lc.position)
            
            result.append(comp_copy)
        
        return result


# ============================================================
# 簡化版佈局（立即可用）
# ============================================================

def simple_layout(
    components: List[Dict[str, Any]],
    connections: List[Dict[str, Any]],
    config: LayoutConfig = None
) -> List[Dict[str, Any]]:
    """
    簡化版佈局函數
    
    直接使用，無需實例化 SmartLayoutEngine
    """
    config = config or LayoutConfig()
    
    if not components:
        return []
    
    # 建立連接圖
    inputs_map = defaultdict(list)  # comp_id -> [輸入來源]
    outputs_map = defaultdict(list)  # comp_id -> [輸出目標]
    
    for conn in connections:
        from_id = conn.get("from", {}).get("component", "")
        to_id = conn.get("to", {}).get("component", "")
        
        if from_id and to_id:
            outputs_map[from_id].append(to_id)
            inputs_map[to_id].append(from_id)
    
    # 計算深度
    depths = {}
    
    def get_depth(comp_id: str, visited: Set[str] = None) -> int:
        if visited is None:
            visited = set()
        
        if comp_id in depths:
            return depths[comp_id]
        
        if comp_id in visited:
            return 0
        
        visited.add(comp_id)
        
        inputs = inputs_map.get(comp_id, [])
        if not inputs:
            depths[comp_id] = 0
        else:
            depths[comp_id] = 1 + max(get_depth(i, visited) for i in inputs)
        
        return depths[comp_id]
    
    # 計算所有元件的深度
    comp_ids = [c.get("id", f"comp_{i}") for i, c in enumerate(components)]
    for comp_id in comp_ids:
        get_depth(comp_id)
    
    # 按深度分組
    depth_groups = defaultdict(list)
    for i, comp in enumerate(components):
        comp_id = comp.get("id", f"comp_{i}")
        depth = depths.get(comp_id, 0)
        depth_groups[depth].append(i)
    
    # 分配位置
    result = []
    
    for i, comp in enumerate(components):
        comp_copy = dict(comp)
        comp_id = comp.get("id", f"comp_{i}")
        depth = depths.get(comp_id, 0)
        
        # 找出在同深度中的索引
        same_depth = depth_groups[depth]
        index_in_depth = same_depth.index(i)
        
        # 計算位置
        x = config.start_x + depth * config.layer_spacing
        y = config.start_y + index_in_depth * config.component_spacing_y
        
        comp_copy["position"] = [x, y]
        result.append(comp_copy)
    
    return result


# ============================================================
# 測試
# ============================================================

if __name__ == "__main__":
    # 測試案例：螺旋曲線
    test_components = [
        {"id": "slider1", "type": "Number Slider", "nickname": "Turns"},
        {"id": "slider2", "type": "Number Slider", "nickname": "Radius"},
        {"id": "series", "type": "Series", "nickname": "Series"},
        {"id": "sin", "type": "Sine", "nickname": "Sin"},
        {"id": "cos", "type": "Cosine", "nickname": "Cos"},
        {"id": "pt", "type": "Construct Point", "nickname": "Pt"},
        {"id": "curve", "type": "Interpolate", "nickname": "Curve"},
    ]
    
    test_connections = [
        {"from": {"component": "slider1"}, "to": {"component": "series"}},
        {"from": {"component": "series"}, "to": {"component": "sin"}},
        {"from": {"component": "series"}, "to": {"component": "cos"}},
        {"from": {"component": "slider2"}, "to": {"component": "sin"}},
        {"from": {"component": "slider2"}, "to": {"component": "cos"}},
        {"from": {"component": "sin"}, "to": {"component": "pt"}},
        {"from": {"component": "cos"}, "to": {"component": "pt"}},
        {"from": {"component": "pt"}, "to": {"component": "curve"}},
    ]
    
    result = simple_layout(test_components, test_connections)
    
    print("佈局結果：")
    for comp in result:
        print(f"  {comp['nickname']}: {comp['position']}")
