# GH_MCP API 使用指南

> 經驗證的正確 API 用法 - 對話壓縮後必讀
> 更新日期: 2026-01-23

---

## 重要規範摘要 (每次請求前必讀)

```
【GH_MCP API 規範 - v1.0 驗證】

✅ 正確用法:
- 新增 Slider: add_component(type="Number Slider") → 取得 id
- 設定 Slider: set_slider_properties(id=..., min=..., max=..., value=...)
- 設定順序: 先 min/max，再 value (避免 clamping)
- 常數值: 使用 Number Slider，不要用 Panel

❌ 禁止使用:
- add_component_advanced() — 不存在！
- set_component_value() 設定 Slider — 無效！
- Panel 作為數值輸入源 — 輸出文字無法轉換

✅ 組件 GUID 必須使用 trusted_guids.json:
- Rotate: 19c70daf-600f-4697-ace2-567f6702144d (新版)
- 避免: 5944e8e2... (OBSOLETE)
```

---

## 標準程式碼模板

### 模板 1: 創建 Number Slider

```python
def add_slider(client, nickname, col, row, value, min_val=0, max_val=100):
    """標準 Slider 建立流程 - 經驗證"""
    x, y = client.pos(col, row)

    # Step 1: 創建 slider
    result = client.send_command('add_component',
        type='Number Slider',
        nickname=nickname,
        x=x, y=y
    )
    comp_id = client.extract_id(result)

    # Step 2: 先設範圍 (關鍵！避免 value 被 clamp)
    client.send_command('set_slider_properties',
        id=comp_id,
        min=min_val,
        max=max_val
    )

    # Step 3: 再設數值
    client.send_command('set_slider_properties',
        id=comp_id,
        value=str(value)
    )

    return comp_id
```

### 模板 2: 創建帶 GUID 的組件

```python
def add_component_safe(client, comp_type, nickname, col, row, guid=None):
    """安全創建組件 - 使用 trusted GUID"""
    x, y = client.pos(col, row)

    params = {
        'nickname': nickname,
        'x': x,
        'y': y
    }

    if guid:
        params['guid'] = guid  # 優先使用 GUID
    else:
        params['type'] = comp_type

    result = client.send_command('add_component', **params)
    return client.extract_id(result)

# 使用範例
ROTATE_GUID = "19c70daf-600f-4697-ace2-567f6702144d"
add_component_safe(client, "Rotate", "RotatedSteps", col=10, row=1, guid=ROTATE_GUID)
```

### 模板 3: 連接組件

```python
def connect(client, from_nick, from_param, to_nick, to_param):
    """連接兩個組件"""
    from_info = client.components[from_nick]
    to_info = client.components[to_nick]

    result = client.send_command('connect_components',
        sourceId=from_info.comp_id,
        sourceParam=from_param,  # 使用 NickName
        targetId=to_info.comp_id,
        targetParam=to_param
    )
    return result.get('success', False)
```

---

## API 命令參考

### 文檔操作

| 命令 | 參數 | 說明 |
|------|------|------|
| `clear_document` | 無 | 清空畫布 |
| `get_document_info` | 無 | 獲取文檔資訊 |

### 組件操作

| 命令 | 參數 | 說明 |
|------|------|------|
| `add_component` | `type`, `nickname`, `x`, `y`, `guid` (可選) | 創建組件 |
| `set_slider_properties` | `id`, `min`, `max`, `value` | 設定 Slider |
| `set_component_value` | `id`, `value` | 設定 Panel 值 (不適用 Slider!) |
| `get_component_candidates` | `name`, `maxResults` | 搜索組件 (注意衝突!) |

### 連接操作

| 命令 | 參數 | 說明 |
|------|------|------|
| `connect_components` | `sourceId`, `sourceParam`, `targetId`, `targetParam` | 連接兩組件 |

---

## 常見錯誤與解決方案

### 錯誤 1: Slider 數值顯示 1.000

**原因**: 先設 value 再設 min/max，value 被 clamp 到預設範圍 0-1

**解決**:
```python
# 錯誤順序
set_slider_properties(id=id, value=360)  # 被 clamp 到 1
set_slider_properties(id=id, min=0, max=720)

# 正確順序
set_slider_properties(id=id, min=0, max=720)  # 先設範圍
set_slider_properties(id=id, value=360)  # 再設數值
```

### 錯誤 2: 組件顯示 "OLD" 標籤

**原因**: 使用了 OBSOLETE 版本的 GUID

**解決**: 查詢非 OBSOLETE 的 GUID
```python
# Rotate 錯誤 GUID (OBSOLETE)
# 5944e8e2-9fb9-4f8b-bdd4-8b18f1955360

# Rotate 正確 GUID (新版)
ROTATE_GUID = "19c70daf-600f-4697-ace2-567f6702144d"
```

### 錯誤 3: 連線顯示虛線 (無資料流)

**原因**: Panel 輸出文字，數學組件需要數值

**解決**: 常數改用 Number Slider
```python
# 錯誤: Panel 輸出文字
add_component(type="Panel", ...)

# 正確: Slider 輸出數值
add_slider("Const360", value=360, min_val=0, max_val=720)
```

### 錯誤 4: 組件類型錯誤 (如 Rotate 變成向量版)

**原因**: MCP fuzzy search 返回第三方插件的同名組件

**解決**: 使用 trusted GUID
```python
# 錯誤: 讓 MCP 自動選擇
add_component(type="Rotate", ...)  # 可能返回 VectorComponents/Rotate

# 正確: 指定 GUID
add_component(type="Rotate", guid="19c70daf-600f-4697-ace2-567f6702144d", ...)
```

---

## Trusted GUIDs 快速參考

```python
TRUSTED_GUIDS = {
    "Number Slider": "57da07bd-ecab-415d-9d86-af36d7073abc",
    "Series": "651c4fa5-dff4-4be6-ba31-6dc267d3ab47",
    "Addition": "d65c653b-7a82-4666-bd4b-a71f3bd841a6",
    "Subtraction": "0ff0bb57-8207-48a0-a732-6fd4d4931193",
    "Multiplication": "2ce3f211-76d2-49e5-9f2f-7e75deed1c0e",
    "Division": "b16a2ec0-f873-4ef7-8e0c-a068e7571cb4",
    "Radians": "a337f645-460f-4f2a-892e-5f7f1ebb51a4",
    "Sine": "96061e03-a68a-4d5d-a02e-f215d27f2d83",
    "Cosine": "1ac463e0-156f-4024-988b-b61bc57965f8",
    "Construct Point": "3581f42a-9592-4549-bd6b-1c0fc39d067b",
    "Center Box": "d1296e28-f64c-4c2a-9a9e-49e7839460de",
    "Cylinder": "4edaf2ed-7b3a-42ed-bce0-3119ed106792",
    "Rotate": "19c70daf-600f-4697-ace2-567f6702144d",  # 新版，非 OBSOLETE
    "Interpolate": "c731696a-ea52-4c47-be86-e64bc80bde08",
    "Pipe": "1ee25749-2e2d-4fc6-9209-0ea0515081f9",
}
```

---

## 除錯 SOP

1. **組件名稱錯誤** → 檢查 `get_component_candidates` 返回的 Library，使用 trusted GUID
2. **Slider 數值錯誤** → 確認設置順序：先 min/max，再 value
3. **連線虛線** → 檢查源組件類型，Panel 改用 Slider
4. **OLD 標籤** → 查詢非 OBSOLETE 的 GUID

---

*此文件是 GH_MCP 開發的權威參考。對話壓縮後，Claude 應優先閱讀此文件。*
