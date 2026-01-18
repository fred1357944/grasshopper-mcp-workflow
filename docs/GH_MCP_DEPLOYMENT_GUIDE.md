# GH_MCP 部署指南與排錯記錄

**建立日期**: 2026-01-09
**版本**: v1.0

---

## 1. 關鍵發現：Grasshopper 有多個插件目錄

### 1.1 問題描述

2026-01-09 部署 GH_MCP v2.0 時發現：Grasshopper 會從**多個目錄**載入插件，導致版本衝突。

### 1.2 Grasshopper 插件目錄結構

| 優先級 | 目錄路徑 | 用途 |
|-------|---------|------|
| 1 | `/Applications/Rhino 8.app/.../GrasshopperPlugin.rhp/Components/` | 系統組件目錄 |
| 2 | `~/Library/.../Grasshopper (b45a29b1-...)/Libraries/` | 用戶 GUID 目錄 |
| 3 | `~/Library/.../Grasshopper/Libraries/` | 用戶簡化目錄 |

**完整路徑**:
```
# 1. 系統組件目錄 (需要管理員權限)
/Applications/Rhino 8.app/Contents/Frameworks/RhCore.framework/Versions/A/Resources/ManagedPlugIns/GrasshopperPlugin.rhp/Components/

# 2. 用戶 GUID Libraries 目錄
~/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper (b45a29b1-4343-4035-989e-044e8580d9cf)/Libraries/

# 3. 用戶簡化 Libraries 目錄
~/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper/Libraries/
```

### 1.3 問題根因

我們只部署到目錄 #3，但 Grasshopper 實際從目錄 #1 和 #2 載入，導致：
- 顯示「File Conflict」對話框
- 載入的是舊版本而非新編譯的版本

---

## 2. 正確的部署流程

### 2.1 自動部署腳本

```bash
#!/bin/bash
# deploy_gh_mcp.sh - GH_MCP 完整部署腳本

SOURCE="/Users/laihongyi/Downloads/grasshopper-mcp-workflow/GH_MCP/GH_MCP/bin/Release/net7.0/GH_MCP.gha"

# 定義所有目標目錄
DEST_COMPONENTS="/Applications/Rhino 8.app/Contents/Frameworks/RhCore.framework/Versions/A/Resources/ManagedPlugIns/GrasshopperPlugin.rhp/Components"
DEST_GUID_LIB="$HOME/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper (b45a29b1-4343-4035-989e-044e8580d9cf)/Libraries"
DEST_SIMPLE_LIB="$HOME/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper/Libraries"

echo "=== GH_MCP 部署腳本 ==="
echo "Source: $SOURCE"
echo ""

# 檢查源檔案
if [ ! -f "$SOURCE" ]; then
    echo "ERROR: 源檔案不存在，請先編譯"
    echo "執行: cd GH_MCP && dotnet build -c Release --framework net7.0"
    exit 1
fi

# 部署到所有目錄
for DEST in "$DEST_COMPONENTS" "$DEST_GUID_LIB" "$DEST_SIMPLE_LIB"; do
    if [ -d "$DEST" ]; then
        echo "部署到: $DEST"
        cp "$SOURCE" "$DEST/GH_MCP.gha"
        ls -la "$DEST/GH_MCP.gha"
    else
        echo "跳過 (目錄不存在): $DEST"
    fi
    echo ""
done

# 驗證 MD5
echo "=== MD5 驗證 ==="
SOURCE_MD5=$(md5 -q "$SOURCE")
echo "Source MD5: $SOURCE_MD5"

for DEST in "$DEST_COMPONENTS" "$DEST_GUID_LIB" "$DEST_SIMPLE_LIB"; do
    if [ -f "$DEST/GH_MCP.gha" ]; then
        DEST_MD5=$(md5 -q "$DEST/GH_MCP.gha")
        if [ "$SOURCE_MD5" = "$DEST_MD5" ]; then
            echo "✓ $DEST"
        else
            echo "✗ MD5 不符: $DEST"
        fi
    fi
done

echo ""
echo "=== 部署完成 ==="
echo "請重啟 Rhino/Grasshopper 載入新版本"
```

### 2.2 一鍵編譯部署命令

```bash
# 編譯 + 部署
cd /Users/laihongyi/Downloads/grasshopper-mcp-workflow/GH_MCP && \
dotnet build -c Release --framework net7.0 && \
bash ../scripts/deploy_gh_mcp.sh
```

---

## 3. 跨平台編譯注意事項

### 3.1 .NET Framework vs .NET 7.0 API 差異

| API | .NET Framework (Windows) | .NET 7.0 (macOS) |
|-----|--------------------------|------------------|
| `IGH_Attributes.Hidden` | ✓ | ✗ 需用反射 |
| `GH_Document.SelectObjects()` | ✓ | ✗ 需條件編譯 |
| `GH_Viewport.Pan` | ✓ | ✗ 需條件編譯 |

### 3.2 條件編譯模式

```csharp
#if NETFRAMEWORK
    // Windows-only code
    component.Attributes.Hidden = hidden.Value;
#else
    // .NET 7.0 alternative
    try
    {
        var hiddenProp = component.Attributes?.GetType().GetProperty("Hidden");
        if (hiddenProp != null && hiddenProp.CanWrite)
        {
            hiddenProp.SetValue(component.Attributes, hidden.Value);
        }
    }
    catch { /* fallback */ }
#endif
```

---

## 4. 排錯檢查清單

### 4.1 部署前檢查

- [ ] `dotnet build` 是否成功 (0 個錯誤)
- [ ] 輸出檔案時間戳是否為最新
- [ ] 輸出檔案大小是否合理 (~120KB)

### 4.2 部署後檢查

- [ ] 所有 3 個目錄的 GH_MCP.gha 時間戳一致
- [ ] 所有 3 個目錄的 MD5 一致
- [ ] Grasshopper 載入時無「File Conflict」警告

### 4.3 驗證命令

```bash
# 檢查所有 GH_MCP.gha 位置和時間
ls -la "/Applications/Rhino 8.app/Contents/Frameworks/RhCore.framework/Versions/A/Resources/ManagedPlugIns/GrasshopperPlugin.rhp/Components/GH_MCP.gha"
ls -la "$HOME/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper (b45a29b1-4343-4035-989e-044e8580d9cf)/Libraries/GH_MCP.gha"
ls -la "$HOME/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper/Libraries/GH_MCP.gha"
```

---

## 5. 常見問題

### Q1: Grasshopper 顯示 "File Conflict" 對話框

**原因**: 多個目錄存在不同版本的 GH_MCP.gha

**解決**: 執行部署腳本更新所有目錄

### Q2: 編譯成功但新功能沒生效

**原因**: 部署到了錯誤的目錄

**解決**: 檢查所有 3 個目錄的時間戳

### Q3: 編譯錯誤 CS1061 (API 不存在)

**原因**: 使用了 Windows-only API

**解決**: 使用 `#if NETFRAMEWORK` 條件編譯

---

## 6. 版本歷史

| 日期 | 版本 | 變更 |
|------|------|------|
| 2026-01-09 | v1.0 | 初始版本，記錄部署問題排錯過程 |
