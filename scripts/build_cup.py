#!/usr/bin/env python3
"""
工業設計水杯 - GH MCP 執行腳本 (含佈局)

設計特點:
- 簡潔的圓柱形杯身
- 微微內收的腰線（符合人體工學）
- 平底設計，穩定性佳
- 5 個可調參數

佈局:
  Col 0      Col 1       Col 2        Col 3       Col 4
  Sliders -> Points  -> Planes   -> Circles -> Loft/Cap
"""

import socket
import json
import time
from typing import Optional, Dict


# 佈局常數
COL_WIDTH = 200   # 欄寬
ROW_HEIGHT = 80   # 行高
START_X = 50      # 起始 X
START_Y = 50      # 起始 Y


class GH_MCP_Client:
    """GH_MCP TCP 客戶端"""

    def __init__(self, host='127.0.0.1', port=8080):
        self.host = host
        self.port = port
        self.components: Dict[str, str] = {}  # nickname -> id
        self.debug = True

    def send_command(self, cmd_type: str, **params) -> dict:
        """發送命令到 GH_MCP"""
        command = {
            'type': cmd_type,
            'parameters': params
        }

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((self.host, self.port))
                s.sendall(json.dumps(command).encode('utf-8'))
                s.shutdown(socket.SHUT_WR)

                response = b''
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    response += chunk

                result = json.loads(response.decode('utf-8-sig'))
                return result
        except socket.timeout:
            return {'success': False, 'error': 'Connection timeout'}
        except ConnectionRefusedError:
            return {'success': False, 'error': 'GH_MCP not running'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def add_slider(self, nickname: str, x: float, y: float,
                   value: float, min_val: float = 0, max_val: float = 200) -> Optional[str]:
        """添加 Number Slider (含位置)"""
        result = self.send_command(
            'add_component',
            type='Number Slider',
            nickname=nickname,
            x=x,
            y=y
        )

        if result.get('success'):
            data = result.get('data', {})
            comp_id = data.get('id') if isinstance(data, dict) else None

            if comp_id:
                self.components[nickname] = comp_id

                # 設置滑桿：分兩步驟（先 range，再 value）
                time.sleep(0.1)
                # Step 1: 設置 min/max 範圍
                self.send_command(
                    'set_slider_properties',
                    id=comp_id,
                    min=min_val,
                    max=max_val
                )
                time.sleep(0.1)
                # Step 2: 設置 value
                self.send_command(
                    'set_slider_properties',
                    id=comp_id,
                    value=str(value)
                )
                return comp_id
        return None

    def add_component(self, comp_type: str, nickname: str,
                      x: float, y: float) -> Optional[str]:
        """添加組件 (含位置)"""
        result = self.send_command(
            'add_component',
            type=comp_type,
            nickname=nickname,
            x=x,
            y=y
        )

        if result.get('success'):
            data = result.get('data', {})
            comp_id = data.get('id') if isinstance(data, dict) else None

            if comp_id:
                self.components[nickname] = comp_id
                return comp_id
        return None

    def connect(self, from_nick: str, from_param: str,
                to_nick: str, to_param: str) -> bool:
        """連接兩個組件"""
        from_id = self.components.get(from_nick)
        to_id = self.components.get(to_nick)

        if not from_id or not to_id:
            return False

        result = self.send_command(
            'connect_components',
            from_component_id=from_id,
            from_parameter=from_param,
            to_component_id=to_id,
            to_parameter=to_param
        )
        return result.get('success', False)

    def clear_canvas(self) -> bool:
        """清空畫布"""
        result = self.send_command('clear_document')
        return result.get('success', False)

    def get_document_info(self) -> dict:
        """獲取文檔資訊"""
        return self.send_command('get_document_info')


def build_industrial_cup():
    """建構工業設計水杯 (含佈局)"""
    print("=" * 60)
    print("工業設計水杯 - GH MCP 建構")
    print("=" * 60)

    client = GH_MCP_Client()

    # 測試連接
    print("\n1. 測試 GH_MCP 連接...")
    result = client.get_document_info()
    if not result.get('success'):
        error = result.get('error', '')
        # 如果是 Index not found 錯誤，可能是空文檔，繼續嘗試
        if 'Index not found' in str(error) or 'connection' not in str(error).lower():
            print(f"   ⚠ {error}")
            print("   → 嘗試繼續...")
        else:
            print(f"   ❌ 無法連接: {error}")
            return False
    else:
        print("   ✓ 連接成功")

    # 清空畫布
    print("\n2. 準備畫布...")
    client.clear_canvas()
    time.sleep(0.5)

    # === 建立組件 (含佈局) ===
    print("\n3. 建立組件...")

    # 佈局計算
    def pos(col: int, row: int) -> tuple:
        return (START_X + col * COL_WIDTH, START_Y + row * ROW_HEIGHT)

    # Column 0: Sliders
    print("\n   【Col 0: 參數滑桿】")
    sliders = [
        ("Height", 0, 0, 120, 80, 200),     # row 0
        ("BottomR", 0, 1, 35, 25, 50),      # row 1
        ("TopR", 0, 2, 40, 25, 60),         # row 2
        ("WaistR", 0, 3, 32.5, 20, 45),     # row 3
        ("WaistH", 0, 4, 40, 20, 80),       # row 4
    ]

    for name, col, row, val, min_v, max_v in sliders:
        x, y = pos(col, row)
        if client.add_slider(name, x, y, val, min_v, max_v):
            print(f"   ✓ {name} = {val} @ ({x}, {y})")
        else:
            print(f"   ✗ {name}")

    # Column 1: Points
    print("\n   【Col 1: 構建點】")
    points = [
        ("Origin", 1, 1),    # 對應 BottomR
        ("WaistPt", 1, 3),   # 對應 WaistR
        ("TopPt", 1, 0),     # 對應 Height
    ]
    for name, col, row in points:
        x, y = pos(col, row)
        if client.add_component("Construct Point", name, x, y):
            print(f"   ✓ {name} @ ({x}, {y})")
        else:
            print(f"   ✗ {name}")

    # Column 2: Planes
    print("\n   【Col 2: XY 平面】")
    planes = [
        ("PlnBottom", 2, 1),
        ("PlnWaist", 2, 3),
        ("PlnTop", 2, 0),
    ]
    for name, col, row in planes:
        x, y = pos(col, row)
        if client.add_component("XY Plane", name, x, y):
            print(f"   ✓ {name} @ ({x}, {y})")
        else:
            print(f"   ✗ {name}")

    # Column 3: Circles
    print("\n   【Col 3: 圓形】")
    circles = [
        ("CircleBottom", 3, 1),
        ("CircleWaist", 3, 3),
        ("CircleTop", 3, 2),  # 放中間
    ]
    for name, col, row in circles:
        x, y = pos(col, row)
        if client.add_component("Circle", name, x, y):
            print(f"   ✓ {name} @ ({x}, {y})")
        else:
            print(f"   ✗ {name}")

    # Column 4: Loft & Cap
    print("\n   【Col 4: 曲面】")
    surfaces = [
        ("Loft", "CupBody", 4, 2),
        ("Cap Holes", "CapBottom", 5, 2),
    ]
    for comp_type, name, col, row in surfaces:
        x, y = pos(col, row)
        if client.add_component(comp_type, name, x, y):
            print(f"   ✓ {name} ({comp_type}) @ ({x}, {y})")
        else:
            print(f"   ✗ {name}")

    time.sleep(0.3)
    print(f"\n   → 已創建 {len(client.components)} 個組件")

    # === 建立連接 ===
    print("\n4. 建立連接...")

    connections = [
        # 高度控制
        ("Height", "N", "TopPt", "Z"),
        ("WaistH", "N", "WaistPt", "Z"),

        # 半徑控制
        ("BottomR", "N", "CircleBottom", "R"),
        ("WaistR", "N", "CircleWaist", "R"),
        ("TopR", "N", "CircleTop", "R"),

        # 平面到圓
        ("PlnBottom", "P", "CircleBottom", "P"),
        ("PlnWaist", "P", "CircleWaist", "P"),
        ("PlnTop", "P", "CircleTop", "P"),

        # 點到平面
        ("Origin", "Pt", "PlnBottom", "O"),
        ("WaistPt", "Pt", "PlnWaist", "O"),
        ("TopPt", "Pt", "PlnTop", "O"),

        # 圓到 Loft
        ("CircleBottom", "C", "CupBody", "C"),
        ("CircleWaist", "C", "CupBody", "C"),
        ("CircleTop", "C", "CupBody", "C"),

        # Loft 到 Cap
        ("CupBody", "L", "CapBottom", "B"),
    ]

    success_count = 0
    for from_nick, from_p, to_nick, to_p in connections:
        if client.connect(from_nick, from_p, to_nick, to_p):
            print(f"   ✓ {from_nick}.{from_p} → {to_nick}.{to_p}")
            success_count += 1
        else:
            print(f"   ✗ {from_nick}.{from_p} → {to_nick}.{to_p}")

    # === 總結 ===
    print("\n" + "=" * 60)
    print("建構結果")
    print("=" * 60)
    print(f"   組件: {len(client.components)} 個")
    print(f"   連接: {success_count}/{len(connections)}")

    if success_count > 0:
        print("\n✓ 水杯已建立！")
        print("\n佈局說明:")
        print("   Col 0: 參數滑桿 (Height, BottomR, TopR, WaistR, WaistH)")
        print("   Col 1: 構建點 (Origin, WaistPt, TopPt)")
        print("   Col 2: XY 平面")
        print("   Col 3: 圓形截面")
        print("   Col 4-5: Loft → Cap")
        print("\n調整參數:")
        print("   - Height: 杯身高度")
        print("   - WaistR < BottomR/TopR: 內收腰線")

    return success_count > 0


if __name__ == "__main__":
    build_industrial_cup()
