# GH_MCP Workflow 專案指南

---

## ⚠️ Phase 5 執行必備 (CRITICAL - 每次執行前必讀)

**執行部署時，務必遵守以下規則：**

```bash
# ✅ 正確命令（清空畫布 + Smart Layout）
python -m grasshopper_tools.cli execute-placement GH_WIP/placement_info.json --clear-first

# ❌ 錯誤（組件會重疊、與舊組件混在一起）
python -m grasshopper_tools.cli execute-placement GH_WIP/placement_info.json --no-smart-layout
```

### Python API 調用

```python
from grasshopper_tools import PlacementExecutor

executor = PlacementExecutor()
result = executor.execute_placement_info(
    json_path="GH_WIP/placement_info.json",
    clear_first=True,       # ← 必須：清空畫布
    use_smart_layout=True   # ← 必須：避免重疊（預設值）
)
```

### 常見錯誤

| 問題 | 原因 | 解決方案 |
|------|------|----------|
| 組件重疊在一起 | 未使用 Smart Layout | `use_smart_layout=True` |
| 舊組件與新組件混在一起 | 未清空畫布 | `clear_first=True` |
| 連接失敗 | 參數名衝突 | 使用 `paramIndex` 而非 `paramName` |

---

## 知識查詢優先原則 (CRITICAL - 執行任何 GH_MCP 操作前必讀)

**核心理念**：不讓 Claude 記住 GUID/連接方式，讓系統記住並在需要時快速提供

### 知識庫配置文件

| 文件 | 用途 | 查詢方式 |
|------|------|----------|
| `config/trusted_guids.json` | 70+ 組件 GUID | `kb.get_component_guid("Face Normals")` |
| `config/connection_patterns.json` | 17 種連接模式 | `kb.search_patterns("wasp")` |
| `config/mcp_commands.json` | 可用/不可用命令 | `kb.is_command_available("clear_canvas")` |

### 快速查詢 Python API

```python
from grasshopper_mcp.knowledge_base import GHKnowledgeBase, lookup, get_guid, is_cmd_ok
kb = GHKnowledgeBase()

# 查組件 GUID 和參數
kb.get_component_guid("Face Normals")
# → {"guid": "f4370b82...", "inputs": ["M"], "outputs": ["C", "N"]}

# 快速獲取 GUID
get_guid("Rotate")
# → "19c70daf-600f-4697-ace2-567f6702144d"

# 查連接模式
kb.get_pattern("WASP_Stochastic")
# → {"description": "WASP 隨機聚集", "wiring": [...], "keywords": [...]}

# 搜索模式
kb.search_patterns("wasp")
# → [{"name": "WASP_Stochastic", ...}, {"name": "WASP_Mesh_Part", ...}]

# 檢查命令可用性
is_cmd_ok("clear_canvas")  # → False
kb.get_workaround("clear_canvas")  # → "使用 clear_document 命令"

# 快速查詢（自動判斷類型）
lookup("Face Normals")
# → {"type": "component", "result": {...}}
```

### LangGraph 知識查詢節點

```python
from grasshopper_mcp.langgraph.nodes import (
    knowledge_query_node,      # 查詢組件和模式
    validate_commands_node,    # 驗證 MCP 命令
    resolve_guids_node,        # 解析可信 GUID
    inject_knowledge_node,     # 一次性注入所有知識
)
```

---

## ⚠️ 對話壓縮後必讀 (CRITICAL)

**在開始任何 GH_MCP 開發工作前，請先閱讀以下文件：**

1. **`docs/GH_MCP_API_GUIDE.md`** - API 使用規範與標準模板
2. **`docs/GH_MCP_DEBUG_KNOWLEDGE.md`** - 除錯知識庫
3. **`config/trusted_guids.json`** - 可信組件 GUID (v3.0: 70+ 組件)

### 快速規範摘要

```
【GH_MCP API 規範 - v1.0 驗證】

✅ 正確用法:
- 清空畫布: clear_document (不是 clear_canvas!)
- 新增 Slider: add_component(type="Number Slider") → 取得 id
- 設定 Slider: set_slider_properties(id=..., min=..., max=..., value=...)
- 設定順序: 先 min/max，再 value (避免 clamping)
- 常數值: 使用 Number Slider，不要用 Panel
- 組件創建: 使用 trusted GUID 避免插件衝突
- 連接時用索引: sourceParamIndex/targetParamIndex (避免 FuzzyMatcher 錯誤)

❌ 禁止使用:
- clear_canvas — 不存在！用 clear_document
- add_component_advanced() — 不存在！
- set_component_value() 設定 Slider — 無效！
- Panel 作為數值輸入源 — 輸出文字無法轉換
- 5944e8e2... 的 Rotate GUID — 是 OBSOLETE！
- 連接時用 "r" 參數名 — 會被映射成 Radius！用索引

✅ 關鍵 GUIDs (非 OBSOLETE):
- Rotate: 19c70daf-600f-4697-ace2-567f6702144d
- Pipe: 1ee25749-2e2d-4fc6-9209-0ea0515081f9
- Series: 651c4fa5-dff4-4be6-ba31-6dc267d3ab47
```

---

## GH_MCP C# 開發關鍵提醒

### 部署注意事項 (CRITICAL)

**Grasshopper 插件正確目錄** (Rhino 8 Mac):

```bash
# 正確路徑 (有 GUID 後綴！)
~/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper (b45a29b1-4343-4035-989e-044e8580d9cf)/Libraries/

# 錯誤路徑 (不要用！)
# ~/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper/Libraries/

# 部署命令
cp GH_MCP_Vision.gha "~/Library/Application Support/McNeel/Rhinoceros/8.0/Plug-ins/Grasshopper (b45a29b1-4343-4035-989e-044e8580d9cf)/Libraries/"
```

### 編譯命令

```bash
cd GH_MCP && dotnet build -c Release --framework net7.0
```

### 跨平台 API 差異

macOS (.NET 7.0) 不支援以下 Windows API：
- `IGH_Attributes.Hidden` → 使用反射
- `GH_Document.SelectObjects()` → 使用 `#if NETFRAMEWORK`
- `GH_Viewport.Pan` → 使用 `#if NETFRAMEWORK`

### 參數名注意

Grasshopper 參數有 **Name** (全名) 和 **NickName** (短名)：
- 連線時優先使用 NickName (`R`, `Pt`, `G`)
- v2.0 已修復：NickName 優先匹配

### 相關文檔

- `docs/GH_MCP_DEPLOYMENT_GUIDE.md` - 部署指南
- `docs/GH_MCP_PARAMETER_REFERENCE.md` - 參數名對照表
- `docs/GH_MCP_V2_UPGRADE_PLAN.md` - 升級計劃
- **`docs/GH_MCP_DEBUG_KNOWLEDGE.md` - 除錯知識庫 (必讀！)**

---

## GH_MCP 除錯關鍵經驗 (CRITICAL - 對話壓縮後必讀)

### 1. MCP Fuzzy Search 會返回錯誤組件
**問題**: `get_component_candidates` 搜索 "Rotate" 可能返回 VectorComponents/Rotate (向量旋轉) 而非 XformComponents/Rotate (幾何旋轉)

**解決**: 使用 trusted GUID (新版，非 OBSOLETE)
```python
ROTATE_GUID = "19c70daf-600f-4697-ace2-567f6702144d"  # XformComponents/Rotate (新版)
client.add_component("Rotate", "RotatedSteps", col=10, row=1, guid=ROTATE_GUID)
```

### 2. Panel 輸出文字無法傳遞給數值輸入
**問題**: Panel 組件輸出文字，傳給 Multiplication 等組件會顯示虛線 (無資料流)

**解決**: 常數改用 Number Slider
```python
# 錯誤: client.add_component("Number", "Num360", ...)
# 正確:
client.add_slider("Num360", col=1, row=1, value=360, min_val=0, max_val=720)
```

### 3. Slider 數值設置順序
**問題**: Slider 預設範圍 0-1，先設 value=360 會被 clamp

**解決**: 先設範圍再設數值
```python
client.send_command('set_slider_properties', id=comp_id, min=0, max=720)
client.send_command('set_slider_properties', id=comp_id, value=360)
```

### 4. 已知組件衝突
| 原生組件 | 衝突插件 | 解決方案 |
|----------|----------|----------|
| Rotate (XformComponents) | VectorComponents | 用 GUID `19c70daf...` (新版) |
| Pipe (SurfaceComponents) | Nautilus | 用 GUID `1ee25749...` |
| Series | Flexibility | 用 GUID `651c4fa5...` |

### 5. Trusted GUIDs (Mac Rhino 8)
完整列表見 `/config/trusted_guids.json`

關鍵組件 (非 OBSOLETE):
- Rotate: `19c70daf-600f-4697-ace2-567f6702144d` (新版)
- Pipe: `1ee25749-2e2d-4fc6-9209-0ea0515081f9`
- Series: `651c4fa5-dff4-4be6-ba31-6dc267d3ab47`

OBSOLETE (避免使用):
- Rotate [OLD]: `5944e8e2-9fb9-4f8b-bdd4-8b18f1955360`

---

## 插件組件參數參考

插件組件的 GUID 需運行時查詢，但參數信息已記錄在 `config/trusted_guids.json` 的 `_plugin_components` 區段：

### WASP (Aggregation)
- **Connection From Direction**: `GEO`(Mesh!), `CEN`, `UP`, `T` → `CONN`
- **Part**: `N`, `GEO`(idx 1), `CONN`(idx 2), `COLL`, `ATT`, `ADD` → `PART`
- **Rule**: `PART`, `CONN`, `PART2`, `CONN2`, `GRTYPE` → `R`
- **Stochastic Aggregation**: `PART`, `RULE`, `COUNT`, `SEED`, `COLL`, `RESET` → `AGG`, `GEO`

### Karamba3D (Structural)
- **LineToBeam**: `Lines`, `CrossSection`, `Material` → `Beams`
- **Assemble**: `Points`, `Beams`, `Shells`, `Supports`, `Loads` → `Model`, `Info`
- **Analyze**: `Model`, `LoadCases` → `Model`, `MaxDisp`, `Energy`, `Info`

### Kangaroo2 (FormFinding)
- **Solver**: `Goals`, `Reset`, `On` → `Geometry`, `Iterations`
- **Anchor**: `Points`, `Targets`, `Strength` → `Goal`
- **SoapFilm**: `Mesh`, `Strength` → `Goal`
- **Pressure**: `Mesh`, `Pressure`, `Strength` → `Goal`

---

## 連接模式快速參考

17 種預定義連接模式，使用 `kb.get_pattern("PatternName")` 查詢：

| 類別 | 模式名稱 | 說明 |
|------|----------|------|
| Structural | `Karamba_Structural` | 線性構件分析 |
| Structural | `Karamba_Shell_Analysis` | 殼體構件分析 |
| Environmental | `Ladybug_Solar` | 日照分析 |
| Environmental | `Honeybee_Energy_Model` | 能源模擬 |
| FormFinding | `Kangaroo_Form_Finding` | 形態找尋 |
| FormFinding | `Kangaroo_Tensile_Structure` | 張力結構 |
| Aggregation | `WASP_Stochastic` | 隨機聚集 |
| Aggregation | `WASP_Mesh_Part` | Mesh Part 創建 (推薦) |
| Panelization | `Lunchbox_Panelization` | 菱形分割 |
| MeshProcessing | `Weaverbird_Subdivision` | Mesh 細分 |
