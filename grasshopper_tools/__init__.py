"""
Grasshopper MCP 工具模組

提供統一的 Grasshopper MCP 操作接口，包括：
- 組件管理（創建、查詢、刪除）
- 連接管理（創建、修正、檢查）
- 參數設置（slider、vector 等）
- 群組管理
- MMD/JSON 解析工具
"""

from .client import GrasshopperClient
from .component_manager import ComponentManager
from .connection_manager import ConnectionManager
from .parameter_setter import ParameterSetter
from .group_manager import GroupManager
from .parser_utils import MMDParser, JSONGenerator
from .placement_executor import PlacementExecutor
from .utils import (
    load_component_id_map,
    save_component_id_map,
    load_placement_info,
    update_guids_in_json,
    DEFAULT_GUID_MAP,
    hex_to_rgb,
    determine_slider_range
)

__all__ = [
    'GrasshopperClient',
    'ComponentManager',
    'ConnectionManager',
    'ParameterSetter',
    'GroupManager',
    'MMDParser',
    'JSONGenerator',
    'PlacementExecutor',
    'load_component_id_map',
    'save_component_id_map',
    'load_placement_info',
    'update_guids_in_json',
    'DEFAULT_GUID_MAP',
    'hex_to_rgb',
    'determine_slider_range',
]

__version__ = '1.0.0'

# CLI 入口點
def cli_main():
    """命令行接口入口點"""
    from .cli import main
    main()

