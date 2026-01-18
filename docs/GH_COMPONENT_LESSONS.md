# Grasshopper 組件使用經驗總結

本文檔記錄在 GH_MCP 開發過程中遇到的組件問題和解決方案。

## 1. 避免 OBSOLETE (OLD) 組件

### 問題描述
Grasshopper 有些組件已標記為 OBSOLETE，在 Canvas 上會顯示 "OLD" 徽章。這些組件雖然仍可使用，但不建議在新專案中使用。

### 常見 OBSOLETE 組件與替代方案

| OBSOLETE 組件 | 替代組件 | 說明 |
|--------------|---------|------|
| `Addition` | `Mass Addition` | 數值加法，支援多輸入 |
| `Multiplication` (用於負數) | `Negative` | 取負值更簡潔 |

### 如何檢查組件是否 OBSOLETE

```python
result = client.send_command('get_component_candidates', name='Addition')
for c in result['data']['candidates']:
    print(f"{c['name']}: obsolete={c['obsolete']}")
```

## 2. 組件參數名稱對照表

### Mass Addition
- **輸入**: `I` (Input) - 可連接多個數值
- **輸出**: `R` (Result), `Pr` (Partial Results)

```python
# 正確用法
("Value1", "N", "MassAdd", "I"),
("Value2", "N", "MassAdd", "I"),  # 多個輸入連到同一個 I
("MassAdd", "R", "Output", "X"),
```

### Negative
- **輸入**: `x` - 要取負的數值
- **輸出**: `y` - 負值結果

```python
# 正確用法
("HalfWidth", "Result", "NegHalfW", "x"),
("NegHalfW", "y", "Point", "X"),
```

### Division
- **輸入**: `A` (被除數), `B` (除數)
- **輸出**: `Result`

```python
("Width", "N", "HalfW", "A"),
("Const2", "N", "HalfW", "B"),
("HalfW", "Result", "Next", "X"),
```

### Center Box
- **輸入**: `Base` (平面), `X`, `Y`, `Z` (半尺寸)
- **輸出**: `B` (Box)

```python
# 注意：是 Base 不是 P
("Plane", "P", "Box", "Base"),  # 正確
("Plane", "P", "Box", "P"),     # 錯誤！
```

### Construct Point
- **輸入**: `X`, `Y`, `Z`
- **輸出**: `Pt`

### XY Plane
- **輸入**: `O` (Origin)
- **輸出**: `P` (Plane)

## 3. 排錯經驗

### 問題 1: Box.P vs Box.Base
**症狀**: 連接 `Plane → Box.P` 失敗
**原因**: Center Box 的平面輸入參數叫 `Base`，不是 `P`
**解決**: 改為 `("Plane", "P", "Box", "Base")`

### 問題 2: OLD Addition 組件
**症狀**: Canvas 上組件顯示 "OLD" 徽章
**原因**: 使用了 OBSOLETE 的 Addition 組件
**解決**: 改用 `Mass Addition`，參數從 `A, B, Result` 改為 `I, R`

### 問題 3: Multiplication 取負值
**症狀**: 想用 `value * -1` 取負值，但 Multiplication 是 OLD
**原因**: 有專用的 Negative 組件更簡潔
**解決**: 使用 `Negative` 組件，輸入 `x`，輸出 `y`

### 問題 4: 連接失敗但無明確錯誤
**症狀**: 連接返回錯誤但訊息被截斷
**原因**: 通常是參數名稱不對
**解決**: 使用 `get_component_info` 查詢實際組件的參數

```python
result = client.send_command('get_component_info', id=component_guid)
print(result['data']['inputs'])   # 查看輸入參數
print(result['data']['outputs'])  # 查看輸出參數
```

## 4. 最佳實踐

### 4.1 查詢組件前先確認
在使用組件前，先查詢其參數：

```python
# 查詢組件候選
result = client.send_command('get_component_candidates', name='Mass Addition')
# 找出 obsolete=False 的版本
for c in result['data']['candidates']:
    if not c['obsolete']:
        print(f"Inputs: {c['inputs']}")
        print(f"Outputs: {c['outputs']}")
```

### 4.2 使用 NickName 連接
Grasshopper 參數有 Name (全名) 和 NickName (短名)：
- 連接時使用 **NickName**（如 `I`, `R`, `x`, `y`）
- 顯示時可能看到 **Name**（如 `Input`, `Result`）

### 4.3 負值處理
不要用 Multiplication + (-1)，直接用 Negative：

```python
# 不推薦
("Value", "N", "Mult", "A"),
("NegOne", "N", "Mult", "B"),  # NegOne = -1

# 推薦
("Value", "N", "Neg", "x"),
("Neg", "y", "Output", "X"),
```

### 4.4 多值相加
Mass Addition 的 `I` 輸入可以連接多個來源：

```python
# 計算 A + B + C
("A", "N", "Sum", "I"),
("B", "N", "Sum", "I"),
("C", "N", "Sum", "I"),
("Sum", "R", "Result", "X"),
```

## 5. 常用組件 GUID

非 OBSOLETE 版本的組件 GUID：

| 組件 | GUID | Category |
|-----|------|----------|
| Mass Addition | `e0946c31-2227-4389-9b97-e6f1ed3fdfd8` | Maths > Operators |
| Negative | (標準組件) | Maths > Operators |
| Division | (標準組件) | Maths > Operators |
| Center Box | (標準組件) | Surface > Primitive |

## 6. 成功案例

### 參數化沙發 (build_sofa_v2.py)
- 48 個組件
- 87 個連接
- 結構：坐墊 + 靠背 + 2 扶手 + 4 腳
- 使用組件：
  - `Division` - 計算半值
  - `Negative` - 計算負座標
  - `Mass Addition` - 計算 Z 座標 (多值相加)
  - `Construct Point` - 建構位置點
  - `XY Plane` - 建構平面
  - `Center Box` - 建構方塊
  - `Solid Union` - 合併所有方塊

### 參數化翹翹板 (build_seesaw.py)
- 36 個組件
- 52 個連接
- 結構：板身 + 支點 + 2 握把
- 使用組件：
  - `Division` - 計算半值 (7 個)
  - `Negative` - 計算負座標 (1 個)
  - `Mass Addition` - 計算 Z 座標 (3 個)
  - `Subtraction` - 計算握把偏移 (2 個)
  - `Construct Point` - 建構位置點 (4 個)
  - `XY Plane` - 建構平面 (4 個)
  - `Center Box` - 板身和支點 (2 個)
  - `Cylinder` - 握把 (2 個)
  - `Solid Union` - 合併所有幾何
- 參數：
  - BoardLen=300, BoardW=30, BoardT=5 (板身)
  - PivotH=50, PivotW=40, PivotD=35 (支點)
  - HandleR=2, HandleH=25 (握把)

## 7. 踩坑記錄：TCP 連接問題

### 問題描述
在 Python 客戶端為每個 `add_component` 調用額外查詢（`_find_best_component_guid`）時，會導致 TCP 連接混亂，造成組件創建錯誤。

### 症狀
- Division 組件變成 "Smooth Naked Edges"
- Number Slider 變成 "Input"
- 大量連接失敗

### 原因
每個組件創建前都做額外的 `search_components` 或 `get_component_candidates` 查詢，增加了 TCP 請求數量，可能導致：
1. 請求/響應錯位
2. 連接超時
3. 緩衝區混亂

### 解決方案
1. **避免在組件創建時做額外查詢** - 讓 GH_MCP C# 端處理 OBSOLETE 過濾
2. **批量預查詢** - 如需要查詢，在開始前一次性查詢所有需要的組件 GUID
3. **使用快取** - 使用 `export_component_library` 導出組件庫，本地快取

### 最佳實踐
```python
# 不推薦：每次創建都查詢
def add_component(self, comp_type, ...):
    guid = self._find_best_component_guid(comp_type)  # 額外 TCP 請求
    self.send_command('add_component', guid=guid, ...)

# 推薦：直接用 type，讓 GH_MCP 處理
def add_component(self, comp_type, ...):
    self.send_command('add_component', type=comp_type, ...)  # 單一請求
```

---

## 8. 自動化 OBSOLETE 過濾機制

### 7.1 GH_MCP C# 端優化 (v2.2+)

`add_component` 命令現在會自動排除 OBSOLETE 組件：

```csharp
// ComponentCommandHandler.cs
// 使用 type 參數時，自動過濾 OBSOLETE
var proxy = candidates.FirstOrDefault(p =>
{
    var typeName = p.Type?.Name ?? "";
    return typeName.IndexOf("OBSOLETE", StringComparison.OrdinalIgnoreCase) < 0 &&
           typeName.IndexOf("Deprecated", StringComparison.OrdinalIgnoreCase) < 0;
});
```

### 7.2 Python 客戶端優化 (client_optimized.py)

`add_component` 方法會先查詢最佳 GUID：

```python
def _find_best_component_guid(self, comp_type: str) -> Optional[str]:
    """
    優先順序：
    1. 嘗試 search_components (GH_MCP_Vision)
    2. 使用 get_component_candidates + 過濾 obsolete
    """
    # 先嘗試 search_components
    result = self.send_command('search_components', name=comp_type, maxResults=1)
    if result.get('success'):
        rec = result.get('data', {}).get('recommended')
        if rec and not rec.get('isObsolete'):
            return rec.get('guid')

    # 退而求其次：get_component_candidates + 過濾
    result = self.send_command('get_component_candidates', name=comp_type)
    if result.get('success'):
        for c in result.get('data', {}).get('candidates', []):
            if not c.get('obsolete', False):
                return c.get('guid')
    return None
```

### 7.3 GH_MCP_Vision 智能搜索 (需重啟 Rhino)

`search_components` 命令提供智能匹配：

```python
# 使用方式
result = client.send_command('search_components', name='Division', maxResults=5)
# 返回: {recommended: {guid, name, isBuiltIn, isObsolete, score}, candidates: [...]}

# 匹配分數計算
# NickName 精確匹配: +100 分
# Name 精確匹配:     +80 分
# 部分匹配:          +20 分
# 內建庫:            +50 分
# 過期組件:          -100 分
```

### 7.4 組件庫導出 (一次性快取)

```python
# 導出完整組件庫到 JSON 文件
result = client.send_command('export_component_library',
                             outputPath='/path/to/component_library.json')
```

導出內容：
- GUID (Type GUID)
- Name / NickName
- Category / Subcategory
- Library (來源插件)
- Input/Output 參數 (Name + NickName)
- IsObsolete 標記

---

## 9. 新組件參數對照

### Cylinder (圓柱體)
- **輸入**: `B` (Base plane), `R` (Radius), `L` (Length)
- **輸出**: `C` (Cylinder brep)

```python
# 正確用法
("PlnHandle", "P", "CylHandle", "B"),  # 底部平面
("HandleR", "N", "CylHandle", "R"),    # 半徑
("HandleH", "N", "CylHandle", "L"),    # 高度/長度
("CylHandle", "C", "Union", "B"),      # 輸出為 C
```

### Subtraction (減法)
- **輸入**: `A`, `B`
- **輸出**: `Result` (= A - B)

```python
# 正確用法
("HalfLen", "Result", "Offset", "A"),
("Margin", "N", "Offset", "B"),
# Result = HalfLen - Margin
```

## 10. 批次連接時序問題

### 問題描述
使用 `connect_batch()` 批次連接時，某些連接可能失敗，但單獨重新連接時成功。

### 症狀
- `Mass Addition.R → Construct Point.Z` 連接失敗
- 錯誤訊息被截斷，難以診斷
- 手動重試連接成功

### 原因
1. 組件剛創建時，輸出參數可能尚未完全初始化
2. 批次處理過快，組件狀態未同步
3. TCP 請求間隔太短

### 解決方案
1. **增加延遲**: 在組件創建後加入 `time.sleep(0.1)`
2. **重試機制**: 對失敗連接進行二次嘗試
3. **手動修復**: 使用 ID map 手動連接失敗項目

```python
# 失敗連接重試
for conn in failed_connections:
    src_id = id_map[conn[0]]
    tgt_id = id_map[conn[2]]
    result = client.send_command('connect_components',
        sourceId=src_id, sourceParam=conn[1],
        targetId=tgt_id, targetParam=conn[3])
```

---

*最後更新: 2026-01-09*
*基於 GH_MCP v2.2 開發經驗*
