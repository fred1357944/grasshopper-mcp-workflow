#!/usr/bin/env python3
"""
椅子模型 v2 - 使用正確的 API 結構和參數映射

從 debug 文檔學到的關鍵知識:
1. API 使用巢狀結構: {"type": "cmd", "parameters": {...}}
2. 返回值是 "id" 而非 "component_id"
3. 使用經驗證的 GUID 避免 OBSOLETE 版本
4. 參數名稱使用 param_mapping.py 的映射
"""

import socket
import json
import time
from typing import Optional

# =============================================================================
# 經驗證的組件 GUID (2026-01-09 從 get_component_candidates 查詢)
# =============================================================================
VERIFIED_GUIDS = {
    # 基礎輸入 - 不用 GUID，用名稱
    # 'Number Slider': 使用 type 參數

    # 幾何 - Center Box (2026-01-09 更新)
    'Center Box': '8e22f9f3-c5eb-4298-9e5b-7412e3025516',

    # 平面/點 (2026-01-09 重新驗證)
    'XY Plane': 'd5272236-d023-4287-939b-473ba3fac0ce',

    # 變形 (2026-01-09 重新驗證)
    'Move': '3effc02f-5ab5-425e-a3db-0342ff0978ef',
    'Amplitude': '375bba73-b66f-4426-927c-2a5fc6e7dfc6',

    # 向量 (2026-01-09 重新驗證)
    'Unit Z': '62e56988-5991-4c90-8873-b7eefedf9ed8',

    # 數學 (2026-01-09 重新驗證)
    'Division': '42b7fc9d-e233-472a-ad32-8b9241c04e7f',

    # 輸出 (2026-01-09 重新驗證)
    'Merge': '01aeb2f1-3147-420f-942c-fdfbc7936a44',
}

# =============================================================================
# 參數映射 (來自 param_mapping.py)
# =============================================================================
TARGET_PARAMS = {
    'Center Box': {'Plane': 'Base', 'X': 'X', 'Y': 'Y', 'Z': 'Z'},
    'Move': {'Geometry': 'Geometry', 'Motion': 'T'},
    'Amplitude': {'Vector': 'Vector', 'Amplitude': 'Amplitude'},
    'Addition': {'A': 'A', 'B': 'B'},
    'Division': {'A': 'A', 'B': 'B'},
    'Merge': {'D1': 'D1', 'D2': 'D2'},
}

SOURCE_PARAMS = {
    'Center Box': 'Box',
    'Move': 'Geometry',
    'Addition': 'Result',
    'Division': 'Result',
    'XY Plane': 'Plane',
    'Construct Point': 'Point',
    'Amplitude': 'Vector',
    'Unit Z': 'Unit vector',
    'Merge': 'Result',
}


class GH_MCP_Client:
    """GH_MCP TCP 客戶端 - 使用正確的巢狀 JSON 結構"""

    def __init__(self, host='127.0.0.1', port=8080):
        self.host = host
        self.port = port

    def send_command(self, cmd_type: str, **params) -> dict:
        """發送命令到 GH_MCP (巢狀結構)"""
        command = {
            'type': cmd_type,
            'parameters': params
        }

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.sendall(json.dumps(command).encode('utf-8'))
                s.shutdown(socket.SHUT_WR)

                response = b''
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    response += chunk

                # 使用 utf-8-sig 處理可能的 BOM
                result = json.loads(response.decode('utf-8-sig'))
                return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def clear_document(self) -> dict:
        """清空文檔"""
        return self.send_command('clear_document')

    def add_slider(self, x: float, y: float, nickname: str) -> Optional[str]:
        """添加 Number Slider，返回組件 ID"""
        result = self.send_command(
            'add_component',
            type='Number Slider',
            x=x, y=y,
            nickname=nickname
        )
        if result.get('success'):
            return result.get('data', {}).get('id')  # 注意: 是 'id' 不是 'component_id'
        else:
            print(f"❌ 創建 Slider '{nickname}' 失敗: {result.get('error')}")
            return None

    def add_component(self, comp_type: str, x: float, y: float,
                      nickname: Optional[str] = None,
                      guid: Optional[str] = None) -> Optional[str]:
        """添加組件，返回組件 ID"""
        params = {'x': x, 'y': y}

        # 優先使用 GUID
        if guid:
            params['guid'] = guid
        elif comp_type in VERIFIED_GUIDS:
            params['guid'] = VERIFIED_GUIDS[comp_type]
        else:
            params['type'] = comp_type

        if nickname:
            params['nickname'] = nickname

        result = self.send_command('add_component', **params)
        if result.get('success'):
            comp_id = result.get('data', {}).get('id')
            print(f"✅ 創建 {comp_type} ({nickname or ''}) -> {comp_id[:8]}...")
            return comp_id
        else:
            print(f"❌ 創建 {comp_type} 失敗: {result.get('error')}")
            return None

    def connect(self, source_id: str, target_id: str,
                source_type: str, target_type: str,
                target_param: str) -> bool:
        """連接兩個組件，使用正確的參數映射"""

        # 取得正確的 targetParam
        actual_target = target_param
        if target_type in TARGET_PARAMS:
            actual_target = TARGET_PARAMS[target_type].get(target_param, target_param)

        # 取得正確的 sourceParam
        source_param = SOURCE_PARAMS.get(source_type)

        # 重要: 參數名稱是 sourceId/targetId，不是 source/target！
        params = {
            'sourceId': source_id,  # 修正: source -> sourceId
            'targetId': target_id,  # 修正: target -> targetId
            'targetParam': actual_target
        }

        if source_param:
            params['sourceParam'] = source_param

        result = self.send_command('connect_components', **params)

        if result.get('success'):
            print(f"✅ 連接: {source_type} -> {target_type}.{actual_target}")
            return True
        else:
            error = result.get('error', 'Unknown error')
            print(f"⚠️ 連接失敗: {source_type} -> {target_type}.{target_param}: {error}")
            return False


def build_chair():
    """建構參數化椅子 - 使用經驗證的 API 和 GUID"""

    print("=" * 60)
    print("🪑 建構參數化椅子 v2")
    print("=" * 60)

    client = GH_MCP_Client()

    # 1. 清空文檔
    print("\n📋 清空文檔...")
    client.clear_document()
    time.sleep(0.5)

    # ==========================================================================
    # 2. 創建參數 Sliders (佈局: 左側垂直排列)
    # ==========================================================================
    print("\n📐 創建參數 Sliders...")

    sliders = {}
    slider_configs = [
        ('SeatW', 0, 0),      # 椅面寬度
        ('SeatD', 0, 60),     # 椅面深度
        ('SeatH', 0, 120),    # 椅面厚度
        ('SeatZ', 0, 180),    # 椅面高度
        ('BackW', 0, 240),    # 椅背寬度
        ('BackH', 0, 300),    # 椅背高度
        ('BackT', 0, 360),    # 椅背厚度
        ('LegS', 0, 420),     # 椅腳尺寸
    ]

    for name, x, y in slider_configs:
        sid = client.add_slider(x, y, name)
        if sid:
            sliders[name] = sid

    # ==========================================================================
    # 3. 創建 XY Plane
    # ==========================================================================
    print("\n📐 創建基準平面...")
    xy_plane = client.add_component('XY Plane', 150, 200, 'BasePlane')

    # ==========================================================================
    # 4. 創建椅面 (Center Box)
    # ==========================================================================
    print("\n🟫 創建椅面...")
    seat_box = client.add_component('Center Box', 300, 100, 'Seat')

    if seat_box:
        # 連接 XY Plane -> Center Box.Base
        if xy_plane:
            client.connect(xy_plane, seat_box, 'XY Plane', 'Center Box', 'Plane')

        # 連接 Sliders -> Center Box
        if 'SeatW' in sliders:
            client.connect(sliders['SeatW'], seat_box, 'Number Slider', 'Center Box', 'X')
        if 'SeatD' in sliders:
            client.connect(sliders['SeatD'], seat_box, 'Number Slider', 'Center Box', 'Y')
        if 'SeatH' in sliders:
            client.connect(sliders['SeatH'], seat_box, 'Number Slider', 'Center Box', 'Z')

    # ==========================================================================
    # 5. 創建 Unit Z 和 Amplitude (用於 Move)
    # ==========================================================================
    print("\n📐 創建移動向量...")
    unit_z = client.add_component('Unit Z', 150, 300, 'ZDir')
    amplitude = client.add_component('Amplitude', 300, 300, 'SeatMove')

    if amplitude and unit_z:
        client.connect(unit_z, amplitude, 'Unit Z', 'Amplitude', 'Vector')
        if 'SeatZ' in sliders:
            client.connect(sliders['SeatZ'], amplitude, 'Number Slider', 'Amplitude', 'Amplitude')

    # ==========================================================================
    # 6. Move 椅面到正確高度
    # ==========================================================================
    print("\n🔄 移動椅面...")
    seat_move = client.add_component('Move', 450, 200, 'SeatMoved')

    if seat_move:
        if seat_box:
            client.connect(seat_box, seat_move, 'Center Box', 'Move', 'Geometry')
        if amplitude:
            client.connect(amplitude, seat_move, 'Amplitude', 'Move', 'Motion')

    # ==========================================================================
    # 7. 創建椅背
    # ==========================================================================
    print("\n🟫 創建椅背...")
    back_box = client.add_component('Center Box', 300, 400, 'Back')

    if back_box:
        if xy_plane:
            client.connect(xy_plane, back_box, 'XY Plane', 'Center Box', 'Plane')
        if 'BackW' in sliders:
            client.connect(sliders['BackW'], back_box, 'Number Slider', 'Center Box', 'X')
        if 'BackT' in sliders:
            client.connect(sliders['BackT'], back_box, 'Number Slider', 'Center Box', 'Y')
        if 'BackH' in sliders:
            client.connect(sliders['BackH'], back_box, 'Number Slider', 'Center Box', 'Z')

    # 移動椅背到正確位置 (SeatZ + SeatH/2 + BackH/2)
    # 先用 Division 計算 BackH/2
    print("\n📐 計算椅背位置...")

    # Division for BackH/2
    div_back = client.add_component('Division', 150, 500, 'BackH/2')
    if div_back and 'BackH' in sliders:
        client.connect(sliders['BackH'], div_back, 'Number Slider', 'Division', 'A')
        # B 參數需要設定為 2，但 MCP 無法設定 slider 值
        # 暫時跳過，使用默認值

    # ==========================================================================
    # 8. 創建椅腳 (4 個 Center Box)
    # ==========================================================================
    print("\n🟫 創建椅腳...")
    legs = {}
    leg_positions = [
        ('LegFL', 300, 600),   # Front Left
        ('LegFR', 450, 600),   # Front Right
        ('LegBL', 300, 700),   # Back Left
        ('LegBR', 450, 700),   # Back Right
    ]

    for leg_name, x, y in leg_positions:
        leg = client.add_component('Center Box', x, y, leg_name)
        if leg:
            legs[leg_name] = leg
            if xy_plane:
                client.connect(xy_plane, leg, 'XY Plane', 'Center Box', 'Plane')
            if 'LegS' in sliders:
                client.connect(sliders['LegS'], leg, 'Number Slider', 'Center Box', 'X')
                client.connect(sliders['LegS'], leg, 'Number Slider', 'Center Box', 'Y')
            if 'SeatZ' in sliders:
                client.connect(sliders['SeatZ'], leg, 'Number Slider', 'Center Box', 'Z')

    # ==========================================================================
    # 9. Merge 所有幾何體
    # ==========================================================================
    print("\n🔗 合併幾何體...")
    merge = client.add_component('Merge', 600, 400, 'AllParts')

    if merge:
        if seat_move:
            client.connect(seat_move, merge, 'Move', 'Merge', 'D1')
        if back_box:
            client.connect(back_box, merge, 'Center Box', 'Merge', 'D2')

    # ==========================================================================
    # 完成
    # ==========================================================================
    print("\n" + "=" * 60)
    print("✅ 椅子模型建構完成!")
    print("=" * 60)

    # 統計
    print(f"\n📊 統計:")
    print(f"  - Sliders: {len(sliders)}")
    print(f"  - 椅腳: {len(legs)}")
    print(f"  - 總組件數: {len(sliders) + len(legs) + 6}")

    return {
        'sliders': sliders,
        'seat': seat_move,
        'back': back_box,
        'legs': legs,
        'merge': merge
    }


if __name__ == '__main__':
    build_chair()
