"""
Placement 執行器

提供執行 placement_info.json 的完整流程
"""

import time
from typing import Dict, Any, Optional

from .client import GrasshopperClient
from .component_manager import ComponentManager
from .connection_manager import ConnectionManager
from .utils import load_placement_info


class PlacementExecutor:
    """Placement 執行器，執行完整的 placement_info.json 流程"""
    
    def __init__(
        self,
        client: Optional[GrasshopperClient] = None,
        component_manager: Optional[ComponentManager] = None,
        connection_manager: Optional[ConnectionManager] = None
    ):
        """
        初始化 Placement 執行器
        
        Args:
            client: Grasshopper 客戶端實例
            component_manager: 組件管理器實例
            connection_manager: 連接管理器實例
        """
        self.client = client or GrasshopperClient()
        self.component_manager = component_manager or ComponentManager(self.client)
        self.connection_manager = connection_manager or ConnectionManager(self.client, self.component_manager)
    
    def clear_canvas(self) -> bool:
        """
        清空 Grasshopper 畫布

        Returns:
            是否成功清空
        """
        print("\n🧹 清空畫布...")
        response = self.client.send_command("clear_document", {})
        if response.get("success"):
            print("   ✓ 畫布已清空")
            return True
        else:
            print(f"   ✗ 清空失敗: {response.get('error', '未知錯誤')}")
            return False

    def check_canvas_empty(self) -> Dict[str, Any]:
        """
        檢查畫布是否為空

        Returns:
            包含組件數量和狀態的字典
        """
        response = self.client.send_command("get_document_info", {})
        if response.get("success"):
            data = response.get("data", {})
            component_count = data.get("componentCount", 0)
            return {
                "success": True,
                "component_count": component_count,
                "is_empty": component_count == 0
            }
        return {"success": False, "component_count": -1, "is_empty": False}

    def execute_placement_info(
        self,
        json_path: str,
        max_workers: int = 10,
        save_id_map: bool = True,
        id_map_path: Optional[str] = None,
        clear_first: bool = False,
        use_smart_layout: bool = True
    ) -> Dict[str, Any]:
        """
        執行 placement_info.json 中的命令

        Args:
            json_path: placement_info.json 文件路徑
            max_workers: 最大並行線程數
            save_id_map: 是否保存組件 ID 映射
            id_map_path: 組件 ID 映射保存路徑，如果為 None 則使用默認路徑
            clear_first: 是否先清空畫布（預設 False）
            use_smart_layout: 是否使用智能佈局避免重疊（預設 True）

        Returns:
            執行結果字典，包含：
                - add_success: 組件創建成功數量
                - add_fail: 組件創建失敗數量
                - connect_success: 連接成功數量
                - connect_fail: 連接失敗數量
                - add_time: 組件創建耗時
                - connect_time: 連接耗時
                - total_time: 總耗時
        """
        print("=" * 80)
        print("執行 placement_info.json")
        print("=" * 80)

        # Step 0: 檢查並清空畫布
        if clear_first:
            canvas_status = self.check_canvas_empty()
            if canvas_status["success"] and not canvas_status["is_empty"]:
                print(f"\n⚠️  畫布上有 {canvas_status['component_count']} 個組件")
                self.clear_canvas()
            elif canvas_status["is_empty"]:
                print("\n✓ 畫布已經是空的")
        
        # 讀取 JSON 文件
        print(f"\n讀取命令文件: {json_path}")
        placement_data = load_placement_info(json_path)
        
        if not placement_data:
            print("\n✗ 無法讀取命令文件，程序退出")
            return {
                "success": False,
                "error": "無法讀取命令文件"
            }
        
        description = placement_data.get("description", "無描述")
        print(f"描述: {description}")

        # 支援兩種格式:
        # 舊格式 (v1.x): commands 陣列包含 add_component 和 connect_components
        # 新格式 (v2.x): 分離的 components 和 connections 陣列
        commands = placement_data.get("commands", [])
        components_v2 = placement_data.get("components", [])
        connections_v2 = placement_data.get("connections", [])

        add_commands = []
        connect_commands = []

        if components_v2 or connections_v2:
            # 新格式 v2.x
            print(f"格式: v2.x (components/connections 分離)")

            # 使用 Smart Layout 計算位置（避免重疊）
            if use_smart_layout:
                print("📐 使用 Smart Layout 計算位置...")
                components_v2 = self._apply_smart_layout(components_v2, connections_v2)

            # 轉換 components 為 add_component 命令
            for comp in components_v2:
                add_commands.append({
                    "type": "add_component",
                    "componentId": comp.get("id"),
                    "comment": f"{comp.get('nickname', comp.get('id'))} ({comp.get('type', 'Unknown')})",
                    "parameters": {
                        "guid": comp.get("guid"),
                        "type": comp.get("type"),  # 組件類型（Panel 等特殊組件用）
                        "x": comp.get("x", 0),
                        "y": comp.get("y", 0),
                        "nickname": comp.get("nickname"),
                        "value": comp.get("value")
                    }
                })

            # 轉換 connections 為 connect_components 命令
            for conn in connections_v2:
                connect_commands.append({
                    "type": "connect_components",
                    "parameters": {
                        "sourceId": conn.get("from"),
                        "sourceParam": conn.get("fromParam"),
                        "targetId": conn.get("to"),
                        "targetParam": conn.get("toParam"),
                        "targetParamIndex": conn.get("toParamIndex")
                    }
                })
        else:
            # 舊格式 v1.x
            print(f"格式: v1.x (commands 陣列)")
            print(f"總命令數: {len(commands)}")

            for cmd in commands:
                cmd_type = cmd.get("type")
                if cmd_type == "add_component":
                    add_commands.append(cmd)
                elif cmd_type == "connect_components":
                    connect_commands.append(cmd)
        
        # 從新格式（v2.1）讀取可變參數設定
        variable_params = placement_data.get("variable_params", [])

        print(f"\n組件創建命令: {len(add_commands)} 個")
        print(f"連接命令: {len(connect_commands)} 個")
        print(f"可變參數設定: {len(variable_params)} 個")
        
        # 設置並行工作線程數
        add_max_workers = min(max_workers, max(1, len(add_commands)))
        connect_max_workers = min(max_workers, max(1, len(connect_commands)))
        print(f"並行執行線程數: 組件創建={add_max_workers}, 連接={connect_max_workers}")
        
        # 執行所有 add_component 命令（並行）
        print("\n" + "=" * 80)
        print("階段 1: 創建組件（並行執行）")
        print("=" * 80)
        
        start_time = time.time()
        add_success, add_fail = self.component_manager.add_components_parallel(
            add_commands,
            max_workers=add_max_workers
        )
        add_time = time.time() - start_time
        
        print(f"\n組件創建完成: 成功 {add_success} 個，失敗 {add_fail} 個（耗時 {add_time:.2f} 秒）")
        print(f"組件 ID 映射: {len(self.component_manager.component_id_map)} 個")
        
        if add_fail > 0:
            print("\n⚠️  警告: 有組件創建失敗，連接可能會失敗")
            print("自動繼續執行連接命令...")

        # 保存組件 ID 映射
        if save_id_map:
            self.component_manager.save_id_map(id_map_path)

        # 執行可變參數設定（如果有）
        vp_success, vp_fail, vp_time = 0, 0, 0.0
        if variable_params:
            print("\n" + "=" * 80)
            print("階段 1.5: 設定可變參數組件 (IGH_VariableParameterComponent)")
            print("=" * 80)

            vp_start = time.time()
            vp_success, vp_fail = self._execute_variable_params(variable_params)
            vp_time = time.time() - vp_start

            print(f"\n可變參數設定完成: 成功 {vp_success} 個，失敗 {vp_fail} 個（耗時 {vp_time:.2f} 秒）")

        # 執行所有 connect_components 命令（並行）
        print("\n" + "=" * 80)
        print("階段 2: 連接組件（並行執行）")
        print("=" * 80)
        
        start_time = time.time()
        connect_success, connect_fail = self.connection_manager.connect_components_parallel(
            connect_commands,
            max_workers=connect_max_workers
        )
        connect_time = time.time() - start_time
        
        print(f"\n連接完成: 成功 {connect_success} 個，失敗 {connect_fail} 個（耗時 {connect_time:.2f} 秒）")
        
        # 總結
        total_time = add_time + vp_time + connect_time
        print("\n" + "=" * 80)
        print("執行總結")
        print("=" * 80)
        print(f"組件創建: {add_success}/{len(add_commands)} 成功（耗時 {add_time:.2f} 秒）")
        if variable_params:
            print(f"可變參數: {vp_success}/{len(variable_params)} 成功（耗時 {vp_time:.2f} 秒）")
        print(f"組件連接: {connect_success}/{len(connect_commands)} 成功（耗時 {connect_time:.2f} 秒）")
        print(f"總耗時: {total_time:.2f} 秒")

        success = (
            add_success == len(add_commands)
            and connect_success == len(connect_commands)
            and vp_success == len(variable_params)
        )

        if success:
            print("\n✓ 所有命令執行成功！")
        else:
            print("\n⚠️  部分命令執行失敗，請檢查錯誤信息。")

        return {
            "success": success,
            "add_success": add_success,
            "add_fail": add_fail,
            "variable_params_success": vp_success,
            "variable_params_fail": vp_fail,
            "connect_success": connect_success,
            "connect_fail": connect_fail,
            "add_time": add_time,
            "variable_params_time": vp_time,
            "connect_time": connect_time,
            "total_time": total_time,
            "component_id_map_size": len(self.component_manager.component_id_map)
        }

    def _execute_variable_params(self, variable_params: list) -> tuple:
        """
        執行可變參數設定

        適用於所有實現 IGH_VariableParameterComponent 的組件：
        Entwine, Merge, List Item, Sort, Dispatch, Gate, Stream Filter,
        Expression, Concatenate, Format, Construct Path, Split Tree 等。

        Args:
            variable_params: 可變參數設定列表，每個元素包含：
                - componentId: 組件的邏輯 ID（會從 component_id_map 解析為實際 GUID）
                - side: "input" 或 "output"
                - count: 目標參數數量
                - comment (可選): 備註說明

        Returns:
            (success_count, fail_count) 元組
        """
        success_count = 0
        fail_count = 0

        for vp in variable_params:
            logical_id = vp.get("componentId")
            side = vp.get("side", "input")
            count = vp.get("count")
            comment = vp.get("comment", "")

            if not logical_id or count is None:
                print(f"  ✗ 無效的可變參數設定: {vp}")
                fail_count += 1
                continue

            # 從組件 ID 映射中獲取實際 GUID
            actual_id = self.component_manager.component_id_map.get(logical_id)
            if not actual_id:
                print(f"  ✗ 找不到組件 '{logical_id}' 的實際 ID")
                fail_count += 1
                continue

            # 執行 set_variable_params 命令
            if comment:
                print(f"  ◐ {logical_id}: {comment}")
            else:
                print(f"  ◐ {logical_id}: 設定 {side} 參數為 {count} 個")

            response = self.client.send_command(
                "set_variable_params",
                {
                    "id": actual_id,
                    "side": side,
                    "count": count
                }
            )

            if response.get("success"):
                data = response.get("data", {})
                final_count = data.get("finalCount", count)
                added = data.get("addedCount", 0)
                removed = data.get("removedCount", 0)
                print(f"  ✓ {logical_id}: {final_count} 個參數 (新增 {added}, 移除 {removed})")
                success_count += 1
            else:
                error = response.get("error", "未知錯誤")
                print(f"  ✗ {logical_id}: {error}")
                fail_count += 1

        return success_count, fail_count

    def _apply_smart_layout(
        self,
        components: list,
        connections: list
    ) -> list:
        """
        應用 Smart Layout 計算組件位置，避免重疊

        Args:
            components: 組件列表
            connections: 連接列表

        Returns:
            帶有計算位置的組件列表（包含 x, y 欄位）
        """
        try:
            import sys
            from pathlib import Path
            # 嘗試導入 smart_layout
            src_path = Path(__file__).parent.parent / "src"
            if str(src_path) not in sys.path:
                sys.path.insert(0, str(src_path))

            from smart_layout import simple_layout, LayoutConfig

            # 配置佈局
            config = LayoutConfig(
                layer_spacing=250,
                component_spacing_x=150,
                component_spacing_y=80,
                start_x=50,
                start_y=50
            )

            # 轉換連接格式 (placement_info 格式 → smart_layout 格式)
            layout_connections = []
            for conn in connections:
                layout_connections.append({
                    "from": {"component": conn.get("from", "")},
                    "to": {"component": conn.get("to", "")}
                })

            # 執行佈局（使用 simple_layout 函數）
            positioned = simple_layout(components, layout_connections, config)

            # 將 position 轉換為 x, y 欄位
            for comp in positioned:
                if "position" in comp:
                    pos = comp["position"]
                    comp["x"] = pos[0] if isinstance(pos, (list, tuple)) and len(pos) > 0 else 50
                    comp["y"] = pos[1] if isinstance(pos, (list, tuple)) and len(pos) > 1 else 50
                    del comp["position"]  # 移除 position 欄位

            print(f"   ✓ Smart Layout 完成，{len(positioned)} 個組件已計算位置")
            return positioned

        except ImportError as e:
            print(f"   ⚠️ Smart Layout 不可用: {e}")
            print("   使用 col/row 計算簡易位置...")
            return self._apply_simple_grid_layout(components)

        except Exception as e:
            print(f"   ⚠️ Smart Layout 錯誤: {e}")
            return self._apply_simple_grid_layout(components)

    def _apply_simple_grid_layout(self, components: list) -> list:
        """
        簡易網格佈局（當 Smart Layout 不可用時的備選）

        使用 col/row 欄位計算位置，避免組件重疊

        Args:
            components: 組件列表

        Returns:
            帶有計算位置的組件列表
        """
        GRID_X = 200  # 水平間距
        GRID_Y = 100  # 垂直間距
        START_X = 50
        START_Y = 50

        for comp in components:
            col = comp.get("col", 0)
            row = comp.get("row", 0)

            # 如果沒有指定 x/y，根據 col/row 計算
            if "x" not in comp or comp.get("x") == 0:
                comp["x"] = START_X + col * GRID_X
            if "y" not in comp or comp.get("y") == 0:
                comp["y"] = START_Y + row * GRID_Y

        print(f"   ✓ 簡易網格佈局完成，使用 {GRID_X}x{GRID_Y} 間距")
        return components

