"""
MCP Adapter - 整合 LangGraph 與 GH_MCP Client
=============================================
將 LangGraph 生成的 gh_code 轉換為 client_optimized.py 的調用

這是整合層，連接：
- 上層：LangGraph 生成的 gh_code (JSON 格式)
- 下層：client_optimized.py 的 add_component/smart_connect
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

# 添加 grasshopper_mcp 到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from grasshopper_mcp.client_optimized import (
    GH_MCP_ClientOptimized,
    SliderConfig,
    PARAM_ALIASES
)
from src.smart_layout import SmartLayoutEngine, LayoutConfig


# ============================================================
# 組件參數索引映射
# ============================================================
# 專家格式用數字索引 (0, 1, 2...)
# GH_MCP 需要參數名 ("N", "S", "y"...)

# 輸出參數映射: 組件類型 -> [第0個輸出, 第1個輸出, ...]
OUTPUT_INDEX_MAP = {
    "Number Slider": ["N"],
    "Series": ["S"],
    "Range": ["R"],
    "Sine": ["y"],
    "Cosine": ["y"],
    "Tangent": ["y"],
    "Radians": ["Radians"],
    "Degrees": ["Degrees"],
    "Addition": ["Result"],
    "Subtraction": ["Result"],
    "Multiplication": ["Result"],
    "Division": ["Result"],
    "Power": ["Result"],
    "Modulus": ["Result"],
    "Absolute": ["Result"],
    "Construct Point": ["Pt"],
    "Deconstruct Point": ["X", "Y", "Z"],
    "Vector XYZ": ["V"],
    "Unit X": ["V"],
    "Unit Y": ["V"],
    "Unit Z": ["V"],
    "Circle": ["C"],
    "Line": ["L"],
    "Polyline": ["Pl"],
    "Interpolate": ["C"],
    "Move": ["G", "T"],
    "Rotate": ["G", "X"],
    "Scale": ["G"],
    "Extrude": ["E"],
    "Loft": ["L"],
    "Pipe": ["P"],
    "Center Box": ["B"],
    "Box 2Pt": ["B"],
    "Cylinder": ["C"],
    "Sphere": ["S"],
}

# 輸入參數映射: 組件類型 -> [第0個輸入, 第1個輸入, ...]
INPUT_INDEX_MAP = {
    "Series": ["S", "N", "C"],  # Start, Step, Count
    "Range": ["D", "N"],  # Domain, Steps
    "Sine": ["x"],
    "Cosine": ["x"],
    "Tangent": ["x"],
    "Radians": ["D"],
    "Degrees": ["R"],
    "Addition": ["A", "B"],
    "Subtraction": ["A", "B"],
    "Multiplication": ["A", "B"],
    "Division": ["A", "B"],
    "Power": ["B", "E"],
    "Construct Point": ["X", "Y", "Z"],
    "Deconstruct Point": ["P"],
    "Vector XYZ": ["X", "Y", "Z"],
    "Circle": ["P", "R"],  # Plane, Radius
    "Line": ["A", "B"],
    "Polyline": ["V"],  # Vertices
    "Interpolate": ["V", "D", "P"],  # Vertices, Degree, Periodic
    "Move": ["G", "T"],  # Geometry, Translation
    "Rotate": ["G", "A", "P"],  # Geometry, Angle, Plane
    "Scale": ["G", "C", "F"],  # Geometry, Center, Factor
    "Extrude": ["B", "D"],  # Base, Direction
    "Loft": ["C", "O"],  # Curves, Options
    "Pipe": ["C", "R"],  # Curve, Radius
    "Center Box": ["B", "X", "Y", "Z"],
    "Cylinder": ["B", "R", "L"],  # Base, Radius, Length
    "Sphere": ["B", "R"],  # Base, Radius
}


@dataclass
class DeploymentResult:
    """部署結果"""
    success: bool
    components_created: int
    connections_made: int
    failed_connections: List[Dict]
    error: Optional[str] = None


class MCPAdapter:
    """
    MCP 適配器 - 將 LangGraph 輸出轉為 GH_MCP 調用

    用法：
        adapter = MCPAdapter()
        result = adapter.deploy(gh_code)
    """

    def __init__(
        self,
        host: str = '127.0.0.1',
        port: int = 8080,
        debug: bool = True,
        use_smart_layout: bool = True
    ):
        self.client = GH_MCP_ClientOptimized(host=host, port=port, debug=debug)
        self.use_smart_layout = use_smart_layout
        self.layout_engine = SmartLayoutEngine() if use_smart_layout else None
        # ID → nickname 映射 (專家格式用 id，我們用 nickname)
        self.id_to_nickname: Dict[str, str] = {}

    def deploy(
        self,
        gh_code: Dict[str, Any],
        clear_first: bool = True
    ) -> DeploymentResult:
        """
        部署 GH Code 到 Grasshopper

        Args:
            gh_code: LangGraph 生成的程式碼結構
                {
                    "components": [
                        {"type": "Number Slider", "nickname": "R", "value": 10, ...},
                        {"type": "Circle", "nickname": "C1", ...},
                    ],
                    "connections": [
                        {"from": "R", "from_param": "N", "to": "C1", "to_param": "R"},
                    ]
                }
            clear_first: 是否先清空畫布

        Returns:
            DeploymentResult
        """
        try:
            # 測試連接
            if not self.client.test_connection():
                return DeploymentResult(
                    success=False,
                    components_created=0,
                    connections_made=0,
                    failed_connections=[],
                    error="無法連接到 GH_MCP (port 8080)"
                )

            # 清空畫布
            if clear_first:
                self.client.clear_canvas()

            # 解析組件和連接
            components = gh_code.get("components", [])
            connections = gh_code.get("connections", [])

            # 智能佈局
            if self.use_smart_layout and self.layout_engine:
                components = self._apply_layout(components, connections)

            # 創建組件
            created = self._create_components(components)

            # 建立連接 (使用 smart_connect)
            conn_success, conn_fail, failed_list = self._create_connections(connections)

            return DeploymentResult(
                success=True,
                components_created=created,
                connections_made=conn_success,
                failed_connections=failed_list,
                error=None
            )

        except Exception as e:
            return DeploymentResult(
                success=False,
                components_created=0,
                connections_made=0,
                failed_connections=[],
                error=str(e)
            )

    def _apply_layout(
        self,
        components: List[Dict],
        connections: List[Dict]
    ) -> List[Dict]:
        """應用智能佈局"""
        # 轉換為 SmartLayoutEngine 格式
        layout_components = []
        for comp in components:
            layout_components.append({
                "id": comp.get("nickname", comp.get("id")),
                "type": comp.get("type"),
                "nickname": comp.get("nickname"),
            })

        layout_connections = []
        for conn in connections:
            layout_connections.append({
                "from": conn.get("from"),
                "to": conn.get("to"),
            })

        # 計算佈局
        positioned = self.layout_engine.layout(layout_components, layout_connections)

        # 更新組件位置
        position_map = {p["id"]: p["position"] for p in positioned}
        for comp in components:
            nick = comp.get("nickname", comp.get("id"))
            if nick in position_map:
                comp["x"], comp["y"] = position_map[nick]

        return components

    def _create_components(self, components: List[Dict]) -> int:
        """創建所有組件"""
        created = 0

        for comp in components:
            comp_type = comp.get("type", "")
            nickname = comp.get("nickname", comp.get("id", ""))

            # 解析位置 - 支援兩種格式
            # 格式 1 (專家): position: [x, y]
            # 格式 2 (本專案): x, y 或 col, row
            position = comp.get("position", [0, 0])
            if isinstance(position, (list, tuple)) and len(position) >= 2:
                x, y = position[0], position[1]
            else:
                x = comp.get("x", 0)
                y = comp.get("y", 0)

            # 計算 col, row
            col = int(x / self.client.COL_WIDTH) if x else comp.get("col", 0)
            row = int(y / self.client.ROW_HEIGHT) if y else comp.get("row", 0)

            # 解析 properties - 支援兩種格式
            # 格式 1 (專家): properties: {min, max, value}
            # 格式 2 (本專案): min, max, value 在頂層
            props = comp.get("properties", {})
            value = props.get("value", comp.get("value", 0))
            min_val = props.get("min", comp.get("min", 0))
            max_val = props.get("max", comp.get("max", 100))

            if comp_type == "Number Slider":
                # Slider 特殊處理
                result = self.client.add_slider(
                    nickname=nickname,
                    col=col,
                    row=row,
                    value=value,
                    min_val=min_val,
                    max_val=max_val
                )
            else:
                # 一般組件
                result = self.client.add_component(
                    comp_type=comp_type,
                    nickname=nickname,
                    col=col,
                    row=row,
                    guid=comp.get("guid")  # 支援指定 GUID
                )

            if result:
                created += 1
                # 記錄 ID → nickname 映射
                comp_id = comp.get("id", nickname)
                self.id_to_nickname[comp_id] = nickname

        return created

    def _create_connections(
        self,
        connections: List[Dict]
    ) -> Tuple[int, int, List[Dict]]:
        """建立所有連接 (使用 smart_connect)"""
        connection_tuples = []

        for conn in connections:
            # 支援兩種格式
            # 格式 1 (專家): {"from": {"component": "X", "output": 0}, "to": {"component": "Y", "input": "Z"}}
            # 格式 2 (本專案): {"from": "X", "from_param": "N", "to": "Y", "to_param": "Z"}

            from_data = conn.get("from")
            to_data = conn.get("to")

            if isinstance(from_data, dict):
                # 專家格式
                from_id = from_data.get("component", "")
                from_param_raw = from_data.get("output", 0)
            else:
                # 本專案格式
                from_id = from_data or ""
                from_param_raw = conn.get("from_param", "N")

            if isinstance(to_data, dict):
                # 專家格式
                to_id = to_data.get("component", "")
                to_param_raw = to_data.get("input", 0)
            else:
                # 本專案格式
                to_id = to_data or ""
                to_param_raw = conn.get("to_param", "R")

            # 解析 nickname
            from_nick = self._resolve_nickname(from_id)
            to_nick = self._resolve_nickname(to_id)

            # 解析參數名 (數字索引 → 實際參數名)
            from_param = self._resolve_param(from_nick, from_param_raw, is_output=True)
            to_param = self._resolve_param(to_nick, to_param_raw, is_output=False)

            if from_nick and to_nick:
                connection_tuples.append((from_nick, from_param, to_nick, to_param))

        return self.client.smart_connect_batch(connection_tuples)

    def _resolve_param(self, nickname: str, param_raw: Any, is_output: bool) -> str:
        """
        解析參數名

        Args:
            nickname: 組件 nickname
            param_raw: 原始參數 (可能是數字索引或字串參數名)
            is_output: True=輸出參數, False=輸入參數

        Returns:
            實際參數名
        """
        # 如果已經是字串，直接返回
        if isinstance(param_raw, str) and param_raw:
            return param_raw

        # 數字索引需要查表
        if isinstance(param_raw, int):
            # 先找到組件類型
            comp_info = self.client.components.get(nickname)
            if comp_info:
                comp_type = comp_info.comp_type
                param_map = OUTPUT_INDEX_MAP if is_output else INPUT_INDEX_MAP
                params = param_map.get(comp_type, [])
                if 0 <= param_raw < len(params):
                    return params[param_raw]

        # 默認值
        return "N" if is_output else "x"

    def _resolve_nickname(self, id_or_nick: str) -> str:
        """
        解析 ID 或 nickname 到實際的組件 nickname

        專家格式用 id (如 "slider_turns", "mul_x")，但組件創建時用 nickname (如 "Turns", "MulX")
        """
        # 優先查找 ID → nickname 映射
        if id_or_nick in self.id_to_nickname:
            return self.id_to_nickname[id_or_nick]

        # 如果已經是已知的 nickname，直接返回
        if id_or_nick in self.client.components:
            return id_or_nick

        # 嘗試從 id 推導 nickname
        id_lower = id_or_nick.lower().replace("_", "")

        for nick in self.client.components:
            nick_lower = nick.lower()
            # 精確匹配 (忽略大小寫和底線)
            if nick_lower == id_lower:
                return nick
            # 部分匹配 (slider_turns -> Turns, mul_x -> MulX)
            if id_lower.endswith(nick_lower) or nick_lower in id_lower:
                return nick
            # 反向匹配 (mulx -> MulX)
            if nick_lower.replace("_", "") == id_lower:
                return nick

        # 找不到就返回原值，讓 smart_connect 報錯
        return id_or_nick

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計"""
        return self.client.get_stats()

    def print_summary(self):
        """打印摘要"""
        self.client.print_summary()


# ============================================================
# 便捷函數
# ============================================================

def deploy_gh_code(
    gh_code: Dict[str, Any],
    clear_first: bool = True,
    debug: bool = True
) -> DeploymentResult:
    """
    快速部署 GH Code

    用法：
        from src.mcp_adapter import deploy_gh_code

        result = deploy_gh_code({
            "components": [...],
            "connections": [...]
        })
    """
    adapter = MCPAdapter(debug=debug)
    return adapter.deploy(gh_code, clear_first=clear_first)


# ============================================================
# 測試
# ============================================================

if __name__ == "__main__":
    # 測試用 gh_code
    test_gh_code = {
        "components": [
            {"type": "Number Slider", "nickname": "Turns", "value": 5, "min": 1, "max": 10},
            {"type": "Number Slider", "nickname": "Radius", "value": 20, "min": 1, "max": 50},
            {"type": "Series", "nickname": "Ser"},
            {"type": "Circle", "nickname": "Circ"},
        ],
        "connections": [
            {"from": "Turns", "from_param": "N", "to": "Ser", "to_param": "C"},
            {"from": "Radius", "from_param": "N", "to": "Circ", "to_param": "R"},
        ]
    }

    result = deploy_gh_code(test_gh_code)
    print(f"\nDeployment: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Components: {result.components_created}")
    print(f"Connections: {result.connections_made}")
    if result.failed_connections:
        print(f"Failed: {result.failed_connections}")
