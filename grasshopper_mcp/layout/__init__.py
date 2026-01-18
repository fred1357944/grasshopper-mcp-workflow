"""
Grasshopper Canvas Layout Module

提供自動佈局計算功能和 MCP 整合執行
"""

from .canvas_layout import (
    CanvasLayoutCalculator,
    ComponentNode,
    Connection,
    LayoutConfig,
)

from .mcp_layout_executor import (
    MCPLayoutExecutor,
    ComponentDef,
    ConnectionDef,
    SliderConfig,
    create_simple_table_design,
)

__all__ = [
    'CanvasLayoutCalculator',
    'ComponentNode',
    'Connection',
    'LayoutConfig',
    'MCPLayoutExecutor',
    'ComponentDef',
    'ConnectionDef',
    'SliderConfig',
    'create_simple_table_design',
]
