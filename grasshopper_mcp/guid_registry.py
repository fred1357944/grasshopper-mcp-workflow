#!/usr/bin/env python3
"""
GH_MCP GUID Registry - 可信組件 GUID 註冊表

核心理念：
1. 運行時查詢 + 本地快取 = 可靠的 GUID 獲取
2. 多組件同名時，用 category 區分
3. 快取失效時自動重新查詢

使用方式：
```python
registry = GUIDRegistry()

# 獲取正確的 Line 組件 GUID (Curve 類別，不是 Params)
guid = registry.get_guid("Line", category="Curve")

# 創建組件時使用 GUID
client.add_component(guid=guid, nickname="MyLine", x=100, y=100)
```

2026-01-23
"""

import socket
import json
import time
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ComponentEntry:
    """組件註冊條目"""
    name: str
    guid: str
    category: str
    subcategory: str
    inputs: List[str]
    outputs: List[str]
    is_obsolete: bool
    queried_at: str  # ISO format


class GUIDRegistry:
    """
    可信 GUID 註冊表

    特點：
    1. 本地快取 + 運行時查詢
    2. 支援 category 區分同名組件
    3. 自動過濾 OBSOLETE 組件
    4. 參數名一起快取
    """

    # 預設快取路徑
    DEFAULT_CACHE_PATH = Path(__file__).parent / "guid_cache.json"

    # 常見衝突組件的正確 category
    PREFERRED_CATEGORIES = {
        "Line": "Curve",           # Curve/Primitive，不是 Params/Input
        "Circle": "Curve",
        "Point": "Vector",         # Vector/Point，不是 Params
        "Plane": "Vector",
        "Number": "Params",        # Params/Input/Number
        "Panel": "Params",
    }

    # 預載入的可信 GUID（手動驗證過的）
    VERIFIED_GUIDS = {
        # 基礎幾何 (Curve 類別)
        ("Line", "Curve"): "31957fba-b08b-45f9-9ec0-5f9e52d3236b",
        ("Circle", "Curve"): "55c7e69f-2c48-4c32-91d0-2d46e9f98a4d",
        ("Line SDL", "Curve"): "834dbb21-1c30-4be5-8e38-b7330e2c9d37",

        # 數學 (Maths 類別)
        ("Division", "Maths"): "b16a2ec0-f873-4ef7-8e0c-a068e7571cb4",
        ("Subtraction", "Maths"): "0ff0bb57-8207-48a0-a732-6fd4d4931193",
        ("Multiplication", "Maths"): "ba265c5c-ea9a-43f0-a35d-0d93e9ea5041",
        ("Addition", "Maths"): "13975a0f-0f14-4b3d-a2a8-7f40bf7b0637",
        ("Negative", "Maths"): "5ef3b98f-0d72-414d-b58f-a9fe3c7dd8cf",
        ("Series", "Sets"): "651c4fa5-dff4-4be6-ba31-6dc267d3ab47",

        # 向量/點 (Vector 類別)
        ("Construct Point", "Vector"): "3581f42a-9592-4549-bd6b-1c0fc39d067b",
        ("XY Plane", "Vector"): "5df6a8c1-de5e-4841-8089-41a95c741c5a",
        ("Unit Z", "Vector"): "654f8c62-3227-420f-9c6d-3b41a0736fe5",

        # 幾何基元 (Surface 類別)
        ("Center Box", "Surface"): "d1296e28-f64c-4c2a-9a9e-49e7839460de",
        ("Cylinder", "Surface"): "4edaf2ed-7b3a-42ed-bce0-3119ed106792",
        ("Sphere", "Surface"): "69f7ba53-d6bf-4c4d-8f1a-0a3a86a7a5b1",
        ("Pipe", "Surface"): "1ee25749-2e2d-4fc6-9209-0ea0515081f9",

        # 參數輸入 (Params 類別)
        ("Number Slider", "Params"): "57da07bd-ecab-415d-9d86-af36d7073abc",
        ("Panel", "Params"): "59e0b89a-e487-49f8-bab8-b5bab16be14c",
        ("Boolean Toggle", "Params"): "2e78987b-9dfb-42a2-8b76-3923ac8bd91a",
        ("Button", "Params"): "a8b97322-2d53-47cd-905e-b932c3ccd74e",
        ("Colour Swatch", "Params"): "9c53bac0-ba66-40bd-8154-ce9829b9db1a",

        # 參數容器 (Params/Geometry) - 注意：與 Vector 類別的 Point 不同
        ("Point", "Params"): "fbac3e32-f100-4292-8692-77240a42fd1a",
        ("Curve", "Params"): "d5967b9f-e8ee-436b-a8ad-29fdcecf32d5",
        ("Brep", "Params"): "919e146f-30ae-4aae-be34-4d72f555e7da",
        ("Geometry", "Params"): "ac2bc2cb-70fb-4dd5-9c78-7e1ea97fe278",

        # 視覺/顯示 (Display 類別)
        ("Colour", "Display"): "6da9f120-3ad0-4b6e-9fe0-f8cde3a649b7",
        ("Material", "Display"): "537b0419-bbc2-4ff4-bf08-afe526367b2c",

        # 數學/Domain
        ("Domain", "Maths"): "f44b92b0-3b5b-493a-86f4-99a982f48eb7",
        ("Graph Mapper", "Maths"): "bc984576-7aa6-491f-a91d-05aa6c91bf08",

        # 向量 (從 WASP 學習)
        ("Unit vector", "Vector"): "d3d195ea-2d59-4ffa-90b1-fe7ce8f43e2c",
        ("Centroid", "Surface"): "2e205f24-9279-47b2-b414-8a43f8b68fc5",

        # 清單操作
        ("List Length", "Sets"): "1817fd29-20ae-4503-b542-f0fb651e67d7",

        # ========== Kangaroo 物理模擬 (從 84 個 .ghx 範例學習) ==========

        # Kangaroo Goals
        ("Spring", "Kangaroo"): "091bae84-8fa9-4b35-8aad-b25b859055f6",
        ("Grab", "Kangaroo"): "3d13a415-6ac5-4b59-9677-3975e4696a85",
        ("Anchor", "Kangaroo"): "e8c7b9f3-5a2c-4d1e-8f3a-2b9c7d4e6a1f",  # Placeholder

        # Kangaroo Solver (注意：有多個版本)
        ("Zombie Solver", "Kangaroo"): "8f9f19c0-207a-419d-90f6-2fcadaa845f9",  # O 組件
        ("Bouncy Solver", "Kangaroo"): "313490f5-8e38-4dde-9e9a-05e4d739b35d",  # 另一個 O

        # Kangaroo Utilities
        ("Goal Debugger", "Kangaroo"): "0ed5e67d-539d-480e-88cb-d81fa795d66c",  # G 組件

        # Mesh 操作 (常用於 Kangaroo)
        ("Mesh", "Params"): "1e936df3-0eea-4246-8549-514cb8862b7a",
        ("Non-Manifold Edges", "Mesh"): "2b9bf01d-5fe5-464c-b0b3-b469eb5f2efb",
        ("Mesh Normals", "Mesh"): "ba2d8f57-0738-42b4-b5a5-fe4d853517eb",
        ("Mesh Vertices", "Mesh"): "afb96615-c59a-45c9-9cac-e27acb1c7ca0",

        # 輔助元件
        ("Item", "Sets"): "59daf374-bc21-4a5e-8282-5504fb7ae9ae",
        ("Scribble", "Params"): "7f5c6c55-f846-4a08-9c9a-cfdc285cc6fe",
        ("Data", "Params"): "8ec86459-bf01-4409-baee-174d0d2b13d0",
    }

    # 參數名映射（組件 GUID → 輸入/輸出參數名）
    PARAM_NAMES = {
        "31957fba-b08b-45f9-9ec0-5f9e52d3236b": {  # Line
            "inputs": ["Start Point", "End Point"],
            "outputs": ["Line"],
        },
        "5df6a8c1-de5e-4841-8089-41a95c741c5a": {  # XY Plane
            "inputs": ["Origin"],
            "outputs": ["Plane"],
        },
        "d1296e28-f64c-4c2a-9a9e-49e7839460de": {  # Center Box
            "inputs": ["Base", "X", "Y", "Z"],
            "outputs": ["Box"],
        },
        "b16a2ec0-f873-4ef7-8e0c-a068e7571cb4": {  # Division
            "inputs": ["A", "B"],
            "outputs": ["Result"],
        },
        "0ff0bb57-8207-48a0-a732-6fd4d4931193": {  # Subtraction
            "inputs": ["A", "B"],
            "outputs": ["Result"],
        },
        "3581f42a-9592-4549-bd6b-1c0fc39d067b": {  # Construct Point
            "inputs": ["X coordinate", "Y coordinate", "Z coordinate"],
            "outputs": ["Point"],
        },
        "651c4fa5-dff4-4be6-ba31-6dc267d3ab47": {  # Series
            "inputs": ["Start", "Step", "Count"],
            "outputs": ["Series"],
        },
        "4edaf2ed-7b3a-42ed-bce0-3119ed106792": {  # Cylinder
            "inputs": ["Base", "Radius", "Length"],
            "outputs": ["Cylinder"],
        },
        "1ee25749-2e2d-4fc6-9209-0ea0515081f9": {  # Pipe
            "inputs": ["Curve", "Radius", "Caps", "Fit Rail"],
            "outputs": ["Pipe"],
        },

        # ========== Kangaroo 組件參數 ==========
        "091bae84-8fa9-4b35-8aad-b25b859055f6": {  # Spring
            "inputs": ["Line", "Length", "Strength"],
            "outputs": ["Spring"],
        },
        "3d13a415-6ac5-4b59-9677-3975e4696a85": {  # Grab
            "inputs": ["On", "Strength", "Range"],
            "outputs": ["Grab"],
        },
        "8f9f19c0-207a-419d-90f6-2fcadaa845f9": {  # Zombie Solver (O)
            "inputs": ["GoalObjects", "Reset", "Threshold"],
            "outputs": ["I", "V", "O"],
        },
        "2b9bf01d-5fe5-464c-b0b3-b469eb5f2efb": {  # Non-Manifold Edges
            "inputs": ["Mesh"],
            "outputs": ["Naked Edges", "Interior Edges", "Non-Manifold Edges"],
        },
        "ba2d8f57-0738-42b4-b5a5-fe4d853517eb": {  # Mesh Normals
            "inputs": ["Mesh"],
            "outputs": ["Vertices", "Faces", "Colours"],
        },
    }

    def __init__(self, host: str = '127.0.0.1', port: int = 8080,
                 cache_path: Optional[Path] = None):
        self.host = host
        self.port = port
        self.cache_path = cache_path or self.DEFAULT_CACHE_PATH
        self._cache: Dict[Tuple[str, str], ComponentEntry] = {}
        self._load_cache()

    def _send_command(self, cmd_type: str, **params) -> dict:
        """發送命令到 GH_MCP"""
        command = {'type': cmd_type, 'parameters': params}
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((self.host, self.port))
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

    def _load_cache(self):
        """載入本地快取"""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key_str, entry_dict in data.items():
                        # key_str 格式: "Line|Curve"
                        parts = key_str.split('|')
                        if len(parts) == 2:
                            key = (parts[0], parts[1])
                            self._cache[key] = ComponentEntry(**entry_dict)
            except Exception:
                pass  # 快取損壞，忽略

    def _save_cache(self):
        """保存快取到本地"""
        data = {}
        for (name, cat), entry in self._cache.items():
            key_str = f"{name}|{cat}"
            data[key_str] = asdict(entry)

        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_guid(self, name: str, category: Optional[str] = None) -> Optional[str]:
        """
        獲取組件的可信 GUID

        優先順序：
        1. VERIFIED_GUIDS (手動驗證過的)
        2. 本地快取
        3. 運行時查詢 GH_MCP

        Args:
            name: 組件名稱 (e.g., "Line", "Division")
            category: 組件類別 (e.g., "Curve", "Maths")，用於區分同名組件

        Returns:
            GUID 字串，或 None
        """
        # 1. 自動決定 category
        if category is None:
            category = self.PREFERRED_CATEGORIES.get(name, "")

        key = (name, category)

        # 2. 檢查 VERIFIED_GUIDS
        if key in self.VERIFIED_GUIDS:
            return self.VERIFIED_GUIDS[key]

        # 3. 檢查本地快取
        if key in self._cache:
            return self._cache[key].guid

        # 4. 運行時查詢
        return self._query_and_cache(name, category)

    def _query_and_cache(self, name: str, category: str) -> Optional[str]:
        """查詢 GH_MCP 並快取結果"""
        result = self._send_command('get_component_candidates', name=name)

        if not result.get('success'):
            return None

        candidates = result.get('data', {}).get('candidates', [])

        # 過濾：非 OBSOLETE + 匹配 category
        best_match = None
        for c in candidates:
            if c.get('isObsolete'):
                continue

            c_category = c.get('category', '')

            # 如果指定了 category，必須匹配
            if category and category.lower() not in c_category.lower():
                continue

            # 名稱精確匹配優先
            if c.get('name') == name or c.get('nickName') == name:
                best_match = c
                break

        if not best_match:
            # 退而求其次：取第一個非 OBSOLETE 的
            for c in candidates:
                if not c.get('isObsolete'):
                    best_match = c
                    break

        if best_match:
            entry = ComponentEntry(
                name=best_match.get('name', name),
                guid=best_match.get('guid'),
                category=best_match.get('category', ''),
                subcategory=best_match.get('subcategory', ''),
                inputs=[p.get('name') for p in best_match.get('inputs', [])],
                outputs=[p.get('name') for p in best_match.get('outputs', [])],
                is_obsolete=best_match.get('isObsolete', False),
                queried_at=datetime.now().isoformat()
            )

            key = (name, category or entry.category)
            self._cache[key] = entry
            self._save_cache()

            return entry.guid

        return None

    def get_params(self, guid: str) -> Optional[Dict]:
        """
        獲取組件的參數名

        Returns:
            {
                "inputs": ["Start Point", "End Point"],
                "outputs": ["Line"]
            }
        """
        # 1. 檢查 PARAM_NAMES
        if guid in self.PARAM_NAMES:
            return self.PARAM_NAMES[guid]

        # 2. 從快取中查找
        for entry in self._cache.values():
            if entry.guid == guid:
                return {
                    "inputs": entry.inputs,
                    "outputs": entry.outputs
                }

        return None

    def validate_placement_info(self, placement_info: Dict) -> List[Dict]:
        """
        驗證 placement_info.json 中的 GUID 和參數名

        Returns:
            問題列表
        """
        issues = []
        components = placement_info.get('components', [])
        connections = placement_info.get('connections', [])

        # 建立組件 ID → 類型映射
        id_to_type = {}
        for comp in components:
            comp_id = comp.get('id')
            comp_type = comp.get('type')
            comp_guid = comp.get('guid')
            id_to_type[comp_id] = (comp_type, comp_guid)

            # 檢查 GUID 是否在可信列表中
            if comp_guid:
                category = self.PREFERRED_CATEGORIES.get(comp_type, "")
                verified_guid = self.VERIFIED_GUIDS.get((comp_type, category))

                if verified_guid and comp_guid != verified_guid:
                    issues.append({
                        'type': 'guid_mismatch',
                        'component_id': comp_id,
                        'component_type': comp_type,
                        'current_guid': comp_guid,
                        'verified_guid': verified_guid,
                        'message': f"{comp_type} GUID 可能錯誤，建議使用 {verified_guid[:16]}..."
                    })

        # 檢查連接參數名
        for conn in connections:
            from_id = conn.get('from')
            to_id = conn.get('to')
            from_param = conn.get('fromParam')
            to_param = conn.get('toParam')

            # 獲取組件的已知參數名
            if from_id in id_to_type:
                _, from_guid = id_to_type[from_id]
                if from_guid:
                    params = self.get_params(from_guid)
                    if params and from_param not in params.get('outputs', []):
                        # 檢查是否是縮寫
                        outputs = params.get('outputs', [])
                        if outputs and from_param not in outputs:
                            issues.append({
                                'type': 'param_warning',
                                'connection': f"{from_id}.{from_param}",
                                'expected_outputs': outputs,
                                'message': f"輸出參數 '{from_param}' 可能應為 {outputs}"
                            })

            if to_id in id_to_type:
                _, to_guid = id_to_type[to_id]
                if to_guid:
                    params = self.get_params(to_guid)
                    if params and to_param not in params.get('inputs', []):
                        inputs = params.get('inputs', [])
                        if inputs and to_param not in inputs:
                            issues.append({
                                'type': 'param_warning',
                                'connection': f"{to_id}.{to_param}",
                                'expected_inputs': inputs,
                                'message': f"輸入參數 '{to_param}' 可能應為 {inputs}"
                            })

        return issues

    def auto_fix_placement_info(self, placement_info: Dict) -> Dict:
        """
        自動修正 placement_info.json

        1. 替換錯誤的 GUID
        2. 替換縮寫參數名為全名

        Returns:
            修正後的配置
        """
        import copy
        fixed = copy.deepcopy(placement_info)

        # 1. 修正組件 GUID
        for comp in fixed.get('components', []):
            comp_type = comp.get('type')
            category = self.PREFERRED_CATEGORIES.get(comp_type, "")
            verified_guid = self.VERIFIED_GUIDS.get((comp_type, category))

            if verified_guid:
                comp['guid'] = verified_guid

        # 2. 建立 ID → GUID 映射
        id_to_guid = {}
        for comp in fixed.get('components', []):
            id_to_guid[comp.get('id')] = comp.get('guid')

        # 3. 修正連接參數名
        PARAM_SHORTCUTS = {
            # 輸出參數縮寫 → 全名
            'R': 'Result',
            'Pt': 'Point',
            'L': 'Line',
            'P': 'Plane',
            'x': 'Result',
            'S': 'Series',
            # 輸入參數縮寫 → 全名
            'O': 'Origin',
            'B': 'Base',
            'C': 'Curve',
        }

        for conn in fixed.get('connections', []):
            from_id = conn.get('from')
            to_id = conn.get('to')
            from_param = conn.get('fromParam')
            to_param = conn.get('toParam')

            from_guid = id_to_guid.get(from_id)
            to_guid = id_to_guid.get(to_id)

            # 修正輸出參數
            if from_guid:
                params = self.get_params(from_guid)
                if params:
                    outputs = params.get('outputs', [])
                    if from_param not in outputs:
                        # 嘗試用縮寫映射
                        full_name = PARAM_SHORTCUTS.get(from_param)
                        if full_name and full_name in outputs:
                            conn['fromParam'] = full_name
                        elif len(outputs) == 1:
                            # 只有一個輸出，直接用
                            conn['fromParam'] = outputs[0]

            # 修正輸入參數
            if to_guid:
                params = self.get_params(to_guid)
                if params:
                    inputs = params.get('inputs', [])
                    if to_param not in inputs:
                        full_name = PARAM_SHORTCUTS.get(to_param)
                        if full_name and full_name in inputs:
                            conn['toParam'] = full_name

        return fixed


def validate_and_fix(placement_path: str, fix: bool = False) -> bool:
    """
    便捷函數：驗證並可選修正 placement_info.json

    Args:
        placement_path: 配置檔路徑
        fix: 是否自動修正

    Returns:
        是否通過驗證（或已修正）
    """
    with open(placement_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    registry = GUIDRegistry()
    issues = registry.validate_placement_info(config)

    if not issues:
        print("✅ 配置檔驗證通過，無問題")
        return True

    print(f"\n⚠️ 發現 {len(issues)} 個問題:\n")
    for issue in issues:
        print(f"  • [{issue['type']}] {issue['message']}")

    if fix:
        print("\n🔧 自動修正中...")
        fixed = registry.auto_fix_placement_info(config)

        with open(placement_path, 'w', encoding='utf-8') as f:
            json.dump(fixed, f, indent=2, ensure_ascii=False)

        print(f"✅ 已保存修正後的配置到 {placement_path}")
        return True

    return False


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        path = sys.argv[1]
        fix = '--fix' in sys.argv
        validate_and_fix(path, fix=fix)
    else:
        # 互動測試
        registry = GUIDRegistry()

        print("=== GUID Registry 測試 ===\n")

        tests = [
            ("Line", "Curve"),
            ("Line", "Params"),
            ("Division", "Maths"),
            ("XY Plane", "Vector"),
            ("Construct Point", "Vector"),
        ]

        for name, cat in tests:
            guid = registry.get_guid(name, cat)
            params = registry.get_params(guid) if guid else None
            print(f"{name} ({cat})")
            print(f"  GUID: {guid}")
            if params:
                print(f"  輸入: {params.get('inputs')}")
                print(f"  輸出: {params.get('outputs')}")
            print()
