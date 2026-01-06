"""
Test: 完整畫桌子流程測試

從 component_info.mmd 到 Grasshopper MCP 執行的端到端測試

測試流程：
1. 解析 component_info.mmd 提取組件和連接
2. 生成 placement_info.json
3. 連接 Grasshopper MCP 執行命令
4. 驗證執行結果
"""

import sys
import os
import re
import json
from pathlib import Path
from typing import Any

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from grasshopper_tools.client import GrasshopperClient
from grasshopper_tools.component_guids import COMPONENT_GUIDS, get_guid, search_components

# 組件名稱到 GUID 的映射（從 component_info.mmd 提取的 GUID 優先）
COMPONENT_TYPE_TO_GUID = {
    "Number Slider": "e2bb9b8d-0d80-44e7-aa2d-2e446f5c61da",
    "XY Plane": "a896f6c1-dd6c-4830-88f2-44808c07dc10",
    "Construct Point": "9dceff86-6201-4c8e-90b1-706ad5bc3d49",
    "Circle": "40dda121-a31b-421b-94b0-e46f5774f98e",
    "Rectangle": "9adebb98-f5c2-42da-8dfe-3bffbb7c12ca",
    "Boundary Surfaces": "9ec27fcf-b30f-4ad2-b2d1-c1934c32f855",
    "Extrude": "1c5e4c65-5f57-432c-96d3-53563470ab51",
    "Center Box": "e1f83fb4-efe0-4f10-8c20-4b38df56b36c",
    "Move": "6af48ec9-decb-4ad7-81ac-cd20452189a2",
    "Orient": "b08eae6f-0030-4f63-be06-9f1c7f89efd1",
    "Solid Union": "cabe86d9-6ef0-4037-90bd-01a02e0d30f0",
    "Unit Z": "9428ce3a-b2a0-4c8f-832a-8ad2b81a9743",
    "Amplitude": "7b93e28d-6191-425a-844e-6e9e4127dd6b",
    "Vector XYZ": "d3116726-7a3e-4089-b3e2-216b266a1245",
    "Division": "7ed9789a-7403-4eeb-9716-d6e5681f4136",
    "Average": "3e0451ca-da24-452d-a6b1-a6877453d4e4",
}

# 路徑設定
GH_WIP_DIR = Path("GH_WIP")
COMPONENT_INFO_PATH = GH_WIP_DIR / "component_info.mmd"
PLACEMENT_INFO_PATH = GH_WIP_DIR / "placement_info.json"


class MermaidParser:
    """解析 Mermaid flowchart 格式的 component_info.mmd"""

    def __init__(self, mmd_content: str):
        self.content = mmd_content
        self.components = {}  # id -> component_info
        self.connections = []  # [(source_id, target_id, param_name)]

    def parse(self) -> dict:
        """解析 Mermaid 內容，返回組件和連接"""
        self._parse_components()
        self._parse_connections()

        return {
            "components": self.components,
            "connections": self.connections
        }

    def _parse_components(self):
        """
        解析組件定義

        格式: ID["ComponentType<br/>...GUID: xxx-xxx...<br/>位置: X=n, Y=m"]
        """
        # 排除的模式（subgraph 標題、class 定義等）
        subgraph_ids = set()

        # 先找出所有 subgraph ID
        subgraph_pattern = r'subgraph\s+(\w+)\['
        for match in re.finditer(subgraph_pattern, self.content):
            subgraph_ids.add(match.group(1))

        # 匹配組件定義
        pattern = r'(\w+)\["([^"]+)"\]'

        for match in re.finditer(pattern, self.content):
            comp_id = match.group(1)
            comp_content = match.group(2)

            # 跳過 subgraph 標題
            if comp_id in subgraph_ids:
                continue

            # 跳過沒有 GUID 的節點（不是真正的 Grasshopper 組件）
            if "GUID:" not in comp_content:
                continue

            # 解析組件內容
            component = self._parse_component_content(comp_id, comp_content)
            if component:
                self.components[comp_id] = component

    def _parse_component_content(self, comp_id: str, content: str) -> dict | None:
        """解析組件內容字串"""
        # 分割 <br/> 標籤
        parts = content.split("<br/>")
        if not parts:
            return None

        # 第一部分是組件類型
        comp_type = parts[0].strip()

        # 解析其他屬性
        guid = None
        position = {"x": 0, "y": 0}
        value = None
        inputs = []
        outputs = []

        for part in parts[1:]:
            part = part.strip()

            # GUID
            if "GUID:" in part:
                guid_match = re.search(r'GUID:\s*([a-f0-9-]+)', part, re.IGNORECASE)
                if guid_match:
                    guid = guid_match.group(1)

            # 位置
            elif "位置:" in part or "位置:" in part:
                pos_match = re.search(r'X\s*=\s*(\d+).*Y\s*=\s*(\d+)', part)
                if pos_match:
                    position = {
                        "x": int(pos_match.group(1)),
                        "y": int(pos_match.group(2))
                    }

            # 輸出值 (如 Number Slider)
            elif "输出:" in part or "輸出:" in part:
                val_match = re.search(r'[输輸]出:\s*([-\d.]+)', part)
                if val_match:
                    try:
                        value = float(val_match.group(1))
                    except ValueError:
                        pass

            # 輸入參數
            elif "输入:" in part or "輸入:" in part:
                input_match = re.search(r'[输輸]入:\s*(.+)', part)
                if input_match:
                    inputs = [i.strip() for i in input_match.group(1).split(",")]

        return {
            "id": comp_id,
            "type": comp_type,
            "guid": guid,
            "position": position,
            "value": value,
            "inputs": inputs,
            "outputs": outputs
        }

    def _parse_connections(self):
        """
        解析連接定義

        格式: SOURCE -->|"ParamName"| TARGET
        或:   SOURCE --> TARGET
        """
        # 帶參數名的連接
        pattern_with_param = r'(\w+)\s*-->\|"([^"]+)"\|\s*(\w+)'
        # 無參數名的連接
        pattern_no_param = r'(\w+)\s*-->\s*(\w+)'

        # 先解析帶參數的
        for match in re.finditer(pattern_with_param, self.content):
            source_id = match.group(1)
            param_name = match.group(2)
            target_id = match.group(3)

            if source_id in self.components and target_id in self.components:
                self.connections.append({
                    "source_id": source_id,
                    "target_id": target_id,
                    "source_param": "output",  # 默認輸出
                    "target_param": param_name
                })


class PlacementInfoGenerator:
    """從解析結果生成 placement_info.json"""

    def __init__(self, parsed_data: dict):
        self.components = parsed_data["components"]
        self.connections = parsed_data["connections"]

    def generate(self) -> dict:
        """生成 placement_info.json 結構"""
        commands = []

        # 1. 按拓撲順序排列組件（按 Y 座標，再按 X 座標）
        sorted_components = sorted(
            self.components.values(),
            key=lambda c: (c["position"]["y"], c["position"]["x"])
        )

        # 2. 生成 add_component 命令
        for comp in sorted_components:
            cmd = self._create_add_command(comp)
            if cmd:
                commands.append(cmd)

        # 3. 生成 connect_components 命令
        for conn in self.connections:
            cmd = self._create_connect_command(conn)
            if cmd:
                commands.append(cmd)

        return {
            "description": "桌子設計 - 從 component_info.mmd 自動生成",
            "version": "1.0",
            "generated_from": "component_info.mmd",
            "commands": commands,
            "metadata": {
                "total_components": len([c for c in commands if c["type"] == "add_component"]),
                "total_connections": len([c for c in commands if c["type"] == "connect_components"])
            }
        }

    def _create_add_command(self, comp: dict) -> dict | None:
        """創建 add_component 命令

        Note: Grasshopper MCP 使用 `type` 參數（組件名稱），不是 `guid`
        """
        comp_type = comp["type"]

        return {
            "type": "add_component",
            "componentId": comp["id"],      # 用於 ID 映射
            "componentType": comp_type,     # 組件名稱（Grasshopper MCP 需要）
            "x": float(comp["position"]["x"]),
            "y": float(comp["position"]["y"]),
            "value": comp.get("value")      # Number Slider 的值
        }

    def _create_connect_command(self, conn: dict) -> dict:
        """創建 connect_components 命令"""
        return {
            "type": "connect_components",
            "comment": f"{conn['source_id']} -> {conn['target_id']}",
            "parameters": {
                "sourceId": conn["source_id"],  # 使用 componentId 作為映射鍵
                "targetId": conn["target_id"],
                "sourceParam": conn["source_param"],  # 輸出參數
                "targetParam": conn["target_param"]   # 輸入參數
            }
        }


def test_1_parse_component_info():
    """測試 1: 解析 component_info.mmd"""
    print("\n=== 測試 1: 解析 component_info.mmd ===")

    # 讀取檔案
    assert COMPONENT_INFO_PATH.exists(), f"找不到 {COMPONENT_INFO_PATH}"

    with open(COMPONENT_INFO_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 解析
    parser = MermaidParser(content)
    result = parser.parse()

    components = result["components"]
    connections = result["connections"]

    print(f"✓ 解析到 {len(components)} 個組件")
    print(f"✓ 解析到 {len(connections)} 個連接")

    # 驗證關鍵組件存在
    expected_components = [
        "CENTER_BOX_TOP",
        "EXTRUDE_LEG_BASE",
        "BOOLEAN_UNION",
        "SLIDER_WIDTH",
        "SLIDER_LENGTH"
    ]

    for comp in expected_components:
        assert comp in components, f"缺少關鍵組件: {comp}"

    print(f"✓ 關鍵組件驗證通過")

    # 顯示部分組件
    print("\n--- 部分組件預覽 ---")
    for comp_id, comp in list(components.items())[:5]:
        print(f"  {comp_id}: {comp['type']} @ ({comp['position']['x']}, {comp['position']['y']})")

    return result


def test_2_generate_placement_info(parsed_data: dict):
    """測試 2: 生成 placement_info.json"""
    print("\n=== 測試 2: 生成 placement_info.json ===")

    generator = PlacementInfoGenerator(parsed_data)
    placement_info = generator.generate()

    # 寫入檔案
    with open(PLACEMENT_INFO_PATH, "w", encoding="utf-8") as f:
        json.dump(placement_info, f, indent=2, ensure_ascii=False)

    print(f"✓ 已生成: {PLACEMENT_INFO_PATH}")

    # 統計
    add_commands = [c for c in placement_info["commands"] if c["type"] == "add_component"]
    connect_commands = [c for c in placement_info["commands"] if c["type"] == "connect_components"]

    print(f"✓ add_component 命令: {len(add_commands)} 個")
    print(f"✓ connect_components 命令: {len(connect_commands)} 個")

    # 驗證結構
    assert "commands" in placement_info, "缺少 commands 欄位"
    assert len(add_commands) > 0, "沒有 add_component 命令"

    # 顯示部分命令
    print("\n--- 部分命令預覽 ---")
    for cmd in add_commands[:3]:
        print(f"  add: {cmd['componentType']} -> {cmd['componentId']}")

    return placement_info


def test_3_check_mcp_connection():
    """測試 3: 檢查 Grasshopper MCP 連接"""
    print("\n=== 測試 3: 檢查 Grasshopper MCP 連接 ===")

    client = GrasshopperClient()

    # 發送 ping 或 get_document_info
    response = client.send_command("get_document_info")

    if response.get("success"):
        print("✓ Grasshopper MCP 連接成功")
        data = response.get("data", {})
        if isinstance(data, dict):
            print(f"  - 文檔: {data.get('name', 'Unknown')}")
            print(f"  - 組件數: {data.get('component_count', 'N/A')}")
        return True
    else:
        print(f"✗ Grasshopper MCP 連接失敗: {response.get('error', 'Unknown error')}")
        print("  請確保 Grasshopper 已開啟且 MCP Server 正在運行 (port 8080)")
        return False


def test_4_execute_subset(placement_info: dict, max_components: int = 5):
    """測試 4: 執行部分組件（驗證流程）"""
    print(f"\n=== 測試 4: 執行前 {max_components} 個組件 ===")

    client = GrasshopperClient()

    # 只取前幾個 add_component 命令
    add_commands = [c for c in placement_info["commands"] if c["type"] == "add_component"]
    test_commands = add_commands[:max_components]

    results = {
        "success": 0,
        "fail": 0,
        "id_map": {}
    }

    for cmd in test_commands:
        # 新格式: componentType, componentId, x, y
        comp_type = cmd["componentType"]
        comp_id = cmd["componentId"]
        x = cmd["x"]
        y = cmd["y"]
        value = cmd.get("value")

        # 構建 add_component 參數（使用 type 而非 guid）
        add_params = {
            "type": comp_type,  # Grasshopper MCP 需要 `type` 參數
            "x": x,
            "y": y
        }

        # 如果有值（如 Number Slider），添加值參數
        if value is not None:
            add_params["value"] = value

        print(f"  創建: {comp_type} -> {comp_id}...", end=" ")

        response = client.send_command("add_component", add_params)

        if response.get("success"):
            actual_id = client.extract_component_id(response)
            results["id_map"][comp_id] = actual_id
            results["success"] += 1
            print(f"✓ (ID: {actual_id[:8] if actual_id else 'N/A'}...)")
        else:
            results["fail"] += 1
            error = response.get("error", "Unknown")
            print(f"✗ ({error[:50]})")

    print(f"\n執行結果: 成功 {results['success']}/{len(test_commands)}, 失敗 {results['fail']}")

    return results


def test_5_execute_full(placement_info: dict):
    """測試 5: 執行完整 placement_info"""
    print("\n=== 測試 5: 執行完整 placement_info ===")

    from grasshopper_tools.placement_executor import PlacementExecutor

    # 先保存 placement_info 到檔案
    with open(PLACEMENT_INFO_PATH, "w", encoding="utf-8") as f:
        json.dump(placement_info, f, indent=2, ensure_ascii=False)

    executor = PlacementExecutor()
    result = executor.execute_placement_info(str(PLACEMENT_INFO_PATH))

    print(f"\n總結:")
    print(f"  組件創建: {result.get('add_success', 0)} 成功, {result.get('add_fail', 0)} 失敗")
    print(f"  組件連接: {result.get('connect_success', 0)} 成功, {result.get('connect_fail', 0)} 失敗")
    print(f"  總耗時: {result.get('total_time', 0):.2f} 秒")

    return result


def run_all_tests():
    """運行所有測試"""
    print("=" * 70)
    print("完整畫桌子流程測試")
    print("=" * 70)

    results = {}

    try:
        # 測試 1: 解析 Mermaid
        parsed_data = test_1_parse_component_info()
        results["test_1_parse"] = "PASS"

        # 測試 2: 生成 placement_info
        placement_info = test_2_generate_placement_info(parsed_data)
        results["test_2_generate"] = "PASS"

        # 測試 3: 檢查 MCP 連接
        mcp_connected = test_3_check_mcp_connection()
        results["test_3_connection"] = "PASS" if mcp_connected else "SKIP"

        if mcp_connected:
            # 測試 4: 執行部分組件
            subset_result = test_4_execute_subset(placement_info, max_components=5)
            results["test_4_subset"] = "PASS" if subset_result["success"] > 0 else "FAIL"

            # 詢問是否執行完整測試
            print("\n" + "-" * 70)
            print("部分測試完成。是否執行完整的 placement_info？")
            print("(這將在 Grasshopper 中創建所有桌子組件)")
            print("-" * 70)

            # 在自動測試模式下，跳過完整執行
            # user_input = input("輸入 'y' 繼續，其他跳過: ").strip().lower()
            # if user_input == 'y':
            #     full_result = test_5_execute_full(placement_info)
            #     results["test_5_full"] = "PASS" if full_result.get("success") else "FAIL"
            # else:
            results["test_5_full"] = "SKIP (manual)"
        else:
            results["test_4_subset"] = "SKIP"
            results["test_5_full"] = "SKIP"

    except AssertionError as e:
        print(f"\n✗ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        results["error"] = str(e)

    except Exception as e:
        print(f"\n✗ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        results["error"] = str(e)

    # 總結
    print("\n" + "=" * 70)
    print("測試總結")
    print("=" * 70)

    for test, result in results.items():
        status = "✓" if result == "PASS" else ("⊘" if "SKIP" in str(result) else "✗")
        print(f"  {status} {test}: {result}")

    return results


if __name__ == "__main__":
    run_all_tests()
