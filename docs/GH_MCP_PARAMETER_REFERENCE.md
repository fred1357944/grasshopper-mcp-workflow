# GH_MCP 參數名對照表與知識庫

**建立日期**: 2026-01-08
**版本**: v1.0
**目的**: 記錄 Grasshopper 組件的正確參數名稱，避免連線失敗

---

## 1. 核心發現：Name vs NickName 問題

### 問題描述
Grasshopper 組件的參數有兩個名稱：
- **Name** (全名): 如 `Result`, `Geometry`, `Data 1`
- **NickName** (短名): 如 `R`, `G`, `D1`

GH_MCP 的 `connect_components` 命令**優先匹配 Name**，如果使用 NickName 可能匹配失敗。

### 影響
- 腳本使用短名（如 `R`, `Pt`, `D1`）會導致連線失敗
- 但 GH_MCP 仍返回 `success: true`，只是內層 `data.success` 為 false

---

## 2. 組件參數名對照表

### 2.1 數學運算組件

| 組件 | 類型名 | 輸入 (Name) | 輸入 (NickName) | 輸出 (Name) | 輸出 (NickName) | 狀態 |
|------|--------|-------------|-----------------|-------------|-----------------|------|
| Division | `Operator_Division` | A, B | A, B | **Result** | R | OK |
| **Mass Addition** | `Component_MassAddition` | Input | **I** | Result, Partial Results | **R**, Pr | **推薦** |
| **Negative** | (標準) | x | **x** | y | **y** | **推薦** |
| Addition | `Component_VariableAddition` | A, B | A, B | **Result** | R | **OBSOLETE** |
| Multiplication | `Operator_Multiplication` | A, B | A, B | **Result** | R | **OBSOLETE** |
| Subtraction | `Operator_Subtraction` | A, B | A, B | **Result** | R | OK |

> **重要**: 避免使用 OBSOLETE 組件！用 Mass Addition 替代 Addition，用 Negative 替代 Multiplication (取負值)

### 2.2 幾何構造組件

| 組件 | 類型名 | 輸入 (Name) | 輸入 (NickName) | 輸出 (Name) | 輸出 (NickName) |
|------|--------|-------------|-----------------|-------------|-----------------|
| Construct Point | `Component_ConstructPoint` | **X coordinate**, **Y coordinate**, **Z coordinate** | X, Y, Z | **Point** | Pt |
| XY Plane | `Component_XYPlane` | Origin | O | **Plane** | Pl |
| Center Box | `Component_CenterBox` | **Base**, X, Y, Z | P, X, Y, Z | **Box** | B |

### 2.3 變形組件

| 組件 | 類型名 | 輸入 (Name) | 輸入 (NickName) | 輸出 (Name) | 輸出 (NickName) |
|------|--------|-------------|-----------------|-------------|-----------------|
| Orient | `Component_Orient` | **Geometry**, **Source**, **Target** | G, A, B | **Geometry**, Transform | G, X |
| Move | `Component_Move` | Geometry, Motion | G, T | Geometry, Transform | G, X |

### 2.4 數據處理組件

| 組件 | 類型名 | 輸入 (Name) | 輸入 (NickName) | 輸出 (Name) | 輸出 (NickName) |
|------|--------|-------------|-----------------|-------------|-----------------|
| Merge | `Component_MergeVariable` | **Data 1**, **Data 2**, Data 3, ... | D1, D2, D3, ... | **Result** | R |

### 2.5 輸入/輸出組件

| 組件 | 類型名 | 輸入 (Name) | 輸入 (NickName) | 輸出 (Name) | 輸出 (NickName) |
|------|--------|-------------|-----------------|-------------|-----------------|
| Number Slider | `GH_NumberSlider` | - | - | **Value** | V |
| Custom Preview | `GH_CustomPreviewComponent` | **Geometry**, Material | G, M | - | - |

---

## 3. 常見錯誤與修正

### 3.1 連線參數名錯誤

| 錯誤用法 | 正確用法 | 說明 |
|----------|----------|------|
| `Division.R` | `Division.Result` | Division 輸出 |
| `Addition.R` | `Addition.Result` | Addition 輸出 |
| `Merge.R` | `Merge.Result` | Merge 輸出 |
| `Merge.D1` | `Merge.Data 1` | Merge 輸入 (注意空格) |
| `Merge.D2` | `Merge.Data 2` | Merge 輸入 (注意空格) |
| `ConstructPoint.Pt` | `ConstructPoint.Point` | 點輸出 |
| `ConstructPoint.X` | `ConstructPoint.X coordinate` | X 座標輸入 (注意空格) |
| `ConstructPoint.Y` | `ConstructPoint.Y coordinate` | Y 座標輸入 (注意空格) |
| `ConstructPoint.Z` | `ConstructPoint.Z coordinate` | Z 座標輸入 (注意空格) |
| `CenterBox.P` | `CenterBox.Base` | Box 的平面輸入 |
| `Orient.G` | `Orient.Geometry` | Orient 幾何輸入/輸出 |
| `Orient.A` | `Orient.Source` | Orient 源平面 |
| `Orient.B` | `Orient.Target` | Orient 目標平面 |
| `XYPlane.P` | `XYPlane.Plane` 或 `Pl` | XY Plane 輸出 (Pl 可行) |
| `Preview.G` | `Preview.Geometry` | Custom Preview 輸入 |

### 3.2 Slider 值設置問題

**問題**: `GetParameter<double?>` 無法解析 JSON 整數

**修復** (已在 `GrasshopperCommand.cs` 中實現):
```csharp
// 使用 Nullable.GetUnderlyingType() 處理 Nullable 類型
Type underlyingType = Nullable.GetUnderlyingType(targetType);
if (underlyingType != null) {
    object converted = ConvertToNumeric(value, underlyingType);
    if (converted != null) return (T)converted;
}
```

### 3.3 組件創建失敗

**問題**: 只用 GUID 創建組件會失敗

**修復** (已在 `mcp_layout_executor.py` 中實現):
```python
params = {
    'guid': guid if guid else 'dummy',
    'type': type_name,  # 同時傳遞 type 做模糊匹配
    'x': x,
    'y': y
}
```

---

## 4. GH_MCP 改進清單

### 4.1 Critical (必須修復)

| # | 問題 | 當前行為 | 建議修改 | 檔案位置 |
|---|------|----------|----------|----------|
| 1 | NickName 匹配優先級低 | 先匹配 Name，後匹配 NickName | **優先匹配 NickName** | `ConnectionCommandHandler.cs:320-348` |
| 2 | 連線失敗無詳細錯誤 | 返回 `success: true` 但 `data.success: false` | 返回「參數 X 不存在，可用: [...]」 | `ConnectionCommandHandler.cs:163-176` |

### 4.2 High (重要改進)

| # | 問題 | 建議修改 |
|---|------|----------|
| 3 | 無批量操作命令 | 新增 `batch_add_components`, `batch_connect` |
| 4 | 創建 OBSOLETE 組件 | 模糊匹配時過濾 `name.Contains("OBSOLETE")` |

### 4.3 Medium (功能增強)

| # | 問題 | 建議修改 |
|---|------|----------|
| 5 | 無法設置組件 NickName | 新增 `set_component_nickname` 命令 |
| 6 | 無法查詢可用參數 | 在 `get_component_info` 返回 Name + NickName |

---

## 5. Python 腳本最佳實踐

### 5.1 連線時使用全名

```python
# 錯誤
executor.define_connection("DIV", "R", "PT", "Z")

# 正確
executor.define_connection("DIV", "Result", "PT", "Z coordinate")
```

### 5.2 檢查連線結果

```python
def create_connection(self, from_name, from_param, to_name, to_param):
    result = self._send_command('connect_components', {...})

    # 檢查外層 AND 內層 success
    if result.get('success'):
        data = result.get('data', {})
        inner_success = data.get('success', data.get('verified', False))
        if inner_success:
            return True
        else:
            print(f"連線失敗: {data.get('message')}")
            return False
    return False
```

### 5.3 組件類型名對照

```python
COMPONENT_TYPES = {
    # 推薦使用的類型名 (避免 OBSOLETE)
    'Number Slider': 'Number Slider',
    'Division': 'Division',
    'Addition': 'Addition',
    'Construct Point': 'Construct Point',
    'XY Plane': 'XY Plane',
    'Center Box': 'Center Box',
    'Orient': 'Orient',
    'Merge': 'Merge',
    'Custom Preview': 'Custom Preview',
}
```

---

## 6. 測試驗證腳本

### 6.1 參數名查詢腳本

```python
#!/usr/bin/env python3
"""查詢組件的實際參數名"""
import socket, json, time

def cmd(cmd_type, params=None):
    s = socket.socket()
    s.settimeout(10)
    s.connect(('127.0.0.1', 8080))
    c = {'type': cmd_type}
    if params: c['parameters'] = params
    s.sendall((json.dumps(c) + '\n').encode())
    time.sleep(0.3)
    data = s.recv(8192).decode('utf-8-sig').strip()
    s.close()
    return json.loads(data)

# 查詢特定組件
comp_id = "your-component-id"
info = cmd('get_component_info', {'id': comp_id})
print(f"輸入: {[i['name'] for i in info['data']['inputs']]}")
print(f"輸出: {[o['name'] for o in info['data']['outputs']]}")
```

### 6.2 連線診斷腳本

位置: `scripts/diagnose_connections.py`

功能: 檢查所有組件的連線狀態，找出未連接的輸入

---

## 7. 版本歷史

| 日期 | 版本 | 變更 |
|------|------|------|
| 2026-01-08 | v1.0 | 初始版本，記錄參數名對照表和常見問題 |
| 2026-01-09 | v1.1 | 新增 Mass Addition、Negative 組件；標記 OBSOLETE 組件 |

---

## 8. 相關文件

| 文件 | 說明 |
|------|------|
| `docs/GH_MCP_DEBUG_REPORT.md` | 完整除錯報告 |
| `docs/GH_MCP_RECOMPILE_GUIDE.md` | 重新編譯指南 |
| `docs/GH_COMPONENT_LESSONS.md` | 組件使用經驗總結 |
| `GH_MCP/GH_MCP/Commands/ConnectionCommandHandler.cs` | 連線命令處理 |
| `GH_MCP/GH_MCP/Models/GrasshopperCommand.cs` | 參數解析邏輯 |
| `grasshopper_mcp/layout/mcp_layout_executor.py` | Python 執行器 |
| `grasshopper_mcp/client_optimized.py` | 優化的 Python Client |

---

**文件位置**: `/Users/laihongyi/Downloads/grasshopper-mcp-workflow/docs/GH_MCP_PARAMETER_REFERENCE.md`
