#!/usr/bin/env python3
"""
使用 GUID 測試連接
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
    print("使用 GUID 測試 MCP")
    print("=" * 70)

    # 1. 查詢 XY Plane 的 GUID
    print("\n[1] 查詢 'XY Plane' 組件候選...")
    r = cmd('get_component_candidates', {'name': 'XY Plane'})
    print(f"    回應: {json.dumps(r, indent=4, ensure_ascii=False)[:500]}")

    if r.get('success') and r.get('data'):
        candidates = r['data']
        if isinstance(candidates, list) and len(candidates) > 0:
            # 找到第一個匹配的
            xy_plane = candidates[0]
            xy_guid = xy_plane.get('guid')
            print(f"\n    找到 XY Plane GUID: {xy_guid}")

    # 2. 查詢 Orient 的 GUID
    print("\n[2] 查詢 'Orient' 組件候選...")
    r = cmd('get_component_candidates', {'name': 'Orient'})
    print(f"    回應: {json.dumps(r, indent=4, ensure_ascii=False)[:500]}")

    # 3. 測試用舊的 add_component 格式
    print("\n[3] 測試用名稱添加組件 (舊格式)...")
    r = cmd('add_component', {'type': 'Number Slider', 'x': 100, 'y': 200})
    print(f"    回應: {json.dumps(r, indent=4, ensure_ascii=False)}")

    # 4. 查看可用命令
    print("\n[4] 查看可用命令...")
    r = cmd('get_available_commands')
    if r.get('success'):
        commands = r.get('data', {})
        if isinstance(commands, dict):
            print("    可用命令:")
            for name, info in commands.items():
                print(f"      - {name}")
        elif isinstance(commands, list):
            print("    可用命令:")
            for c in commands[:20]:
                print(f"      - {c}")
    else:
        print(f"    查詢失敗: {r}")


if __name__ == '__main__':
    main()
