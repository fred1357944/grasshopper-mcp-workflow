# 工業風書架開發日誌

> Industrial Bookshelf Development Log
> 2026-01-23

## 專案概述

- **目標**: 80×180×30cm 工業風書架，5層，金屬支架
- **組件數**: 37 個
- **連接數**: 55 條
- **狀態**: ✅ 部署成功

---

## 關鍵問題與解決

### 問題 1: Data conversion failed from Point to Line

**症狀**: Line 組件顯示紅色錯誤 "Data conversion failed from Point to Line"

**根本原因**: Grasshopper 有多個同名的 "Line" 組件：
- `Line (Curve/Primitive)` - 兩點線段，輸入 Start Point + End Point
- `Line (Params/Input)` - 參數容器，用於儲存線段

GH_MCP 自動搜索時選到了 Params 版本，而非 Curve 版本。

**解決方案**:
1. 建立 GUID Registry，用 category 區分同名組件
2. 在 `placement_info.json` 中明確指定 GUID
3. 修復 `deploy_bookshelf.py` 使其實際使用 GUID

```python
# 正確的 Line 組件 GUID
"Line (Curve)": "31957fba-b08b-45f9-9ec0-5f9e52d3236b"
```

### 問題 2: XY Plane GUID 無效

**症狀**: XY Plane 組件無法創建

**解決方案**: 運行時查詢正確 GUID
```python
"XY Plane": "5df6a8c1-de5e-4841-8089-41a95c741c5a"
```

### 問題 3: 參數名縮寫不匹配

**症狀**: 連接失敗，參數找不到

**原因**: 使用縮寫 (R, Pt, A) 但組件期望全名

**解決方案**: 自動修正系統
```python
PARAM_NAMES = {
    "Division": {"outputs": ["Result"]},   # 不是 R
    "Construct Point": {"outputs": ["Point"]},  # 不是 Pt
    "Line": {"inputs": ["Start Point", "End Point"]},  # 不是 A, B
}
```

---

## 系統架構改進

### 三層防護機制 (Smart Resolver)

```
┌─────────────────────────────────────────┐
│  Layer 1: Registry 查詢                  │
│  - 使用已驗證的可信 GUID                  │
│  - 信心度: 1.0                           │
└────────────────┬────────────────────────┘
                 ↓ 找不到
┌─────────────────────────────────────────┐
│  Layer 2: AI 推斷                        │
│  - 根據上下文自動選擇                     │
│  - context.purpose: 用途描述             │
│  - context.target_connection: 連接目標   │
│  - 信心度: 0.7-0.9                       │
└────────────────┬────────────────────────┘
                 ↓ 不確定
┌─────────────────────────────────────────┐
│  Layer 3: 人工確認                       │
│  - 顯示候選列表                          │
│  - 用戶選擇正確版本                       │
│  - 信心度: 1.0                           │
│  - 記住選擇供下次使用                     │
└─────────────────────────────────────────┘
```

### 新增檔案

1. **`grasshopper_mcp/guid_registry.py`**
   - `VERIFIED_GUIDS`: 可信 GUID 列表 (name, category) → GUID
   - `PARAM_NAMES`: 每個 GUID 的參數名
   - `validate_placement_info()`: 預部署驗證
   - `auto_fix_placement_info()`: 自動修正

2. **`grasshopper_mcp/smart_resolver.py`**
   - `SmartResolver`: 三層防護解析器
   - `resolve()`: 智能解析組件 GUID
   - `resolve_placement_info()`: 批量解析配置

3. **`grasshopper_mcp/auto_debugger.py`**
   - `GHAutoDebugger`: 自動排錯系統
   - `scan_canvas()`: 掃描畫布錯誤
   - `suggest_placement_fixes()`: 預防性診斷

---

## 教訓與最佳實踐

### 1. 永遠使用 Category 區分同名組件

```python
# ❌ 錯誤：只用名稱
registry.get("Line")  # 可能得到錯誤版本

# ✅ 正確：加上 category
registry.get("Line", category="Curve")  # 確保是幾何版本
```

### 2. 參數名優先使用全名

```python
# ❌ 縮寫可能不一致
"fromParam": "R"

# ✅ 全名更可靠
"fromParam": "Result"
```

### 3. 部署前驗證

```python
from grasshopper_mcp.guid_registry import GUIDRegistry

registry = GUIDRegistry()
issues = registry.validate_placement_info(config)
if issues:
    config = registry.auto_fix_placement_info(config)
```

### 4. 錯誤分類

| 錯誤類型 | 描述 | 解決方式 |
|---------|------|---------|
| GUID_MISMATCH | 組件版本選錯 | 使用 Registry 查詢正確 GUID |
| PARAM_NAME | 參數名不匹配 | 使用全名或查詢 PARAM_NAMES |
| DATA_TYPE | 資料類型不匹配 | 檢查連接邏輯 |
| MISSING_INPUT | 缺少必要輸入 | 補充連接 |

---

## 驗證清單

- [x] Line 組件使用 Curve 版本 GUID
- [x] XY Plane 使用正確 GUID
- [x] 所有參數名使用全名
- [x] deploy_bookshelf.py 實際傳遞 GUID
- [x] 部署成功，無紅色錯誤

---

## 後續改進

1. **整合 Smart Resolver 到主工作流程**
   - 自動解析 placement_info.json 中缺少 GUID 的組件

2. **擴展 Registry**
   - 添加更多常用組件的驗證 GUID
   - 建立 GUID 查詢 API

3. **UI 整合**
   - 在部署前顯示驗證結果
   - 人工確認介面優化

---

*記錄於 2026-01-23*
