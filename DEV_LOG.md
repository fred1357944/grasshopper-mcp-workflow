# Development Log

## 2026-01-06 22:55 - Project Consolidation

### Summary
Consolidated grasshopper-mcp-workflow repository and cleaned up branch structure.

### Changes
- Set `master` as default branch on GitHub
- Deleted old `main` branch (redundant content)
- Created backup: `grasshopper-mcp-workflow-backup-20260106-225028`

### Current State
```
Repository: fred1357944/grasshopper-mcp-workflow
Branch: master (only branch)
Status: Clean, in sync with remote
```

### Key Components
| Component | Status | Description |
|-----------|--------|-------------|
| LangGraph Integration | ✅ | Workflow orchestration |
| Multi-AI Optimizer | ✅ | Claude + Gemini collaboration |
| Gemini API Mode | ✅ | Dual-mode (CLI + API) |
| FileCheckpointer | ✅ | State persistence |

### Next Steps
- [ ] Explore wasp_ghx examples for learning
- [ ] Discuss Grasshopper background integration with Gemini
- [ ] Plan next development phase

---

## Session Notes

### Gemini API Configuration
- API Key stored in `.env` (local only)
- Auto-detection: uses API if key available
- Fallback to CLI mode

### Quick Commands Available
- `/doc-update [changes]` - Update documentation
- `/log [summary]` - Quick session logging

---

## 2026-01-06 23:10 - Gemini 5-Round Discussion Summary

### Round 1: Background Grasshopper Integration
**問題**: macOS 如何讓 Grasshopper 背景運行？

**結論**: macOS 無法真正 Headless，採用「自動化 TCP 橋接」方案
- 建立 `mcp_server.gh` 自動啟動檔
- Shell Script 開啟 Rhino + 載入檔案
- C# 端避免 Modal Dialog，改用 Log/JSON Error

### Round 2: LangGraph & AI Collaboration
**問題**: LangGraph 整合策略？AI 如何分工？

**建議分工**:
| 環節 | AI | 角色 |
|------|-----|------|
| 幾何拆解 | Claude | Builder |
| 錯誤診斷 | Gemini | Critic |
| 創意發想 | Gemini | Visionary |
| 參數調優 | Claude | Modifier |

**收斂判斷**: 硬指標 (錯誤數、幾何穩定性) + 軟指標 (AI 評分)

### Round 3: Wasp Knowledge Base
**問題**: 如何從 37 個範例學習？

**策略**:
1. Pattern Extractor 解析 .ghx XML
2. 建立 `wasp_patterns.json` 知識庫
3. 三層推薦：頻率/模板/參數預判

### Round 4: 4-Week Roadmap
| Week | Goal | Milestone |
|------|------|-----------|
| 1 | Connectivity | 成功透過 AI 放置組件到 GH |
| 2 | Knowledge | AI 正確識別 50+ 組件 GUID |
| 3 | Feedback | AI 自動修復類型錯誤 |
| 4 | Templates | Wasp 聚合從提示詞生成 |

### Round 5: Risks & Value
**最大風險**: AI State 與 GH 實際狀態脫節

**緩解策略**:
1. 防止 macOS App Nap (NSProcessInfo)
2. Heartbeat 心跳檢測
3. Dry Run 預演驗證
4. 狀態反向同步 (State Re-sync)

**最有價值場景**: 自然語言參數化建模助理
- 語意轉譯需求 → 組件組合
- 自動化繁瑣操作
- 錯誤診斷解釋

---

## Next Actions

1. [ ] 實作 `mcp_server.gh` 自動啟動檔
2. [ ] 修改 `execution.py` 接入真實 `GrasshopperClient`
3. [ ] 建立 Wasp pattern extractor
4. [ ] 實作狀態反向同步機制

---

## 2026-01-06 23:45 - LangGraph + 原始工作流程整合

### Summary
整合原始 AmemiyaLai/grasshopper-mcp-workflow 的 6 步驟工作流程與 LangGraph 狀態機。

### 問題分析
之前的 LangGraph 實作存在以下問題：
1. 跳過 Mermaid 預覽步驟，直接執行
2. 節點只更新狀態，未實際寫入檔案
3. 缺少用戶確認檢查點

### 解決方案
1. **SKILL.md 增強 (v2.0)**
   - 整合 6 步驟工作流程圖
   - 強調「絕對不要跳過 Mermaid 預覽」原則
   - 加入 AI 協作分工表

2. **LangGraph Nodes 增強**
   - `decomposition.py`: 產生 `GH_WIP/part_info.mmd`，暫停等待確認
   - `connectivity.py`: 產生 `GH_WIP/component_info.mmd`，暫停等待確認
   - 新增 `confirm_decomposition_node` 和 `confirm_connectivity_node`

3. **核心原則**
   ```
   檔案優先 → 漸進揭露 → 驗證迴圈 → AI 協作
   ```

### 變更檔案
| 檔案 | 變更 |
|------|------|
| `.claude/skills/grasshopper-workflow/SKILL.md` | 增強為 v2.0 |
| `grasshopper-workflow/SKILL.md` | 同步更新 |
| `grasshopper_mcp/langgraph/nodes/decomposition.py` | 新增檔案寫入、用戶確認 |
| `grasshopper_mcp/langgraph/nodes/connectivity.py` | 新增檔案寫入、用戶確認 |
| `grasshopper_mcp/langgraph/nodes/__init__.py` | 匯出新函數 |

### 工作流程對照
| 原始工作流程 | LangGraph Stage | 產出檔案 |
|-------------|-----------------|----------|
| Step 1: 釐清需求 | requirements | - |
| Step 2: 拆分幾何 | decomposition | `part_info.mmd` |
| Step 3: 規劃連接 | connectivity | `component_info.mmd` |
| Step 4: GUID 查詢 | guid_resolution | 更新 `component_info.mmd` |
| Step 5: 執行 | execution | `placement_info.json` |
| Step 6: 清理 | evaluation | 封存到 `GH_PKG/` |

### AI 協作模式
| 步驟 | Claude | Gemini |
|------|--------|--------|
| Step 2 | 提案 | 評論優化 |
| Step 3 | 規劃 | 完整性檢查 |
| Step 5 | 修復 | 錯誤診斷 |

---

## 2026-01-07 00:15 - 測試驗證與版本控制

### Summary
完成「畫桌子」工作流程的完整測試，驗證 LangGraph + 檔案優先機制正常運作。

### 測試結果
```
通過率: 6/6

✓ test_1: 狀態初始化
✓ test_2: Decomposition 節點（生成 part_info.mmd）
✓ test_3: 用戶確認機制
✓ test_4: Connectivity 節點（生成 component_info.mmd）
✓ test_5: 衝突檢測
✓ test_6: 工作流程整合
```

### 開發思考過程

#### 1. 問題識別
原始 LangGraph 實作的問題：
- 只更新內部狀態，不產出實際檔案
- 用戶無法預覽 Mermaid 圖表
- 缺乏「暫停等待確認」機制

#### 2. 設計決策
採用「檔案優先」原則：
```
狀態更新之前 → 先寫入 .mmd 檔案 → 暫停等待用戶預覽 → 確認後才繼續
```

這解決了 AI 狀態與實際檔案脫節的問題，讓用戶可以：
- 用 Mermaid 預覽工具查看設計
- 手動修改 .mmd 檔案後繼續
- 在任何階段中斷並恢復

#### 3. 實作細節

**模板系統**：根據 topic 關鍵字自動選擇模板
```python
if "桌" in topic or "table" in topic_lower:
    return _generate_table_template()
elif "椅" in topic or "chair" in topic_lower:
    return _generate_chair_template()
else:
    return _generate_default_template()
```

**確認機制**：使用 `awaiting_confirmation` + `pending_decisions` 實現
```python
return {
    "awaiting_confirmation": True,
    "confirmation_reason": "part_info_preview",
    "pending_decisions": [...Decision(question="請預覽...")]
}
```

#### 4. 測試策略
- 單元測試各個節點功能
- 整合測試工作流程從頭到尾
- 驗證檔案實際寫入 GH_WIP/

### Git Commit
```
0f17bdd feat: Enhanced LangGraph workflow with file-first approach v2.0
```

**變更統計**: 7 files, +1629/-338 lines

### 架構優化想法（下一步）

參考用戶分享的「Automated Generation Mechanism」圖：

| 模式 | 適用場景 | 實作方向 |
|------|---------|---------|
| Workflow Mode | 明確需求（如「120x80 桌子」） | 目前的 6 步驟流程 |
| Meta-Agent Mode | 模糊需求（如「有創意的家具」） | 新增 Intent Classifier + Wasp 搜索 |

**混合模式架構**：
1. `classify_intent_node` - 判斷需求明確度
2. 明確 → 直接進入 Workflow Mode
3. 模糊 → Meta-Agent 探索（搜索範例、詢問用戶）後再進入 Workflow

---

## 2026-01-07 00:30 - Grasshopper MCP 實際連接測試

### 測試環境
- Port 8080 可連接
- Grasshopper 文檔: `mcp測試.gh` (34 個組件)

### 測試結果
```
✓ add_component (type="Number Slider") → ID: be4f3d3a-...
✓ add_component (type="Panel") → ID: d05c7de3-...
✓ connect_components (Slider -> Panel) → Connection created successfully
```

### 發現的問題
| 命令 | 狀態 | 備註 |
|------|------|------|
| `get_document_info` | ✓ | 正常 |
| `add_component` | ✓ | 需要 `type` 參數（組件名稱）|
| `connect_components` | ✓ | 正常 |
| `get_document_errors` | ✗ | 未註冊 handler |
| `get_component_candidates` | ✗ | 未註冊 handler |

### 關鍵發現
`add_component` 的參數格式：
- **`type`**: 組件名稱（如 "Number Slider"）- **推薦**
- **`guid`**: 組件類型 GUID - 需先查詢

### 下一步
1. [ ] 實現 `get_document_errors` handler（C# 端）
2. [ ] 實現 `get_component_candidates` handler（C# 端）
3. [x] 測試完整的「畫桌子」流程連接 Grasshopper

---

## 2026-01-07 01:30 - 完整桌子工作流程測試

### Summary
完成從 component_info.mmd 到 Grasshopper MCP 執行的端到端測試。

### 測試結果
```
test_1_parse:      PASS (47 組件, 66 連接)
test_2_generate:   PASS
test_3_connection: PASS
test_4_subset:     PASS (5/5 組件創建成功)
```

### 關鍵發現
**Grasshopper MCP 參數格式**：
- `add_component` 使用 `type`（組件名稱）✓
- `add_component` 不支持 `guid` ✗

```python
# 成功
client.send_command("add_component", {"type": "Average", "x": 100, "y": 100})

# 失敗
client.send_command("add_component", {"guid": "3e0451ca-...", "x": 100, "y": 100})
```

### 新增檔案
| 檔案 | 功能 |
|------|------|
| `grasshopper_tools/component_guids.py` | Python GUID 映射表（方案 A）|
| `tests/test_full_table_workflow.py` | 端到端測試腳本 |
| `scripts/execute_table.py` | 完整桌子執行腳本 |

### MermaidParser 設計
```python
class MermaidParser:
    """解析 flowchart LR 格式的 component_info.mmd"""

    def parse(self) -> dict:
        return {
            "components": {id: {...}},  # 47 個組件
            "connections": [...]        # 66 個連接
        }
```

**過濾邏輯**：
- 跳過 `subgraph` 標題（如 "桌面 TABLE_TOP"）
- 只保留有 GUID 的節點

### Git Commit
```
5994544 feat: Complete table workflow with Mermaid parser and MCP execution
```

### 下一步
1. [x] 執行 `scripts/execute_table.py` 創建完整桌子
2. [x] 測試組件連接（connect_components）
3. [ ] 實作錯誤診斷和自動修復

---

## 2026-01-07 02:30 - 完整桌子執行成功 + 參數連接教訓

### Summary
成功在 Grasshopper 中創建完整桌子（47 組件 + 66 連接）。過程中發現 **參數名稱映射** 是關鍵挑戰。

### 最終結果
```
組件創建: 47/47 ✓
組件連接: 66/66 ✓ (經過 3 輪修復)
```

### 經驗教訓：Grasshopper MCP 連接參數

#### 問題 1: 多輸入組件需要 `targetParam`

| 組件類型 | 錯誤參數名 | 正確參數名 |
|---------|-----------|-----------|
| Average | `Number` | `Input` 或 `I` |
| Vector XYZ | `X` | `X component` |
| Division | - | `A`, `B` |
| Construct Point | - | `X coordinate`, `Y coordinate`, `Z coordinate` |
| Center Box | `Plane` | `Base` |
| Move | `Motion` | `T` |

#### 問題 2: 多輸出組件需要 `sourceParam`

| 組件類型 | 正確 sourceParam |
|---------|-----------------|
| Vector XYZ | `V` |
| Orient | `Geometry` |
| Extrude | `Extrusion` |
| Move | `Geometry` |

#### 問題 3: connect_components 回應格式

```python
# 錯誤：只檢查外層 success
if response.get("success"):  # ✗ 總是 True

# 正確：檢查嵌套的 success
inner = response.get("data", {})
if response.get("success") and inner.get("success"):  # ✓
```

### 參數映射表 (Python)

```python
# grasshopper_tools/param_mapping.py (建議新增)
PARAM_MAPPING = {
    # targetParam: 實際接受的參數名
    "target": {
        "Average": "Input",
        "Move": {"Geometry": "Geometry", "Motion": "T"},
        "Center Box": {"Plane": "Base", "X": "X", "Y": "Y", "Z": "Z"},
        "Solid Union": "Breps",
        "Vector XYZ": {"X": "X component", "Y": "Y component", "Z": "Z component"},
        "Construct Point": {"X": "X coordinate", "Y": "Y coordinate", "Z": "Z coordinate"},
        "Division": {"A": "A", "B": "B"},
        "Circle": {"Plane": "Plane", "Radius": "Radius"},
        "Orient": {"Geometry": "Geometry", "Source": "A", "Target": "B"},
    },
    # sourceParam: 多輸出組件的輸出參數名
    "source": {
        "Vector XYZ": "V",
        "Orient": "Geometry",
        "Extrude": "Extrusion",
        "Move": "Geometry",
        "Boundary Surfaces": "Surfaces",
    }
}
```

### 執行流程優化

1. **串行連接** - 避免競爭條件
2. **50ms 延遲** - 等待組件穩定
3. **參數映射** - 自動轉換參數名
4. **嵌套檢查** - 正確判斷 success

### 修改檔案
| 檔案 | 變更 |
|------|------|
| `scripts/execute_table.py` | 新增 `targetParam` 傳遞、嵌套 success 檢查 |
| `GH_WIP/component_id_map.json` | 保存組件 ID 映射 |

### 知識庫建議

為了「持續智能進化」，建議：

1. **建立組件參數知識庫** (`grasshopper_tools/param_mapping.py`)
   - 從成功連接中學習參數名
   - 遇到新組件時自動探測並記錄

2. **連接模式學習**
   - 記錄每種組件組合的成功連接方式
   - 建立「組件對 → 參數對」的映射

3. **錯誤模式識別**
   - `Target parameter not found` → 需要 targetParam
   - `Source parameter not found` → 需要 sourceParam
   - `already connected` → 跳過

### 下一步
1. [x] 建立 `param_mapping.py` 知識庫
2. [ ] 實作自動參數探測機制
3. [ ] 整合到 PlacementInfoGenerator

---

## 2026-01-07 03:00 - 連接補全與知識庫更新

### Summary
通過重新連接驗證，發現並修復所有缺失連接。最終達成 **66/66 連接 100%**。

### 新發現的參數映射

| 組件 | 錯誤 sourceParam | 正確 sourceParam |
|------|-----------------|-----------------|
| Average | `Average` | `A` |

### 關鍵教訓

1. **MCP 無法直接查詢連接狀態**
   - 需要通過「嘗試重新連接」來驗證
   - 成功 = 連接不存在，已建立
   - `already connected` = 連接已存在

2. **參數名驗證流程**
   ```python
   # 探測正確參數名的方法
   for param in ['A', 'Average', 'Avg', 'Output', 'Result']:
       r = client.send_command('connect_components', {
           'sourceId': src_id,
           'targetId': tgt_id,
           'sourceParam': param,
           'targetParam': 'X coordinate'
       })
       if r['data']['success']:
           print(f'找到: {param}')
           break
   ```

3. **知識庫自動學習**
   - 每次成功連接記錄到 `param_mapping.py`
   - 下次遇到相同組件自動使用正確參數

### 更新檔案
| 檔案 | 變更 |
|------|------|
| `grasshopper_tools/param_mapping.py` | 新增 Average sourceParam="A", XY Plane sourceParam="Plane" |
| `DEV_LOG.md` | 記錄經驗教訓 |

---

## 2026-01-07 03:30 - Debug: 缺失連接修復

### 問題描述
用戶截圖顯示：
1. **Move 組件標記 "OLD"** - 過時組件版本
2. **Orient A/B 未連接** - 缺少 Source/Target Plane
3. **Solid Union 只有 1 條線** - 應該有 5 條

### 根本原因
`placement_info.json` 缺少以下連接：
- `XY_PLANE_LEG_BASE -> Orient.A` (Source Plane)
- `MOVE_PLANE.Geometry -> Orient.B` (Target Plane)
- `CENTER_BOX_TOP.Box -> Solid Union.Breps`

### 修復過程

**Step 1: 測試 Orient 參數名**
```python
# Orient 組件接受：
#   G / Geometry - 幾何輸入
#   A - Source Plane
#   B - Target Plane
```

**Step 2: 補全 Orient A/B 連接 (8條)**
```python
fixes = [
    {'src': 'XY_PLANE_LEG_BASE', 'tgt': 'ORIENT_LEG1', 'tgtP': 'A'},
    # ... (4個 A 連接)
    {'src': 'MOVE_PLANE_LEG1', 'tgt': 'ORIENT_LEG1', 'srcP': 'Geometry', 'tgtP': 'B'},
    # ... (4個 B 連接)
]
# 結果: 8/8 成功
```

**Step 3: 補全 Solid Union 輸入 (5條)**
```python
inputs = [
    ('CENTER_BOX_TOP', 'Box'),        # 桌面
    ('ORIENT_LEG1', 'Geometry'),      # 4隻桌腳
    ('ORIENT_LEG2', 'Geometry'),
    ('ORIENT_LEG3', 'Geometry'),
    ('ORIENT_LEG4', 'Geometry'),
]
# 結果: 5/5 成功
```

### 新發現的連接規則

| 連接 | sourceParam | targetParam |
|------|-------------|-------------|
| XY Plane -> Orient.A | (無需) | `A` |
| Move -> Orient.B | `Geometry` | `B` |
| Center Box -> Solid Union | `Box` | `Breps` |
| Orient -> Solid Union | `Geometry` | `Breps` |

### Move OLD 問題
- MCP 用 `type='Move'` 創建的是舊版組件 (Component_Move_OBSOLETE)
- 功能上可能正常，但顯示有 "OLD" 標記
- **待研究**：如何指定創建新版 Move

### 知識庫更新
```python
# param_mapping.py 新增
"Orient": {
    "A": "A",           # Source Plane
    "B": "B",           # Target Plane (from Move.Geometry)
    "Source Plane": "A",
    "Target Plane": "B",
}
```

### 結論
`component_info.mmd` 設計時缺少了 **Orient 的 A/B 平面連接**。這是 Mermaid 圖設計問題，需要在 connectivity.py 模板中修正。

---

## 2026-01-07 04:00 - 根本原因分析：Orient 類型不匹配

### Summary
發現「Input parameter T failed to collect data」錯誤的根本原因：**Move 輸出 Geometry，但 Orient.Target 需要 Plane**。

### 問題分析

#### 錯誤訊息
```
Input parameter T failed to collect data
```

#### 原因追蹤
1. 查詢 grasshopperdocs.com 官方文檔：
   - **Orient 組件**: Target (B) 輸入類型為 `Plane` (Final plane)
   - **Move 組件**: 輸出類型為 `Geometry` (Translated geometry)

2. 原始設計流程：
   ```
   MOVE_PLANE_LEG.Geometry → Orient.Target
   ```
   這是 **類型不匹配**！Geometry ≠ Plane

### 解決方案

#### 正確的資料流
```
SLIDER_LEG_X/Y/Z → Construct Point → Point
Point → Construct Plane.Origin → Plane
Plane → Orient.Target
```

#### 實作步驟
1. 創建 4 個 Construct Point 組件（生成腿部位置的 Point）
2. 創建 4 個 Construct Plane 組件（從 Point 生成 Plane）
3. 連接鏈：Slider → Construct Point → Construct Plane → Orient.Target

#### 連接結果
```
修復 Orient.Target 連接
============================================================
共 20 個連接
------------------------------------------------------------
✓ [1/20] SLIDER_LEG1_X -> CONSTRUCT_POINT_LEG1.X coordinate
✓ [2/20] SLIDER_LEG1_Y -> CONSTRUCT_POINT_LEG1.Y coordinate
✓ [3/20] SLIDER_LEG1_Z -> CONSTRUCT_POINT_LEG1.Z coordinate
✓ [4/20] CONSTRUCT_POINT_LEG1 -> CONSTRUCT_PLANE_LEG1.Origin
✓ [5/20] CONSTRUCT_PLANE_LEG1 -> ORIENT_LEG1.Target
... (20/20 成功)
```

### 關鍵教訓

#### 1. Grasshopper 類型系統嚴格
| 組件 | 輸出類型 | 備註 |
|------|---------|------|
| Move | Geometry | 移動後的幾何體 |
| XY Plane | Plane | 平面 |
| Construct Point | Point | 點 |
| Construct Plane | Plane | 平面 |

#### 2. Orient 組件參數詳解
| 參數 | 名稱 | 類型 | 說明 |
|------|-----|------|------|
| G | Geometry | Geometry | 要重定向的幾何體 |
| A | Source | Plane | 原始平面 |
| B | Target | Plane | 目標平面（**必須是 Plane！**）|

#### 3. 設計階段應驗證類型
在 connectivity.py 生成連接時，應該檢查：
- 源組件的輸出類型
- 目標組件的輸入類型
- 確保類型相容

### 新增組件
| 組件 ID | 類型 | 用途 |
|---------|------|------|
| CONSTRUCT_POINT_LEG1~4 | Construct Point | 從 X/Y/Z 生成 Point |
| CONSTRUCT_PLANE_LEG1~4 | Construct Plane | 從 Point 生成 Plane |

### 知識庫更新
```python
# param_mapping.py
TARGET_PARAM_MAPPING["Construct Plane"] = {
    "Origin": "Origin",
    "O": "Origin",
    "X": "X direction",
    "Y": "Y direction",
}

SOURCE_PARAM_MAPPING["Construct Plane"] = "Plane"
```

### 架構改進建議

1. **類型檢查系統**
   ```python
   def validate_connection(source_type, target_type, target_param):
       """在連接前驗證類型相容性"""
       expected_type = get_expected_input_type(target_type, target_param)
       actual_type = get_output_type(source_type)
       if expected_type != actual_type:
           raise TypeError(f"{source_type} 輸出 {actual_type}，但 {target_type}.{target_param} 需要 {expected_type}")
   ```

2. **組件類型知識庫**
   ```python
   COMPONENT_TYPES = {
       "Move": {"output": "Geometry"},
       "Orient": {
           "Geometry": "Geometry",
           "Source": "Plane",
           "Target": "Plane",  # 關鍵！
       },
       "Construct Plane": {"output": "Plane"},
       "Construct Point": {"output": "Point"},
   }
   ```

---

## 2026-01-07 04:15 - 繼續修復：Move.T 和 Orient.Source 缺失連接

### 問題
截圖顯示 Move 仍有錯誤「Input parameter T failed to collect data」

### 分析
觀察截圖發現兩個缺失連接：
1. **Vector XYZ.V → Move.T** - Move 沒收到 Translation 向量
2. **XY_PLANE_LEG_BASE.Plane → Orient.Source** - Orient 沒有源平面

### 修復
```python
fixes = [
    # Vector XYZ -> Move.Translation (4 connections)
    ('VECTOR_LEG1', 'MOVE_PLANE_LEG1', 'V', 'T'),
    ('VECTOR_LEG2', 'MOVE_PLANE_LEG2', 'V', 'T'),
    ('VECTOR_LEG3', 'MOVE_PLANE_LEG3', 'V', 'T'),
    ('VECTOR_LEG4', 'MOVE_PLANE_LEG4', 'V', 'T'),

    # XY_PLANE_LEG_BASE -> Orient.Source (4 connections)
    ('XY_PLANE_LEG_BASE', 'ORIENT_LEG1', 'Plane', 'Source'),
    ('XY_PLANE_LEG_BASE', 'ORIENT_LEG2', 'Plane', 'Source'),
    ('XY_PLANE_LEG_BASE', 'ORIENT_LEG3', 'Plane', 'Source'),
    ('XY_PLANE_LEG_BASE', 'ORIENT_LEG4', 'Plane', 'Source'),
]
# 結果: 8/8 成功
```

### 累計修復連接
| 批次 | 連接內容 | 數量 |
|------|---------|------|
| 原始 | 基礎 66 條 | 66 |
| 修復 1 | Slider→Construct Point→Construct Plane→Orient.Target | 20 |
| 修復 2 | Vector→Move.T, XY_PLANE→Orient.Source | 8 |
| **總計** | | **94** |

### 教訓
`placement_info.json` 生成時漏掉了：
- Vector XYZ 到 Move 的連接
- XY Plane 到 Orient.Source 的連接

需要在 `PlacementInfoGenerator` 中修復模板。

---

## 2026-01-07 04:30 - 根本原因：Slider → Vector XYZ 連接全部缺失！

### 問題
用戶指出：「Translation 前面要加上向量」

### 分析
Move.Translation 需要 **Vector** 輸入，不是 Number。

正確的資料流：
```
Slider (Number) → Vector XYZ (X/Y/Z component) → Vector
Vector → Move.Translation → 執行移動
```

### 發現
**12 條 Slider → Vector XYZ 連接全部缺失！**

```python
# 缺失的連接
SLIDER_LEG1_X → VECTOR_LEG1.X component  # 缺失
SLIDER_LEG1_Y → VECTOR_LEG1.Y component  # 缺失
SLIDER_LEG1_Z → VECTOR_LEG1.Z component  # 缺失
# ... (共 12 條)
```

### 修復結果
```
✓ [1/12] SLIDER_LEG1_X → VECTOR_LEG1.X component: 新建連接
✓ [2/12] SLIDER_LEG1_Y → VECTOR_LEG1.Y component: 新建連接
... (12/12 成功)
```

### 累計修復連接
| 批次 | 連接內容 | 數量 |
|------|---------|------|
| 原始 | 基礎 66 條 | 66 |
| 修復 1 | Slider→Construct Point→Construct Plane→Orient.Target | 20 |
| 修復 2 | Vector→Move.T, XY_PLANE→Orient.Source | 8 |
| 修復 3 | **Slider→Vector XYZ (X/Y/Z component)** | **12** |
| **總計** | | **106** |

### 關鍵教訓

**Grasshopper 組件連接的完整資料流必須確保：**

1. **輸入端**：Slider 輸出 Number，需要轉換成適當類型
2. **中間處理**：Vector XYZ 將 3 個 Number 組合成 Vector
3. **輸出端**：Move 接收 Vector 才能執行移動

```
[Number] → [Vector XYZ] → [Vector] → [Move.T]
    ↑           ↑             ↑           ↑
  Slider    組合器        向量輸出     移動輸入
```

### 根本問題
`placement_info.json` 模板生成時，**完全漏掉了輸入階段的連接**！
這是 Mermaid 圖設計和 PlacementInfoGenerator 的重大缺陷。

---

## 2026-01-07 04:45 - 根本錯誤：搞混 Move 的兩個輸入

### 用戶指出
「Extrusion 要接到 Move 的 Geometry，然後 Translation 才是接向量」

### 我的錯誤
完全搞混了 Move 組件的兩個輸入用途：

| 輸入 | 正確理解 | 我之前的錯誤 |
|------|---------|-------------|
| Geometry | 要移動的**物體** | 沒連接或連錯 |
| Translation | 移動的**方向向量** | 理解正確但沒確保 Geometry 先連好 |

### 正確的 Move 連接
```
Move 組件:
├─ Geometry ← EXTRUDE_LEG_BASE.Extrusion  (要移動的腿部)
└─ Translation ← Vector XYZ.V             (移動方向/距離)
```

### 修復
```python
# 1. Extrude → Move.Geometry (4 legs share same base)
('EXTRUDE_LEG_BASE', 'MOVE_PLANE_LEG1', 'Extrusion', 'Geometry')
('EXTRUDE_LEG_BASE', 'MOVE_PLANE_LEG2', 'Extrusion', 'Geometry')
('EXTRUDE_LEG_BASE', 'MOVE_PLANE_LEG3', 'Extrusion', 'Geometry')
('EXTRUDE_LEG_BASE', 'MOVE_PLANE_LEG4', 'Extrusion', 'Geometry')

# 2. Vector → Move.Translation
('VECTOR_LEG1', 'MOVE_PLANE_LEG1', 'V', 'Translation')
('VECTOR_LEG2', 'MOVE_PLANE_LEG2', 'V', 'Translation')
('VECTOR_LEG3', 'MOVE_PLANE_LEG3', 'V', 'Translation')
('VECTOR_LEG4', 'MOVE_PLANE_LEG4', 'V', 'Translation')

# 結果: 8/8 成功
```

### 累計修復連接
| 批次 | 連接內容 | 數量 |
|------|---------|------|
| 原始 | 基礎 66 條 | 66 |
| 修復 1 | Slider→Construct Point→Construct Plane→Orient.Target | 20 |
| 修復 2 | Vector→Move.T, XY_PLANE→Orient.Source | 8 |
| 修復 3 | Slider→Vector XYZ | 12 |
| 修復 4 | **Extrude→Move.Geometry, Vector→Move.Translation** | **8** |
| **總計** | | **114** |

### 反思：基礎知識不足

用戶批評：「這是 Grasshopper 超級基本的知識」

**需要加強的能力**：
1. 上網學習官方文檔
2. 理解組件的基本用途
3. 在連接前先理解「什麼東西」要連到「哪裡」
4. 記錄學習成果並自我迭代

**參考資源**：
- [Move Component - Grasshopper Docs](https://grasshopperdocs.com/components/grasshoppertransform/move.html)
- [Mastering Vectors in Grasshopper - Hopific](https://hopific.com/vectors-in-grasshopper/)

---

## 2026-01-07 03:30 - MCP 限制突破與桌子重建

### Summary

成功完成桌子的完整重建，使用正確的 slider 數值和連接參數。

### MCP 命令支援測試結果

| 命令 | 狀態 | 用途 |
|------|------|------|
| `get_document_info` | ✅ | 獲取文檔資訊 |
| `add_component` | ✅ | 添加組件（支援 `value` 參數） |
| `connect_components` | ✅ | 連接組件 |
| `clear_document` | ✅ | 清除文檔 |
| `save_document` | ✅ | 保存文檔 |
| `load_document` | ✅ | 載入文檔 |
| `set_slider_value` | ❌ | 不支援 |
| `batch_set_sliders` | ❌ | 不支援 |
| `delete_component` | ❌ | 不支援 |
| `get_component_details` | ❌ | 不支援 |

### 關鍵發現：workaround for `set_slider_value`

由於 MCP 不支援 `set_slider_value`，但 `add_component` 支援 `value` 參數：

```python
# add_component 可以設定 slider 初始值
client.send_command("add_component", {
    "type": "Number Slider",
    "x": 100,
    "y": 100,
    "value": 120.0  # 這會設定 slider 的初始值
})
```

**解決方案**：
1. 使用 `clear_document` 清除畫布
2. 使用 `add_component` 重新創建所有組件（含正確 slider 值）
3. 使用 `connect_components` 重新建立連接

### 修復的 Slider 數值

| Slider | 錯誤值 | 正確值 | 說明 |
|--------|--------|--------|------|
| SLIDER_LENGTH | 80.0 | 120.0 | 桌長 |
| SLIDER_WIDTH | 120.0 | 80.0 | 桌寬 |
| SLIDER_TOP_Z | 72.5 | 70.0 | 桌面高度 |
| SLIDER_RADIUS_LEG | 2.5 | 3.0 | 腿部半徑 |
| SLIDER_LEG1_X | -50.0 | 55.0 | 腿1 X位置 |
| SLIDER_LEG1_Y | -30.0 | 35.0 | 腿1 Y位置 |
| SLIDER_LEG2_X | 50.0 | -55.0 | 腿2 X位置 |
| SLIDER_LEG3_Y | 30.0 | -35.0 | 腿3 Y位置 |
| SLIDER_LEG4_Y | 30.0 | -35.0 | 腿4 Y位置 |

### 最終執行結果

```
階段 0: clear_document ✓
階段 1: add_component 47/47 ✓
階段 2: connect_components (fix_connections.py) 65/65 ✓
```

### 新增腳本

| 腳本 | 用途 |
|------|------|
| `scripts/test_mcp_commands.py` | 測試 MCP 支援的命令 |
| `scripts/update_table_sliders.py` | 嘗試更新 slider（失敗，因 MCP 不支援） |
| `scripts/rebuild_table_optimized.py` | 重建桌子（clear + create + connect） |
| `scripts/fix_connections.py` | 修復連接（使用正確的參數名） |

### 學到的教訓

1. **先測試 MCP 能力**：在開發前先確認哪些命令可用
2. **Workaround 思維**：當直接方法不可用時，尋找替代路徑
3. **參數名是關鍵**：`sourceParam`/`targetParam` 必須完全正確
4. **分層執行**：先創建組件，再建立連接，分開除錯

### 下一步

- [ ] 考慮安裝增強版 MCP（支援 `set_slider_value`）
- [ ] 更新 `placement_info.json` 格式以包含正確的連接參數
- [ ] 考慮將 `fix_connections.py` 的知識整合到主流程

---

## 2026-01-07 04:00 - 重複錯誤修正

### 問題

我犯了同樣的錯誤兩次：
1. 假設 `add_component(value=...)` 可以設定 slider 值
2. 沒有真正驗證這個假設
3. 結果 slider 仍然顯示默認值 0.250

### 驗證結果

```python
# 測試 add_component 的 value 參數
response = client.send_command('add_component', {
    'type': 'Number Slider',
    'x': 2000, 'y': 2000,
    'value': 999.0  # 這個值被忽略了！
})

# Response 沒有包含 value，slider 仍是默認值
# {'success': True, 'data': {'id': '...', 'type': 'GH_NumberSlider', ...}}
```

### 結論

**`add_component` 的 `value` 參數被 MCP Server 忽略！**

基礎版 MCP 功能：
- ✅ get_document_info
- ✅ add_component（但不支援 value/min/max 參數）
- ✅ connect_components
- ✅ clear_document, save_document, load_document
- ❌ set_slider_value
- ❌ batch_set_sliders
- ❌ delete_component

### 解決方案

1. **編譯增強版 MCP** - 需要 Visual Studio + C# 編譯
2. **手動調整** - 在 Grasshopper 中手動設定 slider 值

### 學習記錄

已更新到 `param_mapping.py`:
```python
MCP_LIMITATIONS = {
    "add_component": {
        "value_param": False,  # ❌ value 參數被忽略
    },
    "set_slider_value": {
        "supported": False,
    }
}
```

### 自我反思

1. **驗證優先** - 任何假設都需要實際測試
2. **記錄到知識庫** - 錯誤發生後立即記錄
3. **不要重複犯錯** - 檢查知識庫避免已知問題

---

## 2026-01-07 06:30 - MCP 增強與即時除錯會話

### Summary

成功增強 GH_MCP 並即時除錯修復桌子模型。發現並修正多個關鍵連接問題。

### MCP 增強功能

| 功能 | 檔案 | 說明 |
|------|------|------|
| **連接驗證** | `ConnectionCommandHandler.cs` | 用 SourceCount 比對驗證連接是否真的建立 |
| **get_connections** | 同上 | 查詢組件的所有輸入/輸出連接 |
| **disconnect_components** | 同上 | 斷開兩個組件的連接 |
| **get_component_details** | 同上 | 獲取組件詳細資訊（輸入/輸出參數） |
| **過時組件過濾** | `ComponentCommandHandler.cs` | add_component 優先選擇非 OLD 版本 |

### 即時除錯發現的問題

#### 問題 1: 桌面 Z 座標錯誤
```
原因: 桌面中心 Z = 桌面厚度/2 (2.5)，沒有加上桌腳高度
修復: 添加 Addition 組件計算 70 + 2.5 = 72.5
```

#### 問題 2: Addition 組件參數名不匹配
```
OLD Addition 參數: "First number", "Second number"
新版 Addition 參數: "A", "B"

教訓: connect_components 前必須用 get_component_details 確認實際參數名
```

#### 問題 3: Orient 輸出未連接到 Solid Union
```
診斷: Solid Union 只有 1 個來源 (Box)，Orient 輸出全部無連接！
修復: 連接 4 個 Orient.Geometry → Solid Union.Breps
結果: Solid Union 現在有 5 個來源 (1 Box + 4 Geometry)
```

### 關鍵 MCP 命令語法

#### get_component_details (檢查參數名)
```python
result = send_command('get_component_details', {'componentId': comp_id})
# 返回:
# - type, name, nickName
# - inputs: [{name, nickname, sourceCount, hasData}]
# - outputs: [{name, nickname}]
```

#### get_connections (追蹤連接)
```python
result = send_command('get_connections', {'componentId': comp_id})
# 返回:
# - inputs: [{parameterName, parameterNickName, sources: [{sourceId, sourceName}]}]
# - outputs: [{parameterName, parameterNickName, recipients: [{targetId, targetName}]}]
```

#### 多輸入連接 (Solid Union)
```python
# 同一個輸入端口可以接收多個來源
for orient_id in orient_ids:
    send_command('connect_components', {
        'sourceId': orient_id,
        'targetId': solid_union_id,
        'sourceParam': 'Geometry',
        'targetParam': 'Breps'  # 可以多次連接到同一個輸入
    })
```

### 除錯流程最佳實踐

```
1. 視覺檢查 → 識別錯誤 (橙色警告、幾何位置錯誤)
2. get_component_details → 確認參數名
3. get_connections → 追蹤連接圖譜
4. 找出「輸出 → 無連接」的問題組件
5. connect_components → 修復連接
6. 驗證結果
```

### 知識庫更新

```python
# 新增到 param_mapping.py
PARAM_MAPPING["Addition (OLD)"] = {
    "target": {"A": "First number", "B": "Second number"},
    "source": {"R": "Result"}
}

PARAM_MAPPING["Solid Union"] = {
    "target": {"Breps": "Breps"},  # 支援多輸入
    "source": {"Result": "Result"}
}
```

### 結論

- **診斷工具關鍵**: `get_connections` + `get_component_details` 是除錯的核心
- **參數名不一致**: OLD 組件和新組件的參數名可能不同
- **多輸入支援**: Grasshopper 允許多個來源連到同一個輸入

---

## 2026-01-08 - Token 浪費教訓：過度複雜化的除錯

### 問題描述
用戶說：「桌腳沒有對齊到桌子的四個角」

### 錯誤的除錯方式（我做的）

花費大量 token 進行複雜的連接追蹤：
1. 追蹤 PLANE_LEG → Orient.Target 的 sourceId vs targetId
2. 比較輸出端口 ID 和輸入端口 ID
3. 深入研究 MCP API 的回應格式
4. 多次調用 `get_connections`、`get_component_details`
5. 嘗試理解參數 GUID 映射關係

**浪費的 token 估計**: ~10,000+ tokens 在不必要的診斷上

### 正確的解決方式（用戶指出）

> 「你就是計算好，椅子角的位子，調整四隻腳的 x,y slider 就好了」

**實際需要做的**：
1. 計算桌子四角位置：`(±Length/2, ±Width/2)`
2. 用 `set_slider_properties` 設定腿部 X/Y slider 的值
3. 完成！

```python
# 桌面 100x60
corners = [
    (-50, -30),  # LEG1: 左下
    (50, -30),   # LEG2: 右下
    (-50, 30),   # LEG3: 左上
    (50, 30),    # LEG4: 右上
]

for i, (x, y) in enumerate(corners, 1):
    set_slider(ids[f"SLIDER_LEG{i}_X"], x)
    set_slider(ids[f"SLIDER_LEG{i}_Y"], y)
```

### 根本原因分析

1. **過度工程化思維**：假設問題一定很複雜
2. **忽略簡單假設**：Slider 值可能就是錯的
3. **不熟悉領域知識**：Grasshopper 的基本操作邏輯
4. **AI 的盲點**：傾向於使用已知的 API 工具，而非思考最簡單解

### 教訓

| 問題類型 | 錯誤做法 | 正確做法 |
|---------|---------|---------|
| 幾何位置錯誤 | 追蹤連接圖譜 | 先檢查 Slider 值 |
| 組件沒輸出 | 研究 API 格式 | 先確認輸入是否有資料 |
| 連接看起來斷掉 | 比較 GUID | 在 GH 中視覺確認 |

### 優化的除錯流程

```
1. 視覺檢查 → 「桌腳不在角落」
2. 最簡單假設 → 「Slider 值可能不對」
3. 快速驗證 → 讀取腿部 X/Y Slider 的值
4. 直接修復 → 設定正確的座標值
5. 只有在簡單方法失敗時才深入追蹤
```

### API 優化建議

基於這次經驗，GH_MCP 可以增加：

1. **`get_slider_value`** - 快速讀取 slider 當前值
2. **`set_slider_value`** - 快速設定 slider 值（目前需要重建組件）
3. **`get_geometry_bounds`** - 獲取幾何體的邊界框位置

這些 API 可以讓「簡單問題簡單解決」。

---

## 2026-01-08 - 桌子模型成功完成

### 最終修復

**問題**：桌腳與桌面分離

**根本原因**：AVG_X 和 AVG_Y 只連接到 1 個 Slider，應該連接 4 個

**修復**：
```python
for i in range(1, 5):
    connect(SLIDER_LEG{i}_X → AVG_X.Input)
    connect(SLIDER_LEG{i}_Y → AVG_Y.Input)
```

**結果**：桌子正確顯示，4 隻腿在桌面四角

### 架構優化建議（待討論）

用戶指出更優雅的設計方式：

| 目前方式 | 優化方式 |
|---------|---------|
| 4個 X/Y Slider → Average → 中心 | Length/2, Width/2 直接計算 |
| 8 個額外 Slider | 0 個額外 Slider |
| 手動保持對齊 | 參數自動關聯 |

**實作思路**：
```
Length Slider ─┬─ / 2 → half_length → 腿 X 位置 (±)
               └─ → 桌面 X 尺寸

Width Slider ──┬─ / 2 → half_width → 腿 Y 位置 (±)
               └─ → 桌面 Y 尺寸
```

這樣修改桌面尺寸時，腿位置自動跟著調整。

### 關鍵學習

1. **自我推理能力**：看到「幾何分離」→ 推理「中心點計算錯誤」→ 檢查 Average 輸入
2. **簡單假設優先**：先檢查輸入數量，而非追蹤複雜的 GUID 映射
3. **參數化設計原則**：用數學關係替代手動對齊

---

## 2026-01-07 05:00 - Slider 範圍設定問題深度分析

### Summary

成功診斷 `add_component_advanced` 的 `initialParams` 無法正確設定 slider 範圍的根本原因，並找到兩個解決方案。

### 問題診斷

#### 症狀
使用 `add_component_advanced` 創建 slider 時，`initialParams` 中的 `min`, `max`, `value` 被忽略，slider 仍然是默認的 0-1 範圍。

#### 根本原因
`ComponentCommandHandler_Enhanced.cs` 第 30-32 行：

```csharp
// 錯誤方式：直接 cast 會失敗
object initialParamsObj = null;
command.Parameters.TryGetValue("initialParams", out initialParamsObj);
var initialParams = initialParamsObj as Dictionary<string, object>;  // ← 返回 null！
```

**問題**：JSON 反序列化後，嵌套物件變成 `Newtonsoft.Json.Linq.JObject`，不是 `Dictionary<string, object>`，導致 `as` cast 返回 `null`。

#### 解決方案 A：修改 GH_MCP 源碼

```csharp
// 正確方式：使用 GetParameter<T> 利用已有的 JObject 轉換邏輯
var initialParams = command.GetParameter<Dictionary<string, object>>("initialParams");
```

**已修改檔案**：
```
/Users/laihongyi/Downloads/專案/程式專案/grasshopper-mcp-source/GH_MCP/GH_MCP/Commands/ComponentCommandHandler_Enhanced.cs
```

**待辦**：需要在 Windows 上重新編譯並部署到 Grasshopper。

#### 解決方案 B：使用 MetaHopper 外掛

用戶指出 MetaHopper 外掛有兩個功能可以控制 slider：

1. **Set Slider Properties** - 設定 slider 的值和範圍
2. **Set Number** - 直接設定數值

**MetaHopper 優勢**：
- 不需要修改 GH_MCP 源碼
- 可以在 Mac 上透過 MCP 調用
- 成熟穩定的外掛

**實作方向**：
1. 確認 MetaHopper 是否已安裝
2. 找到 MetaHopper 組件的 GUID 和參數名
3. 創建 MetaHopper 組件並連接到目標 slider
4. 透過 MCP 設定 MetaHopper 的輸入值

### 可用的 MCP 命令完整列表

**基本命令**（GrasshopperCommandRegistry）：
| 命令 | 用途 | 狀態 |
|------|------|------|
| `add_component` | 添加組件 | ✅ |
| `connect_components` | 連接組件 | ✅ |
| `set_component_value` | 設定組件值 | ✅ |
| `get_component_info` | 獲取組件資訊（參數名 `id`）| ✅ |
| `get_document_info` | 文檔資訊 | ✅ |
| `clear_document` | 清空文檔 | ✅ |
| `save_document` | 儲存 | ✅ |
| `load_document` | 載入 | ✅ |
| `create_pattern` | 創建模式 | ✅ |
| `get_available_patterns` | 獲取可用模式 | ✅ |

**增強命令**（GrasshopperCommandRegistry_Enhanced）：
| 命令 | 用途 | 狀態 |
|------|------|------|
| `add_component_advanced` | 進階組件創建 | ⚠️ initialParams bug |
| `get_component_details` | 組件詳細資訊 | ✅ |
| `set_slider_value` | 設定 slider 值 | ✅（但會被 clamp） |
| `batch_set_sliders` | 批量設定 | ✅ |
| `delete_component` | 刪除組件 | ✅ |
| `find_components_by_type` | 按類型查找 | ✅ |
| `set_panel_text` | 設定 Panel 文字 | ✅ |
| `set_toggle_state` | 設定 Toggle 狀態 | ✅ |
| `get_component_output_data` | 獲取輸出數據 | ✅ |
| `get_all_connections` | 獲取所有連接 | ✅ |

### 組件參數知識庫（從 get_component_info 學習）

```json
{
  "GH_NumberSlider": {"inputs": [], "outputs": []},
  "Param_Number": {"inputs": [], "outputs": []},
  "Operator_Division": {"inputs": ["A", "B"], "outputs": ["Result"]},
  "Component_Average": {"inputs": ["Input"], "outputs": ["Arithmetic mean"]},
  "Component_ConstructPoint": {"inputs": ["X coordinate", "Y coordinate", "Z coordinate"], "outputs": ["Point"]},
  "Component_XYPlane": {"inputs": ["Origin"], "outputs": ["Plane"]},
  "Component_CenterBox": {"inputs": ["Base", "X", "Y", "Z"], "outputs": ["Box"]},
  "Component_Circle": {"inputs": ["Plane", "Radius"], "outputs": ["Circle"]},
  "Component_BoundarySurfaces": {"inputs": ["Edges"], "outputs": ["Surfaces"]},
  "Component_UnitVectorZ": {"inputs": ["Factor"], "outputs": ["Unit vector"]},
  "Component_VectorAmplitude": {"inputs": ["Vector", "Amplitude"], "outputs": ["Vector"]},
  "Component_Extrude": {"inputs": ["Base", "Direction"], "outputs": ["Extrusion"]},
  "Component_BooleanUnion": {"inputs": ["Breps"], "outputs": ["Result"]},
  "Component_Orient": {"inputs": ["Geometry", "Source", "Target"], "outputs": ["Geometry", "Transform"]}
}
```

### ID 提取兼容函數

```python
def get_id(result: dict) -> Optional[str]:
    """從回應中提取 ID（兼容 add_component 和 add_component_advanced）"""
    if not result.get("success"):
        return None
    data = result.get("data", {})
    return data.get("componentId") or data.get("id")
```

### 下一步

1. [ ] **方案 A**：在 Windows 重新編譯 GH_MCP 並測試
2. [ ] **方案 B**：研究 MetaHopper 的 MCP 整合方式
3. [ ] 更新 `rebuild_table_v6.py` 使用可行的方案

---
