# GH_MCP 重新編譯指南

**日期**: 2026-01-09
**版本**: v2.0 (參數匹配優化 + 錯誤訊息改進)

---

## 1. 本次修改摘要

### 1.1 核心修復

| 檔案 | 修改 | 影響 |
|------|------|------|
| `Commands/ConnectionCommandHandler.cs:331-370` | **NickName 優先匹配** | **Critical** - 解決連線失敗問題 |
| `Commands/ConnectionCommandHandler.cs:174-186` | **錯誤訊息顯示可用參數** | **High** - 改善除錯體驗 |
| `Models/GrasshopperCommand.cs` | 修復 `GetParameter<T>` 的 Nullable 類型處理 | **Critical** - 解決 Slider 值無法設定問題 |

### 1.2 v2.0 關鍵變更

**參數匹配順序優化** (`GetParameter` 方法):
```
舊順序: Name精確 → Name模糊 → NickName精確 (❌ 常失敗)
新順序: NickName精確 → Name精確 → 模糊匹配 (✓ 腳本友好)
```

**連線失敗錯誤訊息改進**:
```
舊: "Target parameter not found: R"
新: "Target parameter 'R' not found. Available inputs: [Geometry(G), Source(A), Target(B)]"
```

### 1.2 修復內容詳情

**問題**: `GetParameter<double?>` 無法正確解析 JSON 中的整數

**根本原因**:
- JSON 整數 `5` 被解析為 `long`
- `Convert.ChangeType()` 無法將 `long` 轉換為 `Nullable<double>`
- 導致 `min`/`max` 參數總是返回 `null`

**修復方案**:
```csharp
// 新增 Nullable.GetUnderlyingType() 檢查
Type underlyingType = Nullable.GetUnderlyingType(targetType);

if (underlyingType != null)
{
    object converted = ConvertToNumeric(value, underlyingType);
    if (converted != null)
    {
        return (T)converted;
    }
}

// 新增 ConvertToNumeric() 輔助方法處理各種數字類型
```

---

## 2. 環境需求

### 2.1 必要軟體

- **.NET SDK**: 7.0 或更高版本
- **Visual Studio 2022** 或 **dotnet CLI**
- **Rhino 8** + Grasshopper

### 2.2 驗證環境

```bash
# 檢查 .NET SDK
dotnet --version
# 預期輸出: 7.x.x 或 8.x.x

# 列出所有 SDK
dotnet --list-sdks
```

---

## 3. 編譯步驟

### 3.1 方法 A: 使用 dotnet CLI (推薦)

```bash
# 1. 進入 GH_MCP 目錄
cd /Users/laihongyi/Downloads/grasshopper-mcp-workflow/GH_MCP

# 2. 還原 NuGet 套件
dotnet restore

# 3. 編譯 Release 版本
dotnet build --configuration Release

# 4. 確認輸出檔案
ls -la GH_MCP/bin/Release/net7.0/
```

**預期輸出檔案**:
- `GH_MCP.gha` - Grasshopper 插件主檔
- `GH_MCP.dll` - 核心程式庫
- `Newtonsoft.Json.dll` - JSON 處理

### 3.2 方法 B: 使用 Visual Studio

1. 開啟 `GH_MCP.sln`
2. 選擇 **Release** 組態
3. 建置 > 建置方案 (Ctrl+Shift+B)
4. 輸出位於 `GH_MCP/bin/Release/net7.0/`

---

## 4. 部署

### 4.1 自動部署腳本

```bash
#!/bin/bash
# deploy_gh_mcp.sh

# 設定路徑
SOURCE_DIR="/Users/laihongyi/Downloads/grasshopper-mcp-workflow/GH_MCP/GH_MCP/bin/Release/net7.0"
DEST_DIR="$HOME/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper/Libraries"

# 停止 Rhino (如果運行中)
echo "請先關閉 Rhino..."

# 備份舊版本
if [ -f "$DEST_DIR/GH_MCP.gha" ]; then
    BACKUP_NAME="GH_MCP.gha.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$DEST_DIR/GH_MCP.gha" "$DEST_DIR/$BACKUP_NAME"
    echo "舊版本已備份: $BACKUP_NAME"
fi

# 複製新版本
cp "$SOURCE_DIR/GH_MCP.gha" "$DEST_DIR/"
cp "$SOURCE_DIR/GH_MCP.dll" "$DEST_DIR/"
cp "$SOURCE_DIR/Newtonsoft.Json.dll" "$DEST_DIR/" 2>/dev/null

echo "部署完成!"
echo "請重新啟動 Rhino 和 Grasshopper"
```

### 4.2 手動部署

```bash
# 複製檔案到 Grasshopper Libraries
cp GH_MCP/bin/Release/net7.0/GH_MCP.gha \
   ~/Library/Application\ Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper/Libraries/

cp GH_MCP/bin/Release/net7.0/GH_MCP.dll \
   ~/Library/Application\ Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper/Libraries/
```

---

## 5. 驗證測試

### 5.1 基本連接測試

```python
import socket
import json

def test_connection():
    """測試 MCP 基本連接"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    try:
        sock.connect(('127.0.0.1', 8080))
        print("✓ 連接成功!")

        # 發送 get_document_info
        command = json.dumps({"type": "get_document_info"}) + "\n"
        sock.sendall(command.encode())

        response = sock.recv(4096).decode()
        result = json.loads(response)

        if result.get("success"):
            print("✓ MCP 服務正常!")
        else:
            print(f"✗ 錯誤: {result.get('error')}")

    except Exception as e:
        print(f"✗ 連接失敗: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    test_connection()
```

### 5.2 Slider 修復驗證測試

```python
import socket
import json

def send_command(cmd_type, params=None):
    """發送 MCP 命令"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10.0)
    sock.connect(('127.0.0.1', 8080))

    command = {"type": cmd_type}
    if params:
        command["parameters"] = params

    sock.sendall((json.dumps(command) + "\n").encode())
    response = sock.recv(8192).decode('utf-8-sig')
    sock.close()

    return json.loads(response.strip())

def test_slider_fix():
    """驗證 Slider 修復"""
    print("=== 測試 Slider 修復 ===\n")

    # 1. 清空文檔
    print("1. 清空文檔...")
    send_command("clear_document")

    # 2. 創建 Number Slider
    print("2. 創建 Number Slider...")
    result = send_command("add_component", {
        "type": "Number Slider",
        "x": 100,
        "y": 100
    })

    if not result.get("success"):
        print(f"✗ 創建失敗: {result.get('error')}")
        return

    slider_id = result["data"]["id"]
    print(f"   Slider ID: {slider_id}")

    # 3. 設置 Slider 屬性 (關鍵測試)
    print("3. 設置 Slider 屬性 (min=5, max=100, value=70)...")
    result = send_command("set_slider_properties", {
        "id": slider_id,
        "min": 5,       # JSON 整數，測試 Nullable<double> 轉換
        "max": 100,     # JSON 整數
        "value": "70"   # 字串
    })

    print(f"   回應: {json.dumps(result, indent=2)}")

    # 4. 驗證設置結果
    print("\n4. 驗證設置結果...")
    info = send_command("get_component_info", {"id": slider_id})

    if info.get("success"):
        data = info["data"]
        value = data.get("value", "N/A")
        minimum = data.get("minimum", "N/A")
        maximum = data.get("maximum", "N/A")

        print(f"   Value: {value}")
        print(f"   Min: {minimum}")
        print(f"   Max: {maximum}")

        # 判斷是否修復成功
        if minimum == 5.0 and maximum == 100.0 and value == 70.0:
            print("\n✓ Slider 修復驗證成功!")
        elif minimum is None or minimum == 0:
            print("\n✗ 修復失敗! min 仍為 None 或 0")
            print("  請確認已重新編譯並部署 GH_MCP.gha")
        else:
            print(f"\n? 部分成功，請檢查數值")
    else:
        print(f"✗ 獲取信息失敗: {info.get('error')}")

if __name__ == "__main__":
    test_slider_fix()
```

---

## 6. 常見問題

### 6.1 編譯錯誤: 找不到 Grasshopper.dll

```
error CS0234: The type or namespace name 'Kernel' does not exist...
```

**解決方案**:
1. 確認 Rhino 8 已安裝
2. 檢查 `GH_MCP.csproj` 中的參考路徑:
   ```xml
   <HintPath>/Applications/Rhino 8.app/Contents/Frameworks/RhCore.framework/...</HintPath>
   ```

### 6.2 部署後 Grasshopper 無法載入

**可能原因**:
1. .NET 版本不匹配
2. DLL 衝突

**解決方案**:
```bash
# 移除所有舊版本
cd ~/Library/Application\ Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper/Libraries/
rm GH_MCP*.gha GH_MCP*.dll
```

### 6.3 MCP 連接拒絕

**檢查步驟**:
1. 確認 Grasshopper 已開啟
2. 檢查 GH_MCP 組件面板是否出現
3. 查看 Rhino 命令行是否有錯誤訊息

---

## 7. 修改檔案完整路徑

```
grasshopper-mcp-workflow/
├── GH_MCP/
│   └── GH_MCP/
│       ├── Models/
│       │   └── GrasshopperCommand.cs  ← 已修改
│       ├── Commands/
│       │   ├── ComponentCommandHandler.cs
│       │   ├── Components/
│       │   │   └── ComponentProperties.cs
│       │   └── GrasshopperCommandRegistry.cs
│       └── GH_MCP.csproj
└── docs/
    ├── GH_MCP_DEBUG_REPORT.md         ← 除錯報告
    └── GH_MCP_RECOMPILE_GUIDE.md      ← 本文件
```

---

## 8. 快速指令總結

```bash
# 一鍵編譯
cd /Users/laihongyi/Downloads/grasshopper-mcp-workflow/GH_MCP && dotnet build -c Release

# 一鍵部署 (確保 Rhino 已關閉)
cp GH_MCP/bin/Release/net7.0/GH_MCP.gha ~/Library/Application\ Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper/Libraries/

# 驗證部署
ls -la ~/Library/Application\ Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper/Libraries/GH_MCP*
```

---

**文件位置**: `/Users/laihongyi/Downloads/grasshopper-mcp-workflow/docs/GH_MCP_RECOMPILE_GUIDE.md`
