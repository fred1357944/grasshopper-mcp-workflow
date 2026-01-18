#!/usr/bin/env python3
"""
診斷桌腳 Z 座標問題 - 深度分析 Orient 組件
"""

import socket
import json
import time


def cmd(cmd_type, params=None, timeout=15):
    """發送 MCP 命令"""
    s = socket.socket()
    s.settimeout(timeout)
    s.connect(('127.0.0.1', 8080))
    c = {'type': cmd_type}
    if params:
        c['parameters'] = params
    s.sendall((json.dumps(c) + '\n').encode())
    time.sleep(0.5)
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
    print("=" * 70)
    print("桌腳 Z 座標深度診斷")
    print("=" * 70)

    # 1. 獲取所有組件
    r = cmd('get_document_info')
    if not r.get('success'):
        print(f"✗ 連接失敗: {r.get('error')}")
        return

    components = r.get('data', {}).get('components', [])
    print(f"\n找到 {len(components)} 個組件\n")

    # 建立分類
    orients = []
    planes = []
    extrudes = []
    points = []
    sliders = []
    others = []

    for c in components:
        name = c.get('name', 'Unknown')
        nickname = c.get('nickname', '')
        comp_type = c.get('type', '')
        comp_id = c.get('id', '')

        info = {
            'id': comp_id,
            'name': name,
            'nickname': nickname,
            'type': comp_type
        }

        if 'Orient' in name:
            orients.append(info)
        elif 'Plane' in name or 'XY' in comp_type:
            planes.append(info)
        elif 'Extrude' in name:
            extrudes.append(info)
        elif 'Construct Point' in name or 'Point' in comp_type:
            points.append(info)
        elif 'Slider' in comp_type:
            sliders.append(info)
        else:
            others.append(info)

    # 2. 顯示 Orient 組件
    print("=" * 70)
    print("Orient 組件 (桌腳變換)")
    print("=" * 70)

    for o in orients:
        print(f"\n📦 {o['name']} (ID: {o['id'][:8]}...)")

        # 查詢組件詳細資訊
        info = cmd('get_component_info', {'id': o['id']})
        if info.get('success'):
            data = info['data']
            inputs = data.get('inputs', [])
            outputs = data.get('outputs', [])

            print("  輸入:")
            for inp in inputs:
                sources = inp.get('sources', [])
                source_str = ", ".join([s.get('componentName', '?') for s in sources]) if sources else "(未連接)"
                print(f"    - {inp.get('name')} ({inp.get('nickname')}): {source_str}")

            print("  輸出:")
            for out in outputs:
                print(f"    - {out.get('name')} ({out.get('nickname')})")
        else:
            print(f"  ✗ 查詢失敗: {info.get('error')}")

    # 3. 顯示 Construct Point 組件 (桌腳位置)
    print("\n" + "=" * 70)
    print("Construct Point 組件 (桌腳位置點)")
    print("=" * 70)

    for p in points:
        if 'Construct' in p['name']:
            print(f"\n📍 {p['name']} (ID: {p['id'][:8]}...)")

            info = cmd('get_component_info', {'id': p['id']})
            if info.get('success'):
                data = info['data']
                inputs = data.get('inputs', [])

                print("  輸入:")
                for inp in inputs:
                    sources = inp.get('sources', [])
                    source_names = []
                    for s in sources:
                        source_names.append(f"{s.get('componentName', '?')}[{s.get('paramName', '?')}]")
                    source_str = ", ".join(source_names) if source_names else "(未連接)"
                    print(f"    - {inp.get('nickname')}: {source_str}")

    # 4. 顯示 Extrude 組件
    print("\n" + "=" * 70)
    print("Extrude 組件 (桌腳幾何)")
    print("=" * 70)

    for e in extrudes:
        print(f"\n📦 {e['name']} (ID: {e['id'][:8]}...)")

        info = cmd('get_component_info', {'id': e['id']})
        if info.get('success'):
            data = info['data']
            inputs = data.get('inputs', [])
            outputs = data.get('outputs', [])

            print("  輸入:")
            for inp in inputs:
                sources = inp.get('sources', [])
                source_names = [f"{s.get('componentName', '?')}[{s.get('paramName', '?')}]" for s in sources]
                source_str = ", ".join(source_names) if source_names else "(未連接)"
                print(f"    - {inp.get('name')}: {source_str}")

            print("  輸出:")
            for out in outputs:
                targets = out.get('targets', [])
                target_str = f"→ {len(targets)} 個目標" if targets else "(無連接)"
                print(f"    - {out.get('name')}: {target_str}")

    # 5. 檢查 preview 狀態
    print("\n" + "=" * 70)
    print("可能的問題診斷")
    print("=" * 70)

    print("""
🔍 根據截圖分析，桌腳同時出現在 Z=0 和 Z=70+ 的位置。

可能原因:
1. 【Preview 重複】Extrude 的 preview 顯示原始位置的腿，
   而 Orient 的 preview 顯示變換後的腿

2. 【Z 座標錯誤】Construct Point 的 Z 輸入可能接收了錯誤的值

3. 【多餘連接】某個組件可能有多餘的連接導致重複輸出

建議檢查步驟:
1. 在 Grasshopper 中，右鍵 Extrude → 關閉 Preview
2. 檢查每個 Construct Point 的 Z 輸入是否為空
3. 確認只有 Orient 組件的 Preview 是開啟的
""")

    # 6. 關鍵 Slider 值
    print("\n" + "=" * 70)
    print("關鍵參數值")
    print("=" * 70)

    key_params = ['桌腳高度', 'LEG_HEIGHT', '腳高', 'Height']

    for s in sliders:
        info = cmd('get_component_info', {'id': s['id']})
        if info.get('success'):
            d = info['data']
            name = s.get('nickname') or s.get('name', '')
            val = d.get('value', 'N/A')

            # 只顯示桌腳相關的
            if any(k.lower() in name.lower() for k in key_params) or val == 70.0:
                print(f"  {name}: {val} (min={d.get('minimum')}, max={d.get('maximum')})")


if __name__ == '__main__':
    main()
