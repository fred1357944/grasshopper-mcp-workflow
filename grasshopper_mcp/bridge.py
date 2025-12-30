import socket
import json
import sys
import traceback
from typing import Dict, Any, Optional

# 使用 MCP 服務器
from mcp.server.fastmcp import FastMCP

# 設置 Grasshopper MCP 連接參數
GRASSHOPPER_HOST = "localhost"
GRASSHOPPER_PORT = 8080  # 默認端口，可以根據需要修改

# 創建 MCP 服務器
server = FastMCP("Grasshopper Bridge")

def send_to_grasshopper(command_type: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """向 Grasshopper MCP 發送命令"""
    if params is None:
        params = {}
    
    # 創建命令
    command = {
        "type": command_type,
        "parameters": params
    }
    
    try:
        print(f"Sending command to Grasshopper: {command_type} with params: {params}", file=sys.stderr)
        
        # 連接到 Grasshopper MCP
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((GRASSHOPPER_HOST, GRASSHOPPER_PORT))
        
        # 發送命令
        command_json = json.dumps(command)
        client.sendall((command_json + "\n").encode("utf-8"))
        print(f"Command sent: {command_json}", file=sys.stderr)
        
        # 接收響應
        response_data = b""
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            response_data += chunk
            if response_data.endswith(b"\n"):
                break
        
        # 處理可能的 BOM
        response_str = response_data.decode("utf-8-sig").strip()
        print(f"Response received: {response_str}", file=sys.stderr)
        
        # 解析 JSON 響應
        response = json.loads(response_str)
        client.close()
        return response
    except Exception as e:
        print(f"Error communicating with Grasshopper: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return {
            "success": False,
            "error": f"Error communicating with Grasshopper: {str(e)}"
        }

# 註冊 MCP 工具
@server.tool("add_component")
def add_component(guid: str, x: float, y: float):
    """
    Add a component to the Grasshopper canvas using GUID only.
    
    IMPORTANT: This function ONLY accepts GUID. No component name matching is performed.
    To find the GUID for a component, use the 'get_component_candidates' command first.
    
    Args:
        guid: REQUIRED - GUID to uniquely identify the component. Use 'get_component_candidates' to find the correct GUID.
        x: X coordinate on the canvas
        y: Y coordinate on the canvas
    
    Returns:
        Result of adding the component
    
    Usage:
        1. First, query component candidates to get the GUID:
           get_component_candidates(name="Rectangle")
        
        2. Then, use the GUID to add the component:
           add_component(
               guid="86a2e2dd-a3d8-4f24-9421-09ca3abe3a12",
               x=100.0,
               y=100.0
           )
    
    Note:
        - Only GUID is accepted. No component name or text input is required.
        - No matching or searching is performed - the component is created directly from the GUID.
        - Use 'get_component_candidates' command to search for components and obtain their GUIDs.
    """
    if not guid:
        raise ValueError("GUID is required. Use 'get_component_candidates' to find the component GUID.")
    
    params = {
        "guid": guid,
        "x": x,
        "y": y
    }
    
    return send_to_grasshopper("add_component", params)

@server.tool("clear_document")
def clear_document():
    """Clear the Grasshopper document"""
    return send_to_grasshopper("clear_document")

@server.tool("save_document")
def save_document(path: str):
    """
    Save the Grasshopper document
    
    Args:
        path: Save path
    
    Returns:
        Result of the save operation
    """
    params = {
        "path": path
    }
    
    return send_to_grasshopper("save_document", params)

@server.tool("load_document")
def load_document(path: str):
    """
    Load a Grasshopper document
    
    Args:
        path: Document path
    
    Returns:
        Result of the load operation
    """
    params = {
        "path": path
    }
    
    return send_to_grasshopper("load_document", params)

@server.tool("get_document_info")
def get_document_info():
    """Get information about the Grasshopper document"""
    return send_to_grasshopper("get_document_info")

@server.tool("connect_components")
def connect_components(source_id: str, target_id: str, source_param: Optional[str] = None, target_param: Optional[str] = None, source_param_index: Optional[int] = None, target_param_index: Optional[int] = None):
    """
    Connect two components in the Grasshopper canvas
    
    Args:
        source_id: ID of the source component (output)
        target_id: ID of the target component (input)
        source_param: Name of the source parameter (optional)
        target_param: Name of the target parameter (optional)
        source_param_index: Index of the source parameter (optional, used if source_param is not provided)
        target_param_index: Index of the target parameter (optional, used if target_param is not provided)
    
    Returns:
        Result of connecting the components
    """
    # 獲取目標組件的信息，檢查是否已有連接
    target_info = send_to_grasshopper("get_component_info", {"componentId": target_id})
    
    # 檢查組件類型，如果是需要多個輸入的組件（如 Addition, Subtraction 等），智能分配輸入
    if target_info and "result" in target_info and "type" in target_info["result"]:
        component_type = target_info["result"]["type"]
        
        # 獲取現有連接
        connections = send_to_grasshopper("get_connections")
        existing_connections = []
        
        if connections and "result" in connections:
            for conn in connections["result"]:
                if conn.get("targetId") == target_id:
                    existing_connections.append(conn)
        
        # 對於特定需要多個輸入的組件，自動選擇正確的輸入端口
        if component_type in ["Addition", "Subtraction", "Multiplication", "Division", "Math", "Amplitude"]:
            # 如果沒有指定目標參數，且已有連接到第一個輸入，則自動連接到第二個輸入
            if target_param is None and target_param_index is None:
                # 檢查第一個輸入是否已被佔用
                first_input_occupied = False
                for conn in existing_connections:
                    if conn.get("targetParam") == "A" or conn.get("targetParamIndex") == 0:
                        first_input_occupied = True
                        break
                
                # 如果第一個輸入已被佔用，則連接到第二個輸入
                if first_input_occupied:
                    # 對於 Amplitude，第二個輸入是 "Amplitude"，對於其他組件是 "B"
                    if component_type == "Amplitude":
                        target_param = "Amplitude"
                    else:
                        target_param = "B"  # 第二個輸入通常命名為 B
                else:
                    # 對於 Amplitude，第一個輸入是 "Vector"，對於其他組件是 "A"
                    if component_type == "Amplitude":
                        target_param = "Vector"
                    else:
                        target_param = "A"  # 否則連接到第一個輸入
    
    params: Dict[str, Any] = {
        "sourceId": source_id,
        "targetId": target_id
    }
    
    if source_param is not None:
        params["sourceParam"] = source_param
    elif source_param_index is not None:
        params["sourceParamIndex"] = source_param_index
        
    if target_param is not None:
        params["targetParam"] = target_param
    elif target_param_index is not None:
        params["targetParamIndex"] = target_param_index
    
    return send_to_grasshopper("connect_components", params)

@server.tool("create_pattern")
def create_pattern(description: str):
    """
    Create a pattern of components based on a high-level description
    
    Args:
        description: High-level description of what to create (e.g., '3D voronoi cube')
    
    Returns:
        Result of creating the pattern
    """
    params = {
        "description": description
    }
    
    return send_to_grasshopper("create_pattern", params)

@server.tool("get_available_patterns")
def get_available_patterns(query: str):
    """
    Get a list of available patterns that match a query
    
    Args:
        query: Query to search for patterns
    
    Returns:
        List of available patterns
    """
    params = {
        "query": query
    }
    
    return send_to_grasshopper("get_available_patterns", params)

@server.tool("get_component_info")
def get_component_info(component_id: str):
    """
    Get detailed information about a specific component
    
    Args:
        component_id: ID of the component to get information about
    
    Returns:
        Detailed information about the component, including inputs, outputs, and current values
    """
    params = {
        "componentId": component_id
    }
    
    result = send_to_grasshopper("get_component_info", params)
    
    # 增強返回結果，添加更多參數信息
    if result and "result" in result:
        component_data = result["result"]
        
        # 獲取組件類型
        if "type" in component_data:
            component_type = component_data["type"]
            
            # 查詢組件庫，獲取該類型組件的詳細參數信息
            component_library = get_component_library()
            if "components" in component_library:
                for lib_component in component_library["components"]:
                    if lib_component.get("name") == component_type or lib_component.get("fullName") == component_type:
                        # 將組件庫中的參數信息合併到返回結果中
                        if "settings" in lib_component:
                            component_data["availableSettings"] = lib_component["settings"]
                        if "inputs" in lib_component:
                            component_data["inputDetails"] = lib_component["inputs"]
                        if "outputs" in lib_component:
                            component_data["outputDetails"] = lib_component["outputs"]
                        if "usage_examples" in lib_component:
                            component_data["usageExamples"] = lib_component["usage_examples"]
                        if "common_issues" in lib_component:
                            component_data["commonIssues"] = lib_component["common_issues"]
                        break
            
            # 特殊處理某些組件類型
            if component_type == "Number Slider":
                # 嘗試從組件數據中獲取當前滑桿的實際設置
                if "currentSettings" not in component_data:
                    component_data["currentSettings"] = {
                        "min": component_data.get("min", 0),
                        "max": component_data.get("max", 10),
                        "value": component_data.get("value", 5),
                        "rounding": component_data.get("rounding", 0.1),
                        "type": component_data.get("type", "float")
                    }
            
            # 添加組件的連接信息
            connections = send_to_grasshopper("get_connections")
            if connections and "result" in connections:
                # 查找與該組件相關的所有連接
                related_connections = []
                for conn in connections["result"]:
                    if conn.get("sourceId") == component_id or conn.get("targetId") == component_id:
                        related_connections.append(conn)
                
                if related_connections:
                    component_data["connections"] = related_connections
    
    return result

@server.tool("get_document_errors")
def get_document_errors():
    """
    Get all error and warning messages from all components in the current Grasshopper document
    
    Returns:
        Dictionary containing errorCount and a list of all errors/warnings with component information
    """
    result = send_to_grasshopper("get_document_errors", {})
    return result

@server.tool("get_all_components")
def get_all_components():
    """
    Get a list of all components in the current document
    
    Returns:
        List of all components in the document with their IDs, types, and positions
    """
    result = send_to_grasshopper("get_all_components")
    
    # 增強返回結果，為每個組件添加更多參數信息
    if result and "result" in result:
        components = result["result"]
        component_library = get_component_library()
        
        # 獲取所有連接信息
        connections = send_to_grasshopper("get_connections")
        connections_data = connections.get("result", []) if connections else []
        
        # 為每個組件添加詳細信息
        for component in components:
            if "id" in component and "type" in component:
                component_id = component["id"]
                component_type = component["type"]
                
                # 添加組件的詳細參數信息
                if "components" in component_library:
                    for lib_component in component_library["components"]:
                        if lib_component.get("name") == component_type or lib_component.get("fullName") == component_type:
                            # 將組件庫中的參數信息合併到組件數據中
                            if "settings" in lib_component:
                                component["availableSettings"] = lib_component["settings"]
                            if "inputs" in lib_component:
                                component["inputDetails"] = lib_component["inputs"]
                            if "outputs" in lib_component:
                                component["outputDetails"] = lib_component["outputs"]
                            break
                
                # 添加組件的連接信息
                related_connections = []
                for conn in connections_data:
                    if conn.get("sourceId") == component_id or conn.get("targetId") == component_id:
                        related_connections.append(conn)
                
                if related_connections:
                    component["connections"] = related_connections
                
                # 特殊處理某些組件類型
                if component_type == "Number Slider":
                    # 嘗試獲取滑桿的當前設置
                    component_info = send_to_grasshopper("get_component_info", {"componentId": component_id})
                    if component_info and "result" in component_info:
                        info_data = component_info["result"]
                        component["currentSettings"] = {
                            "min": info_data.get("min", 0),
                            "max": info_data.get("max", 10),
                            "value": info_data.get("value", 5),
                            "rounding": info_data.get("rounding", 0.1)
                        }
    
    return result

@server.tool("get_connections")
def get_connections():
    """
    Get a list of all connections between components in the current document
    
    Returns:
        List of all connections between components
    """
    return send_to_grasshopper("get_connections")

@server.tool("search_components")
def search_components(query: str):
    """
    Search for components by name or category
    
    Args:
        query: Search query
    
    Returns:
        List of components matching the search query
    """
    params = {
        "query": query
    }
    
    return send_to_grasshopper("search_components", params)

@server.tool("get_component_parameters")
def get_component_parameters(component_type: str):
    """
    Get a list of parameters for a specific component type
    
    Args:
        component_type: Type of component to get parameters for
    
    Returns:
        List of input and output parameters for the component type
    """
    params = {
        "componentType": component_type
    }
    
    return send_to_grasshopper("get_component_parameters", params)

@server.tool("get_component_candidates")
def get_component_candidates(name: str):
    """
    Get all component candidates that match a given name
    
    This tool searches for all components matching the given name and returns
    detailed information about each candidate, including:
    - Component name and GUID
    - Category and subcategory
    - Library/plugin name
    - Whether it's obsolete or deprecated
    - Whether it's a built-in Grasshopper component
    - Description
    - Input and output parameters
    
    Args:
        name: Component name to search for (e.g., "Rectangle", "Number Slider")
    
    Returns:
        A dictionary containing:
        - query: The original search query
        - normalizedQuery: The normalized component name
        - count: Number of candidates found
        - candidates: List of candidate components with detailed information
    
    Example:
        get_component_candidates("Rectangle") will return all Rectangle components
        with their properties, helping you choose the right one.
    """
    params = {
        "name": name
    }
    
    return send_to_grasshopper("get_component_candidates", params)

@server.tool("validate_connection")
def validate_connection(source_id: str, target_id: str, source_param: Optional[str] = None, target_param: Optional[str] = None):
    """
    Validate if a connection between two components is possible
    
    Args:
        source_id: ID of the source component (output)
        target_id: ID of the target component (input)
        source_param: Name of the source parameter (optional)
        target_param: Name of the target parameter (optional)
    
    Returns:
        Whether the connection is valid and any potential issues
    """
    params = {
        "sourceId": source_id,
        "targetId": target_id
    }
    
    if source_param is not None:
        params["sourceParam"] = source_param
        
    if target_param is not None:
        params["targetParam"] = target_param
    
    return send_to_grasshopper("validate_connection", params)

@server.tool("group_components")
def group_components(component_ids, group_name: Optional[str] = None, color: Optional[str] = None, 
                     color_r: Optional[int] = None, color_g: Optional[int] = None, color_b: Optional[int] = None):
    """
    將多個元件群組起來，可選擇命名和顏色
    
    Args:
        component_ids: 要群組的 componentId 清單，可以是 list 或逗號分隔字串
        group_name (str, optional): 群組名稱
        color (str, optional): 十六進制顏色代碼 (例如: "#FF0000" 或 "FF0000")
        color_r (int, optional): 紅色值 (0-255)
        color_g (int, optional): 綠色值 (0-255)
        color_b (int, optional): 藍色值 (0-255)
    
    Returns:
        dict: 回傳群組資訊
    """
    # 處理 component_ids：如果是字符串，轉換為列表
    if isinstance(component_ids, str):
        ids = [cid.strip() for cid in component_ids.split(",") if cid.strip()]
    else:
        ids = [str(cid) for cid in component_ids if str(cid).strip()]
    
    params: Dict[str, Any] = {"componentIds": ids}
    
    if group_name:
        params["groupName"] = group_name
    
    if color:
        params["color"] = color
    elif color_r is not None and color_g is not None and color_b is not None:
        params["colorR"] = color_r
        params["colorG"] = color_g
        params["colorB"] = color_b
    
    return send_to_grasshopper("group_components", params)

@server.tool("set_slider_properties")
def set_slider_properties(component_id: str, value: Optional[str] = None, min_value: Optional[float] = None, 
                         max_value: Optional[float] = None, rounding: Optional[float] = None):
    """
    設定 Number Slider 的完整屬性
    
    這是一個專門用於設置 Number Slider 屬性的函數，包括值、範圍和精度
    
    Args:
        component_id (str): Number Slider 組件的 ID
        value (str, optional): 要設定的值
        min_value (float, optional): 最小值
        max_value (float, optional): 最大值
        rounding (float, optional): 精度（小數點後幾位）
        
    Returns:
        dict: 設定結果
    """
    params: Dict[str, Any] = {
        "id": component_id,
        "component_type": "Number Slider"
    }
    
    # 添加提供的參數
    if value is not None:
        params["value"] = value
    if min_value is not None:
        params["min"] = min_value
    if max_value is not None:
        params["max"] = max_value
    if rounding is not None:
        params["rounding"] = rounding
    
    return send_to_grasshopper("set_slider_properties", params)

@server.tool("set_component_visibility")
def set_component_visibility(component_id: str, hidden: bool):
    """
    設置組件可見性
    
    控制組件在 Grasshopper 畫布上的顯示/隱藏狀態
    
    Args:
        component_id (str): 組件的 ID
        hidden (bool): 是否隱藏組件（True = 隱藏, False = 顯示）
    
    Returns:
        dict: 操作結果，包含 success 狀態和消息
    """
    params: Dict[str, Any] = {
        "componentId": component_id,
        "hidden": hidden
    }
    
    return send_to_grasshopper("set_component_visibility", params)

@server.tool("zoom_to_components")
def zoom_to_components(component_ids):
    """
    縮放到指定的一個或多個組件
    
    將 Grasshopper 畫布視圖縮放並聚焦到指定的組件位置。可以接受單個組件 ID 或多個組件 ID 列表。
    當提供多個組件時，會計算所有組件的合併邊界框並縮放到該區域。
    
    Args:
        component_ids: 組件 ID 列表，可以是：
            - 單個 ID 字符串
            - 逗號分隔的 ID 字符串（如 "id1,id2,id3"）
            - ID 列表（如 ["id1", "id2", "id3"]）
    
    Returns:
        dict: 操作結果，包含：
            - success: 是否成功
            - message: 操作消息
            - componentCount: 成功縮放的組件數量
            - componentIds: 成功找到的組件 ID 列表
            - notFoundIds: 未找到的組件 ID 列表（如果有）
    
    Example:
        # 縮放到單個組件
        zoom_to_components(component_ids="12345678-1234-1234-1234-123456789012")
        
        # 縮放到多個組件（逗號分隔）
        zoom_to_components(component_ids="id1,id2,id3")
        
        # 縮放到多個組件（列表）
        zoom_to_components(component_ids=["id1", "id2", "id3"])
    """
    # 處理輸入：如果是字符串，轉換為列表
    if isinstance(component_ids, str):
        ids = [cid.strip() for cid in component_ids.split(",") if cid.strip()]
    else:
        ids = [str(cid) for cid in component_ids if str(cid).strip()]
    
    if not ids:
        raise ValueError("At least one component ID is required")
    
    params: Dict[str, Any] = {
        "componentIds": ids
    }
    
    return send_to_grasshopper("zoom_to_components", params)

# 註冊 MCP 資源
@server.resource("grasshopper://status")
def get_grasshopper_status():
    """Get Grasshopper status"""
    try:
        # 獲取文檔信息
        doc_info = send_to_grasshopper("get_document_info")
        
        # 獲取所有組件（使用增強版的 get_all_components）
        components_result = get_all_components()
        components = components_result.get("result", []) if components_result else []
        
        # 獲取所有連接
        connections = send_to_grasshopper("get_connections")
        
        # 添加常用組件的提示信息
        component_hints = {
            "Number Slider": {
                "description": "Single numeric value slider with adjustable range",
                "common_usage": "Use for single numeric inputs like radius, height, count, etc.",
                "parameters": ["min", "max", "value", "rounding", "type"],
                "NOT_TO_BE_CONFUSED_WITH": "MD Slider (which is for multi-dimensional values)"
            },
            "MD Slider": {
                "description": "Multi-dimensional slider for vector input",
                "common_usage": "Use for vector inputs, NOT for simple numeric values",
                "NOT_TO_BE_CONFUSED_WITH": "Number Slider (which is for single numeric values)"
            },
            "Panel": {
                "description": "Displays text or numeric data",
                "common_usage": "Use for displaying outputs and debugging"
            },
            "Addition": {
                "description": "Adds two or more numbers",
                "common_usage": "Connect two Number Sliders to inputs A and B",
                "parameters": ["A", "B"],
                "connection_tip": "First slider should connect to input A, second to input B"
            }
        }
        
        # 為每個組件添加當前參數值的摘要
        component_summaries = []
        for component in components:
            summary = {
                "id": component.get("id", ""),
                "type": component.get("type", ""),
                "position": {
                    "x": component.get("x", 0),
                    "y": component.get("y", 0)
                }
            }
            
            # 添加組件特定的參數信息
            if "currentSettings" in component:
                summary["settings"] = component["currentSettings"]
            elif component.get("type") == "Number Slider":
                # 嘗試從組件信息中提取滑桿設置
                summary["settings"] = {
                    "min": component.get("min", 0),
                    "max": component.get("max", 10),
                    "value": component.get("value", 5),
                    "rounding": component.get("rounding", 0.1)
                }
            
            # 添加連接信息摘要
            if "connections" in component:
                conn_summary = []
                for conn in component["connections"]:
                    if conn.get("sourceId") == component.get("id"):
                        conn_summary.append({
                            "type": "output",
                            "to": conn.get("targetId", ""),
                            "sourceParam": conn.get("sourceParam", ""),
                            "targetParam": conn.get("targetParam", "")
                        })
                    else:
                        conn_summary.append({
                            "type": "input",
                            "from": conn.get("sourceId", ""),
                            "sourceParam": conn.get("sourceParam", ""),
                            "targetParam": conn.get("targetParam", "")
                        })
                
                if conn_summary:
                    summary["connections"] = conn_summary
            
            component_summaries.append(summary)
        
        return {
            "status": "Connected to Grasshopper",
            "document": doc_info.get("result", {}),
            "components": component_summaries,
            "connections": connections.get("result", []),
            "component_hints": component_hints,
            "recommendations": [
                "When needing a simple numeric input control, ALWAYS use 'Number Slider', not MD Slider",
                "For vector inputs (like 3D points), use 'MD Slider' or 'Construct Point' with multiple Number Sliders",
                "Use 'Panel' to display outputs and debug values",
                "When connecting multiple sliders to Addition, first slider goes to input A, second to input B"
            ],
            "canvas_summary": f"Current canvas has {len(component_summaries)} components and {len(connections.get('result', []))} connections"
        }
    except Exception as e:
        print(f"Error getting Grasshopper status: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return {
            "status": f"Error: {str(e)}",
            "document": {},
            "components": [],
            "connections": []
        }

@server.resource("grasshopper://component_guide")
def get_component_guide():
    """Get guide for Grasshopper components and connections"""
    return {
        "title": "Grasshopper Component Guide",
        "description": "Guide for creating and connecting Grasshopper components",
        "components": [
            {
                "name": "Point",
                "category": "Params",
                "description": "Creates a point at specific coordinates",
                "inputs": [
                    {"name": "X", "type": "Number"},
                    {"name": "Y", "type": "Number"},
                    {"name": "Z", "type": "Number"}
                ],
                "outputs": [
                    {"name": "Pt", "type": "Point"}
                ]
            },
            {
                "name": "Circle",
                "category": "Curve",
                "description": "Creates a circle",
                "inputs": [
                    {"name": "Plane", "type": "Plane", "description": "Base plane for the circle"},
                    {"name": "Radius", "type": "Number", "description": "Circle radius"}
                ],
                "outputs": [
                    {"name": "C", "type": "Circle"}
                ]
            },
            {
                "name": "XY Plane",
                "category": "Vector",
                "description": "Creates an XY plane at the world origin or at a specified point",
                "inputs": [
                    {"name": "Origin", "type": "Point", "description": "Origin point", "optional": True}
                ],
                "outputs": [
                    {"name": "Plane", "type": "Plane", "description": "XY plane"}
                ]
            },
            {
                "name": "Addition",
                "fullName": "Addition",
                "description": "Adds two or more numbers",
                "inputs": [
                    {"name": "A", "type": "Number", "description": "First input value"},
                    {"name": "B", "type": "Number", "description": "Second input value"}
                ],
                "outputs": [
                    {"name": "Result", "type": "Number", "description": "Sum of inputs"}
                ],
                "usage_examples": [
                    "Connect two Number Sliders to inputs A and B to add their values",
                    "Connect multiple values to add them all together"
                ],
                "common_issues": [
                    "When connecting multiple sliders, ensure they connect to different inputs (A and B)",
                    "The first slider should connect to input A, the second to input B"
                ]
            },
            {
                "name": "Number Slider",
                "fullName": "Number Slider",
                "description": "Creates a slider for numeric input with adjustable range and precision",
                "inputs": [],
                "outputs": [
                    {"name": "N", "type": "Number", "description": "Number output"}
                ],
                "settings": {
                    "min": {"description": "Minimum value of the slider", "default": 0},
                    "max": {"description": "Maximum value of the slider", "default": 10},
                    "value": {"description": "Current value of the slider", "default": 5},
                    "rounding": {"description": "Rounding precision (0.01, 0.1, 1, etc.)", "default": 0.1},
                    "type": {"description": "Slider type (integer, floating point)", "default": "float"},
                    "name": {"description": "Custom name for the slider", "default": ""}
                },
                "usage_examples": [
                    "Create a Number Slider with min=0, max=100, value=50",
                    "Create a Number Slider for radius with min=0.1, max=10, value=2.5, rounding=0.1"
                ],
                "common_issues": [
                    "Confusing with other slider types",
                    "Not setting appropriate min/max values for the intended use"
                ],
                "disambiguation": {
                    "similar_components": [
                        {
                            "name": "MD Slider",
                            "description": "Multi-dimensional slider for vector input, NOT for simple numeric values",
                            "how_to_distinguish": "Use Number Slider for single numeric values; use MD Slider only when you need multi-dimensional control"
                        },
                        {
                            "name": "Graph Mapper",
                            "description": "Maps values through a graph function, NOT a simple slider",
                            "how_to_distinguish": "Use Number Slider for direct numeric input; use Graph Mapper only for function-based mapping"
                        }
                    ],
                    "correct_usage": "When needing a simple numeric input control, ALWAYS use 'Number Slider', not MD Slider or other variants"
                }
            },
            {
                "name": "Panel",
                "fullName": "Panel",
                "description": "Displays text or numeric data",
                "inputs": [
                    {"name": "Input", "type": "Any"}
                ],
                "outputs": []
            },
            {
                "name": "Math",
                "fullName": "Mathematics",
                "description": "Performs mathematical operations",
                "inputs": [
                    {"name": "A", "type": "Number"},
                    {"name": "B", "type": "Number"}
                ],
                "outputs": [
                    {"name": "Result", "type": "Number"}
                ],
                "operations": ["Addition", "Subtraction", "Multiplication", "Division", "Power", "Modulo"]
            },
            {
                "name": "Construct Point",
                "fullName": "Construct Point",
                "description": "Constructs a point from X, Y, Z coordinates",
                "inputs": [
                    {"name": "X", "type": "Number"},
                    {"name": "Y", "type": "Number"},
                    {"name": "Z", "type": "Number"}
                ],
                "outputs": [
                    {"name": "Pt", "type": "Point"}
                ]
            },
            {
                "name": "Line",
                "fullName": "Line",
                "description": "Creates a line between two points",
                "inputs": [
                    {"name": "Start", "type": "Point"},
                    {"name": "End", "type": "Point"}
                ],
                "outputs": [
                    {"name": "L", "type": "Line"}
                ]
            },
            {
                "name": "Extrude",
                "fullName": "Extrude",
                "description": "Extrudes a curve or surface to create a surface or a solid",
                "inputs": [
                    {"name": "Base", "type": "Curve or Surface", "description": "Base curve or surface to extrude"},
                    {"name": "Direction", "type": "Vector", "description": "Direction vector for extrusion"},
                    {"name": "Height", "type": "Number", "description": "Height of extrusion (optional if Direction is provided)"}
                ],
                "outputs": [
                    {"name": "Brep", "type": "Brep", "description": "Extruded brep (3D solid or surface)"}
                ],
                "important_workflow": {
                    "title": "Standard Workflow for Creating 3D Geometry with Extrude",
                    "description": "When using Extrude to create 3D geometry from 2D curves, follow this standard workflow:",
                    "steps": [
                        {
                            "step": 1,
                            "description": "Create 2D curves (e.g., Rectangle, Circle, Polygon) on a plane"
                        },
                        {
                            "step": 2,
                            "description": "IMPORTANT: For closed 2D curves, you MUST first use Boundary Surfaces to create a surface from the curves",
                            "critical": True
                        },
                        {
                            "step": 3,
                            "description": "Connect the surface output from Boundary Surfaces to Extrude.Base input",
                            "note": "Do NOT connect curves directly to Extrude if you want to create a solid"
                        },
                        {
                            "step": 4,
                            "description": "Create extrusion direction using Unit Z → Amplitude (with Number Slider) → Extrude.Direction"
                        },
                        {
                            "step": 5,
                            "description": "The Extrude component will create a 3D solid from the surface"
                        }
                    ],
                    "workflow_diagram": "2D Curve → Boundary Surfaces → Surface → Extrude.Base + Extrude.Direction → 3D Solid"
                },
                "usage_examples": [
                    "For closed curves (Rectangle, Circle, Polygon): Curve → Boundary Surfaces → Extrude.Base",
                    "For open curves: Can extrude directly, but will create a surface, not a solid",
                    "Standard pattern: Unit Z → Amplitude (with height slider) → Extrude.Direction"
                ],
                "common_issues": [
                    "Trying to extrude closed 2D curves directly without using Boundary Surfaces first - this will fail or create incorrect geometry",
                    "For closed curves, always use Boundary Surfaces before Extrude to create proper 3D solids",
                    "Not understanding the difference: Extrude on curves creates surfaces, Extrude on surfaces creates solids"
                ],
                "critical_note": "2D closed curves MUST be converted to surfaces using Boundary Surfaces before extruding to create 3D solids. This is a required step in the workflow."
            },
            {
                "name": "Boundary Surfaces",
                "fullName": "Boundary Surfaces",
                "category": "Surface",
                "description": "Creates a surface from closed boundary curves. This is REQUIRED before extruding closed 2D curves to create 3D solids.",
                "inputs": [
                    {"name": "Curves", "type": "Curve", "description": "Closed boundary curves (e.g., Rectangle, Circle, Polygon)"}
                ],
                "outputs": [
                    {"name": "Surface", "type": "Surface", "description": "Surface created from the boundary curves"}
                ],
                "usage_examples": [
                    "Connect a closed curve (Rectangle, Circle, Polygon) to Boundary Surfaces to create a surface",
                    "Then connect the surface output to Extrude.Base to create a 3D solid",
                    "Required workflow: Closed Curve → Boundary Surfaces → Surface → Extrude → 3D Solid"
                ],
                "common_issues": [
                    "Forgetting to use Boundary Surfaces before Extrude when working with closed curves",
                    "Trying to extrude closed curves directly - this will not create proper solids"
                ],
                "critical_note": "This component is REQUIRED in the workflow when you want to extrude closed 2D curves (Rectangle, Circle, Polygon) to create 3D solids. Do not skip this step."
            },
            {
                "name": "Amplitude",
                "fullName": "Amplitude",
                "category": "Vector",
                "description": "Scales a vector by a specified amplitude (magnitude). Used to scale unit vectors to specific lengths.",
                "inputs": [
                    {"name": "Vector", "type": "Vector", "description": "Input vector to scale"},
                    {"name": "Amplitude", "type": "Number", "description": "The magnitude/amplitude to scale the vector to"}
                ],
                "outputs": [
                    {"name": "Vector", "type": "Vector", "description": "Scaled vector with the specified amplitude"}
                ],
                "usage_examples": [
                    "Connect Unit Z (outputs (0,0,1)) to Vector input and a Number Slider (e.g., 15.0) to Amplitude input to create a vertical vector of length 15",
                    "Use with Extrude component: Unit Z → Amplitude → Extrude.Direction to extrude geometry vertically by a specific height"
                ],
                "common_issues": [
                    "Do NOT use Multiply component for vector scaling - Amplitude is the correct component",
                    "Ensure the input vector is a unit vector if you want to scale it to a specific length",
                    "The output vector maintains the direction of the input vector but with the specified magnitude"
                ],
                "important_note": "Amplitude is specifically for vector scaling. For number multiplication, use Multiplication component instead."
            },
            {
                "name": "Unit Z",
                "fullName": "Unit Z",
                "category": "Vector",
                "description": "Creates a unit vector in the Z direction (0, 0, 1)",
                "inputs": [],
                "outputs": [
                    {"name": "Vector", "type": "Vector", "description": "Unit vector pointing in the positive Z direction"}
                ],
                "usage_examples": [
                    "Use with Amplitude to create vertical vectors of specific lengths",
                    "Connect to Amplitude component to scale to desired height for extrusion"
                ]
            }
        ],
        "connectionRules": [
            {
                "from": "Number",
                "to": "Circle.Radius",
                "description": "Connect a number to the radius input of a circle"
            },
            {
                "from": "Point",
                "to": "Circle.Plane",
                "description": "Connect a point to the plane input of a circle (not recommended, use XY Plane instead)"
            },
            {
                "from": "XY Plane",
                "to": "Circle.Plane",
                "description": "Connect an XY Plane to the plane input of a circle (recommended)"
            },
            {
                "from": "Number",
                "to": "Math.A",
                "description": "Connect a number to the first input of a Math component"
            },
            {
                "from": "Number",
                "to": "Math.B",
                "description": "Connect a number to the second input of a Math component"
            },
            {
                "from": "Number",
                "to": "Construct Point.X",
                "description": "Connect a number to the X input of a Construct Point component"
            },
            {
                "from": "Number",
                "to": "Construct Point.Y",
                "description": "Connect a number to the Y input of a Construct Point component"
            },
            {
                "from": "Number",
                "to": "Construct Point.Z",
                "description": "Connect a number to the Z input of a Construct Point component"
            },
            {
                "from": "Point",
                "to": "Line.Start",
                "description": "Connect a point to the start input of a Line component"
            },
            {
                "from": "Point",
                "to": "Line.End",
                "description": "Connect a point to the end input of a Line component"
            },
            {
                "from": "Circle",
                "to": "Boundary Surfaces.Curves",
                "description": "Connect a closed curve (Circle, Rectangle, Polygon) to Boundary Surfaces to create a surface first"
            },
            {
                "from": "Boundary Surfaces",
                "to": "Extrude.Base",
                "description": "Connect Boundary Surfaces output to Extrude.Base - this is REQUIRED for closed curves to create 3D solids"
            },
            {
                "from": "Number",
                "to": "Extrude.Height",
                "description": "Connect a number to the height input of an Extrude component (optional if Direction is provided)"
            },
            {
                "from": "Unit Z",
                "to": "Amplitude.Vector",
                "description": "Connect Unit Z to the Vector input of Amplitude to get a vertical direction vector"
            },
            {
                "from": "Number",
                "to": "Amplitude.Amplitude",
                "description": "Connect a Number Slider to the Amplitude input to specify the vector magnitude"
            },
            {
                "from": "Amplitude",
                "to": "Extrude.Direction",
                "description": "Connect Amplitude output to Extrude Direction input to extrude geometry by a specific distance in a specific direction"
            }
        ],
        "commonIssues": [
            "Using Point component instead of XY Plane for inputs that require planes",
            "Not specifying parameter names when connecting components",
            "Using incorrect component names (e.g., 'addition' instead of 'Math' with Addition operation)",
            "Trying to connect incompatible data types",
            "Not providing all required inputs for a component",
            "Using incorrect parameter names (e.g., 'A' and 'B' for Math component instead of the actual parameter names)",
            "Not checking if a connection was successful before proceeding",
            "Using Multiply component for vector scaling - use Amplitude instead",
            "Confusing Amplitude (for vectors) with Multiplication (for numbers)",
            "CRITICAL: Trying to extrude closed 2D curves (Rectangle, Circle, Polygon) directly without using Boundary Surfaces first",
            "Forgetting to use Boundary Surfaces before Extrude when creating 3D solids from closed curves",
            "Not understanding that Extrude on curves creates surfaces, while Extrude on surfaces creates solids"
        ],
        "tips": [
            "Always use XY Plane component for plane inputs",
            "Specify parameter names when connecting components",
            "For Circle components, make sure to use the correct inputs (Plane and Radius)",
            "Test simple connections before creating complex geometry",
            "Avoid using components that require selection from Rhino",
            "Use get_component_info to check the actual parameter names of a component",
            "Use get_connections to verify if connections were established correctly",
            "Use search_components to find the correct component name before adding it",
            "Use validate_connection to check if a connection is possible before attempting it",
            "For vector scaling (e.g., scaling Unit Z to a specific height), use Amplitude component, NOT Multiply",
            "Amplitude is for vectors, Multiplication is for numbers - don't confuse them",
            "Common pattern: Unit Z → Amplitude (with Number Slider) → Extrude.Direction for vertical extrusion",
            "CRITICAL WORKFLOW: When creating 3D solids from closed 2D curves, ALWAYS use: Closed Curve → Boundary Surfaces → Extrude.Base",
            "For closed curves (Rectangle, Circle, Polygon), you MUST use Boundary Surfaces before Extrude to create proper 3D solids",
            "Standard extrusion workflow: 2D Closed Curve → Boundary Surfaces → Surface → Extrude.Base + Extrude.Direction (from Amplitude) → 3D Solid",
            "Remember: Extrude on curves creates surfaces, Extrude on surfaces creates solids. Use Boundary Surfaces to convert closed curves to surfaces first."
        ]
    }

@server.resource("grasshopper://component_library")
def get_component_library():
    """Get a comprehensive library of Grasshopper components"""
    # 這個資源提供了一個更全面的組件庫，包括常用組件的詳細信息
    return {
        "categories": [
            {
                "name": "Params",
                "components": [
                    {
                        "name": "Point",
                        "fullName": "Point Parameter",
                        "description": "Creates a point parameter",
                        "inputs": [
                            {"name": "X", "type": "Number", "description": "X coordinate"},
                            {"name": "Y", "type": "Number", "description": "Y coordinate"},
                            {"name": "Z", "type": "Number", "description": "Z coordinate"}
                        ],
                        "outputs": [
                            {"name": "Pt", "type": "Point", "description": "Point output"}
                        ]
                    },
                    {
                        "name": "Number Slider",
                        "fullName": "Number Slider",
                        "description": "Creates a slider for numeric input with adjustable range and precision",
                        "inputs": [],
                        "outputs": [
                            {"name": "N", "type": "Number", "description": "Number output"}
                        ],
                        "settings": {
                            "min": {"description": "Minimum value of the slider", "default": 0},
                            "max": {"description": "Maximum value of the slider", "default": 10},
                            "value": {"description": "Current value of the slider", "default": 5},
                            "rounding": {"description": "Rounding precision (0.01, 0.1, 1, etc.)", "default": 0.1},
                            "type": {"description": "Slider type (integer, floating point)", "default": "float"},
                            "name": {"description": "Custom name for the slider", "default": ""}
                        },
                        "usage_examples": [
                            "Create a Number Slider with min=0, max=100, value=50",
                            "Create a Number Slider for radius with min=0.1, max=10, value=2.5, rounding=0.1"
                        ],
                        "common_issues": [
                            "Confusing with other slider types",
                            "Not setting appropriate min/max values for the intended use"
                        ],
                        "disambiguation": {
                            "similar_components": [
                                {
                                    "name": "MD Slider",
                                    "description": "Multi-dimensional slider for vector input, NOT for simple numeric values",
                                    "how_to_distinguish": "Use Number Slider for single numeric values; use MD Slider only when you need multi-dimensional control"
                                },
                                {
                                    "name": "Graph Mapper",
                                    "description": "Maps values through a graph function, NOT a simple slider",
                                    "how_to_distinguish": "Use Number Slider for direct numeric input; use Graph Mapper only for function-based mapping"
                                }
                            ],
                            "correct_usage": "When needing a simple numeric input control, ALWAYS use 'Number Slider', not MD Slider or other variants"
                        }
                    },
                    {
                        "name": "Panel",
                        "fullName": "Panel",
                        "description": "Displays text or numeric data",
                        "inputs": [
                            {"name": "Input", "type": "Any", "description": "Any input data"}
                        ],
                        "outputs": []
                    }
                ]
            },
            {
                "name": "Maths",
                "components": [
                    {
                        "name": "Math",
                        "fullName": "Mathematics",
                        "description": "Performs mathematical operations",
                        "inputs": [
                            {"name": "A", "type": "Number", "description": "First number"},
                            {"name": "B", "type": "Number", "description": "Second number"}
                        ],
                        "outputs": [
                            {"name": "Result", "type": "Number", "description": "Result of the operation"}
                        ],
                        "operations": ["Addition", "Subtraction", "Multiplication", "Division", "Power", "Modulo"]
                    }
                ]
            },
            {
                "name": "Vector",
                "components": [
                    {
                        "name": "XY Plane",
                        "fullName": "XY Plane",
                        "description": "Creates an XY plane at the world origin or at a specified point",
                        "inputs": [
                            {"name": "Origin", "type": "Point", "description": "Origin point", "optional": True}
                        ],
                        "outputs": [
                            {"name": "Plane", "type": "Plane", "description": "XY plane"}
                        ]
                    },
                    {
                        "name": "Unit Z",
                        "fullName": "Unit Z",
                        "description": "Creates a unit vector in the Z direction (0, 0, 1)",
                        "inputs": [],
                        "outputs": [
                            {"name": "Vector", "type": "Vector", "description": "Unit vector pointing in the positive Z direction"}
                        ],
                        "usage_examples": [
                            "Use with Amplitude to create vertical vectors of specific lengths",
                            "Connect to Amplitude component to scale to desired height for extrusion"
                        ]
                    },
                    {
                        "name": "Amplitude",
                        "fullName": "Amplitude",
                        "description": "Scales a vector by a specified amplitude (magnitude). Used to scale unit vectors to specific lengths.",
                        "inputs": [
                            {"name": "Vector", "type": "Vector", "description": "Input vector to scale"},
                            {"name": "Amplitude", "type": "Number", "description": "The magnitude/amplitude to scale the vector to"}
                        ],
                        "outputs": [
                            {"name": "Vector", "type": "Vector", "description": "Scaled vector with the specified amplitude"}
                        ],
                        "usage_examples": [
                            "Connect Unit Z (outputs (0,0,1)) to Vector input and a Number Slider (e.g., 15.0) to Amplitude input to create a vertical vector of length 15",
                            "Use with Extrude component: Unit Z → Amplitude → Extrude.Direction to extrude geometry vertically by a specific height"
                        ],
                        "common_issues": [
                            "Do NOT use Multiply component for vector scaling - Amplitude is the correct component",
                            "Ensure the input vector is a unit vector if you want to scale it to a specific length",
                            "The output vector maintains the direction of the input vector but with the specified magnitude"
                        ],
                        "important_note": "Amplitude is specifically for vector scaling. For number multiplication, use Multiplication component instead."
                    },
                    {
                        "name": "Construct Point",
                        "fullName": "Construct Point",
                        "description": "Constructs a point from X, Y, Z coordinates",
                        "inputs": [
                            {"name": "X", "type": "Number", "description": "X coordinate"},
                            {"name": "Y", "type": "Number", "description": "Y coordinate"},
                            {"name": "Z", "type": "Number", "description": "Z coordinate"}
                        ],
                        "outputs": [
                            {"name": "Pt", "type": "Point", "description": "Constructed point"}
                        ]
                    }
                ]
            },
            {
                "name": "Curve",
                "components": [
                    {
                        "name": "Circle",
                        "fullName": "Circle",
                        "description": "Creates a circle",
                        "inputs": [
                            {"name": "Plane", "type": "Plane", "description": "Base plane for the circle"},
                            {"name": "Radius", "type": "Number", "description": "Circle radius"}
                        ],
                        "outputs": [
                            {"name": "C", "type": "Circle", "description": "Circle output"}
                        ]
                    },
                    {
                        "name": "Line",
                        "fullName": "Line",
                        "description": "Creates a line between two points",
                        "inputs": [
                            {"name": "Start", "type": "Point", "description": "Start point"},
                            {"name": "End", "type": "Point", "description": "End point"}
                        ],
                        "outputs": [
                            {"name": "L", "type": "Line", "description": "Line output"}
                        ]
                    }
                ]
            },
            {
                "name": "Surface",
                "components": [
                    {
                        "name": "Extrude",
                        "fullName": "Extrude",
                        "description": "Extrudes a curve or surface to create a surface or a solid",
                        "inputs": [
                            {"name": "Base", "type": "Curve or Surface", "description": "Base curve or surface to extrude. For closed curves, MUST use Boundary Surfaces first."},
                            {"name": "Direction", "type": "Vector", "description": "Direction of extrusion", "optional": True},
                            {"name": "Height", "type": "Number", "description": "Height of extrusion", "optional": True}
                        ],
                        "outputs": [
                            {"name": "Brep", "type": "Brep", "description": "Extruded brep (3D solid or surface)"}
                        ],
                        "workflow": "For closed 2D curves: Curve → Boundary Surfaces → Surface → Extrude.Base + Extrude.Direction → 3D Solid",
                        "important": "2D closed curves MUST be converted to surfaces using Boundary Surfaces before extruding to create 3D solids"
                    },
                    {
                        "name": "Boundary Surfaces",
                        "fullName": "Boundary Surfaces",
                        "description": "Creates a surface from closed boundary curves. REQUIRED before extruding closed 2D curves.",
                        "inputs": [
                            {"name": "Curves", "type": "Curve", "description": "Closed boundary curves (Rectangle, Circle, Polygon, etc.)"}
                        ],
                        "outputs": [
                            {"name": "Surface", "type": "Surface", "description": "Surface created from boundary curves"}
                        ],
                        "workflow": "Required step: Closed Curve → Boundary Surfaces → Surface → Extrude → 3D Solid"
                    }
                ]
            }
        ],
        "dataTypes": [
            {
                "name": "Number",
                "description": "A numeric value",
                "compatibleWith": ["Number", "Integer", "Double"]
            },
            {
                "name": "Point",
                "description": "A 3D point in space",
                "compatibleWith": ["Point3d", "Point"]
            },
            {
                "name": "Vector",
                "description": "A 3D vector",
                "compatibleWith": ["Vector3d", "Vector"]
            },
            {
                "name": "Plane",
                "description": "A plane in 3D space",
                "compatibleWith": ["Plane"]
            },
            {
                "name": "Circle",
                "description": "A circle curve",
                "compatibleWith": ["Circle", "Curve"]
            },
            {
                "name": "Line",
                "description": "A line segment",
                "compatibleWith": ["Line", "Curve"]
            },
            {
                "name": "Curve",
                "description": "A curve object",
                "compatibleWith": ["Curve", "Circle", "Line", "Arc", "Polyline"]
            },
            {
                "name": "Brep",
                "description": "A boundary representation object",
                "compatibleWith": ["Brep", "Surface", "Solid"]
            }
        ]
    }

def main():
    """Main entry point for the Grasshopper MCP Bridge Server"""
    try:
        # 啟動 MCP 服務器
        print("Starting Grasshopper MCP Bridge Server...", file=sys.stderr)
        print("Please add this MCP server to Claude Desktop", file=sys.stderr)
        server.run()
    except Exception as e:
        print(f"Error starting MCP server: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
