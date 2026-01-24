# GH_MCP 除錯知識庫

> 從螺旋樓梯 (Spiral Staircase) 案例累積的關鍵經驗
> 更新日期: 2026-01-23

## 核心問題：MCP Fuzzy Search 導致錯誤組件

### 問題描述
MCP 的 `get_component_candidates` 使用模糊搜索，當系統安裝多個插件時，會返回**第三方插件的同名組件**而非原生 Grasshopper 組件。

### 案例 1: Rotate 組件衝突
```
查詢: "Rotate"
期望: XformComponents/Rotate (幾何旋轉)
實際返回: VectorComponents/Rotate (向量旋轉)

症狀: 組件輸入顯示 Vector/Axis/Angle 而非 G/A/P
```

**解決方案**: 使用 trusted GUID
```python
ROTATE_GUID = "5944e8e2-9fb9-4f8b-bdd4-8b18f1955360"  # XformComponents/Rotate
client.add_component("Rotate", "RotatedSteps", col=10, row=1, guid=ROTATE_GUID)
```

### 案例 2: Pipe 組件衝突
```
查詢: "Pipe"
期望: SurfaceComponents/Pipe (管狀曲面)
實際返回: Nautilus/Loxodrome Piped (螺旋管)

症狀: 組件名顯示 "Loxodrome Piped" 而非 "Pipe"
```

**解決方案**: 使用 trusted GUID
```python
PIPE_GUID = "1ee25749-2e2d-4fc6-9209-0ea0515081f9"  # SurfaceComponents/Pipe
```

### 案例 3: Series 組件衝突
```
查詢: "Series"
期望: Sets/Sequence/Series
實際返回: Flexibility/Series variable

症狀: 組件行為異常，參數名稱不同
```

---

## 核心問題：Panel vs Number Slider 資料流

### 問題描述
Panel 組件輸出**文字型別**，傳遞給數學組件 (Multiplication, Division) 的數值輸入時**資料無法流通**。

### 症狀
- Multiplication 組件顯示橘色警告
- 輸入連線顯示虛線 (dashed line)
- 錯誤訊息: "Input parameter A failed to collect data"

### 解決方案
**使用 Number Slider 替代 Panel 存放常數**

```python
# 錯誤做法: Panel 輸出文字
client.add_component("Number", "Num360", col=1, row=1)  # 這不是 slider!
client.send_command('set_slider_properties', id=comp_id, value=360)  # 無效

# 正確做法: Number Slider 輸出數值
client.add_slider("Num360", col=1, row=1, value=360, min_val=0, max_val=720)
```

---

## 核心問題：Slider 數值設置順序

### 問題描述
Slider 預設範圍是 0-1。如果先設置 value=360，會被 clamp 到 1。

### 正確順序
```python
# Step 1: 創建 slider
result = client.send_command('add_component', type='Number Slider', x=x, y=y)

# Step 2: 先設置範圍
client.send_command('set_slider_properties', id=comp_id, min=0, max=720)

# Step 3: 再設置數值
client.send_command('set_slider_properties', id=comp_id, value=360)
```

---

## 核心問題：參數名 Name vs NickName

### 問題描述
Grasshopper 組件參數有兩個名稱：
- **Name**: 完整名稱 (e.g., "Radians", "Degrees", "Result")
- **NickName**: 簡稱 (e.g., "R", "D")

MCP 連接時**需要根據組件類型使用正確的名稱**。

### 已知映射
| 組件 | 輸入 Name | 輸入 NickName | 輸出 Name | 輸出 NickName |
|------|-----------|---------------|-----------|---------------|
| Radians | Degrees | D | Radians | R |
| Sine | x | x | y | y |
| Cosine | x | x | y | y |
| Division | A, B | A, B | Result | R |
| Multiplication | A, B | A, B | Result | R |
| Construct Point | X, Y, Z | X, Y, Z | Pt | Pt |
| Center Box | Base, X, Y, Z | B, X, Y, Z | Box | B |
| Rotate (Xform) | Geometry, Angle, Plane | G, A, P | Geometry, Transform | G, X |

### 建議
連接時優先使用 **NickName**，因為 MCP v2.0+ 已優化為 NickName 優先匹配。

---

## 核心問題：組件 Library 識別

### Mac Rhino 8 原生組件 Library 名稱
| 組件類別 | Library |
|----------|---------|
| 數學運算 (Add, Sub, Mul, Div) | MathComponents |
| 三角函數 (Sin, Cos, Radians) | MathComponents |
| 變換 (Rotate, Move, Scale) | XformComponents |
| 曲面 (Pipe, Extrude) | SurfaceComponents |
| 其他大部分 | Grasshopper |

### 識別方法
```python
result = send('get_component_candidates', name='Rotate', maxResults=20)
for c in result['data']['candidates']:
    print(f"{c['name']}: {c['library']} - {c['guid']}")
```

**選擇標準**: Library 為 `XformComponents`、`MathComponents`、`SurfaceComponents` 或 `Grasshopper` 的組件。

---

## Trusted GUIDs 對照表 (Mac Rhino 8 驗證)

```json
{
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
  "Rotate": "19c70daf-600f-4697-ace2-567f6702144d",
  "Interpolate": "c731696a-ea52-4c47-be86-e64bc80bde08",
  "Pipe": "1ee25749-2e2d-4fc6-9209-0ea0515081f9"
}
```

### OBSOLETE GUIDs (避免使用)
```json
{
  "Rotate [OBSOLETE]": "5944e8e2-9fb9-4f8b-bdd4-8b18f1955360"
}
```

---

## 已知插件衝突列表

| 原生組件 | 衝突插件 | 衝突組件 |
|----------|----------|----------|
| Rotate (XformComponents) | VectorComponents | Rotate (向量) |
| Pipe (SurfaceComponents) | Nautilus | Loxodrome Piped |
| Series (Grasshopper) | Flexibility | Series variable |
| Multiplication | MathComponents (Colour) | Multiplication (向量) |

---

## MCP API 正確用法

### 清空畫布
```python
client.send_command('clear_document')
```

### 創建組件 (使用 GUID)
```python
client.send_command('add_component',
    guid='5944e8e2-9fb9-4f8b-bdd4-8b18f1955360',
    nickname='RotatedSteps',
    x=100, y=200)
```

### 創建組件 (使用 type，可能有衝突風險)
```python
client.send_command('add_component',
    type='Rotate',  # 可能返回錯誤版本
    nickname='RotatedSteps',
    x=100, y=200)
```

### 設置 Slider
```python
# 分兩步: 先範圍再數值
client.send_command('set_slider_properties', id=comp_id, min=0, max=720)
client.send_command('set_slider_properties', id=comp_id, value=360)
```

### 連接組件
```python
client.send_command('connect_components',
    sourceId='xxx',
    sourceParam='N',  # 用 NickName
    targetId='yyy',
    targetParam='A')
```

---

## 除錯流程 SOP

### 當組件顯示錯誤名稱或輸入/輸出不對時:
1. 使用 `get_component_candidates` 搜索組件
2. 檢查返回的 Library 欄位
3. 找到正確的 GUID (Library 應為原生)
4. 在腳本中明確傳入 guid 參數

### 當連線顯示虛線 (無資料流通) 時:
1. 檢查源組件是否正常工作 (無橘色/紅色警告)
2. 確認參數名是否正確 (Name vs NickName)
3. 如果源是 Panel，改用 Number Slider

### 當 Slider 數值錯誤時:
1. 確認設置順序: 先 min/max，再 value
2. 確認 value 在 min/max 範圍內

---

## 參考檔案

- `/config/trusted_guids.json` - 可信 GUID 對照表
- `/grasshopper_mcp/client_optimized.py` - 優化客戶端
- `/scripts/build_spiral_staircase.py` - 螺旋樓梯完整範例

---

---

## WASP 連接問題 (2026-01-24 新增)

### 核心問題：Connection From Plane vs Connection From Direction

**錯誤選擇**: 使用 `Connection From Plane` 組件
**正確選擇**: 使用 `Connection From Direction` 組件

```
Connection From Direction 參數：
- GEO: Part 幾何體 (必須是 Mesh 或 Brep)
- CEN: 連接平面的原點 (中心點)
- UP: X軸方向的線 (決定平面旋轉，可選)
- T: 連接類型 (可選)

關鍵特性：它會自動從幾何體法線計算 Z 方向！
```

### 案例：Error "No valid plane provided for connection 0-5"

**錯誤訊息**:
```
No valid plane provided for connection 0-5
```

**技術原理**:
```python
# Connection From Direction 內部使用這個函數
part_geo.ClosestMeshPoint(center, global_tolerance)
# 尋找距離中心點最近的 Mesh 點，並取得該處的法線向量
```

**根本原因**:
1. **中心點位置偏差** - 連接點並未準確位於 Mesh 表面上
2. **Mesh 精度問題** - 由 Brep 生成的 Mesh 解析度不夠

**解決方案**:
```
選項 1: 使用 Face Normals 組件 (推薦)
  Mesh → Face Normals → C (Center), N (Normal)
  C 輸出就是每個面的精確中心點

選項 2: 使用 Deconstruct Brep + Area Moments
  Center Box → Deconstruct Brep → Faces
  Faces → List Item (選取特定面)
  Selected Face → Area Moments → C (Centroid)
```

---

### 核心問題：Brep vs Mesh 輸入

**重要**: WASP 的 `Connection From Direction` 的 GEO 輸入需要的是 **Mesh**，不是 **Brep**！

**錯誤做法**:
```
Center Box → WASP Connection (GEO)  ❌
# Center Box 輸出 Brep，不是 Mesh
```

**正確做法**:
```
選項 1: 使用 Mesh Box 直接生成 Mesh
  Mesh Box → WASP Connection (GEO)  ✅

選項 2: 轉換 Brep 為 Mesh
  Center Box → Mesh Brep → WASP Connection (GEO)  ✅
```

---

### 核心問題：獲取 Mesh 面中心點

**推薦方法**: Face Normals 組件

```
Face Normals 組件：
輸入: M (Mesh)
輸出: C (Centers - 每個面的中心點)
       N (Normals - 每個面的法向量)
```

**工作流程**:
```
Mesh Box → Face Normals → C (6 個面中心點)
                       → N (6 個法向量)
Face Normals.C → WASP Connection.CEN
```

**為什麼不用 Area Moments?**
- Area Moments 從 Brep 計算 Centroid
- 這些點不一定在 Mesh 表面上
- 會導致 ClosestMeshPoint 找不到對應的面

---

### WASP 正確連接模式

```
┌─────────────────────────────────────────────────────┐
│  WASP Part 創建流程 (程式化生成)                       │
└─────────────────────────────────────────────────────┘

1. 幾何體準備：
   Mesh Box ─────────────────────→ GEO (給 WASP Part)
       │
       └─→ Face Normals ─→ C (Centers) → CEN (給 Connection)
                        → N (Normals) → [可選，自動計算]

2. 連接創建：
   Face Normals.C → Connection From Direction.CEN
   Mesh Box      → Connection From Direction.GEO
   [Line]        → Connection From Direction.UP  (可選)

3. Part 組裝：
   WASP Connection → WASP Part (Connections 輸入，索引 2)
   Mesh Box        → WASP Part (Geometry 輸入，索引 1)

4. 聚集：
   WASP Part → WASP Rule
   WASP Rule → WASP Stochastic Aggregation
```

---

### Trusted GUIDs - WASP 組件

```json
{
  "Face Normals": "f4370b82-4bd6-4ca7-90e8-c88584b280d5",
  "Mesh Box": "9cd3b252-ea78-43f6-873a-9944a1b21e18",
  "Deconstruct Brep": "fab91d2a-93fb-4377-b7f4-bf2b9ad4a5e3",
  "Area Moments": "8c2bade2-fac0-4a47-844b-a96c25b8ed15"
}
```

**注意**: WASP 組件本身的 GUID 需要從系統查詢，因為是第三方插件。

---

### 除錯 SOP - WASP 連接失敗

1. **檢查 GEO 輸入類型**
   - 確認是 Mesh 而非 Brep
   - 如果是 Brep，先用 Mesh Brep 轉換

2. **檢查 CEN 輸入來源**
   - 使用 Face Normals.C 而非 Area Moments.C
   - 確認中心點在 Mesh 表面上

3. **檢查組件版本**
   - 使用 Connection From Direction（不是 Connection From Plane）
   - Connection From Plane 需要完整 Plane，較複雜

4. **清理舊組件**
   - 舊版本 v3/v4 組件可能還在畫布上
   - 檢查錯誤訊息中的組件 ID 是否屬於當前版本

---

---

## 核心問題：組件創建後數值未設定 (2026-01-24 新增)

### 問題描述
`PlacementExecutor` 創建 Slider 和 Panel 組件時，**不會自動設定數值**。組件創建後需要額外調用 API 設定。

### 症狀
- Slider 顯示預設值 0.250（範圍 0-1）而非指定值
- Panel 顯示 "Double click to edit panel content…"
- WASP 組件報錯 "Part name contains a space or reserved characters"

### 解決方案 - 創建後立即設定數值

```python
# 1. 創建 Slider
result = client.send_command('add_component', {
    'type': 'Number Slider',
    'nickname': 'Size',
    'position': {'x': 50, 'y': 100}
})
slider_id = result['data']['id']

# 2. 必須：設定 Slider 屬性（先範圍再數值）
client.send_command('set_slider_properties', {
    'id': slider_id,
    'min': 1,
    'max': 50,
    'value': 10,
    'decimals': 0
})

# 3. 創建 Panel
result = client.send_command('add_component', {
    'type': 'Panel',
    'nickname': 'PartName',
    'position': {'x': 50, 'y': 200}
})
panel_id = result['data']['id']

# 4. 必須：設定 Panel 內容
client.send_command('set_component_value', {
    'id': panel_id,
    'value': 'Cube'
})
```

### 關鍵 API

| 操作 | 命令 | 參數 |
|------|------|------|
| 設定 Slider | `set_slider_properties` | id, min, max, value, decimals |
| 設定 Panel | `set_component_value` | id, value |
| 清空畫布 | `clear_document` | 無 |

### 注意事項
- `clear_canvas` 不存在，正確命令是 `clear_document`
- Slider 設定順序：先 min/max，再 value（避免 clamping）
- Panel 內容不能有空格或保留字元 `_|>` 用於 WASP Part Name

---

## 核心問題：Evaluate Surface 的 uv 輸入 (2026-01-24 新增)

### 問題描述
`Evaluate Surface` 的 uv 輸入是 **Point 類型**，不是兩個獨立的 U/V 數值。

### 錯誤做法
```
Slider(0.5) → Evaluate Surface (U)  ❌
Slider(0.5) → Evaluate Surface (V)  ❌
```

### 正確做法
```
Slider(0.5) → Construct Point (X)
Slider(0.5) → Construct Point (Y)
Construct Point (Pt) → Evaluate Surface (uv)  ✅
```

### 參數對照
```
Evaluate Surface:
  輸入:
    - S (Surface): 要評估的曲面
    - uv (Point): uv 座標點，如 (0.5, 0.5, 0) 表示面中心
  輸出:
    - P (Point): 該位置的點
    - N (Vector): 法向量
    - U (Vector): U 方向
    - V (Vector): V 方向
    - F (Plane): 該位置的 Frame (用於 Connection From Plane)
```

---

---

## 核心問題：FuzzyMatcher 參數名映射衝突 (2026-01-24 新增)

### 問題描述
GH_MCP 的 `FuzzyMatcher.cs` 會將常用簡寫映射到完整參數名，但這會與第三方插件衝突。

### 案例：WASP 的 R 參數
```
WASP Rules Generator 輸出: R (Rules)
FuzzyMatcher 映射: "r" → "Radius"
結果: 連接失敗，錯誤訊息 "Source parameter not found: Radius"
```

### 解決方案

**方法 1: 使用索引連接 (推薦)**
```python
# 不用參數名，用索引
client.send_command('connect_components', {
    'sourceId': rules_id,
    'sourceParamIndex': 0,  # R 是第一個輸出
    'targetId': agg_id,
    'targetParamIndex': 3   # RULES 是第四個輸入
})
```

**方法 2: 修改 FuzzyMatcher (已修復)**
```csharp
// GH_MCP/Utils/FuzzyMatcher.cs - 已移除衝突映射
// { "r", "Radius" },  // 與 WASP 的 R 衝突
// { "geo", "Geometry" },  // 與 WASP 的 GEO 衝突
```

### 已知衝突映射

| 簡寫 | 原映射 | 衝突插件 | 狀態 |
|------|--------|----------|------|
| r | Radius | WASP (R = Rules) | 已移除 |
| geo | Geometry | WASP (GEO) | 已移除 |

---

## 核心問題：API 返回值結構誤導 (2026-01-24 新增)

### 問題描述
`send_command` 返回的結構有兩層 success：
```python
{
    'success': True,  # 外層：HTTP 請求成功
    'data': {
        'success': False,  # 內層：命令執行失敗！
        'error': 'Missing required parameter: sourceId'
    }
}
```

### 正確檢查方式
```python
result = client.send_command('connect_components', params)

# 錯誤：只檢查外層
if result.get('success'):  # 這可能是 True 但命令失敗！
    print('成功')

# 正確：檢查內層
if result.get('data', {}).get('success'):
    print('真的成功')
else:
    print(f"失敗: {result.get('data', {}).get('error')}")
```

---

## WASP v10 完整工作流程 (2026-01-24 驗證)

### 架構圖
```
Number Sliders (Size, Count, Seed, UV)
     │
     ├─→ Center Box ─→ Deconstruct Brep ─→ [6 Faces]
     │        │                                  │
     │        │                                  ↓
     │        │              Construct Point (0.5, 0.5, 0)
     │        │                                  │
     │        │                                  ↓
     │        └───────────→ Evaluate Surface ←──┘
     │                              │
     │                              ↓ (Frame)
     │                    Connection From Plane
     │                              │
     │                              ↓ (CONN)
     └─────────────────────→ Basic Part ←── Panel ("Cube")
                                   │
                                   ↓ (PART)
                            Rules Generator
                                   │
                                   ↓ (R) [用索引 0]
                        Stochastic Aggregation ← Sliders (N, SEED, RESET)
                                   │             [RULES 用索引 3]
                                   ↓
                          Get Part Geometry
```

### 關鍵設定步驟
1. **清空畫布**: `clear_document` (不是 clear_canvas!)
2. **創建組件後設值**:
   - Slider: `set_slider_properties(id, min, max, value, decimals)`
   - Panel: `set_component_value(id, value)`
3. **連接時避免 FuzzyMatcher**:
   - 使用 `sourceParamIndex` / `targetParamIndex`
   - 或使用完整參數名（不要用簡寫）

---

*此文件應在每次遇到新問題時更新，作為 GH_MCP 開發的持久知識庫。*
