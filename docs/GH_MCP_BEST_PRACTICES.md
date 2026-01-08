# GH_MCP 開發最佳實踐

> 從 GH_MCP C# 代碼深度分析中總結的關鍵知識

## 關鍵要點速查

| # | 知識點 | 重要性 |
|---|--------|--------|
| 1 | **ObjectProxy 是創建組件的唯一正確方式** | Critical |
| 2 | **v2.0+ NickName 優先匹配** | Critical |
| 3 | **連線後須強制重新計算** `doc.NewSolution(true)` | Critical |
| 4 | **所有操作必須在 UI 線程** | Critical |
| 5 | 參數類型轉換需要特殊處理 (Nullable<T>) | High |
| 6 | 連線後須驗證成功（不要盲目相信 API） | High |
| 7 | 創建組件前檢查 Attributes 不為 null | High |

---

## 1. 組件匹配邏輯

### 正確的創建方式
```csharp
// 使用 ObjectProxy（推薦）
var proxy = Grasshopper.Instances.ComponentServer.ObjectProxies
    .FirstOrDefault(p => p.Desc.Name.Equals(type, StringComparison.OrdinalIgnoreCase));
component = proxy.CreateInstance();
```

### Python 端最佳實踐
```python
def add_component(name, x, y):
    # 步驟 1: 查詢候選組件
    candidates = send_cmd('get_component_candidates', name=name)

    # 步驟 2: 優先選擇內置組件、避免 OBSOLETE
    best = next((c for c in candidates
                 if c['library'] in ['MathComponents', 'SurfaceComponents', ...]
                 and not c['obsolete']), None)

    # 步驟 3: 使用 GUID 創建
    return send_cmd('add_component', guid=best['guid'], x=x, y=y)
```

---

## 2. 參數映射（Name vs NickName）

### 匹配優先級（v2.0+）
1. **NickName 精確匹配**（如 `R`, `G`, `X`）
2. **Name 精確匹配**（如 `Result`, `Geometry`）
3. **模糊匹配**（包含搜索）

### 常用參數映射
| 組件 | Input Name | Input NickName | Output Name | Output NickName |
|------|------------|----------------|-------------|-----------------|
| Center Box | Base, X, Y, Z | B, X, Y, Z | Box | B |
| Move | Geometry, Motion | G, T | Geometry, Transform | G, X |
| Division | A, B | A, B | Result | R |
| Merge Multiple | Stream 0, Stream 1 | 0, 1 | Stream | S |
| Unit Z | Factor | F | Vector | V |
| Amplitude | Vector, Amplitude | V, A | Vector | V |

---

## 3. 連線機制

### 正確的連線流程
```csharp
// 1. 禁用自動重算
doc.Enabled = false;
try {
    // 2. 添加連線
    targetParameter.AddSource(sourceParameter);

    // 3. 通知參數變更
    targetParameter.ExpireSolution(false);
} finally {
    // 4. 重新啟用
    doc.Enabled = true;
}

// 5. 強制重新計算（關鍵！）
doc.NewSolution(true, GH_SolutionMode.Silent);

// 6. 刷新畫布
canvas.Invalidate();
```

### 連線驗證
```csharp
int countBefore = targetParameter.SourceCount;
targetParameter.AddSource(sourceParameter);
int countAfter = targetParameter.SourceCount;
bool success = (countAfter > countBefore);
```

---

## 4. 常見陷阱

### 陷阱 1: GUID 類型混淆
```csharp
// 錯誤：實例 GUID（每次都不同）
Guid instanceGuid = component.InstanceGuid;

// 正確：類型 GUID（固定的）
Guid typeGuid = proxy.Desc.InstanceGuid;
```

### 陷阱 2: 第三方插件組件錯配
問題：`Division` 匹配到 Weaverbird 的 `Loop Subdivision`

解決方案：
- 使用 `get_component_candidates` 獲取完整列表
- 檢查 `library` 字段，優先選擇內置組件
- 檢查 `obsolete` 字段，避免過期組件

### 陷阱 3: 參數類型轉換
```csharp
// 錯誤
double? minValue = command.GetParameter<double?>("min");  // JSON int → null

// 正確
object minObj = command.GetParameter<object>("min");
double? minValue = (minObj is int i) ? (double)i :
                   (minObj is double d) ? d : null;
```

### 陷阱 4: 未檢查 Attributes
```csharp
// 錯誤
component.Attributes.Pivot = new PointF(x, y);  // NullReferenceException

// 正確
if (component.Attributes == null)
    component.CreateAttributes();
component.Attributes.Pivot = new PointF(x, y);
```

---

## 5. 推薦工作流程

```
1. 查詢組件 (get_component_candidates)
   ↓
2. 選擇最佳候選（內置、非過期）
   ↓
3. 使用 GUID 創建組件 (add_component)
   ↓
4. 查詢參數信息 (get_component_info)
   ↓
5. 使用正確參數名連線 (connect_components)
   ↓
6. 驗證連線結果
```

---

## 6. 組件知識庫

已建立 `GH_WIP/component_knowledge.json`，包含 202 個常用組件的：
- GUID
- 輸入/輸出參數名和 NickName
- 所屬庫和類別

查詢示例：
```bash
jq '.["Division"]' GH_WIP/component_knowledge.json
```

---

## 相關文件

| 文件 | 用途 |
|------|------|
| `GH_MCP/Commands/ComponentCommandHandler.cs` | 組件操作邏輯 |
| `GH_MCP/Commands/ConnectionCommandHandler.cs` | 連線系統核心 |
| `GH_MCP/Utils/FuzzyMatcher.cs` | 名稱匹配演算法 |
| `GH_WIP/component_knowledge.json` | 組件知識庫 |
| `grasshopper_tools/param_mapping.py` | Python 端參數映射 |

---

*基於 GH_MCP 代碼分析 | 2026-01-09*
