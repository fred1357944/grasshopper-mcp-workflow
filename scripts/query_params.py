#!/usr/bin/env python3
"""查詢組件參數名"""
import socket, json, time

def cmd(cmd_type, params=None):
    s = socket.socket()
    s.settimeout(10)
    s.connect(('127.0.0.1', 8080))
    c = {'type': cmd_type}
    if params: c['parameters'] = params
    s.sendall((json.dumps(c) + '\n').encode())
    time.sleep(0.3)
    chunks = []
    while True:
        try:
            chunk = s.recv(8192)
            if not chunk: break
            chunks.append(chunk)
            if b'\n' in chunk: break
        except: break
    s.close()
    return json.loads(b''.join(chunks).decode('utf-8-sig').strip())

# 獲取 Canvas 組件
r = cmd('get_document_info')
components = r.get('data', {}).get('components', [])

# 查詢特定類型組件
target_types = ['Division', 'Addition', 'Merge', 'Construct', 'Preview']
seen = set()

for c in components:
    comp_type = c.get('type', '')
    for t in target_types:
        if t in comp_type and t not in seen:
            seen.add(t)
            comp_id = c.get('id')
            info = cmd('get_component_info', {'id': comp_id})
            if info.get('success'):
                d = info.get('data', {})
                print(f"\n=== {comp_type} ===")
                print(f"輸入: {[i.get('name', i.get('nickname')) for i in d.get('inputs', [])]}")
                print(f"輸出: {[o.get('name', o.get('nickname')) for o in d.get('outputs', [])]}")
