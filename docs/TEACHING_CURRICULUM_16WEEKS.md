# GH_MCP 參數化設計與 AI 自動化 — 16 週教學課程

> **課程目標**：從 Grasshopper 基礎到 AI 輔助參數化建模的完整學習路徑

**適用對象**：建築/設計背景學生、具備基本程式概念者
**先備知識**：Rhino 基本操作、Python 基礎（Week 9 後需要）

---

## 課程總覽

| 階段 | 週數 | 主題 | 核心技能 |
|------|------|------|----------|
| **基礎篇** | 1-4 | Grasshopper 核心 | 數據流、組件、參數 |
| **進階篇** | 5-8 | 幾何操作與數據樹 | 表面、向量、樹狀結構 |
| **整合篇** | 9-12 | MCP 與 Python 連接 | API、自動化腳本 |
| **AI 篇** | 13-16 | AI 輔助設計工作流 | LangGraph、多模式編排 |

---

## 第一階段：Grasshopper 基礎（Week 1-4）

### Week 1：Grasshopper 入門與數據流思維

**學習目標**
- 理解視覺化程式設計概念
- 認識 Grasshopper 介面與基本操作
- 掌握「數據流」思維模式

**課程內容**
| 時段 | 主題 | 活動 |
|------|------|------|
| 1.1 | 介面導覽 | Canvas、組件面板、參數面板 |
| 1.2 | 第一個定義 | Point → Circle → Extrude |
| 1.3 | Number Slider | 參數控制幾何 |
| 1.4 | Panel 與數據檢視 | 理解數據如何流動 |

**實作練習**
```
練習 1-1：創建可調整半徑的圓柱體
- Number Slider (0-50) → Circle → Extrude
- 使用 Panel 觀察每個階段的數據
```

**關鍵概念**
- 輸入（Input）→ 處理（Process）→ 輸出（Output）
- 組件之間的連線 = 數據流動

**評量標準**
- [ ] 能獨立建立基本幾何
- [ ] 理解 Slider 與幾何的關係
- [ ] 能使用 Panel 檢視數據

---

### Week 2：基本幾何生成與列表操作

**學習目標**
- 掌握常用幾何生成組件
- 理解列表（List）概念
- 學習基本列表操作

**課程內容**
| 時段 | 主題 | 重點組件 |
|------|------|----------|
| 2.1 | 點與向量 | Construct Point, Vector XYZ |
| 2.2 | 曲線生成 | Line, Arc, Polyline, Interpolate |
| 2.3 | 列表基礎 | Series, Range, List Item |
| 2.4 | 列表操作 | List Length, Reverse, Shift |

**實作練習**
```
練習 2-1：螺旋點陣列
- Series (0-360, step=30) → 極座標轉換 → 點列表

練習 2-2：參數化樓梯
- Series 生成高度列表 → Rectangle → Move
```

**關鍵概念**
- 列表索引從 0 開始
- 一對多連接 = 批量處理

**本週組件清單**
| 組件 | 功能 | 常用參數 |
|------|------|----------|
| Series | 等差數列 | Start, Step, Count |
| Range | 範圍數列 | Domain, Steps |
| List Item | 取列表項 | Index |
| Shift List | 循環偏移 | Offset, Wrap |

---

### Week 3：曲面基礎與 UV 參數

**學習目標**
- 理解曲面的 UV 參數空間
- 掌握曲面生成方法
- 學習曲面評估技巧

**課程內容**
| 時段 | 主題 | 重點 |
|------|------|------|
| 3.1 | 曲面生成 | Loft, Sweep, Extrude |
| 3.2 | UV 概念 | 參數空間 (0-1) |
| 3.3 | 曲面評估 | Evaluate Surface, Closest Point |
| 3.4 | 法向量 | Surface Normal, Deconstruct Plane |

**實作練習**
```
練習 3-1：曲面上的點陣列
- Surface → 等分 UV → Evaluate Surface → 點陣列

練習 3-2：曲面法向量可視化
- Evaluate Surface → Plane → Normal → Vector Display
```

**關鍵概念圖解**
```
UV 參數空間
┌────────────────┐
│ (0,1)    (1,1) │
│                │
│    UV 曲面     │
│                │
│ (0,0)    (1,0) │
└────────────────┘
```

---

### Week 4：變換與空間操作

**學習目標**
- 掌握幾何變換組件
- 理解座標系統與平面
- 學習空間定位技巧

**課程內容**
| 時段 | 主題 | 組件 |
|------|------|------|
| 4.1 | 移動與複製 | Move, Copy |
| 4.2 | 旋轉與縮放 | Rotate, Scale |
| 4.3 | 平面操作 | Construct Plane, Orient |
| 4.4 | 進階變換 | Mirror, Array |

**期中作業：參數化傢俱**
```
設計一張可調整的桌子：
- 桌面尺寸（長、寬、厚）
- 桌腳高度
- 桌腳位置（邊緣內縮量）
使用至少 5 個 Number Slider 控制參數
```

---

## 第二階段：進階 Grasshopper（Week 5-8）

### Week 5：數據樹結構

**學習目標**
- 理解數據樹（Data Tree）概念
- 掌握樹狀結構操作
- 學習路徑（Path）管理

**課程內容**
| 時段 | 主題 | 組件 |
|------|------|------|
| 5.1 | 樹的概念 | Graft, Flatten, Simplify |
| 5.2 | 路徑操作 | Shift Paths, Path Mapper |
| 5.3 | 樹的分支 | Explode Tree, Entwine |
| 5.4 | 進階操作 | Relative Item, Partition |

**關鍵概念圖解**
```
數據樹結構
{0;0} ─ [a, b, c]     ← 分支 0;0
{0;1} ─ [d, e, f]     ← 分支 0;1
{1;0} ─ [g, h]        ← 分支 1;0
{1;1} ─ [i, j, k, l]  ← 分支 1;1
```

**實作練習**
```
練習 5-1：交錯網格
- 創建點網格 → Partition 分組 → Shift Paths → 交錯連線

這是本專案的核心技術！參考：
grasshopper-mcp-enhanced/docs/Grasshopper_教學文件.md
```

---

### Week 6：向量運算與幾何分析

**學習目標**
- 掌握向量運算
- 學習幾何分析方法
- 理解法向量應用

**課程內容**
| 時段 | 主題 | 組件 |
|------|------|------|
| 6.1 | 向量基礎 | Vector 2Pt, Unit Vector |
| 6.2 | 向量運算 | Add, Cross Product, Dot Product |
| 6.3 | 向量應用 | Amplitude, Angle |
| 6.4 | 幾何分析 | Area, Volume, Centroid |

**實作練習**
```
練習 6-1：沿法向量擠出
- Surface → Divide → Normal → Extrude 每個分區
```

---

### Week 7：進階曲面操作

**學習目標**
- 掌握曲面細分技術
- 學習表面映射
- 理解 Brep 操作

**課程內容**
| 時段 | 主題 | 組件 |
|------|------|------|
| 7.1 | 曲面細分 | Subdivide, Diamond Panels |
| 7.2 | 表面映射 | Map to Surface, Surface Morph |
| 7.3 | Brep 操作 | Deconstruct Brep, Cap Holes |
| 7.4 | 展開曲面 | Unroll, Smash |

**實作練習**
```
練習 7-1：參數化立面面板
- 曲面 → Diamond Panels → 每個面板內縮 → 厚度擠出
```

---

### Week 8：網格與三角化

**學習目標**
- 理解網格（Mesh）結構
- 掌握三角化技術
- 學習 Delaunay 應用

**課程內容**
| 時段 | 主題 | 組件 |
|------|------|------|
| 8.1 | Mesh 基礎 | Mesh, Mesh Vertices, Mesh Faces |
| 8.2 | Delaunay | Delaunay Mesh, Delaunay Edges |
| 8.3 | Voronoi | Voronoi, Voronoi 3D |
| 8.4 | 應用案例 | 結構優化、立面設計 |

**期中專案：參數化立面系統**
```
設計一個可適應不同曲面的立面面板系統：
1. 輸入任意 NURBS 曲面
2. 自動生成面板網格
3. 每個面板可調整深度
4. 支援至少兩種面板類型（三角/菱形）
```

---

## 第三階段：MCP 整合（Week 9-12）

### Week 9：Python 腳本入門

**學習目標**
- 在 Grasshopper 中使用 Python
- 理解 GhPython 組件
- 學習基本腳本編寫

**課程內容**
| 時段 | 主題 | 重點 |
|------|------|------|
| 9.1 | GhPython 組件 | 輸入輸出設定 |
| 9.2 | RhinoCommon | 幾何類別 |
| 9.3 | 列表處理 | Python 列表 vs GH 列表 |
| 9.4 | 實用腳本 | 點去重、條件篩選 |

**程式碼範例**
```python
# GhPython: 點去重
import rhinoscriptsyntax as rs
import Rhino.Geometry as rg

def remove_duplicates(points, tolerance=0.001):
    unique = []
    for pt in points:
        is_dup = False
        for u in unique:
            if pt.DistanceTo(u) < tolerance:
                is_dup = True
                break
        if not is_dup:
            unique.append(pt)
    return unique

a = remove_duplicates(x, tol)
```

---

### Week 10：GH_MCP 系統架構

**學習目標**
- 理解 MCP 協議
- 認識 GH_MCP 架構
- 學習 TCP 通訊基礎

**課程內容**
| 時段 | 主題 | 重點 |
|------|------|------|
| 10.1 | MCP 概念 | Model Context Protocol |
| 10.2 | 系統架構 | GH_MCP.gha ↔ Python Bridge ↔ AI |
| 10.3 | 安裝設定 | 組件安裝、環境配置 |
| 10.4 | 第一次連線 | 測試基本命令 |

**架構圖**
```
┌─────────────┐     TCP      ┌─────────────┐     MCP      ┌─────────────┐
│  Grasshopper │ ◄─────────► │   Python    │ ◄─────────► │   Claude    │
│   GH_MCP.gha │   Port 8080 │   Bridge    │             │   Cursor    │
└─────────────┘              └─────────────┘              └─────────────┘
```

**實作練習**
```bash
# 安裝 GH_MCP
pip install grasshopper-mcp

# 啟動 Bridge Server
python -m grasshopper_mcp.bridge

# 在 Grasshopper 中放置 GH_MCP 組件
```

---

### Week 11：MCP 命令與 API

**學習目標**
- 掌握 GH_MCP 命令格式
- 學習組件 GUID 系統
- 理解參數設定機制

**課程內容**
| 時段 | 主題 | 重點命令 |
|------|------|----------|
| 11.1 | 組件操作 | add_component, get_component_info |
| 11.2 | 連線管理 | connect_components |
| 11.3 | 參數設定 | set_slider_value (兩步驟) |
| 11.4 | 群組管理 | create_group |

**API 使用範例**
```python
from grasshopper_mcp.client_optimized import GH_MCP_ClientOptimized

async def create_box():
    client = GH_MCP_ClientOptimized()

    # 新增組件
    box_id = await client.add_component(
        name="Box",
        x=100, y=100
    )

    # 設定 Slider (重要：先設 range 再設 value)
    await client.set_slider_value(
        slider_id,
        value=10,
        min_value=0,
        max_value=100
    )
```

**關鍵知識**
```
⚠️ Slider 兩步驟設定（避免 Clamp 問題）
1. 先設定 range: set_slider_properties(min=0, max=100)
2. 再設定 value: set_slider_value(value=50)

原因：如果原本 range 是 0-10，直接設 value=50 會被 clamp 到 10
```

---

### Week 12：自動化腳本開發

**學習目標**
- 開發完整自動化腳本
- 學習 placement_info.json 格式
- 掌握批量操作技巧

**課程內容**
| 時段 | 主題 | 範例 |
|------|------|------|
| 12.1 | JSON 工作流 | placement_info.json 結構 |
| 12.2 | 腳本架構 | scripts/create_table_v3.py |
| 12.3 | 錯誤處理 | 連線失敗、組件找不到 |
| 12.4 | 除錯技巧 | Panel 驗證、Log 記錄 |

**placement_info.json 範例**
```json
{
  "components": [
    {
      "id": "WIDTH_SLIDER",
      "type": "Number Slider",
      "position": {"x": 100, "y": 100},
      "value": 50,
      "range": [0, 100]
    },
    {
      "id": "BOX",
      "type": "Box",
      "position": {"x": 300, "y": 100}
    }
  ],
  "connections": [
    {
      "from": "WIDTH_SLIDER",
      "from_param": "N",
      "to": "BOX",
      "to_param": "X"
    }
  ]
}
```

**期末專案預備：定義你的參數化模型**
```
選擇一個傢俱/建築元素，定義其：
1. 組件清單 (component_info.mmd)
2. 部件關係 (part_info.mmd)
3. 佈置資訊 (placement_info.json)
```

---

## 第四階段：AI 輔助設計（Week 13-16）

### Week 13：LangGraph 工作流

**學習目標**
- 理解 LangGraph 概念
- 認識狀態機工作流
- 學習節點與邊的設計

**課程內容**
| 時段 | 主題 | 重點 |
|------|------|------|
| 13.1 | LangGraph 概念 | State, Node, Edge |
| 13.2 | GH_MCP 狀態 | DesignState 結構 |
| 13.3 | 工作流設計 | 意圖解析 → 工具選擇 → 執行 |
| 13.4 | 條件路由 | 根據結果決定下一步 |

**狀態定義範例**
```python
from typing import TypedDict, List, Optional

class DesignState(TypedDict):
    task: str                    # 用戶任務描述
    components: List[dict]       # 已建立的組件
    connections: List[dict]      # 已建立的連線
    errors: List[str]            # 錯誤訊息
    iteration: int               # 迭代次數
    is_complete: bool            # 是否完成
```

**工作流圖**
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Intent    │ ──► │    Tool     │ ──► │   Execute   │
│   Parser    │     │  Selector   │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
                          ┌───────────────────────────────┐
                          │  Validation  ──► ✓ Complete   │
                          │              ──► ✗ Fix Loop   │
                          └───────────────────────────────┘
```

---

### Week 14：多模式 AI 編排

**學習目標**
- 理解 Superpower 整合架構
- 掌握四種工作模式
- 學習意圖路由機制

**課程內容**
| 時段 | 主題 | 模式 |
|------|------|------|
| 14.1 | Workflow 模式 | 確定性四階段管線 |
| 14.2 | Think-Partner 模式 | 蘇格拉底式探索 |
| 14.3 | Brainstorm 模式 | 三階段腦力激盪 |
| 14.4 | Meta-Agent 模式 | 動態工具創建 |

**模式選擇邏輯**
```python
from grasshopper_mcp.langgraph.core import IntentRouter, IntentType

router = IntentRouter()

# 關鍵詞觸發
"create a table"        → IntentType.WORKFLOW   (確定性執行)
"how should I design"   → IntentType.THINK      (探索式對話)
"brainstorm ideas"      → IntentType.BRAINSTORM (發散思維)
"create a new tool"     → IntentType.META       (創建工具)
```

**CLI 命令使用**
```python
from grasshopper_mcp.cli import CommandHandler

handler = CommandHandler()

# 直接指定模式
await handler.execute("/think parametric chair design")
await handler.execute("/brainstorm modern table ideas")
await handler.execute("/workflow create a simple box")
await handler.execute("/meta create spiral pattern tool")
```

---

### Week 15：Agent Orchestrator 實戰

**學習目標**
- 使用 EnhancedGHOrchestrator
- 理解 Cascade + MoE 策略
- 實作完整設計流程

**課程內容**
| 時段 | 主題 | 重點 |
|------|------|------|
| 15.1 | Orchestrator 架構 | EnhancedGHOrchestrator |
| 15.2 | Cascade 策略 | 層級化 Agent 調度 |
| 15.3 | Confidence 評估 | 信心分數與決策 |
| 15.4 | 完整流程演示 | 從自然語言到 GH 定義 |

**完整使用範例**
```python
from grasshopper_mcp.langgraph.core.integration import EnhancedGHOrchestrator

async def design_chair():
    # 初始化 Orchestrator
    orch = EnhancedGHOrchestrator.create()

    # 第一階段：探索設計
    result1 = await orch.execute_with_mode_selection(
        task="我想設計一張現代簡約的椅子",
        context={}
    )
    # → 自動選擇 THINK 模式，進行蘇格拉底式對話

    # 第二階段：確定規格
    result2 = await orch.execute_with_mode_selection(
        task="椅子高度 45cm，座椅寬度 40cm，有扶手",
        context=result1.context
    )
    # → 自動選擇 WORKFLOW 模式，執行建模

    # 第三階段：調整優化
    result3 = await orch.execute_with_mode_selection(
        task="扶手太高了，降低 5cm",
        context=result2.context
    )
```

---

### Week 16：期末專案與展示

**學習目標**
- 完成完整 AI 輔助設計流程
- 展示學習成果
- 反思與未來方向

**期末專案要求**

```markdown
## 專案規格

### 基本要求
1. 選擇一個傢俱/建築元素設計
2. 使用 GH_MCP 系統完成參數化建模
3. 至少包含：
   - 5 個以上可調參數
   - 3 種以上組件類型
   - 完整的連線關係

### 進階要求（加分）
- 使用 LangGraph 工作流
- 整合多種 AI 模式
- 自動化錯誤修復

### 交付物
1. Grasshopper 定義檔 (.gh)
2. placement_info.json
3. 設計說明文件（含截圖）
4. 5 分鐘展示影片
```

**展示評分標準**
| 項目 | 權重 | 評分標準 |
|------|------|----------|
| 參數化設計品質 | 30% | 參數合理性、可調整性 |
| MCP 整合程度 | 25% | API 使用正確性、自動化程度 |
| AI 模式運用 | 25% | 模式選擇恰當、流程順暢 |
| 文件與展示 | 20% | 說明清晰、展示專業 |

---

## 附錄

### A. 環境設定指南

```bash
# 1. 安裝 Python 環境
conda create -n gh_mcp python=3.10
conda activate gh_mcp

# 2. 安裝依賴
pip install grasshopper-mcp
pip install langgraph

# 3. 設定 API Key（如需 AI 功能）
export ANTHROPIC_API_KEY="your-key"
export GEMINI_API_KEY="your-key"

# 4. 啟動 Bridge Server
python -m grasshopper_mcp.bridge
```

### B. 常見問題排解

| 問題 | 解決方案 |
|------|----------|
| GH_MCP 組件載入失敗 | 確認 .gha 在正確目錄，右鍵解除封鎖 |
| 連線失敗 | 確認 Bridge Server 已啟動，Port 8080 未被占用 |
| Slider 值設定無效 | 使用兩步驟：先設 range 再設 value |
| 組件找不到 | 確認 GUID 正確，使用 get_component_info 查詢 |

### C. 參考資料

**專案文檔**
- `docs/GH_MCP_DEPLOYMENT_GUIDE.md` - 部署指南
- `docs/GH_MCP_PARAMETER_REFERENCE.md` - 參數對照表
- `docs/design/SUPERPOWER_INTEGRATION_ARCHITECTURE.md` - AI 架構

**範例腳本**
- `scripts/create_table_v3.py` - 桌子參數化
- `scripts/build_chair.py` - 椅子參數化
- `scripts/test_superpower.py` - AI 模式測試

**知識庫**
- `grasshopper_mcp/joseki/` - 常用模式庫
- `GH_WIP/` - 工作進度檔案

---

## 教學建議

### 課堂組織

**前半段（Week 1-8）**
- 著重實機操作
- 每週至少 2 小時上機時間
- 小組討論數據樹概念

**後半段（Week 9-16）**
- 專案導向學習
- 鼓勵查閱程式碼
- 使用 Git 版本控制

### 評量方式

| 類型 | 比重 | 說明 |
|------|------|------|
| 每週練習 | 30% | 基礎技能驗證 |
| 期中專案 | 30% | Grasshopper 綜合應用 |
| 期末專案 | 40% | AI 整合完整流程 |

### 補充資源

1. **Grasshopper Primer** - 官方入門指南
2. **The Grasshopper Tutorials** - 線上教學系列
3. **本專案 GitHub** - fred1357944/grasshopper-mcp-workflow

---

**文件版本**：1.0
**建立日期**：2026-01-18
**維護者**：GH_MCP Development Team
