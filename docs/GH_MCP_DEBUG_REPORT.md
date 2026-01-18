# GH_MCP 除錯報告與改進方案

**日期**: 2026-01-08
**專案**: grasshopper-mcp-workflow
**目標**: 修復 GH_MCP 的已知問題，並擴展功能

---

## 1. 問題總覽

| # | 問題 | 嚴重度 | 狀態 |
|---|------|--------|------|
| 1 | Slider 值無法設定 (min/max 解析失敗) | **Critical** | 待修復 |
| 2 | Move 組件創建 OBSOLETE 版本 | Medium | 已知原因 |
| 3 | 組件 GUID 模糊匹配不精確 | Medium | 已 workaround |
| 4 | 參數名稱大小寫敏感 | Low | 需文檔化 |

---

## 2. 問題 1: Slider 值無法設定 (Critical)

### 2.1 現象
```python
# Python 發送命令
{'type': 'set_slider_properties', 'parameters': {'id': 'xxx', 'min': 5, 'max': 100, 'value': 70}}

# MCP 回應 (看似成功)
{'success': True, 'data': {'value': '70', 'min': None, 'max': None}}

# 實際結果
Slider 值仍為 1.0 (預設範圍 0-1，value=70 被 clamp)
```

### 2.2 根本原因
**檔案**: `GH_MCP/Commands/Components/ComponentProperties.cs`

```csharp
// 行 25-27: GetParameter<double?> 對 JSON 整數返回 null
double? minValue = command.GetParameter<double?>("min");  // 返回 null!
double? maxValue = command.GetParameter<double?>("max");  // 返回 null!

// 行 69-77: 因為 minValue.HasValue = false，所以不執行
if (minValue.HasValue)  // FALSE - 跳過!
{
    slider.Slider.Minimum = (decimal)minValue.Value;
}

// 行 98-101: value 被 clamp 到預設範圍 0-1
if (sliderValue < slider.Slider.Minimum)  // 70 < 0? NO
    sliderValue = slider.Slider.Minimum;
if (sliderValue > slider.Slider.Maximum)  // 70 > 1? YES!
    sliderValue = slider.Slider.Maximum;  // value = 1.0
```

### 2.3 問題分析
`GetParameter<double?>()` 方法無法正確解析 JSON 中的整數類型為 `double?`。

可能原因:
1. JSON 反序列化時 `5` 被解析為 `long` 或 `int`，無法直接轉為 `double?`
2. `Nullable<double>` 的類型轉換邏輯有誤

### 2.4 修復方案

**方案 A: 修改 GetParameter 方法** (推薦)

```csharp
// 在 Command 類或 ComponentProperties 中加入輔助方法
private static double? GetDoubleParameter(Command command, string name)
{
    var value = command.GetParameter<object>(name);
    if (value == null) return null;

    // 處理各種數字類型
    if (value is double d) return d;
    if (value is int i) return (double)i;
    if (value is long l) return (double)l;
    if (value is float f) return (double)f;
    if (value is decimal dec) return (double)dec;

    // 嘗試字符串解析
    if (value is string s && double.TryParse(s, out double result))
        return result;

    return null;
}
```

**方案 B: 修改 SetSliderProperties 方法**

```csharp
public static object SetSliderProperties(Command command)
{
    string idStr = command.GetParameter<string>("id");

    // 使用 object 接收，然後手動轉換
    object minObj = command.GetParameter<object>("min");
    object maxObj = command.GetParameter<object>("max");
    string value = command.GetParameter<string>("value");

    double? minValue = ConvertToDouble(minObj);
    double? maxValue = ConvertToDouble(maxObj);

    // ... 其餘邏輯不變
}

private static double? ConvertToDouble(object obj)
{
    if (obj == null) return null;
    try { return Convert.ToDouble(obj); }
    catch { return null; }
}
```

---

## 3. 問題 2: Move 組件創建 OBSOLETE 版本

### 3.1 現象
```python
add_component(type='Move', x=100, y=100)
# 創建的是 Component_Move_OBSOLETE (標記 "OLD")
```

### 3.2 原因
Grasshopper 有兩個 Move 組件:
- `Component_Move_OBSOLETE` (OLD) - GUID: `7b9b38ec-...`
- `Component_Move` (新版) - GUID: `612a46bd-d9a2-4353-9682-cab31ab5e922`

MCP 的 `FuzzyMatcher` 模糊匹配優先返回了舊版本。

### 3.3 修復方案

**方案 A: 在 add_component 中過濾 OBSOLETE**

```csharp
// ComponentCommandHandler.cs
var matches = FuzzyMatcher.FindMatches(componentType);

// 過濾掉 OBSOLETE 組件
matches = matches.Where(m =>
    !m.Type.Name.Contains("OBSOLETE") &&
    !m.Type.Name.Contains("_OLD")
).ToList();
```

**方案 B: 支援 GUID 直接創建** (推薦)

```csharp
// 新增 add_component_by_guid 命令
public static object AddComponentByGuid(Command command)
{
    string guidStr = command.GetParameter<string>("guid");
    double x = command.GetParameter<double>("x");
    double y = command.GetParameter<double>("y");

    Guid componentGuid = Guid.Parse(guidStr);
    // 直接用 GUID 創建組件
}
```

---

## 4. 問題 3: GUID 模糊匹配不精確

### 4.1 現象
```python
add_component(type='Circle')
# 可能創建 Circle CNR、Circle 3Pt、Circle Fit 等任一版本
```

### 4.2 已實施 Workaround
在 Python 端建立精確 GUID 對照表:

```python
# mcp_layout_executor.py
COMPONENT_GUIDS = {
    'Number Slider': '1ce51ec5-d2af-4673-b720-0c7927e25da8',
    'Center Box': '4e874a4e-95cd-46d0-904d-19cca8fd962c',
    'Orient': 'faed5c8d-971c-47d3-8bf3-053fc4602a0e',
    # ...
}
```

### 4.3 建議改進
新增 `add_component_by_guid` 命令，允許直接指定 GUID。

---

## 5. 問題 4: 參數名稱大小寫敏感

### 5.1 已知參數名對照表

| 組件 | 輸入參數 | 輸出參數 |
|------|----------|----------|
| Number Slider | - | `V` (Value) |
| Construct Point | `X`, `Y`, `Z` | `Pt` |
| XY Plane | `O` (Origin) | `P` (Plane) |
| Center Box | `P` (Plane), `X`, `Y`, `Z` | `B` (Box) |
| Division | `A`, `B` | `R` (Result) |
| Addition | `A`, `B` | `R` (Result) |
| Orient | `G` (Geometry), `A` (Source), `B` (Target) | `G` |
| Merge | `D1`, `D2`, `D3`... | `R` (Result) |
| Custom Preview | `G` (Geometry), `M` (Material) | - |

---

## 6. 新功能建議

### 6.1 新增命令清單

| 命令 | 用途 | 優先級 |
|------|------|--------|
| `add_component_by_guid` | 用 GUID 精確創建組件 | High |
| `get_available_commands` | 列出所有可用命令 | Medium |
| `batch_add_components` | 批量創建組件 | Medium |
| `batch_connect` | 批量連線 | Medium |
| `get_component_parameters` | 查詢組件的輸入/輸出參數名 | High |
| `set_component_nickname` | 設定組件暱稱 | Low |
| `group_components` | 組件分組 | Low |

### 6.2 add_component_by_guid 設計

```json
{
  "type": "add_component_by_guid",
  "parameters": {
    "guid": "4e874a4e-95cd-46d0-904d-19cca8fd962c",
    "x": 100,
    "y": 200,
    "nickname": "MyBox"
  }
}
```

### 6.3 get_component_parameters 設計

```json
// Request
{
  "type": "get_component_parameters",
  "parameters": {
    "id": "xxx-xxx-xxx"
  }
}

// Response
{
  "success": true,
  "data": {
    "inputs": [
      {"name": "P", "nickname": "Plane", "type": "Plane"},
      {"name": "X", "nickname": "X Size", "type": "Number"},
      {"name": "Y", "nickname": "Y Size", "type": "Number"},
      {"name": "Z", "nickname": "Z Size", "type": "Number"}
    ],
    "outputs": [
      {"name": "B", "nickname": "Box", "type": "Box"}
    ]
  }
}
```

### 6.4 batch_add_components 設計

```json
{
  "type": "batch_add_components",
  "parameters": {
    "components": [
      {"type": "Number Slider", "x": 50, "y": 50, "nickname": "Width"},
      {"type": "Number Slider", "x": 50, "y": 100, "nickname": "Height"},
      {"type": "Center Box", "x": 200, "y": 75}
    ]
  }
}
```

---

## 7. 需要修改的檔案清單

| 檔案 | 修改內容 |
|------|----------|
| `Commands/Components/ComponentProperties.cs` | 修復 `GetParameter<double?>` 問題 |
| `Commands/ComponentCommandHandler.cs` | 新增 `add_component_by_guid` |
| `Commands/ComponentCommandHandler.cs` | 過濾 OBSOLETE 組件 |
| `Commands/GrasshopperCommandRegistry.cs` | 註冊新命令 |
| `Models/Command.cs` | 檢查 `GetParameter` 類型轉換 |

---

## 8. 測試驗證清單

### 8.1 Slider 設值測試
```python
# 測試案例
set_slider_properties(id='xxx', min=5, max=100, value=70)
# 預期: Slider 範圍 5-100, 值 70
# 驗證: get_component_info 確認值
```

### 8.2 組件創建測試
```python
# 測試案例 1: 模糊匹配
add_component(type='Move')
# 預期: 創建新版 Move (非 OBSOLETE)

# 測試案例 2: GUID 創建
add_component_by_guid(guid='612a46bd-...', x=100, y=100)
# 預期: 創建指定 GUID 的組件
```

### 8.3 連線測試
```python
# 測試案例
connect_components(source='BoxA', target='BoxB', sourceParam='B', targetParam='G')
# 驗證: Canvas 上可見連線
```

---

## 9. 附錄: 常用組件 GUID 對照表

```python
COMPONENT_GUIDS = {
    # 輸入
    'Number Slider': '1ce51ec5-d2af-4673-b720-0c7927e25da8',
    'Panel': '59e0b89a-e487-49f8-bab8-b5bab16be14c',
    'Boolean Toggle': '2e78987b-9dfb-42a2-8b76-3923ac8bd91a',

    # 點/平面
    'Construct Point': '57c9ff28-1d2f-4af5-9a55-10e279d7b794',
    'XY Plane': '0cc80429-363d-4581-8636-647a753b7560',
    'Unit Z': '53ce9fce-0704-4c57-ba24-68330c2cfc47',

    # 幾何
    'Center Box': '4e874a4e-95cd-46d0-904d-19cca8fd962c',
    'Rectangle 2Pt': '5b50caf1-5d51-4029-b457-5da9bc4b2e63',
    'Circle CNR': '2961b083-c1ee-43a9-a818-b8b47f50d625',

    # 變形
    'Move': '612a46bd-d9a2-4353-9682-cab31ab5e922',  # 新版
    'Orient': 'faed5c8d-971c-47d3-8bf3-053fc4602a0e',
    'Amplitude': 'a7cae2fa-97dd-4034-b613-490b5b4fc7f4',

    # 數學
    'Division': '4f1021a9-657a-4255-9d44-09337cf36705',
    'Addition': 'c6b0aa44-217a-4ae2-88d6-867ce10b3f3a',

    # 數據
    'Merge': '32b92248-1673-4d8b-84da-3b14ce36b2b0',

    # 輸出
    'Custom Preview': '6d8c8b5b-3221-4611-9794-01f16c7b0278',
    'Extrusion': 'e5b9ef88-e10f-4d64-93e9-cac414005cc9',
    'Solid Union': '6de7e1f0-2d51-4e1a-9073-ec17bf699e51',
}
```

---

## 10. 重新編譯指南

### 10.1 環境需求
- .NET 7.0 SDK
- Visual Studio 2022 或 `dotnet` CLI
- Rhino 8 + Grasshopper

### 10.2 編譯步驟
```bash
cd /Users/laihongyi/Downloads/grasshopper-mcp-workflow/GH_MCP
dotnet restore
dotnet build --configuration Release
```

### 10.3 部署
```bash
# 複製 DLL 到 Grasshopper Libraries
cp GH_MCP/bin/Release/net7.0/GH_MCP.gha ~/Library/Application\ Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper/Libraries/
```

---

**文件位置**: `/Users/laihongyi/Downloads/grasshopper-mcp-workflow/docs/GH_MCP_DEBUG_REPORT.md`
