"""
GHX Parser - Grasshopper 文件解析器
====================================
解析 .ghx 文件的 XML 結構，提取元件、連接、群組等資訊
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import re
import logging

from .models import (
    GHDocument, GHComponent, GHConnection, GHGroup,
    Parameter, DataType, ComponentCategory
)

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# 元件 GUID 對照表 (常見元件)
# ============================================================

KNOWN_COMPONENT_GUIDS = {
    # Params - Primitive
    "57da07bd-ecab-415d-9d86-af36d7073abc": ("Number Slider", "Slider"),
    "59e0b89a-e487-49f8-bab8-b5bab16be14c": ("Panel", "Panel"),
    "d5967b9f-e8ee-436b-a8ad-29fdcecf32d5": ("Number", "Num"),
    "2e78987b-9dfb-42a2-8b76-3eba5fbc8226": ("Integer", "Int"),
    "d8d6edc6-b4a1-43b8-a54c-0e3c7d552a84": ("Boolean Toggle", "Toggle"),
    
    # Params - Geometry
    "8529dbdf-9b6f-42e9-8e1f-c7a2bde56a70": ("Point", "Pt"),
    "3581f42a-9592-4549-bd6b-1c0fc39d067b": ("Curve", "Crv"),
    "5a9e1695-ea02-4277-b381-23df1d080b1f": ("Surface", "Srf"),
    "2a8b0e2b-6d82-4696-8c0a-4cc5b4a7f521": ("Brep", "Brep"),
    
    # Maths - Domain
    "825ea536-aebb-41e6-a463-2ae4e609ed53": ("Construct Domain", "Dom"),
    "df8cce8f-ae39-452f-90ba-a5b8bad1de11": ("Range", "Range"),
    "4a7093e6-e7b5-4189-92e7-17f64e70dbc0": ("Series", "Series"),
    
    # Maths - Operators
    "a0d62394-a118-422d-abb3-6af115c75b25": ("Addition", "Add"),
    "ce46b74e-00c9-43c4-805a-193b69ea4a11": ("Subtraction", "Sub"),
    "4c619bc9-39fd-4717-82a6-1e07ea237bbe": ("Multiplication", "Mul"),
    "eb45c732-7b53-46ed-8641-4b90c4804b82": ("Division", "Div"),
    
    # Maths - Trig
    "7f5c6c55-f846-44d4-9edb-416fdf93ffc0": ("Sine", "Sin"),
    "14d53f06-f04f-4c35-bf60-d70dbf096eca": ("Cosine", "Cos"),
    
    # Maths - Util
    "b0a93f90-e946-47e9-a1e0-a34a3d0e10af": ("Remap Numbers", "ReMap"),
    "df33647b-75e5-4c8d-8a03-c5a5d8905d57": ("Graph Mapper", "Graph"),
    
    # Vector - Point
    "3581f42a-9592-4549-bd6b-1c0fc39d067b": ("Construct Point", "Pt"),
    "9abae6b7-fa1d-448c-9209-4a8155345841": ("Deconstruct Point", "DePt"),
    "933e7a23-e3c4-48a3-b2c8-2f8f0f94c8a7": ("Point XYZ", "XYZ"),
    
    # Vector - Vector
    "56b92eab-d121-43f7-94d3-6cd8f0ddead8": ("Unit X", "X"),
    "7f1c7e4d-b4ae-48b9-a8f9-d91c6e4f3c47": ("Unit Y", "Y"),
    "47b224ff-e8e9-4c42-91bc-8bb23d3ce918": ("Unit Z", "Z"),
    "15a50725-e3d3-4075-9f7c-142ba5f40747": ("Vector XYZ", "Vec"),
    "d8d6edc6-b4a1-43b8-a54c-0e3c7d552a84": ("Amplitude", "Amp"),
    
    # Curve - Primitive
    "c318e774-8f7a-4d2d-8560-f9c35d461779": ("Line", "Ln"),
    "807b86e3-be8e-445f-9673-d0b49e58e999": ("Line SDL", "Line"),
    "a4cd2751-414d-42ec-8916-476ebf62d7fe": ("Circle", "Cir"),
    "2bbb48f5-9a95-45e2-b812-8e7b3b95cab5": ("Arc", "Arc"),
    "f4070a37-c822-410e-9620-188ec1e4b347": ("Polyline", "Pline"),
    "5a9b8da7-f85a-49dd-a8d2-7f0d6f5dc5c5": ("Rectangle", "Rec"),
    
    # Curve - Spline
    "7bafe137-0175-4b53-92a7-b524f3d913e2": ("Interpolate", "IntCrv"),
    "d4b3aa47-5c03-4025-b0cc-e377e6bb3c39": ("Nurbs Curve", "Nurbs"),
    
    # Curve - Analysis
    "11bbd48b-bb0a-4f1b-8167-fa297590390d": ("Evaluate Curve", "EvalCrv"),
    "d62dd5f6-f3af-4f0e-a65e-84defe4c40d3": ("Curve Length", "Len"),
    
    # Curve - Division
    "f12daa2f-4fd5-48c1-8ac3-5dea476912ca": ("Divide Curve", "Div"),
    "05df93ed-97e0-4cff-85a6-44f0f7ee62ca": ("Divide Length", "DivLen"),
    "e6c3423f-5f9e-41ab-9e21-3e5b42a14e51": ("Shatter", "Shatter"),
    
    # Curve - Util
    "4c4e56eb-2f04-43f9-95a3-cc46a14f495a": ("Join Curves", "Join"),
    "9c53bac0-ba66-40bd-8154-ce9829b9db1e": ("Flip Curve", "Flip"),
    "e35c8b96-f25d-4f8b-9cb6-92a29ad9d4e6": ("Offset Curve", "Offset"),
    
    # Surface - Freeform
    "4c619bc9-39fd-4717-82a6-1e07ea237bbe": ("Loft", "Loft"),
    "fe0e7c0c-7123-4a9c-9c10-e86199295043": ("Extrude", "Extr"),
    "3d9df4f8-f42c-4eca-8ba7-2f8f90c7f8f9": ("Revolve", "Rev"),
    "6b54c82b-c173-4b6c-9c0c-8c0a3f3c7b82": ("Sweep1", "Swp1"),
    
    # Surface - Analysis
    "9bcd1f38-3add-4f15-aaf3-ef8e79e0e0a8": ("Evaluate Surface", "EvalSrf"),
    
    # Transform - Euclidean
    "bc194e76-c227-4c0d-9e34-4b9ec95c4e34": ("Move", "Move"),
    "a7c97e13-3c8b-4f95-be48-95c9b0c0d9d1": ("Rotate", "Rot"),
    "6b0b0da4-8c0c-4c12-8c0a-4cc5b4a7f521": ("Scale", "Scale"),
    "7731a923-46a1-4df7-9d6e-8a7f7c0e0f3a": ("Mirror", "Mirror"),
    "9a54b8c5-f3e8-4f0a-9c0c-8c0a3f3c7b82": ("Orient", "Orient"),
    
    # Transform - Array
    "6b0e6b6c-2e24-4a23-a66e-5d9e4e5c9e9d": ("Linear Array", "ArrLin"),
    "e33f9e33-e8e9-4c42-91bc-8bb23d3ce918": ("Rectangular Array", "ArrRec"),
    "b3e8a8d5-f3e8-4f0a-9c0c-8c0a3f3c7b82": ("Polar Array", "ArrPol"),
    
    # Sets - List
    "d1a785c7-7f3a-4e78-b6e6-97ad95ae69f7": ("List Item", "Item"),
    "9c53bac0-ba66-40bd-8154-ce9829b9db1e": ("List Length", "Lng"),
    "0c9d2714-58b3-48db-9f20-d88a1f2a5e51": ("Reverse List", "Rev"),
    "9a53f913-89ca-427d-8d37-c9a6e0d51779": ("Shift List", "Shift"),
    "a9c1e336-eee4-4280-a1b0-6a5a7a8a0f7b": ("Sort List", "Sort"),
    
    # Sets - Tree
    "d1a785c7-7f3a-4e78-b6e6-97ad95ae69f7": ("Flatten", "Flat"),
    "5f8c8c6f-3e8e-4f0a-9c0c-8c0a3f3c7b82": ("Graft", "Graft"),
    "7f8c8c6f-3e8e-4f0a-9c0c-8c0a3f3c7b82": ("Simplify", "Simp"),
    
    # Display
    "8d6e6b6c-2e24-4a23-a66e-5d9e4e5c9e9d": ("Custom Preview", "Preview"),
    "b0b0da4-8c0c-4c12-8c0a-4cc5b4a7f521": ("Colour Swatch", "Swatch"),
}


# 根據元件名稱推斷分類
CATEGORY_KEYWORDS = {
    ComponentCategory.PARAMS: ["slider", "panel", "number", "integer", "boolean", "point", "curve", "surface", "brep", "geometry"],
    ComponentCategory.MATHS: ["add", "sub", "mul", "div", "math", "sin", "cos", "tan", "domain", "range", "series", "remap", "graph"],
    ComponentCategory.VECTOR: ["vector", "point", "plane", "amplitude", "unit", "cross", "dot"],
    ComponentCategory.CURVE: ["curve", "line", "circle", "arc", "polyline", "interpolate", "nurbs", "divide", "evaluate", "length", "offset", "join", "fillet"],
    ComponentCategory.SURFACE: ["surface", "loft", "extrude", "revolve", "sweep", "patch", "boundary"],
    ComponentCategory.MESH: ["mesh", "deconstruct mesh", "mesh join"],
    ComponentCategory.TRANSFORM: ["move", "rotate", "scale", "mirror", "orient", "array", "morph"],
    ComponentCategory.SETS: ["list", "tree", "flatten", "graft", "partition", "cull", "dispatch", "item", "shift", "reverse"],
    ComponentCategory.INTERSECT: ["intersect", "collision", "project", "closest"],
    ComponentCategory.DISPLAY: ["preview", "colour", "color", "display", "bake"],
}


class GHXParser:
    """Grasshopper .ghx 文件解析器"""
    
    def __init__(self):
        self.document: Optional[GHDocument] = None
        self._component_map: Dict[str, GHComponent] = {}
        # 映射: param_guid -> (component_guid, "input"|"output", index)
        self._param_source_map: Dict[str, Tuple[str, str, int]] = {}
    
    def parse_file(self, filepath: str) -> GHDocument:
        """
        解析 .ghx 文件
        
        Args:
            filepath: .ghx 文件路徑
            
        Returns:
            GHDocument 物件
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        if path.suffix.lower() != '.ghx':
            raise ValueError(f"Expected .ghx file, got: {path.suffix}")
        
        logger.info(f"Parsing GHX file: {filepath}")
        
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        self.document = GHDocument(filepath=str(path.absolute()))
        
        # 解析文件元資料
        self._parse_metadata(root)
        
        # 解析元件定義
        self._parse_definition(root)
        
        # 建立連接關係
        self._build_connections()
        
        logger.info(f"Parsed {self.document.component_count} components, "
                   f"{self.document.connection_count} connections")
        
        return self.document
    
    def parse_string(self, xml_string: str) -> GHDocument:
        """
        解析 XML 字串
        
        Args:
            xml_string: .ghx 文件的 XML 內容
            
        Returns:
            GHDocument 物件
        """
        root = ET.fromstring(xml_string)
        
        self.document = GHDocument()
        
        self._parse_metadata(root)
        self._parse_definition(root)
        self._build_connections()
        
        return self.document
    
    def _parse_metadata(self, root: ET.Element):
        """解析文件元資料"""
        # 尋找 Archive 標籤的屬性
        if root.tag == "Archive":
            self.document.grasshopper_version = root.get("name", "")
        
        # 尋找 DocumentHeader
        header = self._find_element(root, "DocumentHeader")
        if header:
            doc_id = self._find_element(header, "DocumentID")
            if doc_id is not None and doc_id.text:
                self.document.document_id = doc_id.text
    
    def _parse_definition(self, root: ET.Element):
        """解析定義區塊"""
        # GHX 結構: Archive > chunks > chunk[@name="Definition"] > chunks > chunk[@name="DefinitionObjects"]
        definition = self._find_chunk(root, "Definition")
        if definition is None:
            logger.warning("No Definition chunk found")
            return
        
        def_objects = self._find_chunk(definition, "DefinitionObjects")
        if def_objects is None:
            logger.warning("No DefinitionObjects chunk found")
            return
        
        # 解析物件列表
        object_chunks = self._find_all_chunks(def_objects, "Object")
        
        for obj_chunk in object_chunks:
            self._parse_object(obj_chunk)
    
    def _parse_object(self, obj_chunk: ET.Element):
        """解析單個物件（元件）"""
        # 取得物件類型
        guid = self._get_item_value(obj_chunk, "GUID")
        name = self._get_item_value(obj_chunk, "Name")
        nickname = self._get_item_value(obj_chunk, "NickName", name)
        
        if not guid:
            return
        
        # 建立元件
        component = GHComponent(
            instance_guid=guid,
            component_guid=self._get_item_value(obj_chunk, "ComponentGuid", ""),
            name=name or "Unknown",
            nickname=nickname or name or "Unknown"
        )
        
        # 解析位置
        pivot = self._get_item_value(obj_chunk, "Pivot")
        if pivot:
            component.pivot = self._parse_point2d(pivot)
            component.position = component.pivot
        
        # 推斷分類
        component.category = self._infer_category(component.name)
        
        # 解析輸入輸出參數
        container = self._find_chunk(obj_chunk, "Container")
        if container:
            self._parse_parameters(container, component)
        
        # 解析屬性
        self._parse_component_properties(obj_chunk, component)
        
        self.document.components[guid] = component
        self._component_map[guid] = component
    
    def _parse_parameters(self, container: ET.Element, component: GHComponent):
        """解析元件的輸入輸出參數"""
        input_index = 0
        output_index = 0
        
        # 遍歷所有 chunk
        for chunk in container.iter("chunk"):
            chunk_name = chunk.get("name", "")
            
            # 支援兩種格式: "param_input" 或 "InputParam"
            if "param_input" in chunk_name or chunk_name == "InputParam":
                param = self._parse_single_parameter(chunk, input_index)
                if param:
                    # 記錄參數 GUID 與元件的對應
                    param_guid = self._get_item_value(chunk, "InstanceGuid")
                    if param_guid:
                        self._param_source_map[self._clean_guid(param_guid)] = (
                            component.instance_guid,
                            "input",
                            input_index
                        )
                    component.inputs.append(param)
                    input_index += 1

            # 支援兩種格式: "param_output" 或 "OutputParam"
            elif "param_output" in chunk_name or chunk_name == "OutputParam":
                param = self._parse_single_parameter(chunk, output_index)
                if param:
                    # 記錄輸出參數 GUID
                    param_guid = self._get_item_value(chunk, "InstanceGuid")
                    if param_guid:
                        self._param_source_map[self._clean_guid(param_guid)] = (
                            component.instance_guid,
                            "output",
                            output_index
                        )
                    component.outputs.append(param)
                    output_index += 1
    
    def _parse_single_parameter(self, param_chunk: ET.Element, index: int) -> Optional[Parameter]:
        """解析單個參數"""
        name = self._get_item_value(param_chunk, "Name")
        nickname = self._get_item_value(param_chunk, "NickName", name)
        
        if not name:
            return None
        
        param = Parameter(
            name=name,
            nickname=nickname or name,
            index=index,
            data_type=self._infer_data_type(name)
        )
        
        # 解析來源連接 (用於建立連接關係)
        # Source 是直接帶有 GUID 文字的 item 標籤
        for item in param_chunk.iter("item"):
            if item.get("name") == "Source" and item.text:
                # Source item 直接包含來源參數的 GUID
                param.connected_sources.append(item.text)

        return param
    
    def _parse_component_properties(self, obj_chunk: ET.Element, component: GHComponent):
        """解析元件特定屬性"""
        # Slider 特有屬性
        if "slider" in component.name.lower():
            slider_val = self._get_item_value(obj_chunk, "Value")
            slider_min = self._get_item_value(obj_chunk, "Min")
            slider_max = self._get_item_value(obj_chunk, "Max")
            
            if slider_val:
                component.properties["value"] = float(slider_val)
            if slider_min:
                component.properties["min"] = float(slider_min)
            if slider_max:
                component.properties["max"] = float(slider_max)
        
        # Panel 特有屬性
        elif "panel" in component.name.lower():
            text = self._get_item_value(obj_chunk, "UserText")
            if text:
                component.properties["text"] = text
        
        # 檢查是否被禁用
        enabled = self._get_item_value(obj_chunk, "Enabled")
        if enabled and enabled.lower() == "false":
            component.is_disabled = True
    
    def _build_connections(self):
        """根據參數的 Source 建立連接關係"""
        for comp_guid, component in self.document.components.items():
            for inp_idx, inp in enumerate(component.inputs):
                for source_ref in inp.connected_sources:
                    # source_ref 是來源輸出參數的 GUID，格式如 "{guid}"
                    source_param_guid = self._clean_guid(source_ref)
                    
                    # 從映射表查找來源元件資訊
                    source_info = self._param_source_map.get(source_param_guid)
                    
                    if source_info:
                        source_comp_guid, param_type, param_index = source_info
                        
                        # 只有當來源是輸出參數時才建立連接
                        if param_type == "output" and source_comp_guid in self.document.components:
                            source_comp = self.document.components[source_comp_guid]
                            
                            # 取得輸出參數名稱
                            output_name = "output"
                            if param_index < len(source_comp.outputs):
                                output_name = source_comp.outputs[param_index].name
                            
                            connection = GHConnection(
                                source_component_id=source_comp_guid,
                                source_output_index=param_index,
                                source_output_name=output_name,
                                target_component_id=comp_guid,
                                target_input_index=inp_idx,
                                target_input_name=inp.name
                            )
                            
                            self.document.connections.append(connection)
    
    # ============================================================
    # XML 輔助方法
    # ============================================================
    
    def _find_element(self, parent: ET.Element, tag: str) -> Optional[ET.Element]:
        """遞迴尋找特定標籤的元素"""
        for elem in parent.iter():
            if elem.tag == tag:
                return elem
        return None
    
    def _find_chunk(self, parent: ET.Element, chunk_name: str) -> Optional[ET.Element]:
        """尋找特定名稱的 chunk"""
        for chunk in parent.iter("chunk"):
            if chunk.get("name") == chunk_name:
                return chunk
        return None
    
    def _find_all_chunks(self, parent: ET.Element, chunk_name: str) -> List[ET.Element]:
        """尋找所有特定名稱的 chunk"""
        results = []
        for chunk in parent.iter("chunk"):
            if chunk.get("name") == chunk_name:
                results.append(chunk)
        return results
    
    def _get_item_value(self, parent: ET.Element, item_name: str, default: str = "") -> str:
        """取得 item 的值"""
        for item in parent.iter("item"):
            if item.get("name") == item_name:
                return item.text or default
        return default
    
    def _get_all_item_values(self, parent: ET.Element, item_name: str) -> List[str]:
        """取得所有同名 item 的值"""
        return [
            item.text for item in parent.iter("item")
            if item.get("name") == item_name and item.text
        ]
    
    def _parse_point2d(self, point_str: str) -> Tuple[float, float]:
        """解析 2D 點座標字串"""
        # 格式可能是 "123.45, 67.89" 或 "{123.45, 67.89}"
        clean = point_str.strip("{}() ")
        parts = clean.split(",")
        if len(parts) >= 2:
            try:
                return (float(parts[0].strip()), float(parts[1].strip()))
            except ValueError:
                pass
        return (0.0, 0.0)
    
    def _clean_guid(self, guid_str: str) -> str:
        """清理 GUID 字串"""
        return guid_str.strip("{}").lower()
    
    def _infer_category(self, name: str) -> ComponentCategory:
        """根據元件名稱推斷分類"""
        name_lower = name.lower()
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return category
        return ComponentCategory.UNKNOWN
    
    def _infer_data_type(self, param_name: str) -> DataType:
        """根據參數名稱推斷資料類型"""
        name_lower = param_name.lower()
        
        type_mapping = {
            "point": DataType.POINT,
            "curve": DataType.CURVE,
            "surface": DataType.SURFACE,
            "brep": DataType.BREP,
            "mesh": DataType.MESH,
            "number": DataType.NUMBER,
            "integer": DataType.INTEGER,
            "boolean": DataType.BOOLEAN,
            "text": DataType.TEXT,
            "string": DataType.TEXT,
            "vector": DataType.VECTOR,
            "plane": DataType.PLANE,
            "transform": DataType.TRANSFORM,
            "domain": DataType.DOMAIN,
            "interval": DataType.INTERVAL,
            "color": DataType.COLOR,
            "colour": DataType.COLOR,
            "geometry": DataType.GEOMETRY,
        }
        
        for key, dtype in type_mapping.items():
            if key in name_lower:
                return dtype
        
        return DataType.UNKNOWN


# ============================================================
# 便利函數
# ============================================================

def parse_ghx(filepath: str) -> GHDocument:
    """
    解析 GHX 文件的便利函數
    
    Args:
        filepath: .ghx 文件路徑
        
    Returns:
        GHDocument 物件
    """
    parser = GHXParser()
    return parser.parse_file(filepath)


def parse_ghx_string(xml_string: str) -> GHDocument:
    """
    解析 GHX XML 字串的便利函數
    
    Args:
        xml_string: XML 內容
        
    Returns:
        GHDocument 物件
    """
    parser = GHXParser()
    return parser.parse_string(xml_string)


# ============================================================
# CLI 介面
# ============================================================

if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python ghx_parser.py <file.ghx> [--json]")
        sys.exit(1)
    
    filepath = sys.argv[1]
    output_json = "--json" in sys.argv
    
    try:
        doc = parse_ghx(filepath)
        
        if output_json:
            print(doc.to_json())
        else:
            print(doc.summary())
            print("\n--- Connections ---")
            for conn in doc.connections[:20]:  # 只顯示前 20 個
                src = doc.components.get(conn.source_component_id)
                tgt = doc.components.get(conn.target_component_id)
                src_name = src.nickname if src else "?"
                tgt_name = tgt.nickname if tgt else "?"
                print(f"  {src_name}[{conn.source_output_name}] -> {tgt_name}[{conn.target_input_name}]")
            
            if len(doc.connections) > 20:
                print(f"  ... and {len(doc.connections) - 20} more connections")
                
    except Exception as e:
        logger.error(f"Error parsing file: {e}")
        sys.exit(1)
