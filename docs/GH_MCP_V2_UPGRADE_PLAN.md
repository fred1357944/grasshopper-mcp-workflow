# GH_MCP v2.0 升級計劃

**建立日期**: 2026-01-08
**版本**: v2.0-draft
**目標**: 解決連線問題、提升錯誤處理、增加批量操作

---

## 1. 核心問題分析

### 1.1 參數匹配順序問題 (Critical)

**位置**: `ConnectionCommandHandler.cs:320-348`

**當前邏輯**:
```csharp
// 1. Name 精確匹配 (case-insensitive)
foreach (var p in parameters) {
    if (string.Equals(p.Name, connection.ParameterName, StringComparison.OrdinalIgnoreCase))
        return p;
}

// 2. Name 模糊匹配 (contains)
foreach (var p in parameters) {
    if (p.Name.IndexOf(connection.ParameterName, StringComparison.OrdinalIgnoreCase) >= 0)
        return p;
}

// 3. NickName 精確匹配 (case-insensitive) ← 放在最後！
foreach (var p in parameters) {
    if (string.Equals(p.NickName, connection.ParameterName, StringComparison.OrdinalIgnoreCase))
        return p;
}
```

**問題**:
- NickName 匹配放在最後，但腳本通常使用 NickName (`R`, `G`, `Pt`)
- 導致連線請求使用 `R` 時，先嘗試 Name 匹配失敗（因為實際是 `Result`）
- 返回 null 導致連線失敗

**建議修改**:
```csharp
private static IGH_Param GetParameter(IGH_DocumentObject docObj, Connection connection, bool isInput)
{
    // ... existing code for param and component handling ...

    if (!string.IsNullOrEmpty(connection.ParameterName))
    {
        string requestedName = connection.ParameterName;

        // 1. NickName 精確匹配 (最常用)
        foreach (var p in parameters)
        {
            if (string.Equals(p.NickName, requestedName, StringComparison.OrdinalIgnoreCase))
            {
                RhinoApp.WriteLine($"  Matched parameter by NickName: {requestedName} -> {p.Name}");
                return p;
            }
        }

        // 2. Name 精確匹配
        foreach (var p in parameters)
        {
            if (string.Equals(p.Name, requestedName, StringComparison.OrdinalIgnoreCase))
            {
                RhinoApp.WriteLine($"  Matched parameter by Name: {requestedName}");
                return p;
            }
        }

        // 3. 模糊匹配 (Name 或 NickName 包含請求字串)
        foreach (var p in parameters)
        {
            if (p.Name.IndexOf(requestedName, StringComparison.OrdinalIgnoreCase) >= 0 ||
                p.NickName.IndexOf(requestedName, StringComparison.OrdinalIgnoreCase) >= 0)
            {
                RhinoApp.WriteLine($"  Matched parameter by fuzzy: {requestedName} -> {p.Name} ({p.NickName})");
                return p;
            }
        }

        // 4. 未找到 - 返回詳細錯誤訊息
        var availableParams = string.Join(", ", parameters.Select(p => $"{p.Name}({p.NickName})"));
        RhinoApp.WriteLine($"  Parameter '{requestedName}' not found. Available: {availableParams}");
    }

    // ... rest of existing code ...
}
```

---

### 1.2 連線失敗詳細訊息 (High)

**位置**: `ConnectionCommandHandler.cs:163-176`

**當前行為**:
- 返回 `Target parameter not found: {name}`
- 沒有告訴使用者可用的參數名稱

**建議修改**:
在連線失敗時，返回可用參數列表：

```csharp
// 獲取目標參數
IGH_Param targetParameter = GetParameter(targetComponent, connection.Target, true);
if (targetParameter == null)
{
    // 收集可用參數名稱
    var availableInputs = new List<string>();
    if (targetComponent is IGH_Component tc)
    {
        foreach (var p in tc.Params.Input)
        {
            availableInputs.Add($"{p.Name} ({p.NickName})");
        }
    }

    string requested = connection.Target.ParameterName ?? connection.Target.ParameterIndex?.ToString() ?? "unknown";
    string available = string.Join(", ", availableInputs);
    exception = new ArgumentException(
        $"Target parameter '{requested}' not found.\n" +
        $"Available inputs: [{available}]");
    return;
}
```

---

### 1.3 OBSOLETE 組件過濾 (Medium)

**位置**: `ComponentCommandHandler.cs:84-108`

**當前行為**:
- 使用 `type` 參數時，已經優先選擇非過時組件 ✓
- 但只使用 GUID 時，無法過濾

**建議改進**:
在 `GetComponentCandidates` 返回結果中，明確標記 `obsolete: true` 並建議替代組件：

```csharp
// 在返回候選時，添加替代建議
var result = new {
    // ... existing fields ...
    obsolete = isObsolete,
    suggestion = isObsolete ? FindNonObsoleteAlternative(p.Desc.Name) : null
};
```

---

## 2. 新增功能

### 2.1 批量操作命令

#### batch_add_components
```json
{
  "type": "batch_add_components",
  "parameters": {
    "components": [
      { "type": "Number Slider", "x": 0, "y": 0, "name": "SLIDER_1" },
      { "type": "Division", "x": 200, "y": 0, "name": "DIV_1" }
    ]
  }
}
```

#### batch_connect
```json
{
  "type": "batch_connect",
  "parameters": {
    "connections": [
      { "from": "SLIDER_1", "fromParam": "V", "to": "DIV_1", "toParam": "A" }
    ]
  }
}
```

### 2.2 查詢參數名命令

#### get_parameter_names
```json
{
  "type": "get_parameter_names",
  "parameters": {
    "componentId": "xxx-xxx-xxx"
  }
}

// 返回
{
  "inputs": [
    { "name": "Geometry", "nickname": "G", "type": "Param_Geometry" }
  ],
  "outputs": [
    { "name": "Result", "nickname": "R", "type": "Param_Number" }
  ]
}
```

---

## 3. 實作優先順序

| 優先級 | 項目 | 檔案 | 預估工作量 |
|-------|------|------|-----------|
| **P0** | NickName 優先匹配 | `ConnectionCommandHandler.cs:320-348` | 30 行 |
| **P0** | 連線失敗詳細訊息 | `ConnectionCommandHandler.cs:163-176` | 20 行 |
| **P1** | batch_connect 命令 | 新增 `BatchCommandHandler.cs` | 100 行 |
| **P1** | batch_add_components | 新增 `BatchCommandHandler.cs` | 80 行 |
| **P2** | get_parameter_names 命令 | `ComponentCommandHandler.cs` | 40 行 |
| **P2** | 過濾 OBSOLETE 組件建議 | `ComponentCommandHandler.cs:723` | 30 行 |

---

## 4. 測試計劃

### 4.1 參數匹配測試案例

| 請求參數 | 實際 Name | 實際 NickName | 預期結果 |
|---------|----------|---------------|---------|
| `R` | Result | R | 匹配成功 (by NickName) |
| `Result` | Result | R | 匹配成功 (by Name) |
| `Res` | Result | R | 匹配成功 (by fuzzy) |
| `Data 1` | Data 1 | D1 | 匹配成功 (by Name) |
| `D1` | Data 1 | D1 | 匹配成功 (by NickName) |
| `X coordinate` | X coordinate | X | 匹配成功 (by Name) |
| `X` | X coordinate | X | 匹配成功 (by NickName) |

### 4.2 批量操作測試

```python
# test_batch_operations.py
def test_batch_connect():
    connections = [
        ("SLIDER_1", "V", "DIV_1", "A"),
        ("SLIDER_2", "V", "DIV_1", "B"),
        ("DIV_1", "R", "PT_1", "Z"),  # 使用 NickName
        ("DIV_1", "Result", "PT_2", "Z coordinate"),  # 使用 Name
    ]
    result = client.batch_connect(connections)
    assert result["successCount"] == 4
    assert len(result["failures"]) == 0
```

---

## 5. 相關文件

| 文件 | 說明 |
|------|------|
| `docs/GH_MCP_PARAMETER_REFERENCE.md` | 參數名對照表 |
| `GH_MCP/GH_MCP/Commands/ConnectionCommandHandler.cs` | 連線處理 |
| `GH_MCP/GH_MCP/Commands/ComponentCommandHandler.cs` | 組件處理 |
| `docs/GH_MCP_RECOMPILE_GUIDE.md` | 重新編譯指南 |

---

## 6. 版本歷史

| 日期 | 版本 | 變更 |
|------|------|------|
| 2026-01-08 | v2.0-draft | 初始升級計劃 |

