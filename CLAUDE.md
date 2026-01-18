# GH_MCP Workflow 專案指南

## GH_MCP C# 開發關鍵提醒

### 部署注意事項 (CRITICAL)

**Grasshopper 插件正確目錄** (Rhino 8 Mac):

```bash
# 正確路徑 (有 GUID 後綴！)
~/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper (b45a29b1-4343-4035-989e-044e8580d9cf)/Libraries/

# 錯誤路徑 (不要用！)
# ~/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper/Libraries/

# 部署命令
cp GH_MCP_Vision.gha "~/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper (b45a29b1-4343-4035-989e-044e8580d9cf)/Libraries/"
```

### 編譯命令

```bash
cd GH_MCP && dotnet build -c Release --framework net7.0
```

### 跨平台 API 差異

macOS (.NET 7.0) 不支援以下 Windows API：
- `IGH_Attributes.Hidden` → 使用反射
- `GH_Document.SelectObjects()` → 使用 `#if NETFRAMEWORK`
- `GH_Viewport.Pan` → 使用 `#if NETFRAMEWORK`

### 參數名注意

Grasshopper 參數有 **Name** (全名) 和 **NickName** (短名)：
- 連線時優先使用 NickName (`R`, `Pt`, `G`)
- v2.0 已修復：NickName 優先匹配

### 相關文檔

- `docs/GH_MCP_DEPLOYMENT_GUIDE.md` - 部署指南
- `docs/GH_MCP_PARAMETER_REFERENCE.md` - 參數名對照表
- `docs/GH_MCP_V2_UPGRADE_PLAN.md` - 升級計劃
