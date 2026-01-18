#!/usr/bin/env python3
"""
測試 Slider 修復腳本
驗證 GetParameter<double?> 是否能正確解析 JSON 整數
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

    msg = json.dumps(c) + '\n'
    s.sendall(msg.encode())

    # 等待並讀取完整回應
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
    except json.JSONDecodeError as e:
        return {'success': False, 'error': f'JSON decode error: {e}', 'raw': data[:200]}

def main():
    print('=== 測試 Slider 修復 ===\n')

    print('1. 清空文檔...')
    r = cmd('clear_document')
    print(f'   回應: {r}')

    if not r.get('success'):
        print(f'   警告: {r}')

    time.sleep(1)

    print('\n2. 創建 Number Slider...')
    # Number Slider GUID: e7fc11d2-13cc-4c77-9166-8722ae9b8405
    r = cmd('add_component', {
        'guid': 'e7fc11d2-13cc-4c77-9166-8722ae9b8405',
        'x': 100,
        'y': 100
    })
    print(f'   回應: {json.dumps(r, indent=2, ensure_ascii=False)}')

    if not r.get('success'):
        print(f'   ✗ 創建失敗')
        return

    sid = r['data']['id']
    print(f'   Slider ID: {sid}')

    time.sleep(0.5)

    print('\n3. 設置 min=5, max=100, value=70...')
    r = cmd('set_slider_properties', {'id': sid, 'min': 5, 'max': 100, 'value': '70'})
    print(f'   回應: {json.dumps(r, indent=2, ensure_ascii=False)}')

    time.sleep(0.5)

    print('\n4. 驗證設置結果...')
    info = cmd('get_component_info', {'id': sid})
    print(f'   回應: {json.dumps(info, indent=2, ensure_ascii=False)}')

    if info.get('success'):
        d = info['data']
        value = d.get('value', 'N/A')
        minimum = d.get('minimum', 'N/A')
        maximum = d.get('maximum', 'N/A')

        print(f'\n   === 結果 ===')
        print(f'   Value: {value}')
        print(f'   Min: {minimum}')
        print(f'   Max: {maximum}')

        # 判斷修復是否成功
        if minimum == 5.0 and maximum == 100.0 and value == 70.0:
            print('\n✓ Slider 修復驗證成功!')
        elif minimum is None or minimum == 0:
            print('\n✗ 修復失敗! min 仍為 None 或 0')
            print('  請確認已重新編譯並部署 GH_MCP.gha，且已重啟 Rhino')
        else:
            print(f'\n? 部分成功，請檢查數值')
    else:
        print(f'   ✗ 獲取信息失敗: {info}')

if __name__ == '__main__':
    main()
