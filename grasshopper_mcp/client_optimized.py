#!/usr/bin/env python3
"""
GH_MCP 優化客戶端 - 整合所有最佳實踐

從以下腳本提取經驗：
- build_chair_v2.py: GUID 驗證、參數映射
- execute_table.py: ID 提取、id_map 管理
- create_tower.py: 簡潔的 helper 函數
- build_cup.py: 兩步驟 slider 設置 (先 range 再 value)

關鍵學習：
1. API 返回格式: {"success": bool, "data": {"id": "..."}, "error": "..."}
2. Slider 必須分兩步設置: 先 min/max，再 value (避免 clamping)
3. 連接參數: sourceId, targetId (不是 source, target)
4. 組件位置: 必須傳 x, y 參數

2026-01-09 from DEV_LOG.md
"""

import socket
import json
import time
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

# =========================================================================
# 參數別名表 (從實際錯誤案例學習)
# =========================================================================
# 當連接失敗時，自動嘗試這些別名
# 格式: "組件類型": ["優先參數", "備選1", "備選2", ...]

PARAM_ALIASES = {
    # 數學運算組件 - 輸出參數
    "Division": ["Result", "R"],
    "Multiplication": ["Result", "R"],
    "Addition": ["Result", "R"],
    "Subtraction": ["Result", "R"],
    "Modulus": ["Result", "R"],
    "Power": ["Result", "R"],
    "Absolute": ["Result", "R"],
    "Negative": ["Result", "R"],

    # 三角函數組件 - 注意 Radians 組件輸出參數是全名
    "Radians": ["Radians", "R", "Result"],
    "Degrees": ["Degrees", "D", "Result"],
    "Sine": ["y", "Result", "R"],
    "Cosine": ["y", "Result", "R"],
    "Tangent": ["y", "Result", "R"],

    # 數列組件
    "Series": ["S", "Series", "Result"],
    "Range": ["R", "Range", "Result"],
    "Random": ["R", "Random", "Result"],

    # 點/向量組件
    "Construct Point": ["Pt", "Point", "P"],
    "Deconstruct Point": ["X", "Y", "Z"],  # 多輸出
    "Unit X": ["V", "Vector", "Unit"],
    "Unit Y": ["V", "Vector", "Unit"],
    "Unit Z": ["V", "Vector", "Unit"],
    "Vector XYZ": ["V", "Vector", "Result"],

    # 幾何組件
    "Center Box": ["B", "Box", "Geometry"],
    "Circle": ["C", "Circle", "Geometry"],
    "Line": ["L", "Line", "Geometry"],
    "Cylinder": ["C", "Cylinder", "Geometry"],
    "Sphere": ["S", "Sphere", "Geometry"],
    "Pipe": ["P", "Pipe", "Geometry"],

    # 變換組件
    "Move": ["G", "Geometry", "Result"],
    "Rotate": ["G", "Geometry", "Result"],
    "Scale": ["G", "Geometry", "Result"],
    "Mirror": ["G", "Geometry", "Result"],

    # 曲線組件
    "Interpolate": ["C", "Curve", "Result"],
    "Polyline": ["Pl", "Polyline", "Result"],

    # 數據組件
    "Number Slider": ["N", "Number"],
    "Panel": ["Out", "Output", "Data"],
}

# 嘗試導入 Gemini 分析器
try:
    from gh_learning.src.gemini_analyzer import GeminiAnalyzer
    GEMINI_AVAILABLE = True
except ImportError:
    GeminiAnalyzer = None  # type: ignore
    GEMINI_AVAILABLE = False


@dataclass
class ComponentInfo:
    """組件資訊"""
    nickname: str
    comp_id: str
    comp_type: str
    x: float = 0
    y: float = 0


@dataclass
class SliderConfig:
    """Slider 配置"""
    nickname: str
    value: float
    min_val: float = 0
    max_val: float = 100
    col: int = 0
    row: int = 0


class GH_MCP_ClientOptimized:
    """
    GH_MCP 優化客戶端

    特點：
    1. 自動追蹤 nickname → id 映射
    2. 兩步驟 slider 設置 (避免 clamping)
    3. 統一的 ID 提取邏輯
    4. 佈局輔助函數
    5. 詳細的錯誤報告
    """

    # 佈局常數
    COL_WIDTH = 200
    ROW_HEIGHT = 80
    START_X = 50
    START_Y = 50

    def __init__(self, host: str = '127.0.0.1', port: int = 8080, debug: bool = True, use_gemini: bool = False):
        self.host = host
        self.port = port
        self.debug = debug
        self.use_gemini = use_gemini and GEMINI_AVAILABLE

        # 組件追蹤
        self.components: Dict[str, ComponentInfo] = {}
        self.connection_count = 0

        # Gemini 分析器（用於智能診斷）
        self._gemini = GeminiAnalyzer(timeout=30) if (self.use_gemini and GeminiAnalyzer) else None
        self._failed_connections: List[Dict] = []  # 記錄失敗的連接供後續分析

    # =========================================================================
    # 核心通訊
    # =========================================================================

    def send_command(self, cmd_type: str, **params) -> dict:
        """
        發送命令到 GH_MCP

        使用巢狀結構: {"type": "cmd", "parameters": {...}}
        """
        command = {
            'type': cmd_type,
            'parameters': params
        }

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

                # 處理 BOM
                result = json.loads(response.decode('utf-8-sig'))
                return result

        except socket.timeout:
            return {'success': False, 'error': 'Connection timeout'}
        except ConnectionRefusedError:
            return {'success': False, 'error': 'GH_MCP not running (port 8080)'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def extract_id(self, result: dict) -> Optional[str]:
        """
        從 API 回應提取組件 ID

        關鍵: ID 在 result.data.id，不是 result.id
        """
        if not result.get('success'):
            return None

        data = result.get('data', {})
        if isinstance(data, dict):
            return data.get('id') or data.get('componentId')
        return None

    # =========================================================================
    # 佈局輔助
    # =========================================================================

    def pos(self, col: int, row: int) -> Tuple[float, float]:
        """計算組件位置 (column, row based)"""
        x = self.START_X + col * self.COL_WIDTH
        y = self.START_Y + row * self.ROW_HEIGHT
        return (x, y)

    # =========================================================================
    # 文檔操作
    # =========================================================================

    def clear_canvas(self) -> bool:
        """清空畫布"""
        result = self.send_command('clear_document')
        if result.get('success'):
            self.components.clear()
            self.connection_count = 0
            if self.debug:
                print("   ✓ 畫布已清空")
        return result.get('success', False)

    def get_document_info(self) -> dict:
        """獲取文檔資訊"""
        return self.send_command('get_document_info')

    def test_connection(self) -> bool:
        """測試連接"""
        result = self.get_document_info()
        if result.get('success'):
            if self.debug:
                print("   ✓ GH_MCP 連接成功")
            return True
        else:
            error = result.get('error', '')
            # Index not found 可能是空文檔，繼續嘗試
            if 'Index not found' in str(error):
                if self.debug:
                    print(f"   ⚠ {error} (嘗試繼續)")
                return True
            if self.debug:
                print(f"   ✗ 無法連接: {error}")
            return False

    # =========================================================================
    # 組件創建
    # =========================================================================

    def add_slider(
        self,
        nickname: str,
        col: int,
        row: int,
        value: float,
        min_val: float = 0,
        max_val: float = 100
    ) -> Optional[str]:
        """
        添加 Number Slider (含位置)

        重要: 分兩步設置 slider:
        1. 先設置 min/max 範圍
        2. 再設置 value

        這避免了 value 被 clamp 到默認範圍 (0-1) 的問題
        """
        x, y = self.pos(col, row)

        # Step 1: 創建 slider
        result = self.send_command(
            'add_component',
            type='Number Slider',
            nickname=nickname,
            x=x,
            y=y
        )

        comp_id = self.extract_id(result)
        if not comp_id:
            if self.debug:
                print(f"   ✗ {nickname}: {result.get('error', 'Unknown')}")
            return None

        # 記錄組件
        self.components[nickname] = ComponentInfo(
            nickname=nickname,
            comp_id=comp_id,
            comp_type='Number Slider',
            x=x,
            y=y
        )

        # Step 2: 設置範圍 (先於 value!)
        time.sleep(0.05)
        range_result = self.send_command(
            'set_slider_properties',
            id=comp_id,  # 注意: 是 'id' 不是 'component_id'
            min=min_val,
            max=max_val
        )

        # Step 3: 設置 value
        time.sleep(0.05)
        value_result = self.send_command(
            'set_slider_properties',
            id=comp_id,
            value=str(value)  # value 作為字串傳遞更可靠
        )

        if self.debug:
            if range_result.get('success') and value_result.get('success'):
                print(f"   ✓ {nickname} = {value} (range: {min_val}-{max_val}) @ ({x}, {y})")
            else:
                print(f"   ⚠ {nickname}: 創建成功但屬性設置可能有問題")

        return comp_id

    def add_component(
        self,
        comp_type: str,
        nickname: str,
        col: int,
        row: int,
        guid: Optional[str] = None
    ) -> Optional[str]:
        """
        添加組件 (含位置)

        Args:
            comp_type: 組件類型名稱 (e.g., "XY Plane", "Circle")
            nickname: 組件暱稱
            col: 列位置
            row: 行位置
            guid: 可選的經驗證 GUID (避免 OBSOLETE 衝突)

        Note:
            GH_MCP v2.2+ 在 C# 端會自動過濾 OBSOLETE 組件
        """
        x, y = self.pos(col, row)

        params = {
            'nickname': nickname,
            'x': x,
            'y': y
        }

        if guid:
            params['guid'] = guid
        else:
            # 使用 type 讓 GH_MCP 自動選擇非 OBSOLETE 版本
            params['type'] = comp_type

        result = self.send_command('add_component', **params)
        comp_id = self.extract_id(result)

        if not comp_id:
            if self.debug:
                print(f"   ✗ {nickname} ({comp_type}): {result.get('error', 'Unknown')}")
            return None

        # 記錄組件
        self.components[nickname] = ComponentInfo(
            nickname=nickname,
            comp_id=comp_id,
            comp_type=comp_type,
            x=x,
            y=y
        )

        if self.debug:
            print(f"   ✓ {nickname} ({comp_type}) @ ({x}, {y})")

        return comp_id

    # =========================================================================
    # 批量創建
    # =========================================================================

    def add_sliders_batch(self, configs: List[SliderConfig]) -> Dict[str, str]:
        """批量創建 sliders"""
        results = {}
        for cfg in configs:
            comp_id = self.add_slider(
                nickname=cfg.nickname,
                col=cfg.col,
                row=cfg.row,
                value=cfg.value,
                min_val=cfg.min_val,
                max_val=cfg.max_val
            )
            if comp_id:
                results[cfg.nickname] = comp_id
        return results

    def add_components_batch(
        self,
        configs: List[Tuple[str, str, int, int]]
    ) -> Dict[str, str]:
        """
        批量創建組件

        Args:
            configs: [(comp_type, nickname, col, row), ...]
        """
        results = {}
        for comp_type, nickname, col, row in configs:
            comp_id = self.add_component(comp_type, nickname, col, row)
            if comp_id:
                results[nickname] = comp_id
        return results

    # =========================================================================
    # 連接
    # =========================================================================

    def connect(
        self,
        from_nick: str,
        from_param: str,
        to_nick: str,
        to_param: str
    ) -> bool:
        """
        連接兩個組件 (使用 nickname)

        Args:
            from_nick: 源組件 nickname
            from_param: 源參數名 (e.g., "N", "Pt", "C")
            to_nick: 目標組件 nickname
            to_param: 目標參數名 (e.g., "Z", "O", "R")
        """
        from_info = self.components.get(from_nick)
        to_info = self.components.get(to_nick)

        if not from_info:
            if self.debug:
                print(f"   ✗ 找不到源組件: {from_nick}")
            return False

        if not to_info:
            if self.debug:
                print(f"   ✗ 找不到目標組件: {to_nick}")
            return False

        # 注意: 參數名是 sourceId/targetId，不是 from_component_id
        result = self.send_command(
            'connect_components',
            sourceId=from_info.comp_id,
            sourceParam=from_param,
            targetId=to_info.comp_id,
            targetParam=to_param
        )

        # 檢查成功 (可能在外層或內層)
        success = result.get('success', False)
        inner = result.get('data', {})
        inner_success = inner.get('success', False) if isinstance(inner, dict) else False
        already = 'already connected' in str(inner).lower()

        if success and (inner_success or already):
            self.connection_count += 1
            if self.debug:
                print(f"   ✓ {from_nick}.{from_param} → {to_nick}.{to_param}")
            return True
        else:
            error = inner.get('error', str(result)) if isinstance(inner, dict) else result.get('error', 'Unknown')
            if self.debug:
                print(f"   ✗ {from_nick}.{from_param} → {to_nick}.{to_param}: {str(error)[:40]}")

            # 記錄失敗的連接
            self._failed_connections.append({
                'from': f"{from_nick}.{from_param}",
                'to': f"{to_nick}.{to_param}",
                'from_type': from_info.comp_type,
                'to_type': to_info.comp_type,
                'error': str(error)
            })
            return False

    def smart_connect(
        self,
        from_nick: str,
        from_param: str,
        to_nick: str,
        to_param: str,
        verbose: bool = True
    ) -> bool:
        """
        智能連接 - 失敗時自動嘗試參數別名

        工作流程：
        1. 先嘗試原始參數名
        2. 若失敗，根據源組件類型查找別名
        3. 依序嘗試別名直到成功
        4. 全部失敗則記錄並返回 False

        Args:
            from_nick: 源組件 nickname
            from_param: 源參數名
            to_nick: 目標組件 nickname
            to_param: 目標參數名
            verbose: 是否顯示別名嘗試過程

        Returns:
            bool: 連接是否成功
        """
        from_info = self.components.get(from_nick)
        if not from_info:
            if self.debug:
                print(f"   ✗ 找不到源組件: {from_nick}")
            return False

        # 1. 先嘗試原始參數名
        if self.connect(from_nick, from_param, to_nick, to_param):
            return True

        # 2. 查找組件類型的別名
        comp_type = from_info.comp_type
        aliases = PARAM_ALIASES.get(comp_type, [])

        # 3. 嘗試每個別名
        tried = [from_param]
        for alias in aliases:
            if alias == from_param:
                continue  # 跳過已嘗試的
            tried.append(alias)

            # 暫時關閉 debug 避免重複輸出
            original_debug = self.debug
            self.debug = False
            success = self.connect(from_nick, alias, to_nick, to_param)
            self.debug = original_debug

            if success:
                if verbose and self.debug:
                    print(f"   ↳ 使用別名: {from_nick}.{from_param} → {from_nick}.{alias}")
                return True

        # 4. 全部失敗
        if self.debug:
            print(f"   ✗ {from_nick}.{from_param} → {to_nick}.{to_param} (嘗試: {', '.join(tried)})")

        return False

    def smart_connect_batch(
        self,
        connections: List[Tuple[str, str, str, str]]
    ) -> Tuple[int, int, List[Dict]]:
        """
        批量智能連接

        Args:
            connections: [(from_nick, from_param, to_nick, to_param), ...]

        Returns:
            (success_count, fail_count, failed_list)
        """
        success = 0
        fail = 0
        failed_list = []

        for from_nick, from_param, to_nick, to_param in connections:
            if self.smart_connect(from_nick, from_param, to_nick, to_param):
                success += 1
            else:
                fail += 1
                failed_list.append({
                    'from': f"{from_nick}.{from_param}",
                    'to': f"{to_nick}.{to_param}"
                })

        return (success, fail, failed_list)

    def connect_batch(
        self,
        connections: List[Tuple[str, str, str, str]]
    ) -> Tuple[int, int]:
        """
        批量連接

        Args:
            connections: [(from_nick, from_param, to_nick, to_param), ...]

        Returns:
            (success_count, fail_count)
        """
        success = 0
        fail = 0

        for from_nick, from_param, to_nick, to_param in connections:
            if self.connect(from_nick, from_param, to_nick, to_param):
                success += 1
            else:
                fail += 1

        return (success, fail)

    # =========================================================================
    # 統計
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計資訊"""
        comp_types = {}
        for info in self.components.values():
            comp_types[info.comp_type] = comp_types.get(info.comp_type, 0) + 1

        return {
            'total_components': len(self.components),
            'total_connections': self.connection_count,
            'component_types': comp_types,
        }

    def print_summary(self):
        """打印摘要"""
        stats = self.get_stats()
        print("\n" + "=" * 60)
        print("建構結果")
        print("=" * 60)
        print(f"   組件: {stats['total_components']} 個")
        print(f"   連接: {stats['total_connections']} 個")

        if stats['component_types']:
            print("\n   組件類型:")
            for comp_type, count in sorted(stats['component_types'].items()):
                print(f"      - {comp_type}: {count}")

    def get_id_map(self) -> Dict[str, str]:
        """獲取 nickname → id 映射"""
        return {
            nick: info.comp_id
            for nick, info in self.components.items()
        }

    # =========================================================================
    # Gemini 智能診斷
    # =========================================================================

    def diagnose_failures(self) -> List[Dict]:
        """
        使用 Gemini 診斷連接失敗原因

        Returns:
            診斷結果列表，每個包含 cause, correct_params, solution
        """
        if not self._gemini or not self._failed_connections:
            return []

        results = []
        if self.debug:
            print(f"\n🔮 Gemini 診斷 {len(self._failed_connections)} 個失敗連接...")

        for fc in self._failed_connections[:5]:  # 最多診斷 5 個
            try:
                diagnosis = self._gemini.analyze_connection_failure(
                    source_comp=f"{fc['from']} ({fc['from_type']})",
                    target_comp=f"{fc['to']} ({fc['to_type']})",
                    error_msg=fc['error']
                )
                diagnosis['original'] = fc
                results.append(diagnosis)

                if self.debug and 'cause' in diagnosis:
                    print(f"   💡 {fc['from']} → {fc['to']}")
                    print(f"      原因: {diagnosis.get('cause', 'Unknown')[:60]}")
                    if 'correct_params' in diagnosis:
                        cp = diagnosis['correct_params']
                        print(f"      建議: {cp.get('source', '?')} → {cp.get('target', '?')}")

            except Exception as e:
                results.append({'error': str(e), 'original': fc})

        return results

    def get_failed_connections(self) -> List[Dict]:
        """獲取失敗的連接列表"""
        return self._failed_connections.copy()

    def clear_failed_connections(self):
        """清空失敗連接記錄"""
        self._failed_connections.clear()

    # =========================================================================
    # 智能組件查找 (使用 GH_MCP_Vision 的 search_components)
    # =========================================================================

    def send_vision_command(self, cmd_type: str, **params) -> dict:
        """
        發送命令到 GH_MCP_Vision (端口 8081)

        Vision 服務器提供組件庫查詢功能：
        - search_components: 智能搜索組件
        - export_component_library: 導出組件知識庫
        - validate_components: 驗證組件是否存在
        """
        command = {
            'type': cmd_type,
            'parameters': params
        }

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(30)  # Vision 操作可能較慢
                s.connect((self.host, 8081))  # Vision 端口
                s.sendall(json.dumps(command).encode('utf-8'))
                s.shutdown(socket.SHUT_WR)

                response = b''
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    response += chunk

                result = json.loads(response.decode('utf-8-sig'))
                return result

        except socket.timeout:
            return {'success': False, 'error': 'Vision timeout (may be exporting large library)'}
        except ConnectionRefusedError:
            return {'success': False, 'error': 'GH_MCP_Vision not running (port 8081)'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def search_component(self, name: str, max_results: int = 5) -> Optional[Dict]:
        """
        智能搜索組件 (使用 GH_MCP_Vision 的 search_components)

        匹配分數計算：
        - NickName 精確匹配: +100 分
        - Name 精確匹配: +80 分
        - 部分匹配: +20 分
        - 內建庫: +50 分
        - 過期組件: -100 分

        Returns:
            {
                'recommended': {guid, name, nickName, score, isBuiltIn, isObsolete},
                'candidates': [...]
            }
        """
        result = self.send_vision_command('search_components', name=name, maxResults=max_results)

        if result.get('success'):
            data = result.get('data', {})
            if self.debug and data.get('recommended'):
                rec = data['recommended']
                print(f"   → 推薦: {rec.get('name')} (score: {rec.get('score')}, built-in: {rec.get('isBuiltIn')})")
            return data
        else:
            if self.debug:
                print(f"   ⚠ Vision search failed: {result.get('error')}")
            return None

    def export_component_library(self, output_path: str) -> bool:
        """
        導出完整組件知識庫到 JSON (使用 GH_MCP_Vision)

        一次性獲取所有已安裝組件（包括第三方插件）的：
        - GUID
        - Name / NickName
        - Category
        - 輸入/輸出參數
        - IsObsolete 標記
        - Library 來源
        """
        result = self.send_vision_command('export_component_library', outputPath=output_path)

        if result.get('success'):
            if self.debug:
                data = result.get('data', {})
                count = data.get('processedCount', 0)
                print(f"   ✓ 導出 {count} 個組件到 {output_path}")
            return True
        else:
            if self.debug:
                print(f"   ✗ 導出失敗: {result.get('error')}")
            return False

    def safe_add_component(
        self,
        comp_name: str,
        nickname: str,
        col: int,
        row: int
    ) -> Optional[str]:
        """
        安全添加組件 - 方案 C 的實現

        工作流程：
        1. 使用 GH_MCP_Vision 的 search_components 查詢最佳匹配
        2. 驗證組件不是過期版本
        3. 使用正確的 GUID 創建組件

        避免的問題：
        - "Division" → "Subdivision" (Weaverbird 衝突)
        - "Merge" → "Loop Subdivision" (同名衝突)
        - OBSOLETE 過期組件
        """
        # Step 1: 通過 Vision 搜索最佳匹配
        search_result = self.search_component(comp_name, max_results=3)

        if search_result and search_result.get('recommended'):
            rec = search_result['recommended']
            guid = rec.get('guid')
            actual_name = rec.get('name')
            is_obsolete = rec.get('isObsolete', False)
            is_built_in = rec.get('isBuiltIn', False)

            # Step 2: 警告過期組件
            if is_obsolete:
                if self.debug:
                    print(f"   ⚠ 警告: '{actual_name}' 是過期組件")
                # 嘗試找非過期的候選
                candidates = search_result.get('candidates', [])
                for cand in candidates:
                    if not cand.get('isObsolete'):
                        guid = cand.get('guid')
                        actual_name = cand.get('name')
                        if self.debug:
                            print(f"   → 改用: {actual_name}")
                        break

            # Step 3: 使用 GUID 創建
            if self.debug:
                print(f"   🔍 {comp_name} → {actual_name} ({'內建' if is_built_in else '插件'})")

            return self.add_component(actual_name, nickname, col, row, guid=guid)
        else:
            # Vision 查詢失敗，回退到 GH_MCP 內建匹配 (方案 A 已優化)
            if self.debug:
                print(f"   ⚠ Vision 查詢失敗，使用 GH_MCP 內建匹配")
            return self.add_component(comp_name, nickname, col, row)

    # 別名：add_component_smart = safe_add_component
    add_component_smart = safe_add_component


# =========================================================================
# 便捷函數
# =========================================================================

def create_client(debug: bool = True) -> GH_MCP_ClientOptimized:
    """創建客戶端實例"""
    return GH_MCP_ClientOptimized(debug=debug)


def quick_test() -> bool:
    """快速測試 GH_MCP 連接"""
    client = GH_MCP_ClientOptimized(debug=False)
    return client.test_connection()
