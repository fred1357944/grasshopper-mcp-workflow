#!/usr/bin/env python3
"""
診斷四腳桌問題 - 查詢各組件的實際值
"""

import socket
import json
import time

def cmd(cmd_type, params=None, timeout=10):
    """發送 MCP 命令"""
    s = socket.socket()
    s.settimeout(timeout)
    s.connect(('127.0.0.1', 8080))
    c = {'type': cmd_type}
    if params:
        c['parameters'] = params
    s.sendall((json.dumps(c) + '\n').encode())
    time.sleep(0.3)
    chunks = []
    while True:
        try:
            chunk = s.recv(8192)
            if not chunk:
                break
            chunks.append(chunk)
            if b'\n' in chunk:
                break
        except socket.timeout:
            break
    s.close()
    data = b''.join(chunks).decode('utf-8-sig').strip()
    if not data:
        return {'success': False, 'error': 'Empty response'}
    try:
        return json.loads(data)
    except:
        return {'success': False, 'error': 'JSON error', 'raw': data[:200]}


def main():
    print("=== 四腳桌診斷 ===\n")

    # 1. 獲取所有組件
    print("1. 獲取 Canvas 上的所有組件...")
    r = cmd('get_document_info')

    if not r.get('success'):
        print(f"  ✗ 錯誤: {r.get('error')}")
        return

    components = r.get('data', {}).get('components', [])
    print(f"  找到 {len(components)} 個組件\n")

    # 建立 nickname -> id 對照表
    name_to_id = {}
    sliders = []

    for c in components:
        nickname = c.get('nickname', c.get('name', 'Unknown'))
        comp_id = c.get('id')
        comp_type = c.get('type', 'Unknown')

        name_to_id[nickname] = comp_id

        if 'Slider' in comp_type:
            sliders.append((nickname, comp_id))

    # 2. 查詢所有 Slider 的值
    print("2. 查詢 Slider 值...")
    print("-" * 60)
    print(f"{'名稱':<20} {'Min':>10} {'Value':>10} {'Max':>10}")
    print("-" * 60)

    position_sliders = []

    for nickname, comp_id in sliders:
        info = cmd('get_component_info', {'id': comp_id})

        if info.get('success'):
            d = info['data']
            min_v = d.get('minimum', 'N/A')
            max_v = d.get('maximum', 'N/A')
            val = d.get('value', 'N/A')

            # 標記問題
            flag = ""
            if 'POS' in nickname and min_v is not None:
                if min_v >= 0:
                    flag = "⚠ min應為負數!"
                position_sliders.append((nickname, min_v, val, max_v))

            print(f"{nickname:<20} {str(min_v):>10} {str(val):>10} {str(max_v):>10} {flag}")
        else:
            print(f"{nickname:<20} {'?':>10} {'?':>10} {'?':>10}")

    print("-" * 60)

    # 3. 分析位置 Slider
    print("\n3. 桌腳位置分析...")

    expected_positions = {
        'SLIDER_POS1_X': 50, 'SLIDER_POS1_Y': 30,   # 前右
        'SLIDER_POS2_X': -50, 'SLIDER_POS2_Y': 30,  # 前左
        'SLIDER_POS3_X': -50, 'SLIDER_POS3_Y': -30, # 後左
        'SLIDER_POS4_X': 50, 'SLIDER_POS4_Y': -30,  # 後右
    }

    issues = []
    for name, min_v, val, max_v in position_sliders:
        expected = expected_positions.get(name)
        if expected is not None and val is not None:
            if abs(float(val) - expected) > 0.1:
                issues.append(f"  ⚠ {name}: 實際={val}, 預期={expected}")
            if min_v is not None and float(min_v) >= 0:
                issues.append(f"  ⚠ {name}: min={min_v} (應該是 -100)")

    if issues:
        print("  發現問題:")
        for issue in issues:
            print(issue)
    else:
        print("  ✓ 位置 Slider 值正確")

    # 4. 總結
    print("\n" + "=" * 60)
    print("診斷總結:")
    print("=" * 60)

    if any('POS' in name and min_v >= 0 for name, min_v, val, max_v in position_sliders if min_v is not None):
        print("""
問題: Slider 的 min 值無法設置為負數!

這是 GH_MCP 的 Bug:
- set_slider_properties 可能不支持負數 min
- 或者 Slider 組件有最小值限制

修復建議:
1. 檢查 GH_MCP 的 SetSliderProperties 實現
2. 確認 Grasshopper Slider 是否支持負數範圍
""")
    else:
        print("""
Slider 值看起來正確，問題可能在:
1. Orient 組件的 A/B 連接
2. 平面方向問題
3. 其他幾何計算錯誤
""")


if __name__ == '__main__':
    main()
