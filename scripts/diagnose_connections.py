#!/usr/bin/env python3
"""
診斷連線狀態 - 檢查 Orient 的 A/B 是否正確連接
"""

import socket
import json
import time

def cmd(cmd_type, params=None, timeout=10):
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
    return json.loads(data) if data else {}


def main():
    print("=== 連線診斷 ===\n")

    # 獲取所有組件
    r = cmd('get_document_info')
    if not r.get('success'):
        print(f"Error: {r.get('error')}")
        return

    components = r.get('data', {}).get('components', [])
    print(f"組件總數: {len(components)}\n")

    # 按類型分組
    by_type = {}
    for c in components:
        t = c.get('type', 'Unknown')
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(c)

    print("組件類型統計:")
    for t, comps in sorted(by_type.items()):
        print(f"  {t}: {len(comps)}")

    # 找 Orient 組件
    print("\n" + "=" * 50)
    print("Orient 組件詳情:")
    print("=" * 50)

    orients = [c for c in components if 'Orient' in c.get('type', '')]

    for o in orients:
        comp_id = o.get('id')
        print(f"\n組件 ID: {comp_id}")
        print(f"  類型: {o.get('type')}")
        print(f"  位置: ({o.get('x')}, {o.get('y')})")

        # 獲取詳細信息
        info = cmd('get_component_info', {'id': comp_id})
        if info.get('success'):
            d = info.get('data', {})
            inputs = d.get('inputs', [])
            outputs = d.get('outputs', [])

            print(f"  輸入參數:")
            for inp in inputs:
                name = inp.get('name', inp.get('nickname', '?'))
                source_count = inp.get('sourceCount', 0)
                connected = "✓ 已連接" if source_count > 0 else "✗ 未連接"
                print(f"    - {name}: {connected} (sources: {source_count})")

            print(f"  輸出參數:")
            for out in outputs:
                name = out.get('name', out.get('nickname', '?'))
                print(f"    - {name}")
        else:
            print(f"  ✗ 無法獲取詳情: {info.get('error')}")

    # 檢查 Center Box
    print("\n" + "=" * 50)
    print("Center Box 組件:")
    print("=" * 50)

    boxes = [c for c in components if 'Center Box' in c.get('type', '') or 'Box' in c.get('type', '')]

    for b in boxes:
        comp_id = b.get('id')
        print(f"\n組件 ID: {comp_id}")
        print(f"  類型: {b.get('type')}")

        info = cmd('get_component_info', {'id': comp_id})
        if info.get('success'):
            d = info.get('data', {})
            inputs = d.get('inputs', [])

            print(f"  輸入參數連接狀態:")
            for inp in inputs:
                name = inp.get('name', inp.get('nickname', '?'))
                source_count = inp.get('sourceCount', 0)
                connected = "✓" if source_count > 0 else "✗"
                print(f"    {connected} {name}: {source_count} sources")

    # 檢查是否有多餘組件
    print("\n" + "=" * 50)
    print("潛在問題:")
    print("=" * 50)

    # 檢查是否有未連接的輸入
    unconnected = []
    for c in components:
        comp_id = c.get('id')
        info = cmd('get_component_info', {'id': comp_id})
        if info.get('success'):
            for inp in info.get('data', {}).get('inputs', []):
                if inp.get('sourceCount', 0) == 0:
                    name = inp.get('name', '?')
                    # 排除 Slider 的輸入（它們是初始值）
                    if 'Slider' not in c.get('type', ''):
                        unconnected.append(f"{c.get('type')} [{comp_id[:8]}]: {name}")

    if unconnected:
        print(f"\n未連接的輸入 (前 10 個):")
        for item in unconnected[:10]:
            print(f"  - {item}")
    else:
        print("\n所有必要輸入都已連接")


if __name__ == '__main__':
    main()
