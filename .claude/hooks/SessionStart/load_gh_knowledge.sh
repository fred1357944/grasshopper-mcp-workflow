#!/bin/bash
# GH_MCP Knowledge Loader - SessionStart Hook
# Outputs key knowledge at session start to help Claude remember critical info

CONFIG_DIR="$(dirname "$0")/../../../config"

echo "=== GH_MCP Knowledge Loaded ==="
echo ""

# Available Commands
echo "【Available MCP Commands】"
if command -v jq &> /dev/null && [ -f "$CONFIG_DIR/mcp_commands.json" ]; then
    jq -r '.available | keys[]' "$CONFIG_DIR/mcp_commands.json" 2>/dev/null | head -10
else
    echo "  add_component, connect_components, set_slider_properties"
    echo "  set_component_value, get_component_candidates, get_errors"
    echo "  get_document_info, get_component_info, clear_document"
fi
echo ""

# Unavailable Commands
echo "【Unavailable Commands (DO NOT USE)】"
if command -v jq &> /dev/null && [ -f "$CONFIG_DIR/mcp_commands.json" ]; then
    jq -r '.unavailable[]' "$CONFIG_DIR/mcp_commands.json" 2>/dev/null | head -8
else
    echo "  clear_canvas, new_document, save_document, undo, redo"
fi
echo ""

# Critical GUIDs
echo "【Critical GUIDs (Verified Mac Rhino 8)】"
echo "  Rotate: 19c70daf-600f-4697-ace2-567f6702144d"
echo "  Pipe: 1ee25749-2e2d-4fc6-9209-0ea515081f9"
echo "  Series: 651c4fa5-dff4-4be6-ba31-6dc267d3ab47"
echo "  Face Normals: f4370b82-4bd6-4ca7-90e8-c88584b280d5"
echo "  Mesh Box: c4ac4e68-060e-4cd0-85b1-1f2e3663c449"
echo ""

# Common Mistakes
echo "【Common Mistakes to AVOID】"
echo "  1. Panel as number input -> Use Number Slider"
echo "  2. set_slider_properties value before min/max -> Set range first"
echo "  3. clear_canvas command -> Use clear_document"
echo "  4. Rotate GUID 5944e8e2... -> OBSOLETE, use 19c70daf..."
echo ""

# Available Patterns
echo "【Available Patterns】"
if command -v jq &> /dev/null && [ -f "$CONFIG_DIR/connection_patterns.json" ]; then
    jq -r '.patterns | keys[]' "$CONFIG_DIR/connection_patterns.json" 2>/dev/null | head -10
else
    echo "  WASP_Stochastic, WASP_Mesh_Part, Karamba_Structural"
    echo "  Kangaroo_Form_Finding, Ladybug_Solar, Lunchbox_Panelization"
fi
echo ""

echo "=== Query: from grasshopper_mcp.knowledge_base import lookup ==="
