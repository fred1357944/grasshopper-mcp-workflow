#!/usr/bin/env python3
"""
簡單連接測試 - 驗證 GH_MCP v2.0 連接功能
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
    print("=" * 70)
    print("GH_MCP v2.0 簡單連接測試")
    print("=" * 70)

    # 1. 清空 canvas
    print("\n[1] 清空 Canvas...")
    r = cmd('clear_document')
    print(f"    結果: {r.get('success')}")
    time.sleep(0.3)

    # 2. 創建 XY Plane
    print("\n[2] 創建 XY Plane...")
    r = cmd('add_component', {'type': 'XY Plane', 'x': 100, 'y': 100})
    if not r.get('success'):
        print(f"    ✗ 失敗: {r}")
        return
    plane_id = r.get('data', {}).get('componentId') or r.get('data', {}).get('id')
    print(f"    ✓ ID: {plane_id}")

    # 3. 創建 Orient
    print("\n[3] 創建 Orient...")
    r = cmd('add_component', {'type': 'Orient', 'x': 300, 'y': 100})
    if not r.get('success'):
        print(f"    ✗ 失敗: {r}")
        return
    orient_id = r.get('data', {}).get('componentId') or r.get('data', {}).get('id')
    print(f"    ✓ ID: {orient_id}")

    # 4. 測試連接 - 使用 Name ("Source")
    print("\n[4] 測試連接: XY Plane → Orient.Source (用 Name)...")
    r = cmd('connect_components', {
        'sourceId': plane_id,
        'targetId': orient_id,
        'sourceParam': 'Plane',
        'targetParam': 'Source'
    })
    print(f"    API 回應: {json.dumps(r, indent=6)}")

    # 5. 驗證連接狀態
    print("\n[5] 驗證 Orient 連接狀態...")
    info = cmd('get_component_info', {'id': orient_id})
    if info.get('success'):
        inputs = info['data'].get('inputs', [])
        for inp in inputs:
            sources = inp.get('sources', [])
            if sources:
                status = f"✓ 已連接 ({sources[0].get('componentName', '?')})"
            else:
                status = "✗ 未連接"
            print(f"    {inp.get('name'):15} ({inp.get('nickname')}): {status}")
    else:
        print(f"    ✗ 查詢失敗: {info.get('error')}")

    # 6. 測試用 NickName ("A")
    print("\n[6] 測試連接: XY Plane → Orient.A (用 NickName)...")
    r = cmd('connect_components', {
        'sourceId': plane_id,
        'targetId': orient_id,
        'sourceParam': 'Plane',
        'targetParam': 'A'
    })
    print(f"    API 回應: {json.dumps(r, indent=6)}")

    # 7. 再次驗證
    print("\n[7] 再次驗證 Orient 連接狀態...")
    info = cmd('get_component_info', {'id': orient_id})
    if info.get('success'):
        inputs = info['data'].get('inputs', [])
        for inp in inputs:
            sources = inp.get('sources', [])
            if sources:
                status = f"✓ 已連接 ({sources[0].get('componentName', '?')})"
            else:
                status = "✗ 未連接"
            print(f"    {inp.get('name'):15} ({inp.get('nickname')}): {status}")

    print("\n" + "=" * 70)
    print("測試完成")
    print("=" * 70)


if __name__ == '__main__':
    main()
