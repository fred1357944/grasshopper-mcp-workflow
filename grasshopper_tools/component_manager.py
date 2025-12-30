"""
組件管理工具

提供組件的創建、查詢、刪除等功能
"""

import time
from typing import Dict, Any, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from .client import GrasshopperClient
from .utils import save_component_id_map


class ComponentManager:
    """組件管理器"""
    
    def __init__(self, client: Optional[GrasshopperClient] = None):
        """
        初始化組件管理器
        
        Args:
            client: Grasshopper 客戶端實例，如果為 None 則創建新實例
        """
        self.client = client or GrasshopperClient()
        self.component_id_map: Dict[str, str] = {}
        self._map_lock = Lock()  # 保護 component_id_map 的鎖
    
    def add_component(self, guid: str, x: float, y: float, component_id: Optional[str] = None) -> Optional[str]:
        """
        創建組件
        
        Args:
            guid: 組件類型 GUID
            x: X 座標
            y: Y 座標
            component_id: 可選的組件 ID（用於映射）
        
        Returns:
            創建的組件實際 ID，如果失敗則返回 None
        """
        response = self.client.send_command("add_component", {
            "guid": guid,
            "x": x,
            "y": y
        })
        
        if response.get("success"):
            actual_id = self.client.extract_component_id(response)
            if actual_id and component_id:
                with self._map_lock:
                    self.component_id_map[component_id] = actual_id
            return actual_id
        else:
            error = response.get("error", "未知錯誤")
            self.client.safe_print(f"創建組件失敗: {error}")
            return None
    
    def add_components_parallel(self, commands: List[Dict[str, Any]], max_workers: int = 10) -> Tuple[int, int]:
        """
        並行創建多個組件
        
        Args:
            commands: 組件創建命令列表，每個命令包含：
                - guid: 組件類型 GUID
                - x: X 座標
                - y: Y 座標
                - componentId: 可選的組件 ID（用於映射）
            max_workers: 最大並行線程數
        
        Returns:
            (成功數量, 失敗數量) 元組
        """
        success_count = 0
        fail_count = 0
        
        def execute_add(cmd: Dict[str, Any], index: int, total: int) -> Tuple[bool, Optional[str]]:
            component_id = cmd.get("componentId", "")
            
            # 支持兩種格式：
            # 1. 直接格式: {"guid": "...", "x": 100, "y": 50}
            # 2. parameters 格式: {"parameters": {"guid": "...", "x": 100, "y": 50}}
            parameters = cmd.get("parameters", {})
            if parameters:
                # 從 parameters 中提取
                guid = parameters.get("guid") or cmd.get("guid")
                x = parameters.get("x") if "x" in parameters else cmd.get("x")
                y = parameters.get("y") if "y" in parameters else cmd.get("y")
            else:
                # 直接從命令中提取
                guid = cmd.get("guid")
                x = cmd.get("x")
                y = cmd.get("y")
            
            if not guid:
                self.client.safe_print(f"  ✗ [{index}/{total}] 錯誤: 缺少 GUID")
                return False, None
            
            # 確保 x 和 y 是 float 類型
            if x is None or not isinstance(x, (int, float)):
                self.client.safe_print(f"  ✗ [{index}/{total}] 錯誤: 無效的 x 座標")
                return False, None
            if y is None or not isinstance(y, (int, float)):
                self.client.safe_print(f"  ✗ [{index}/{total}] 錯誤: 無效的 y 座標")
                return False, None
            
            x_float = float(x)
            y_float = float(y)
            
            comment = cmd.get("comment", component_id or f"組件 {index}")
            self.client.safe_print(f"  [{index}/{total}] 創建組件: {comment} (GUID: {guid[:8]}...)")
            
            actual_id = self.add_component(guid, x_float, y_float, component_id)
            
            # 添加延遲，避免 Grasshopper 處理過快
            time.sleep(0.05)  # 50 毫秒延遲
            
            if actual_id:
                self.client.safe_print(f"      ✓ 成功創建，ID: {actual_id}")
                return True, actual_id
            else:
                self.client.safe_print("      ✗ 創建失敗")
                return False, None
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_command = {
                executor.submit(execute_add, cmd, i, len(commands)): (i, cmd)
                for i, cmd in enumerate(commands, 1)
            }
            
            for future in as_completed(future_to_command):
                index, cmd = future_to_command[future]
                try:
                    success, actual_id = future.result()
                    if success:
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception as e:
                    self.client.safe_print(f"  ✗ [{index}/{len(commands)}] 執行時發生異常: {e}")
                    fail_count += 1
        
        return success_count, fail_count
    
    def delete_component(self, component_id: str) -> bool:
        """
        刪除組件
        
        Args:
            component_id: 組件 ID
        
        Returns:
            是否成功刪除
        """
        response = self.client.send_command("delete_component", {
            "componentId": component_id
        })
        
        if response.get("success"):
            # 從映射中移除
            with self._map_lock:
                keys_to_remove = [k for k, v in self.component_id_map.items() if v == component_id]
                for key in keys_to_remove:
                    del self.component_id_map[key]
            return True
        else:
            error = response.get("error", "未知錯誤")
            self.client.safe_print(f"刪除組件失敗: {error}")
            return False
    
    def set_component_visibility(self, component_id: str, hidden: bool) -> bool:
        """
        設置組件可見性
        
        Args:
            component_id: 組件 ID
            hidden: 是否隱藏（True = 隱藏, False = 顯示）
        
        Returns:
            是否成功設置
        """
        # 如果提供了映射鍵，從映射中查找實際 ID
        actual_id = self.get_component_id(component_id)
        if actual_id:
            component_id = actual_id
        
        response = self.client.send_command("set_component_visibility", {
            "componentId": component_id,
            "hidden": hidden
        })
        
        if response.get("success"):
            return True
        else:
            error = response.get("error", "未知錯誤")
            self.client.safe_print(f"設置組件可見性失敗: {error}")
            return False
    
    def zoom_to_components(self, component_ids: List[str]) -> bool:
        """
        縮放到指定組件
        
        Args:
            component_ids: 組件 ID 列表（可以是實際 ID 或映射鍵）
        
        Returns:
            是否成功縮放
        """
        # 如果提供了映射鍵，從映射中查找實際 ID
        actual_ids = []
        for comp_id in component_ids:
            actual_id = self.get_component_id(comp_id)
            if actual_id:
                actual_ids.append(actual_id)
            else:
                actual_ids.append(comp_id)  # 使用原始 ID
        
        response = self.client.send_command("zoom_to_components", {
            "componentIds": actual_ids
        })
        
        if response.get("success"):
            return True
        else:
            error = response.get("error", "未知錯誤")
            self.client.safe_print(f"縮放到組件失敗: {error}")
            return False
    
    def get_component_guid(self, component_name: str) -> Optional[Dict[str, Any]]:
        """
        查詢組件的 GUID
        
        Args:
            component_name: 組件名稱
        
        Returns:
            包含 name, guid, category, isBuiltIn 的字典，如果未找到則返回 None
        """
        response = self.client.send_command("get_component_candidates", {
            "name": component_name
        })
        
        if response.get("success"):
            response_data = response.get("data") or response.get("result", {})
            candidates = response_data.get("candidates", [])
            
            if not candidates:
                return None
            
            # 優先選擇非廢棄的內置組件
            for candidate in candidates:
                if not candidate.get('obsolete', False) and candidate.get('isBuiltIn', False):
                    return {
                        "name": candidate.get('name', component_name),
                        "guid": candidate.get('guid', ''),
                        "category": candidate.get('category', ''),
                        "isBuiltIn": True
                    }
            
            # 其次選擇非廢棄組件
            for candidate in candidates:
                if not candidate.get('obsolete', False):
                    return {
                        "name": candidate.get('name', component_name),
                        "guid": candidate.get('guid', ''),
                        "category": candidate.get('category', ''),
                        "isBuiltIn": candidate.get('isBuiltIn', False)
                    }
            
            # 最後選擇第一個候選
            candidate = candidates[0]
            return {
                "name": candidate.get('name', component_name),
                "guid": candidate.get('guid', ''),
                "category": candidate.get('category', ''),
                "isBuiltIn": candidate.get('isBuiltIn', False)
            }
        else:
            self.client.safe_print(f"查詢 {component_name} 失敗: {response.get('error', '未知錯誤')}")
            return None
    
    def get_component_id(self, component_id: str) -> Optional[str]:
        """
        獲取組件的實際 ID（從映射中查找）
        
        Args:
            component_id: 組件 ID（映射鍵）
        
        Returns:
            實際組件 ID，如果未找到則返回 None
        """
        with self._map_lock:
            return self.component_id_map.get(component_id)
    
    def save_id_map(self, file_path: Optional[str] = None):
        """保存組件 ID 映射到文件"""
        with self._map_lock:
            save_component_id_map(self.component_id_map, file_path)
    
    def load_id_map(self, file_path: Optional[str] = None):
        """從文件加載組件 ID 映射"""
        from .utils import load_component_id_map
        loaded_map = load_component_id_map(file_path)
        if loaded_map:
            with self._map_lock:
                self.component_id_map.update(loaded_map)

