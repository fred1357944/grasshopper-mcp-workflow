#!/usr/bin/env python3
"""
Grasshopper Canvas 自動佈局模組

基於拓撲排序的層級佈局算法 (Sugiyama-style)
- 將組件按數據流方向從左到右排列
- 同一層的組件垂直對齊
- 自動計算合理間距
"""

from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class ComponentNode:
    """表示 Canvas 上的一個組件"""
    id: str
    name: str
    type: str
    width: float = 120.0   # 預設組件寬度
    height: float = 40.0   # 預設組件高度
    layer: int = -1        # 層級（-1 表示未計算）
    position_in_layer: int = 0
    x: float = 0.0
    y: float = 0.0


@dataclass
class Connection:
    """表示組件之間的連線"""
    from_id: str
    from_param: str
    to_id: str
    to_param: str


@dataclass
class LayoutConfig:
    """佈局配置"""
    horizontal_spacing: float = 180.0  # 層與層之間的水平間距
    vertical_spacing: float = 60.0     # 同層組件之間的垂直間距
    start_x: float = 50.0              # Canvas 起始 X
    start_y: float = 50.0              # Canvas 起始 Y

    # 組件尺寸估算（根據類型）
    component_sizes: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        # (width, height)
        'Number Slider': (200, 20),
        'GH_NumberSlider': (200, 20),
        'Panel': (100, 60),
        'GH_Panel': (100, 60),
        'default': (120, 40),
    })


class CanvasLayoutCalculator:
    """Canvas 佈局計算器"""

    def __init__(self, config: Optional[LayoutConfig] = None):
        self.config = config or LayoutConfig()
        self.nodes: Dict[str, ComponentNode] = {}
        self.connections: List[Connection] = []
        self.adjacency: Dict[str, List[str]] = defaultdict(list)  # 出邊
        self.reverse_adjacency: Dict[str, List[str]] = defaultdict(list)  # 入邊

    def add_component(self, id: str, name: str, type: str,
                      width: Optional[float] = None,
                      height: Optional[float] = None):
        """添加組件"""
        # 估算尺寸
        if width is None or height is None:
            est_w, est_h = self.config.component_sizes.get(
                type, self.config.component_sizes['default']
            )
            width = width or est_w
            height = height or est_h

        self.nodes[id] = ComponentNode(
            id=id, name=name, type=type,
            width=width, height=height
        )

    def add_connection(self, from_id: str, from_param: str,
                       to_id: str, to_param: str):
        """添加連線"""
        self.connections.append(Connection(
            from_id=from_id, from_param=from_param,
            to_id=to_id, to_param=to_param
        ))
        self.adjacency[from_id].append(to_id)
        self.reverse_adjacency[to_id].append(from_id)

    def _find_sources(self) -> List[str]:
        """找出所有源節點（沒有入邊的節點）"""
        sources = []
        for node_id in self.nodes:
            if not self.reverse_adjacency[node_id]:
                sources.append(node_id)
        return sources

    def _compute_layers_bfs(self) -> Dict[int, List[str]]:
        """使用 BFS 計算層級"""
        layers: Dict[int, List[str]] = defaultdict(list)

        # 初始化：源節點為第 0 層
        sources = self._find_sources()

        # 如果沒有源節點，所有節點都為第 0 層
        if not sources:
            layers[0] = list(self.nodes.keys())
            for node_id in self.nodes:
                self.nodes[node_id].layer = 0
            return layers

        # BFS 分配層級
        visited: Set[str] = set()
        queue = [(src, 0) for src in sources]
        max_layer: Dict[str, int] = {}  # 記錄每個節點的最大層級

        for src in sources:
            max_layer[src] = 0

        while queue:
            node_id, layer = queue.pop(0)

            # 更新節點的最大層級
            if node_id in max_layer:
                max_layer[node_id] = max(max_layer[node_id], layer)
            else:
                max_layer[node_id] = layer

            # 處理所有出邊
            for next_id in self.adjacency[node_id]:
                new_layer = max_layer[node_id] + 1
                if next_id not in max_layer or new_layer > max_layer[next_id]:
                    max_layer[next_id] = new_layer
                    queue.append((next_id, new_layer))

        # 處理未訪問的孤立節點
        for node_id in self.nodes:
            if node_id not in max_layer:
                max_layer[node_id] = 0

        # 將節點分配到層級
        for node_id, layer in max_layer.items():
            self.nodes[node_id].layer = layer
            layers[layer].append(node_id)

        return layers

    def _order_within_layers(self, layers: Dict[int, List[str]]):
        """在每層內排序節點以減少交叉"""
        # 簡單啟發式：按入邊來源的平均位置排序
        for layer_idx in sorted(layers.keys()):
            if layer_idx == 0:
                # 第一層按名稱排序
                layers[layer_idx].sort(key=lambda nid: self.nodes[nid].name)
            else:
                # 後續層按前一層連線位置的平均值排序
                def get_avg_source_pos(node_id):
                    sources = self.reverse_adjacency[node_id]
                    if not sources:
                        return 0
                    positions = [self.nodes[s].position_in_layer
                                 for s in sources if s in self.nodes]
                    return sum(positions) / len(positions) if positions else 0

                layers[layer_idx].sort(key=get_avg_source_pos)

            # 更新位置索引
            for pos, node_id in enumerate(layers[layer_idx]):
                self.nodes[node_id].position_in_layer = pos

    def _assign_coordinates(self, layers: Dict[int, List[str]]):
        """分配 X, Y 座標"""
        for layer_idx, node_ids in layers.items():
            # X 座標根據層級
            x = self.config.start_x + layer_idx * self.config.horizontal_spacing

            # 計算這層的總高度
            total_height = sum(self.nodes[nid].height for nid in node_ids)
            total_height += self.config.vertical_spacing * (len(node_ids) - 1)

            # 從中心開始分配 Y
            current_y = self.config.start_y

            for node_id in node_ids:
                node = self.nodes[node_id]
                node.x = x
                node.y = current_y
                current_y += node.height + self.config.vertical_spacing

    def calculate_layout(self) -> Dict[str, Tuple[float, float]]:
        """
        計算所有組件的佈局位置

        Returns:
            Dict[str, Tuple[float, float]]: 組件 ID -> (x, y) 座標
        """
        if not self.nodes:
            return {}

        # 1. 計算層級
        layers = self._compute_layers_bfs()

        # 2. 層內排序
        self._order_within_layers(layers)

        # 3. 分配座標
        self._assign_coordinates(layers)

        # 返回結果
        return {
            node_id: (node.x, node.y)
            for node_id, node in self.nodes.items()
        }

    def get_layout_summary(self) -> str:
        """獲取佈局摘要"""
        lines = ["=== Canvas Layout Summary ==="]

        # 按層級分組
        by_layer: Dict[int, List[ComponentNode]] = defaultdict(list)
        for node in self.nodes.values():
            by_layer[node.layer].append(node)

        for layer_idx in sorted(by_layer.keys()):
            lines.append(f"\nLayer {layer_idx}:")
            for node in by_layer[layer_idx]:
                lines.append(f"  [{node.name}] at ({node.x:.0f}, {node.y:.0f})")

        return "\n".join(lines)


def create_layout_for_table() -> CanvasLayoutCalculator:
    """
    示例：為桌子設計創建佈局
    """
    calc = CanvasLayoutCalculator()

    # 添加組件（示意）
    components = [
        ("slider_width", "TABLE_WIDTH", "Number Slider"),
        ("slider_height", "TABLE_HEIGHT", "Number Slider"),
        ("slider_leg", "LEG_HEIGHT", "Number Slider"),
        ("pt_origin", "ORIGIN", "Construct Point"),
        ("rect_top", "TABLE_TOP", "Rectangle"),
        ("extrude_top", "EXTRUDE_TOP", "Extrude"),
        ("box_leg", "LEG", "Box"),
        ("union", "TABLE", "Solid Union"),
    ]

    for cid, name, ctype in components:
        calc.add_component(cid, name, ctype)

    # 添加連線
    connections = [
        ("slider_width", "N", "rect_top", "X"),
        ("slider_height", "N", "rect_top", "Y"),
        ("pt_origin", "Pt", "rect_top", "P"),
        ("rect_top", "R", "extrude_top", "B"),
        ("slider_leg", "N", "box_leg", "Z"),
        ("extrude_top", "E", "union", "B"),
        ("box_leg", "B", "union", "B"),
    ]

    for from_id, from_p, to_id, to_p in connections:
        calc.add_connection(from_id, from_p, to_id, to_p)

    return calc


if __name__ == "__main__":
    # 測試
    calc = create_layout_for_table()
    positions = calc.calculate_layout()
    print(calc.get_layout_summary())

    print("\n=== Positions ===")
    for comp_id, (x, y) in positions.items():
        print(f"{comp_id}: ({x}, {y})")
