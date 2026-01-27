"""
連接驗證器 - 在執行前驗證參數語義
=============================================
從「背答案」升級到「理解語義」的關鍵模組

功能：
1. 驗證參數名與索引是否一致
2. 驗證類型是否兼容
3. 提供修正建議
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """驗證錯誤"""
    connection_id: str
    error_type: str  # "index_mismatch", "type_mismatch", "param_not_found", "index_out_of_range"
    message: str
    suggestion: str
    severity: str = "error"  # "error", "warning"


@dataclass
class ValidationResult:
    """驗證結果"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    @property
    def can_continue(self) -> bool:
        """是否可以繼續執行（沒有 error 級別問題）"""
        return len(self.errors) == 0


class ConnectionValidator:
    """連接驗證器"""

    # 類型兼容性規則
    TYPE_COMPATIBILITY = {
        "number": ["number", "integer", "domain", "interval", "unknown"],
        "integer": ["number", "integer", "unknown"],
        "point": ["point", "geometry", "unknown"],
        "curve": ["curve", "geometry", "unknown"],
        "surface": ["surface", "geometry", "brep", "unknown"],
        "brep": ["brep", "geometry", "unknown"],
        "mesh": ["mesh", "geometry", "unknown"],
        "plane": ["plane", "unknown"],
        "vector": ["vector", "unknown"],
        "geometry": ["point", "curve", "surface", "brep", "mesh", "geometry", "unknown"],
        "box": ["box", "brep", "geometry", "unknown"],
        "text": ["text", "unknown"],
        "boolean": ["boolean", "unknown"],
        "transform": ["transform", "unknown"],
        # WASP 類型
        "wasp_connection": ["wasp_connection", "unknown"],
        "wasp_part": ["wasp_part", "unknown"],
        "wasp_rule": ["wasp_rule", "unknown"],
        "wasp_aggregation": ["wasp_aggregation", "unknown"],
        # 通配
        "unknown": ["unknown"],
    }

    # 類型轉換建議
    TYPE_CONVERSION_SUGGESTIONS = {
        ("number", "plane"): "使用 'XY Plane' 組件將 Point 轉換為 Plane",
        ("number", "point"): "使用 'Construct Point' 組件將數值轉換為 Point",
        ("number", "vector"): "使用 'Unit X/Y/Z' 組件將數值轉換為 Vector",
        ("point", "plane"): "使用 'XY Plane' 組件將 Point 轉換為 Plane",
        ("brep", "mesh"): "使用 'Mesh Brep' 組件將 Brep 轉換為 Mesh",
        ("box", "mesh"): "使用 'Mesh Box' 組件將 Box 轉換為 Mesh",
        ("curve", "point"): "使用 'Evaluate Curve' 或 'Divide Curve' 提取 Point",
        ("surface", "curve"): "使用 'Iso Curve' 或 'Contour' 提取 Curve",
        ("text", "number"): "Panel 輸出的是文字，無法直接轉換為數值。改用 Number Slider",
    }

    def __init__(self, specs_path: Optional[Path] = None):
        if specs_path is None:
            specs_path = Path(__file__).parent.parent / "config" / "component_specs.json"

        self.specs: Dict = {}
        if specs_path.exists():
            with open(specs_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.specs = data.get("components", {})
            logger.info(f"已載入 {len(self.specs)} 個組件規格")
        else:
            logger.warning(f"組件規格文件不存在: {specs_path}")

    def validate_connection(
        self,
        from_comp: str,
        from_param: str,
        from_param_index: int,
        to_comp: str,
        to_param: str,
        to_param_index: int
    ) -> List[ValidationError]:
        """
        驗證單個連接

        Args:
            from_comp: 來源組件類型名
            from_param: 來源參數名（name 或 nickname）
            from_param_index: 來源參數索引
            to_comp: 目標組件類型名
            to_param: 目標參數名（name 或 nickname）
            to_param_index: 目標參數索引

        Returns:
            驗證錯誤列表
        """
        errors = []
        conn_id = f"{from_comp}.{from_param} -> {to_comp}.{to_param}"

        # 1. 驗證來源組件和參數
        source_spec = self.specs.get(from_comp)
        source_type = "unknown"

        if source_spec:
            source_outputs = source_spec.get("outputs", [])

            # 驗證索引是否有效
            if from_param_index >= len(source_outputs):
                errors.append(ValidationError(
                    connection_id=conn_id,
                    error_type="index_out_of_range",
                    message=f"{from_comp} 只有 {len(source_outputs)} 個輸出，索引 {from_param_index} 無效",
                    suggestion=f"使用索引 0-{len(source_outputs)-1}" if source_outputs else "檢查組件類型是否正確",
                    severity="error"
                ))
            elif from_param_index >= 0:
                expected_param = source_outputs[from_param_index]
                source_type = expected_param.get("type", "unknown")

                # 驗證參數名是否匹配索引
                if from_param:
                    expected_names = [expected_param.get("name", ""), expected_param.get("nickname", "")]
                    if from_param not in expected_names:
                        errors.append(ValidationError(
                            connection_id=conn_id,
                            error_type="param_name_mismatch",
                            message=f"{from_comp} 索引 {from_param_index} 的參數是 {expected_param.get('name')}/{expected_param.get('nickname')}，不是 '{from_param}'",
                            suggestion=f"使用 '{expected_param.get('nickname')}' 或索引 {from_param_index}",
                            severity="warning"
                        ))
        else:
            logger.debug(f"組件 {from_comp} 不在規格庫中")

        # 2. 驗證目標組件和參數
        target_spec = self.specs.get(to_comp)
        target_type = "unknown"

        if target_spec:
            target_inputs = target_spec.get("inputs", [])

            # 驗證索引是否有效
            if to_param_index >= len(target_inputs):
                errors.append(ValidationError(
                    connection_id=conn_id,
                    error_type="index_out_of_range",
                    message=f"{to_comp} 只有 {len(target_inputs)} 個輸入，索引 {to_param_index} 無效",
                    suggestion=f"使用索引 0-{len(target_inputs)-1}" if target_inputs else "檢查組件類型是否正確",
                    severity="error"
                ))
            elif to_param_index >= 0:
                expected_param = target_inputs[to_param_index]
                target_type = expected_param.get("type", "unknown")

                # 驗證參數名是否匹配索引
                if to_param:
                    expected_names = [expected_param.get("name", ""), expected_param.get("nickname", "")]
                    if to_param not in expected_names:
                        errors.append(ValidationError(
                            connection_id=conn_id,
                            error_type="param_name_mismatch",
                            message=f"{to_comp} 索引 {to_param_index} 的參數是 {expected_param.get('name')}/{expected_param.get('nickname')}，不是 '{to_param}'",
                            suggestion=f"使用 '{expected_param.get('nickname')}' 或索引 {to_param_index}",
                            severity="warning"
                        ))

        # 3. 驗證類型兼容性
        if source_type != "unknown" and target_type != "unknown":
            if not self._types_compatible(source_type, target_type):
                suggestion = self._get_type_conversion_suggestion(source_type, target_type)
                errors.append(ValidationError(
                    connection_id=conn_id,
                    error_type="type_mismatch",
                    message=f"類型不兼容: {source_type} -> {target_type}",
                    suggestion=suggestion,
                    severity="error"
                ))

        return errors

    def _types_compatible(self, from_type: str, to_type: str) -> bool:
        """檢查類型是否兼容"""
        from_type = from_type.lower()
        to_type = to_type.lower()

        if from_type == to_type:
            return True

        # 查詢兼容性表
        compatible_types = self.TYPE_COMPATIBILITY.get(from_type, [from_type])
        return to_type in compatible_types

    def _get_type_conversion_suggestion(self, from_type: str, to_type: str) -> str:
        """獲取類型轉換建議"""
        from_type = from_type.lower()
        to_type = to_type.lower()

        suggestion = self.TYPE_CONVERSION_SUGGESTIONS.get((from_type, to_type))
        if suggestion:
            return suggestion

        return f"需要將 {from_type} 轉換為 {to_type}"

    def validate_placement_info(self, placement_info: Dict) -> ValidationResult:
        """
        驗證完整的 placement_info

        Args:
            placement_info: placement_info.json 的內容

        Returns:
            ValidationResult
        """
        all_errors = []
        all_warnings = []

        # 建立組件 ID 到類型的映射
        id_to_type = {}
        for comp in placement_info.get("components", []):
            id_to_type[comp["id"]] = comp.get("type", "Unknown")

        # 驗證每個連接
        for conn in placement_info.get("connections", []):
            from_id = conn.get("from")
            to_id = conn.get("to")

            from_type = id_to_type.get(from_id)
            to_type = id_to_type.get(to_id)

            if from_type and to_type:
                conn_errors = self.validate_connection(
                    from_comp=from_type,
                    from_param=conn.get("fromParam", ""),
                    from_param_index=conn.get("fromParamIndex", 0),
                    to_comp=to_type,
                    to_param=conn.get("toParam", ""),
                    to_param_index=conn.get("toParamIndex", 0)
                )

                for err in conn_errors:
                    if err.severity == "error":
                        all_errors.append(err)
                    else:
                        all_warnings.append(err)

        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings
        )

    def validate_json_file(self, json_path: Path) -> ValidationResult:
        """
        驗證 JSON 文件

        Args:
            json_path: placement_info.json 的路徑

        Returns:
            ValidationResult
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            placement_info = json.load(f)

        return self.validate_placement_info(placement_info)

    def get_component_spec(self, comp_type: str) -> Optional[Dict]:
        """獲取組件規格"""
        return self.specs.get(comp_type)

    def suggest_connection(
        self,
        from_comp: str,
        from_param_index: int,
        to_comp: str
    ) -> Optional[int]:
        """
        根據輸出類型，建議合適的輸入參數索引

        Args:
            from_comp: 來源組件類型
            from_param_index: 來源參數索引
            to_comp: 目標組件類型

        Returns:
            建議的目標參數索引，或 None
        """
        source_spec = self.specs.get(from_comp)
        target_spec = self.specs.get(to_comp)

        if not source_spec or not target_spec:
            return None

        source_outputs = source_spec.get("outputs", [])
        target_inputs = target_spec.get("inputs", [])

        if from_param_index >= len(source_outputs):
            return None

        source_type = source_outputs[from_param_index].get("type", "unknown")

        # 找到第一個類型兼容的輸入
        for i, inp in enumerate(target_inputs):
            if self._types_compatible(source_type, inp.get("type", "unknown")):
                return i

        return None


def main():
    """測試驗證器"""
    validator = ConnectionValidator()

    print("=== 測試 ConnectionValidator ===\n")

    # 測試 1: 有效連接
    print("測試 1: 有效連接 (Multiplication.R -> Construct Point.X)")
    errors = validator.validate_connection(
        from_comp="Multiplication",
        from_param="R",
        from_param_index=0,
        to_comp="Construct Point",
        to_param="X",
        to_param_index=0
    )
    print(f"  錯誤數: {len(errors)}")
    for err in errors:
        print(f"  - [{err.severity}] {err.message}")

    # 測試 2: 索引錯誤
    print("\n測試 2: 索引錯誤 (Construct Point 只有 3 個輸入)")
    errors = validator.validate_connection(
        from_comp="Multiplication",
        from_param="R",
        from_param_index=0,
        to_comp="Construct Point",
        to_param="W",
        to_param_index=5
    )
    print(f"  錯誤數: {len(errors)}")
    for err in errors:
        print(f"  - [{err.severity}] {err.message}")
        print(f"    建議: {err.suggestion}")

    # 測試 3: 類型不兼容
    print("\n測試 3: 類型不兼容 (Panel.text -> Construct Point.X)")
    errors = validator.validate_connection(
        from_comp="Panel",
        from_param="out",
        from_param_index=0,
        to_comp="Construct Point",
        to_param="X",
        to_param_index=0
    )
    print(f"  錯誤數: {len(errors)}")
    for err in errors:
        print(f"  - [{err.severity}] {err.message}")
        print(f"    建議: {err.suggestion}")

    # 測試 4: WASP 連接 - Connection.GEO 必須是 Mesh
    print("\n測試 4: WASP Connection.GEO 類型檢查")
    spec = validator.get_component_spec("Connection From Direction")
    if spec:
        print(f"  Connection From Direction inputs:")
        for inp in spec.get("inputs", []):
            print(f"    [{inp['index']}] {inp['nickname']} ({inp['type']})")

    # 測試建議功能
    print("\n測試 5: 連接建議")
    suggested_idx = validator.suggest_connection(
        from_comp="Multiplication",
        from_param_index=0,
        to_comp="Construct Point"
    )
    print(f"  Multiplication[0] -> Construct Point 建議索引: {suggested_idx}")


if __name__ == "__main__":
    main()
