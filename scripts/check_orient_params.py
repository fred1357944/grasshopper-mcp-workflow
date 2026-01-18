#!/usr/bin/env python3
"""
檢查 Orient 組件的實際參數名稱
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
    print("檢查 Orient 組件參數名稱")
    print("=" * 70)

    # 獲取所有組件
    r = cmd('get_document_info')
    if not r.get('success'):
        print(f"✗ 連接失敗: {r.get('error')}")
        return

    components = r.get('data', {}).get('components', [])

    # 找出 Orient 組件
    orients = [c for c in components if 'Orient' in c.get('name', '')]

    if not orients:
        print("找不到 Orient 組件，嘗試創建一個...")
        r = cmd('add_component', {'type': 'Orient', 'x': 100, 'y': 100})
        if r.get('success'):
            orient_id = r.get('data', {}).get('componentId') or r.get('data', {}).get('id')
            print(f"✓ 創建 Orient: {orient_id}")
        else:
            print(f"✗ 創建失敗: {r}")
            return

        # 重新獲取
        r = cmd('get_document_info')
        components = r.get('data', {}).get('components', [])
        orients = [c for c in components if 'Orient' in c.get('name', '')]

    # 顯示每個 Orient 的參數詳情
    for orient in orients[:1]:  # 只檢查第一個
        print(f"\n📦 Orient 組件")
        print(f"   ID: {orient.get('id')}")
        print(f"   Name: {orient.get('name')}")
        print(f"   NickName: {orient.get('nickname')}")

        # 獲取詳細資訊
        info = cmd('get_component_info', {'id': orient.get('id')})
        if info.get('success'):
            data = info['data']

            print("\n   輸入參數 (Inputs):")
            for inp in data.get('inputs', []):
                print(f"      Name: {inp.get('name'):<15} NickName: {inp.get('nickname'):<5}")

            print("\n   輸出參數 (Outputs):")
            for out in data.get('outputs', []):
                print(f"      Name: {out.get('name'):<15} NickName: {out.get('nickname'):<5}")

    # 測試連接
    print("\n" + "=" * 70)
    print("測試連接 Orient 組件")
    print("=" * 70)

    if orients:
        orient = orients[0]

        # 創建測試 XY Plane
        print("\n1. 創建測試 XY Plane...")
        r = cmd('add_component', {'type': 'XY Plane', 'x': 0, 'y': 100})
        if r.get('success'):
            plane_id = r.get('data', {}).get('componentId') or r.get('data', {}).get('id')
            print(f"   ✓ Plane ID: {plane_id}")

            # 嘗試不同的參數名連接到 Orient 的 Source
            print("\n2. 測試連接 Plane → Orient.Source...")

            # 測試 1: 用 "Source"
            print("   嘗試 targetParam='Source'...")
            r1 = cmd('connect_components', {
                'sourceId': plane_id,
                'targetId': orient.get('id'),
                'sourceParam': 'Plane',
                'targetParam': 'Source'
            })
            print(f"      結果: success={r1.get('success')}, data={r1.get('data')}")

            # 測試 2: 用 "A" (NickName)
            print("   嘗試 targetParam='A'...")
            r2 = cmd('connect_components', {
                'sourceId': plane_id,
                'targetId': orient.get('id'),
                'sourceParam': 'Plane',
                'targetParam': 'A'
            })
            print(f"      結果: success={r2.get('success')}, data={r2.get('data')}")

            # 驗證連接狀態
            print("\n3. 驗證連接狀態...")
            info = cmd('get_component_info', {'id': orient.get('id')})
            if info.get('success'):
                inputs = info['data'].get('inputs', [])
                for inp in inputs:
                    sources = inp.get('sources', [])
                    status = f"已連接 ({len(sources)} 源)" if sources else "未連接"
                    print(f"   {inp.get('name')} ({inp.get('nickname')}): {status}")


if __name__ == '__main__':
    main()
