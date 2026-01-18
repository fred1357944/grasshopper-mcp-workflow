#!/usr/bin/env python3
"""
GH MCP Layout Executor

整合佈局計算與 MCP 命令執行
- 自動計算組件位置
- 批量創建組件和連線
- 支持群組和視圖調整
"""

import socket
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from .canvas_layout import CanvasLayoutCalculator, LayoutConfig


@dataclass
class ComponentDef:
    """組件定義"""
    name: str              # 組件名稱（用於佈局計算）
    type: str              # Grasshopper 組件類型名稱
    guid: Optional[str] = None  # 組件 GUID（優先使用）


@dataclass
class ConnectionDef:
    """連線定義"""
    from_name: str         # 來源組件名稱
    from_param: str        # 來源參數名稱
    to_name: str           # 目標組件名稱
    to_param: str          # 目標參數名稱


@dataclass
class SliderConfig:
    """Slider 配置"""
    name: str
    min_val: float
    max_val: float
    default_val: float


class MCPLayoutExecutor:
    """整合佈局計算的 MCP 執行器"""

    # 精確的 GUID 映射表 (避免模糊匹配問題)
    # 組件類型名稱 -> GUID (從 MCP 直接驗證)
    COMPONENT_GUIDS = {
        # === 輸入參數組件 ===
        'Number Slider': '1ce51ec5-d2af-4673-b720-0c7927e25da8',
        'Panel': '59e0b89a-e487-49f8-bab8-b5bab16be14c',
        'Boolean Toggle': '2e78987b-9dfb-42a2-8b76-3923ac8bd91a',
        'Button': 'a8b97322-2d53-47cd-905e-b932c3ccd74e',

        # === 幾何圖元 ===
        'Point': 'fbac3e32-f100-4292-8692-77240a42fd1a',
        'Construct Point': '57c9ff28-1d2f-4af5-9a55-10e279d7b794',
        'Rectangle 2Pt': '5b50caf1-5d51-4029-b457-5da9bc4b2e63',
        'Circle CNR': '2961b083-c1ee-43a9-a818-b8b47f50d625',
        'Center Box': '4e874a4e-95cd-46d0-904d-19cca8fd962c',

        # === 平面和向量 ===
        'XY Plane': '0cc80429-363d-4581-8636-647a753b7560',
        'Unit Z': '53ce9fce-0704-4c57-ba24-68330c2cfc47',
        'Amplitude': 'a7cae2fa-97dd-4034-b613-490b5b4fc7f4',
        'Vector 2Pt': '57562128-0426-462c-9f27-c4d6e5f2a1b3',

        # === 變形操作 ===
        'Move': '612a46bd-d9a2-4353-9682-cab31ab5e922',  # 新版 Move (非 OBSOLETE)
        'Move To Plane': '816bd9f1-10fb-4852-8eba-181abe7d2365',
        'Orient': 'faed5c8d-971c-47d3-8bf3-053fc4602a0e',  # G, A (Source), B (Target) → G

        # === 曲面/實體操作 ===
        'Extrusion': 'e5b9ef88-e10f-4d64-93e9-cac414005cc9',
        'Solid Union': '6de7e1f0-2d51-4e1a-9073-ec17bf699e51',
        'Brep': '919e146f-30ae-4aae-be34-4d72f555e7da',

        # === 數據處理 ===
        'Merge': '32b92248-1673-4d8b-84da-3b14ce36b2b0',
        'List Item': '59daf374-bc21-4a5e-8282-5504fb7ae9ae',
        'List Length': '1817fd29-20ae-4503-b542-f0fb651e67d7',

        # === 數學運算 ===
        'Division': '4f1021a9-657a-4255-9d44-09337cf36705',  # A, B → R
        'Addition': 'c6b0aa44-217a-4ae2-88d6-867ce10b3f3a',  # A, B → R

        # === 輸出/預覽 ===
        'Custom Preview': '6d8c8b5b-3221-4611-9794-01f16c7b0278',
        'Geometry': 'ac2bc2cb-70fb-4dd5-9c78-7e1ea97fe278',
    }

    def __init__(self, host: str = '127.0.0.1', port: int = 8080):
        self.host = host
        self.port = port
        self.layout_calc = CanvasLayoutCalculator(LayoutConfig(
            horizontal_spacing=200,  # 增加水平間距
            vertical_spacing=80,     # 增加垂直間距
        ))

        # 組件 name -> instance_id 映射
        self.component_ids: Dict[str, str] = {}

        # 組件 name -> 位置
        self.component_positions: Dict[str, Tuple[float, float]] = {}

        # GUID 緩存 (合併預定義 + 動態查詢)
        self.guid_cache: Dict[str, str] = dict(self.COMPONENT_GUIDS)

        # Canvas 偏移（用於避開現有組件）
        self.canvas_offset_x: float = 0
        self.canvas_offset_y: float = 0

    def check_canvas_status(self) -> Dict[str, Any]:
        """
        檢查 Canvas 狀態

        Returns:
            包含組件數量和邊界資訊的字典
        """
        result = self._send_command('get_document_info')
        if not result.get('success'):
            return {'success': False, 'error': result.get('error')}

        data = result.get('data', {})
        components = data.get('components', [])

        # 計算現有組件的邊界
        if components:
            min_x = min(c.get('x', 0) for c in components)
            max_x = max(c.get('x', 0) for c in components)
            min_y = min(c.get('y', 0) for c in components)
            max_y = max(c.get('y', 0) for c in components)

            return {
                'success': True,
                'component_count': len(components),
                'bounds': {
                    'min_x': min_x, 'max_x': max_x,
                    'min_y': min_y, 'max_y': max_y,
                    'width': max_x - min_x,
                    'height': max_y - min_y,
                },
                'is_empty': False
            }
        else:
            return {
                'success': True,
                'component_count': 0,
                'bounds': None,
                'is_empty': True
            }

    def clear_canvas(self) -> bool:
        """清空 Canvas 上的所有組件"""
        result = self._send_command('clear_document')
        return result.get('success', False)

    def set_offset_from_existing(self, margin: float = 100):
        """根據現有組件設置偏移，在右側空白處創建新組件"""
        status = self.check_canvas_status()
        if status.get('success') and not status.get('is_empty'):
            bounds = status['bounds']
            # 在現有組件右側留出空間
            self.canvas_offset_x = bounds['max_x'] + margin
            self.canvas_offset_y = bounds['min_y']
            return True
        return False

    def _send_command(self, cmd_type: str, params: Optional[Dict] = None) -> Dict:
        """發送 MCP 命令"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15.0)
            sock.connect((self.host, self.port))

            command = {'type': cmd_type}
            if params:
                command['parameters'] = params

            message = json.dumps(command) + '\n'
            sock.sendall(message.encode('utf-8'))

            response = b''
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b'\n' in response:
                    break

            sock.close()
            return json.loads(response.decode('utf-8-sig').strip())

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_component_guid(self, type_name: str) -> Optional[str]:
        """獲取組件 GUID"""
        if type_name in self.guid_cache:
            return self.guid_cache[type_name]

        result = self._send_command('get_component_candidates', {'name': type_name})

        if result.get('success') and result.get('data'):
            candidates = result['data'].get('candidates', [])
            for c in candidates:
                if not c.get('obsolete', False):
                    guid = c.get('guid')
                    if guid:
                        self.guid_cache[type_name] = guid
                        return guid
            # 如果全是 obsolete，取第一個
            if candidates:
                guid = candidates[0].get('guid')
                if guid:
                    self.guid_cache[type_name] = guid
                    return guid

        return None

    def define_component(self, name: str, type_name: str, width: float = 120, height: float = 40):
        """定義一個組件（不創建）"""
        self.layout_calc.add_component(
            id=name,
            name=name,
            type=type_name,
            width=width,
            height=height
        )

    def define_connection(self, from_name: str, from_param: str,
                          to_name: str, to_param: str):
        """定義一個連線（不創建）"""
        self.layout_calc.add_connection(from_name, from_param, to_name, to_param)

    def calculate_layout(self) -> Dict[str, Tuple[float, float]]:
        """計算所有組件的佈局"""
        self.component_positions = self.layout_calc.calculate_layout()
        return self.component_positions

    def create_component(self, name: str, type_name: str,
                         x: Optional[float] = None,
                         y: Optional[float] = None) -> Optional[str]:
        """創建組件"""
        # 使用預計算的位置
        if x is None or y is None:
            if name in self.component_positions:
                x, y = self.component_positions[name]
            else:
                x, y = 0, 0

        # 應用 Canvas 偏移
        x += self.canvas_offset_x
        y += self.canvas_offset_y

        # 獲取 GUID（用於備用）
        guid = self.get_component_guid(type_name)

        # 創建組件 - 同時傳遞 guid 和 type
        # MCP 會優先使用 type 做模糊匹配，guid 作為備用
        params = {
            'guid': guid if guid else 'dummy',  # guid 是必須參數
            'type': type_name,  # 優先使用 type 做匹配
            'x': x,
            'y': y
        }
        result = self._send_command('add_component', params)

        if result.get('success') and result.get('data'):
            comp_id = result['data'].get('id')
            if comp_id:
                self.component_ids[name] = comp_id
                print(f"  ✓ 創建 {name} ({type_name}) at ({x:.0f}, {y:.0f})")
                return comp_id

        error = result.get('error', 'Unknown error')
        print(f"  ✗ 創建 {name} 失敗: {error}")
        return None

    def create_connection(self, from_name: str, from_param: str,
                          to_name: str, to_param: str) -> bool:
        """創建連線"""
        from_id = self.component_ids.get(from_name)
        to_id = self.component_ids.get(to_name)

        if not from_id or not to_id:
            print(f"  ⚠ 連線失敗: {from_name} 或 {to_name} 不存在")
            return False

        result = self._send_command('connect_components', {
            'sourceId': from_id,
            'targetId': to_id,
            'sourceParam': from_param,
            'targetParam': to_param
        })

        # 檢查外層和內層的 success
        if result.get('success'):
            data = result.get('data', {})
            # 檢查內層 success（實際連線結果）
            inner_success = data.get('success', data.get('verified', False))
            if inner_success:
                actual_source = data.get('sourceParam', from_param)
                actual_target = data.get('targetParam', to_param)
                print(f"  ✓ 連線: {from_name}.{actual_source} → {to_name}.{actual_target}")
                return True
            else:
                msg = data.get('message', 'Connection may have failed')
                print(f"  ⚠ 連線可能失敗 {from_name}.{from_param} → {to_name}.{to_param}: {msg}")
                return False
        else:
            error = result.get('error', 'Unknown error')
            print(f"  ✗ 連線失敗 {from_name} → {to_name}: {error}")
            return False

    def set_slider(self, name: str, min_val: float, max_val: float,
                   value: float) -> bool:
        """設置 Slider 值"""
        comp_id = self.component_ids.get(name)
        if not comp_id:
            print(f"  ⚠ Slider {name} 不存在")
            return False

        result = self._send_command('set_slider_properties', {
            'id': comp_id,
            'min': min_val,
            'max': max_val,
            'value': str(value)
        })

        if result.get('success'):
            print(f"  ✓ 設置 {name}: {min_val} < {value} < {max_val}")
            return True
        else:
            error = result.get('error', 'Unknown error')
            print(f"  ✗ 設置 {name} 失敗: {error}")
            return False

    def zoom_to_all(self) -> bool:
        """縮放到所有組件"""
        all_ids = list(self.component_ids.values())
        if not all_ids:
            return False

        result = self._send_command('zoom_to_components', {
            'componentIds': all_ids
        })

        return result.get('success', False)


def create_simple_table_design() -> MCPLayoutExecutor:
    """
    創建一個簡單的桌子設計

    Returns:
        配置好的 MCPLayoutExecutor
    """
    executor = MCPLayoutExecutor()

    # === 定義組件 ===
    # 輸入參數
    executor.define_component("WIDTH", "Number Slider", width=200, height=20)
    executor.define_component("DEPTH", "Number Slider", width=200, height=20)
    executor.define_component("TOP_THICK", "Number Slider", width=200, height=20)
    executor.define_component("LEG_SIZE", "Number Slider", width=200, height=20)
    executor.define_component("LEG_HEIGHT", "Number Slider", width=200, height=20)

    # 構造點
    executor.define_component("ORIGIN", "Construct Point", width=100, height=50)
    executor.define_component("LEG_OFFSET", "Construct Point", width=100, height=50)

    # 桌面
    executor.define_component("TABLE_RECT", "Rectangle", width=100, height=60)
    executor.define_component("TABLE_SURFACE", "Extrude", width=100, height=50)

    # 桌腳
    executor.define_component("LEG_BOX", "Box", width=100, height=50)
    executor.define_component("MIRROR_X", "Mirror", width=100, height=50)
    executor.define_component("MIRROR_Y", "Mirror", width=100, height=50)

    # 輸出
    executor.define_component("UNION", "Solid Union", width=100, height=50)
    executor.define_component("PREVIEW", "Custom Preview", width=100, height=50)

    # === 定義連線 ===
    # 桌面尺寸
    executor.define_connection("WIDTH", "Number", "TABLE_RECT", "X")
    executor.define_connection("DEPTH", "Number", "TABLE_RECT", "Y")
    executor.define_connection("ORIGIN", "Point", "TABLE_RECT", "P")

    # 桌面厚度
    executor.define_connection("TABLE_RECT", "Rectangle", "TABLE_SURFACE", "Base")
    executor.define_connection("TOP_THICK", "Number", "TABLE_SURFACE", "Direction")

    # 桌腳
    executor.define_connection("LEG_OFFSET", "Point", "LEG_BOX", "P")
    executor.define_connection("LEG_SIZE", "Number", "LEG_BOX", "X")
    executor.define_connection("LEG_SIZE", "Number", "LEG_BOX", "Y")
    executor.define_connection("LEG_HEIGHT", "Number", "LEG_BOX", "Z")

    # 鏡像
    executor.define_connection("LEG_BOX", "Box", "MIRROR_X", "Geometry")
    executor.define_connection("MIRROR_X", "Geometry", "MIRROR_Y", "Geometry")

    # 合併
    executor.define_connection("TABLE_SURFACE", "Extrusion", "UNION", "Breps")
    executor.define_connection("MIRROR_Y", "Geometry", "UNION", "Breps")

    # 預覽
    executor.define_connection("UNION", "Result", "PREVIEW", "Geometry")

    return executor


if __name__ == "__main__":
    print("=== GH MCP Layout Executor Test ===\n")

    executor = create_simple_table_design()

    # 計算佈局
    print("1. 計算佈局...")
    positions = executor.calculate_layout()
    print(executor.layout_calc.get_layout_summary())

    print("\n2. 測試 MCP 連接...")
    result = executor._send_command('get_document_info')
    if result.get('success'):
        print("  ✓ MCP 連接正常")
    else:
        print(f"  ✗ MCP 連接失敗: {result.get('error')}")
        print("\n請確保 Grasshopper 正在運行且 MCP 插件已載入")
