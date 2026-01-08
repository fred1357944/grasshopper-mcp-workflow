#!/usr/bin/env python3
"""測試 GH_MCP connect_components 修復"""

import socket
import json
import time

def send_cmd(cmd_type, **params):
    command = {'type': cmd_type, 'parameters': params}
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('127.0.0.1', 8080))
            s.sendall(json.dumps(command).encode('utf-8'))
            s.shutdown(socket.SHUT_WR)
            response = b''
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
            return json.loads(response.decode('utf-8-sig'))
    except Exception as e:
        return {'error': str(e)}

print("=== 測試 GH_MCP 連線功能 ===")
print()

# 1. 清空文檔
print("1. 清空文檔...")
send_cmd('clear_document')
time.sleep(0.5)

# 2. 創建 Slider
print("2. 創建 Number Slider...")
r1 = send_cmd('add_component', type='Number Slider', x=100, y=100, nickname='TestSlider')
slider_id = r1.get('data', {}).get('id')
print(f"   Slider ID: {slider_id}")

# 3. 創建 Center Box
print("3. 創建 Center Box...")
r2 = send_cmd('add_component', guid='8e22f9f3-c5eb-4298-9e5b-7412e3025516', x=350, y=100, nickname='TestBox')
print(f"   Response: {r2}")
box_id = r2.get('data', {}).get('id') if r2 else None
print(f"   Box ID: {box_id}")

time.sleep(0.3)

# 4. 連接
print("4. 連接 Slider -> Box.X...")
r3 = send_cmd('connect_components',
    sourceId=slider_id,
    targetId=box_id,
    targetParam='X'
)

# 解析結果
if r3.get('success'):
    data = r3.get('data', {})
    inner = data.get('data', {}) if isinstance(data, dict) else {}
    print(f"   結果: {inner.get('message', data.get('message', 'unknown'))}")
    print(f"   驗證: {inner.get('verified', 'N/A')}")
else:
    print(f"   錯誤: {r3.get('error')}")

print()
print("=== 請檢查 Grasshopper 畫布 ===")
print("Slider 和 Center Box 之間應該有連線！")
print()
print("如果沒有連線，請檢查 Rhino 命令行窗口的 [GH_MCP] 日誌")
