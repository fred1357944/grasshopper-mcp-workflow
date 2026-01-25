#!/usr/bin/env python3
"""
GHX Parser - 批量解析 Grasshopper .ghx 文件

.ghx 文件結構: gzip 壓縮的 XML
"""

import gzip
import xml.etree.ElementTree as ET
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Parameter:
    """組件參數"""
    nickname: str
    name: str
    type_hint: Optional[str] = None
    type_hint_id: Optional[str] = None  # TypeHintID GUID
    access: int = 0  # 0=Item, 1=List, 2=Tree
    source_count: int = 0
    is_optional: bool = False  # 根據描述或 source_count 推斷


@dataclass
class Component:
    """Grasshopper 組件"""
    instance_guid: str
    component_guid: str
    name: str
    nickname: str
    category: str = ""
    subcategory: str = ""
    inputs: List[Parameter] = field(default_factory=list)
    outputs: List[Parameter] = field(default_factory=list)
    position_x: float = 0.0
    position_y: float = 0.0


@dataclass
class Connection:
    """組件連接"""
    from_component: str  # instance GUID
    from_param: str      # parameter name/index
    to_component: str    # instance GUID
    to_param: str        # parameter name/index


@dataclass
class GHXDocument:
    """解析後的 GHX 文件"""
    file_path: str
    components: List[Component] = field(default_factory=list)
    connections: List[Connection] = field(default_factory=list)
    groups: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class GHXParser:
    """Grasshopper .ghx 文件解析器"""

    def __init__(self):
        self.parsed_count = 0
        self.error_count = 0
        self.errors = []

    def parse_ghx(self, ghx_path: str) -> Optional[GHXDocument]:
        """解析單個 .ghx 文件"""
        path = Path(ghx_path)

        if not path.exists():
            self.errors.append(f"File not found: {ghx_path}")
            self.error_count += 1
            return None

        try:
            # .ghx/.gh 可能是 gzip 壓縮或純 XML
            # 先嘗試純 XML (處理 UTF-8 BOM)，失敗再嘗試 gzip
            content = None

            if path.suffix.lower() in ['.ghx', '.gh']:
                # 嘗試 1: 純 XML (可能有 UTF-8 BOM)
                try:
                    with open(path, 'r', encoding='utf-8-sig') as f:
                        content = f.read()
                    # 驗證是否為有效 XML
                    if not content.strip().startswith('<?xml') and not content.strip().startswith('<'):
                        content = None  # 不是 XML，嘗試 gzip
                except UnicodeDecodeError:
                    content = None

                # 嘗試 2: gzip 壓縮
                if content is None:
                    try:
                        with gzip.open(path, 'rt', encoding='utf-8') as f:
                            content = f.read()
                    except (gzip.BadGzipFile, OSError):
                        pass

                if content is None:
                    self.errors.append(f"Cannot read file (not XML or gzip): {ghx_path}")
                    self.error_count += 1
                    return None
            else:
                self.errors.append(f"Unsupported file type: {path.suffix}")
                return None

            root = ET.fromstring(content)

            doc = GHXDocument(
                file_path=str(path),
                components=self._extract_components(root),
                connections=self._extract_connections(root),
                groups=self._extract_groups(root),
                metadata=self._extract_metadata(root)
            )

            self.parsed_count += 1
            return doc

        except ET.ParseError as e:
            self.errors.append(f"XML parse error in {ghx_path}: {e}")
            self.error_count += 1
            return None
        except Exception as e:
            self.errors.append(f"Error parsing {ghx_path}: {e}")
            self.error_count += 1
            return None

    def _extract_components(self, root: ET.Element) -> List[Component]:
        """提取所有組件"""
        components = []

        # 優先使用 chunk-based 格式 (較新的 GH 格式)
        for chunk in root.findall(".//chunk[@name='Object']"):
            component = self._parse_chunk_object(chunk)
            if component:
                components.append(component)

        # 如果沒找到 chunk 格式，嘗試舊格式
        if not components:
            for obj in root.iter():
                if obj.tag == 'Object' or obj.get('Guid') or obj.get('ComponentGuid'):
                    component = self._parse_component_node(obj)
                    if component:
                        components.append(component)

        return components

    def _parse_component_node(self, obj: ET.Element) -> Optional[Component]:
        """解析組件節點"""
        instance_guid = obj.get('Guid') or obj.get('InstanceGuid') or ''
        component_guid = obj.get('ComponentGuid') or ''

        if not instance_guid and not component_guid:
            return None

        name = obj.get('Name') or ''
        nickname = obj.get('NickName') or obj.get('Nickname') or ''

        # 提取輸入輸出參數
        inputs = []
        outputs = []

        for inp in obj.findall(".//InputParam") + obj.findall(".//Input"):
            inputs.append(Parameter(
                nickname=inp.get('NickName', inp.get('Nickname', '')),
                name=inp.get('Name', ''),
                type_hint=inp.get('TypeHint', inp.get('Type', ''))
            ))

        for out in obj.findall(".//OutputParam") + obj.findall(".//Output"):
            outputs.append(Parameter(
                nickname=out.get('NickName', out.get('Nickname', '')),
                name=out.get('Name', ''),
                type_hint=out.get('TypeHint', out.get('Type', ''))
            ))

        return Component(
            instance_guid=instance_guid,
            component_guid=component_guid,
            name=name,
            nickname=nickname,
            inputs=inputs,
            outputs=outputs
        )

    def _parse_chunk_object(self, chunk: ET.Element) -> Optional[Component]:
        """解析 chunk 格式的組件（較新的 GH 格式）"""
        # 提取基本屬性 - 從 Object chunk 的 items 中
        component_guid = ''
        name = ''

        for item in chunk.findall("items/item"):
            item_name = item.get('name', '')
            if item_name == 'GUID':
                component_guid = item.text or ''
            elif item_name == 'Name':
                name = item.text or ''

        # 從 Container chunk 中提取更多資訊
        container = chunk.find(".//chunk[@name='Container']")
        instance_guid = ''
        nickname = ''
        inputs = []
        outputs = []

        if container is not None:
            for item in container.findall("items/item"):
                item_name = item.get('name', '')
                if item_name == 'InstanceGuid':
                    instance_guid = item.text or ''
                elif item_name == 'NickName':
                    nickname = item.text or ''
                elif item_name == 'Name' and not name:
                    name = item.text or ''

            # 提取輸入參數 - 支援多種格式
            # 格式 1: param_input (原生 GH 組件)
            for param_chunk in container.findall(".//chunk[@name='param_input']"):
                param = self._parse_param_chunk(param_chunk)
                if param:
                    inputs.append(param)

            # 格式 2: InputParam (插件組件，如 WASP, Karamba)
            # 這些參數在 ParameterData chunk 內
            param_data = container.find(".//chunk[@name='ParameterData']")
            if param_data is not None:
                for param_chunk in param_data.findall(".//chunk[@name='InputParam']"):
                    param = self._parse_param_chunk(param_chunk)
                    if param:
                        inputs.append(param)

                for param_chunk in param_data.findall(".//chunk[@name='OutputParam']"):
                    param = self._parse_param_chunk(param_chunk)
                    if param:
                        outputs.append(param)

            # 提取輸出參數 - 格式 1: param_output (原生 GH 組件)
            for param_chunk in container.findall(".//chunk[@name='param_output']"):
                param = self._parse_param_chunk(param_chunk)
                if param:
                    outputs.append(param)

        # 跳過 Group 等非組件物件
        if name == 'Group' or not (instance_guid or component_guid):
            return None

        return Component(
            instance_guid=instance_guid,
            component_guid=component_guid,
            name=name,
            nickname=nickname,
            inputs=inputs,
            outputs=outputs
        )

    def _parse_param_chunk(self, param_chunk: ET.Element) -> Optional[Parameter]:
        """解析參數 chunk - 增強版：提取 Access, TypeHintID"""
        name = ''
        nickname = ''
        source_count = 0
        access = 0  # 預設 Item
        type_hint_id = None
        description = ''

        for item in param_chunk.findall("items/item"):
            item_name = item.get('name', '')
            if item_name == 'Name':
                name = item.text or ''
            elif item_name == 'NickName':
                nickname = item.text or ''
            elif item_name == 'SourceCount':
                source_count = int(item.text or '0')
            elif item_name == 'Access':
                # Access: 0=Item, 1=List, 2=Tree
                try:
                    access = int(item.text or '0')
                except ValueError:
                    access = 0
            elif item_name == 'TypeHintID':
                type_hint_id = item.text or None
            elif item_name == 'Description':
                description = item.text or ''

        # 推斷是否為選填參數（描述中包含 Optional 或 source_count 通常為 0）
        is_optional = 'optional' in description.lower() if description else False

        if nickname or name:
            return Parameter(
                nickname=nickname or name,
                name=name or nickname,
                type_hint_id=type_hint_id,
                access=access,
                source_count=source_count,
                is_optional=is_optional
            )
        return None

    def _extract_connections(self, root: ET.Element) -> List[Connection]:
        """提取所有連接"""
        connections = []

        # 先嘗試 chunk-based 格式
        # 在這個格式中，連線資訊嵌入在 param_input/param_output 的 Source 元素
        # 需要建立 param InstanceGuid -> (component InstanceGuid, param name) 的映射

        # 步驟 1: 建立參數 InstanceGuid 到 (組件 InstanceGuid, 參數名) 的映射
        param_to_component = {}  # param_instance_guid -> (component_instance_guid, param_name)

        for obj_chunk in root.findall(".//chunk[@name='Object']"):
            container = obj_chunk.find(".//chunk[@name='Container']")
            if container is None:
                continue

            # 獲取組件 InstanceGuid
            comp_instance_guid = ''
            for item in container.findall("items/item"):
                if item.get('name') == 'InstanceGuid':
                    comp_instance_guid = item.text or ''
                    break

            if not comp_instance_guid:
                continue

            # 記錄所有輸出參數 - 支援兩種格式
            # 格式 1: param_output (原生 GH 組件)
            # 格式 2: ParameterData/OutputParam (插件組件如 WASP, Karamba)
            output_chunks = (
                container.findall(".//chunk[@name='param_output']") +
                container.findall(".//chunk[@name='OutputParam']")
            )
            for param_chunk in output_chunks:
                param_instance_guid = ''
                param_name = ''
                for item in param_chunk.findall("items/item"):
                    if item.get('name') == 'InstanceGuid':
                        param_instance_guid = item.text or ''
                    elif item.get('name') == 'NickName':
                        param_name = item.text or ''
                    elif item.get('name') == 'Name' and not param_name:
                        param_name = item.text or ''

                if param_instance_guid:
                    param_to_component[param_instance_guid] = (comp_instance_guid, param_name)

        # 步驟 2: 從 param_input 的 Source 元素提取連線
        for obj_chunk in root.findall(".//chunk[@name='Object']"):
            container = obj_chunk.find(".//chunk[@name='Container']")
            if container is None:
                continue

            # 獲取目標組件 InstanceGuid
            to_comp_guid = ''
            for item in container.findall("items/item"):
                if item.get('name') == 'InstanceGuid':
                    to_comp_guid = item.text or ''
                    break

            if not to_comp_guid:
                continue

            # 檢查每個輸入參數的 Source - 支援兩種格式
            input_chunks = (
                container.findall(".//chunk[@name='param_input']") +
                container.findall(".//chunk[@name='InputParam']")
            )
            for param_chunk in input_chunks:
                to_param_name = ''
                for item in param_chunk.findall("items/item"):
                    if item.get('name') == 'NickName':
                        to_param_name = item.text or ''
                    elif item.get('name') == 'Name' and not to_param_name:
                        to_param_name = item.text or ''

                # 獲取所有 Source（一個輸入可能有多個來源）
                for item in param_chunk.findall("items/item[@name='Source']"):
                    source_guid = item.text or ''
                    if source_guid and source_guid in param_to_component:
                        from_comp_guid, from_param_name = param_to_component[source_guid]
                        connections.append(Connection(
                            from_component=from_comp_guid,
                            from_param=from_param_name,
                            to_component=to_comp_guid,
                            to_param=to_param_name
                        ))

        # 如果沒找到 chunk 格式的連線，嘗試 Wire 格式
        if not connections:
            for wire in root.iter('Wire'):
                conn = Connection(
                    from_component=wire.get('FromObject', ''),
                    from_param=wire.get('FromParam', ''),
                    to_component=wire.get('ToObject', ''),
                    to_param=wire.get('ToParam', '')
                )
                if conn.from_component and conn.to_component:
                    connections.append(conn)

        return connections

    def _extract_groups(self, root: ET.Element) -> List[Dict]:
        """提取組群資訊"""
        groups = []

        for group in root.iter('Group'):
            groups.append({
                'name': group.get('Name', ''),
                'nickname': group.get('NickName', ''),
                'colour': group.get('Colour', ''),
                'members': [m.text for m in group.findall('.//Member') if m.text]
            })

        return groups

    def _extract_metadata(self, root: ET.Element) -> Dict[str, Any]:
        """提取文件元數據"""
        metadata = {}

        # 文件版本
        definition = root.find('.//Definition') or root
        metadata['version'] = definition.get('Version', '')
        metadata['name'] = definition.get('Name', '')

        # 作者資訊
        author = root.find('.//Author')
        if author is not None:
            metadata['author'] = author.text or ''

        return metadata

    def batch_parse(self, folder: str, recursive: bool = True) -> List[GHXDocument]:
        """批量解析資料夾內的 .ghx/.gh 文件"""
        results = []
        folder_path = Path(folder)

        if not folder_path.exists():
            print(f"Folder not found: {folder}")
            return results

        pattern = "**/*.gh*" if recursive else "*.gh*"

        for file_path in folder_path.glob(pattern):
            if file_path.suffix.lower() in ['.ghx', '.gh']:
                print(f"Parsing: {file_path.name}")
                doc = self.parse_ghx(str(file_path))
                if doc:
                    results.append(doc)

        print(f"\nParsed: {self.parsed_count}, Errors: {self.error_count}")
        return results

    def to_json(self, documents: List[GHXDocument], output_path: str = None) -> str:
        """將解析結果轉為 JSON"""
        data = []
        for doc in documents:
            doc_dict = {
                'file': doc.file_path,
                'metadata': doc.metadata,
                'component_count': len(doc.components),
                'connection_count': len(doc.connections),
                'components': [asdict(c) for c in doc.components],
                'connections': [asdict(c) for c in doc.connections],
                'groups': doc.groups
            }
            data.append(doc_dict)

        json_str = json.dumps(data, indent=2, ensure_ascii=False)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            print(f"Saved to: {output_path}")

        return json_str


# CLI 介面
if __name__ == "__main__":
    import sys

    parser = GHXParser()

    if len(sys.argv) < 2:
        print("Usage: python ghx_parser.py <folder_or_file> [output.json]")
        print("\nExamples:")
        print("  python ghx_parser.py ./ghx_samples/")
        print("  python ghx_parser.py myfile.ghx output.json")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    path = Path(input_path)

    if path.is_dir():
        docs = parser.batch_parse(input_path)
    elif path.is_file():
        doc = parser.parse_ghx(input_path)
        docs = [doc] if doc else []
    else:
        print(f"Path not found: {input_path}")
        sys.exit(1)

    if docs:
        json_output = parser.to_json(docs, output_path)
        if not output_path:
            print("\n--- Parsed Result ---")
            print(json_output[:2000] + "..." if len(json_output) > 2000 else json_output)

    if parser.errors:
        print("\n--- Errors ---")
        for err in parser.errors:
            print(f"  - {err}")
