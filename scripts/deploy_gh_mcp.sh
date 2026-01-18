#!/bin/bash
# deploy_gh_mcp.sh - GH_MCP 完整部署腳本
# 用法: bash scripts/deploy_gh_mcp.sh

set -e

SOURCE="/Users/laihongyi/Downloads/grasshopper-mcp-workflow/GH_MCP/GH_MCP/bin/Release/net7.0/GH_MCP.gha"

# 定義所有目標目錄
DEST_COMPONENTS="/Applications/Rhino 8.app/Contents/Frameworks/RhCore.framework/Versions/A/Resources/ManagedPlugIns/GrasshopperPlugin.rhp/Components"
DEST_GUID_LIB="$HOME/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper (b45a29b1-4343-4035-989e-044e8580d9cf)/Libraries"
DEST_SIMPLE_LIB="$HOME/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper/Libraries"

echo "╔════════════════════════════════════════╗"
echo "║     GH_MCP 部署腳本 v1.0              ║"
echo "╚════════════════════════════════════════╝"
echo ""

# 檢查源檔案
if [ ! -f "$SOURCE" ]; then
    echo "❌ ERROR: 源檔案不存在"
    echo "   路徑: $SOURCE"
    echo ""
    echo "請先編譯:"
    echo "   cd GH_MCP && dotnet build -c Release --framework net7.0"
    exit 1
fi

echo "📦 源檔案:"
ls -la "$SOURCE"
SOURCE_MD5=$(md5 -q "$SOURCE")
echo "   MD5: $SOURCE_MD5"
echo ""

# 部署到所有目錄
DEPLOYED=0
for DEST in "$DEST_COMPONENTS" "$DEST_GUID_LIB" "$DEST_SIMPLE_LIB"; do
    if [ -d "$DEST" ]; then
        echo "📁 部署到: $(basename "$DEST")"

        # 備份舊版本
        if [ -f "$DEST/GH_MCP.gha" ]; then
            BACKUP="$DEST/GH_MCP.gha.backup.$(date +%Y%m%d_%H%M%S)"
            cp "$DEST/GH_MCP.gha" "$BACKUP"
            echo "   備份: $(basename "$BACKUP")"
        fi

        # 複製新版本
        cp "$SOURCE" "$DEST/GH_MCP.gha"

        # 驗證
        DEST_MD5=$(md5 -q "$DEST/GH_MCP.gha")
        if [ "$SOURCE_MD5" = "$DEST_MD5" ]; then
            echo "   ✓ MD5 驗證通過"
            DEPLOYED=$((DEPLOYED + 1))
        else
            echo "   ✗ MD5 不符!"
        fi
        echo ""
    fi
done

echo "════════════════════════════════════════"
echo "✓ 部署完成: $DEPLOYED 個目錄"
echo ""
echo "🔄 請重啟 Rhino/Grasshopper 載入新版本"
echo ""

# 顯示所有 GH_MCP.gha 的狀態
echo "📋 當前所有 GH_MCP.gha:"
for DEST in "$DEST_COMPONENTS" "$DEST_GUID_LIB" "$DEST_SIMPLE_LIB"; do
    if [ -f "$DEST/GH_MCP.gha" ]; then
        TIMESTAMP=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$DEST/GH_MCP.gha")
        echo "   $TIMESTAMP  $(basename "$(dirname "$DEST")")/$(basename "$DEST")"
    fi
done
