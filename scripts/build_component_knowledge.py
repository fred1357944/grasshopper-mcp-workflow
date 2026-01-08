#!/usr/bin/env python3
"""
建立 GH 組件知識庫 - 一次性查詢所有常用組件
避免每次碰到問題才查詢，浪費 token
"""

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

# 常用組件類別
COMPONENT_QUERIES = [
    # 基礎輸入
    'Number Slider', 'Panel', 'Boolean Toggle', 'Value List',
    # 幾何 - Primitive
    'Center Box', 'Box', 'Sphere', 'Cylinder', 'Cone', 'Plane',
    # 幾何 - Point
    'Point', 'Construct Point', 'Deconstruct Point',
    # 平面
    'XY Plane', 'XZ Plane', 'YZ Plane', 'Construct Plane',
    # 向量
    'Unit X', 'Unit Y', 'Unit Z', 'Vector XYZ', 'Amplitude',
    # 變形
    'Move', 'Rotate', 'Scale', 'Mirror', 'Orient',
    # 數學
    'Addition', 'Subtraction', 'Multiplication', 'Division',
    'Average', 'Mass Addition', 'Absolute',
    # 集合/樹
    'Merge', 'Merge Multiple', 'Entwine', 'Flatten', 'Graft',
    'List Item', 'List Length', 'Reverse List',
    # 曲線
    'Line', 'Polyline', 'Circle', 'Arc', 'Rectangle',
    'Interpolate', 'Nurbs Curve',
    # 曲面
    'Loft', 'Extrude', 'Sweep', 'Boundary Surface',
    # Brep
    'Brep Join', 'Cap Holes', 'Solid Union', 'Solid Difference',
    # 顯示
    'Custom Preview', 'Colour Swatch',
]

print("=" * 70)
print("建立 GH 組件知識庫")
print("=" * 70)

knowledge = {}

for query in COMPONENT_QUERIES:
    result = send_cmd('get_component_candidates', name=query, limit=5)
    if result.get('success'):
        candidates = result.get('data', {}).get('candidates', [])
        # 過濾掉 obsolete 和第三方插件
        for c in candidates:
            if not c.get('obsolete'):
                lib = c.get('library', '')
                # 優先選擇內建組件
                is_builtin = lib in ['Grasshopper', 'MathComponents', 'SurfaceComponents', 
                                     'CurveComponents', 'FieldComponents', 'VectorComponents',
                                     'IntersectComponents', 'TransformComponents', 'TriangulationComponents']
                
                key = c['name']
                if key not in knowledge or is_builtin:
                    knowledge[key] = {
                        'guid': c['guid'],
                        'fullName': c.get('fullName', c['name']),
                        'category': c.get('category', ''),
                        'subCategory': c.get('subCategory', ''),
                        'library': lib,
                        'typeName': c.get('typeName', ''),
                        'inputs': [{'name': i['name'], 'nickname': i['nickname']} 
                                   for i in c.get('inputs', [])],
                        'outputs': [{'name': o['name'], 'nickname': o['nickname']} 
                                    for o in c.get('outputs', [])],
                    }
                    if is_builtin:
                        break
    time.sleep(0.05)  # 避免過快請求

# 保存知識庫
output_path = 'GH_WIP/component_knowledge.json'
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(knowledge, f, indent=2, ensure_ascii=False)

print(f"\n✅ 已保存 {len(knowledge)} 個組件到 {output_path}")
print("\n組件列表:")
for name, info in sorted(knowledge.items()):
    inputs = ', '.join([i['nickname'] for i in info['inputs'][:3]])
    outputs = ', '.join([o['nickname'] for o in info['outputs'][:2]])
    print(f"  {name}: [{inputs}] -> [{outputs}]")
