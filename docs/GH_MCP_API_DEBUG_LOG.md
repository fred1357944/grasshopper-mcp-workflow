# GH_MCP API 調試記錄

## 日期: 2026-01-09

## 已解決問題

### 1. 參數名稱問題 ✅ 已解決

| API | 錯誤參數 | 正確參數 |
|-----|---------|---------|
| `add_component` | `component_type` | `type` (在 `parameters` 物件內) |
| `set_slider_properties` | `component_id` | `id` |
| `get_component_info` | `component_id` | `id` |
| `connect_components` | `source`, `target` | `sourceId`, `targetId` (2026-01-09 發現) |

**關鍵**: `connect_components` 使用 `sourceId`/`targetId`，不是 `source`/`target`！
```python
# 錯誤
{'source': 'xxx', 'target': 'yyy', 'targetParam': 'X'}

# 正確
{'sourceId': 'xxx', 'targetId': 'yyy', 'targetParam': 'X'}
```

### 2. JSON 結構 ✅ 已解決

**錯誤 (扁平結構)**:
```json
{"type": "add_component", "type": "Number Slider", "x": 100, "y": 200}
```

**正確 (巢狀結構)**:
```json
{
    "type": "add_component",
    "parameters": {
        "type": "Number Slider",
        "x": 100,
        "y": 200
    }
}
```

### 3. 返回值結構 ✅ 已解決

`add_component` 返回的是 `id` 而非 `component_id`：

```python
# 錯誤
result.get('data', {}).get('component_id')  # None!

# 正確
result.get('data', {}).get('id')  # 正確 GUID
```

### 4. UTF-8 BOM 問題 ✅ 已解決 (2026-01-09 新增)

GH_MCP 返回的 JSON 帶有 BOM 標記，需要使用 `utf-8-sig` 解碼：

```python
# 錯誤
response.decode('utf-8')  # Unexpected UTF-8 BOM error

# 正確
response.decode('utf-8-sig')  # 自動處理 BOM
```

### 5. 正確的組件 GUID (2026-01-09 最終驗證)

> **重要**: GUID 可能因 Rhino/GH 版本不同而變化，務必使用 `get_component_candidates` 查詢

```python
COMPONENT_GUIDS = {
    # 幾何 (2026-01-09 重新驗證)
    'Center Box': '8e22f9f3-c5eb-4298-9e5b-7412e3025516',

    # 平面/點 (2026-01-09 重新驗證)
    'XY Plane': 'd5272236-d023-4287-939b-473ba3fac0ce',

    # 變形 (2026-01-09 重新驗證)
    'Move': '3effc02f-5ab5-425e-a3db-0342ff0978ef',
    'Amplitude': '375bba73-b66f-4426-927c-2a5fc6e7dfc6',

    # 向量 (2026-01-09 重新驗證)
    'Unit Z': '62e56988-5991-4c90-8873-b7eefedf9ed8',

    # 數學 (2026-01-09 重新驗證)
    'Division': '42b7fc9d-e233-472a-ad32-8b9241c04e7f',

    # 輸出 (2026-01-09 重新驗證)
    'Merge': '01aeb2f1-3147-420f-942c-fdfbc7936a44',
}
```

**重要**: 使用 `get_component_candidates` 命令查詢最新 GUID：
```python
{'type': 'get_component_candidates', 'parameters': {'name': 'Move', 'limit': 3}}
```

### 6. 連接參數映射 (關鍵知識)

參考 `grasshopper_tools/param_mapping.py`:

| 組件 | targetParam 映射 |
|------|-----------------|
| Center Box | `Plane` → `Base`, X/Y/Z 保持 |
| Move | `Motion` → `T`, `Geometry` → `Geometry` |
| Amplitude | `Vector` → `Vector`, `Amplitude` → `Amplitude` |
| Average | `Number` → `Input` |
| Division | A/B 保持 |
| Addition | A/B 保持 |

| 組件 | sourceParam |
|------|-------------|
| Number Slider | 不需要 (預設 output) |
| Center Box | `Box` |
| XY Plane | `Plane` |
| Unit Z | `Unit vector` |
| Move | `Geometry` |
| Amplitude | `Vector` |
| Addition | `Result` |
| Division | `Result` |
| Merge | `Result` |

### 7. 椅子模型成功建構 (2026-01-09)

使用正確的 GUID 和參數映射，成功建構了包含以下組件的參數化椅子：
- 8 個 Number Sliders (SeatW, SeatD, SeatH, SeatZ, BackW, BackH, BackT, LegS)
- 1 個 XY Plane (基準平面)
- 6 個 Center Box (椅面、椅背、4 個椅腳)
- 1 個 Unit Z + 1 個 Amplitude (移動向量)
- 1 個 Move (移動椅面)
- 1 個 Division (計算)
- 1 個 Merge (合併幾何)

**成功腳本**: `scripts/build_chair_v2.py`

### 10. connect_components 連線修復 ✅ 已解決 (2026-01-09)

**問題**: API 返回 `success: true` 和 `verified: true`，但 Grasshopper 畫布上沒有實際連線

**根本原因**: `AddSource()` 呼叫後沒有正確觸發 Grasshopper 的重算機制

**修復位置**: `GH_MCP/GH_MCP/Commands/ConnectionCommandHandler.cs`

**修復方法**:
```csharp
// 1. 在 AddSource() 前禁用自動重算
doc.Enabled = false;
try
{
    // 2. 呼叫 AddSource
    targetParameter.AddSource(sourceParameter);

    // 3. 通知參數變更
    targetParameter.ExpireSolution(false);
}
finally
{
    // 4. 重新啟用文檔
    doc.Enabled = true;
}

// 5. 強制觸發重新計算
doc.NewSolution(true, GH_SolutionMode.Silent);

// 6. 刷新畫布顯示
var canvas = Grasshopper.Instances.ActiveCanvas;
if (canvas != null)
{
    canvas.Invalidate();
}
```

**驗證**: 使用 `scripts/test_connection.py` 確認連線正常顯示

---

## 待解決問題

### 1. Slider 值設定問題 (Critical)
`set_slider_properties` 的 min/max 參數可能被忽略（JSON 整數轉 double? 失敗）

**參考**: `docs/GH_MCP_DEBUG_REPORT.md` Section 2

**Workaround**: 目前 Slider 只能使用默認值 0-1，需要修改 C# 端的類型轉換

### 2. OBSOLETE 組件問題 (已解決)
使用精確 GUID 而非名稱匹配可避免匹配到 OBSOLETE 版本。

**解法**:
1. 使用 `get_component_candidates` 查詢正確 GUID
2. 選擇不含 "OBSOLETE" 的版本
3. 使用 GUID 創建組件

## 經驗教訓 (2026-01-09)

1. **先查詢再使用**: 組件 GUID 可能因環境不同而變化，始終使用 `get_component_candidates` 查詢
2. **巢狀 JSON**: GH_MCP 使用 `{"type": "cmd", "parameters": {...}}` 結構
3. **BOM 處理**: Python 解碼時使用 `utf-8-sig`
4. **參數映射**: 參考 `grasshopper_tools/param_mapping.py`
5. **Debug 文檔互相學習**: 本文檔與 `docs/GH_MCP_DEBUG_REPORT.md` 互補

### 8. Vision MCP 協議差異 (2026-01-09 新增)

**GH_MCP (port 8080)** 和 **GH_MCP_Vision (port 8081)** 使用不同的 TCP 協議：

| 特性 | GH_MCP (8080) | GH_MCP_Vision (8081) |
|------|---------------|---------------------|
| 命令格式 | JSON | JSON + `\n` 換行符 |
| 連接方式 | 發送後 shutdown | 持續連接 |
| 回應格式 | 直接 JSON | JSON + `\n` 換行符 |

```python
# GH_MCP (8080)
s.sendall(json.dumps(cmd).encode('utf-8'))
s.shutdown(socket.SHUT_WR)  # 必須關閉寫端

# GH_MCP_Vision (8081)
s.sendall((json.dumps(cmd) + '\n').encode('utf-8'))  # 加換行符
# 等待回應以 \n 結尾
```

**Vision MCP 命令**：
- `capture_canvas` - 截取 GH 畫布（macOS 可能返回空白）
- `capture_rhino_view` - 截取 Rhino 3D 視圖 ✅ 正常
- `get_canvas_info` - 獲取畫布信息 ✅ 正常
- `vision_zoom_extents` - 縮放到全部 ✅ 正常
- `vision_zoom_to_components` - 縮放到指定組件

### 9. 已知問題：Slider 值無法設定

由於 `set_slider_properties` 的 min/max 參數被忽略，所有 Slider 使用預設範圍 0-1。
這導致建構的椅子模型非常小（在 Rhino 視圖中只是一個小點）。

**Workaround**: 手動在 Grasshopper 中調整 Slider 範圍

**根本修復**: 需要修改 C# 端的 `ComponentProperties.cs`，參見 `docs/GH_MCP_DEBUG_REPORT.md` Section 2

## 相關文件

| 文件 | 用途 |
|------|------|
| `docs/GH_MCP_DEBUG_REPORT.md` | 完整問題報告與 C# 修復方案 |
| `DEV_LOG.md` | 開發記錄與經驗教訓 |
| `grasshopper_tools/param_mapping.py` | 參數映射知識庫 |
| `scripts/build_chair_v2.py` | 椅子建構腳本 (成功範例) |
| `rhino_view.png` | Vision MCP 截取的 Rhino 視圖 |
