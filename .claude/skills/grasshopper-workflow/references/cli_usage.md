# Grasshopper Tools CLI 使用說明

所有工具都可以通過命令提示符（命令行）使用！

## 📋 安裝與使用

### 方式 1: 使用入口腳本（推薦，最簡單）

```bash
# 在項目根目錄下
python GH_WIP/gh_tools_cli.py <命令> [參數]

# 或在 GH_WIP 目錄下
cd GH_WIP
python gh_tools_cli.py <命令> [參數]
```

### 方式 2: 作為模組運行

```bash
# 在 GH_WIP 目錄下
cd GH_WIP
python -m grasshopper_tools.cli <命令> [參數]
```

### 方式 3: 直接運行 CLI 腳本

```bash
# 在 GH_WIP/grasshopper_tools 目錄下
cd GH_WIP/grasshopper_tools
python cli.py <命令> [參數]
```

---

## 🚀 可用命令

### 1. execute-placement - 執行 placement_info.json

執行完整的 placement_info.json 流程（創建組件、連接、保存 ID 映射）

```bash
python GH_WIP/gh_tools_cli.py execute-placement placement_info.json
python GH_WIP/gh_tools_cli.py execute-placement placement_info.json --max-workers 20
python GH_WIP/gh_tools_cli.py execute-placement placement_info.json --no-save-id-map
```

**參數：**
- `json_path` (必需): placement_info.json 文件路徑
- `--max-workers` (可選): 最大並行線程數，默認 10
- `--no-save-id-map` (可選): 不保存組件 ID 映射

---

### 2. parse-mmd - 解析 MMD 文件

解析 component_info.mmd 文件，提取組件、連接、subgraph 或 slider 值

```bash
# 解析組件和連接
python GH_WIP/gh_tools_cli.py parse-mmd GH_WIP/component_info.mmd --action components -o output.json

# 解析 subgraph
python GH_WIP/gh_tools_cli.py parse-mmd GH_WIP/component_info.mmd --action subgraphs -o subgraphs.json

# 解析 slider 值
python GH_WIP/gh_tools_cli.py parse-mmd GH_WIP/component_info.mmd --action sliders -o sliders.json
```

**參數：**
- `mmd_path` (必需): MMD 文件路徑
- `--action` (必需): 解析動作
  - `components`: 解析組件和連接
  - `subgraphs`: 解析 subgraph
  - `sliders`: 解析 slider 值
- `-o, --output` (可選): 輸出 JSON 文件路徑

---

### 3. generate-json - 生成 placement_info.json

從 MMD 文件生成 placement_info.json

```bash
python GH_WIP/gh_tools_cli.py generate-json GH_WIP/component_info.mmd -o GH_WIP/placement_info.json
python GH_WIP/gh_tools_cli.py generate-json GH_WIP/component_info.mmd -o GH_WIP/placement_info.json --description "桌子創建"
```

**參數：**
- `mmd_path` (必需): MMD 文件路徑
- `-o, --output` (可選): 輸出 JSON 文件路徑，默認 placement_info.json
- `--description` (可選): 描述信息，默認 "自動生成"

---

### 4. update-guids - 更新 GUID

更新 JSON 文件中的 GUID

```bash
python GH_WIP/gh_tools_cli.py update-guids GH_WIP/placement_info.json
python GH_WIP/gh_tools_cli.py update-guids GH_WIP/placement_info.json --guid-map custom_guid_map.json
```

**參數：**
- `json_path` (必需): JSON 文件路徑
- `--guid-map` (可選): 自定義 GUID 映射文件（JSON 格式）

---

### 5. add-component - 創建組件

創建單個組件

```bash
python GH_WIP/gh_tools_cli.py add-component --guid "e2bb9b8d-0d80-44e7-aa2d-2e446f5c61da" --x 100 --y 200
python GH_WIP/gh_tools_cli.py add-component --guid "e2bb9b8d-0d80-44e7-aa2d-2e446f5c61da" --x 100 --y 200 --component-id SLIDER_WIDTH
```

**參數：**
- `--guid` (必需): 組件類型 GUID
- `--x` (必需): X 座標
- `--y` (必需): Y 座標
- `--component-id` (可選): 組件 ID 鍵（用於映射）

---

### 6. delete-component - 刪除組件

刪除組件

```bash
python GH_WIP/gh_tools_cli.py delete-component "組件實際ID"
```

**參數：**
- `component_id` (必需): 組件實際 ID

---

### 7. query-guid - 查詢組件 GUID

查詢組件的 GUID

```bash
python GH_WIP/gh_tools_cli.py query-guid "Number Slider"
python GH_WIP/gh_tools_cli.py query-guid "XY Plane"
```

**參數：**
- `component_name` (必需): 組件名稱，如 "Number Slider", "XY Plane"

---

### 8. connect - 連接組件

連接兩個組件

```bash
python GH_WIP/gh_tools_cli.py connect --source-id SLIDER_WIDTH --target-id DIVISION_X --source-param Number --target-param A
```

**參數：**
- `--source-id` (必需): 源組件 ID 鍵
- `--target-id` (必需): 目標組件 ID 鍵
- `--source-param` (可選): 源組件參數名稱
- `--target-param` (可選): 目標組件參數名稱

---

### 9. set-slider - 設置 Slider

設置 Number Slider 的值和屬性

```bash
python GH_WIP/gh_tools_cli.py set-slider --component-id SLIDER_WIDTH --value "120.0" --min 0 --max 200 --rounding 0.1
```

**參數：**
- `--component-id` (必需): 組件 ID 鍵
- `--value` (必需): 當前值
- `--min` (可選): 最小值
- `--max` (可選): 最大值
- `--rounding` (可選): 精度，默認 0.1

---

### 10. set-vector - 設置 Vector XYZ

設置 Vector XYZ 組件的 X、Y、Z 值

```bash
python GH_WIP/gh_tools_cli.py set-vector --component-id VECTOR_LEG1 --x -50.0 --y -30.0 --z 0.0
```

**參數：**
- `--component-id` (必需): 組件 ID 鍵
- `--x` (必需): X 值
- `--y` (必需): Y 值
- `--z` (必需): Z 值

---

### 11. group - 創建群組

將多個組件群組起來

```bash
# 使用 RGB 顏色
python GH_WIP/gh_tools_cli.py group --component-ids "SLIDER_WIDTH,SLIDER_LENGTH" --group-name "桌面參數" --color "225,245,255"

# 使用十六進制顏色
python GH_WIP/gh_tools_cli.py group --component-ids "SLIDER_WIDTH,SLIDER_LENGTH" --group-name "桌面參數" --color-hex "#FF0000"
```

**參數：**
- `--component-ids` (必需): 組件 ID 鍵列表（逗號分隔）
- `--group-name` (必需): 群組名稱
- `--color` (可選): RGB 顏色（格式: r,g,b）
- `--color-hex` (可選): 十六進制顏色（格式: #FF0000）

---

### 12. get-errors - 獲取文檔錯誤

獲取 Grasshopper 文檔中的所有錯誤

```bash
python GH_WIP/gh_tools_cli.py get-errors
python GH_WIP/gh_tools_cli.py get-errors -o errors.json
```

**參數：**
- `-o, --output` (可選): 輸出 JSON 文件路徑

---

## 📝 完整工作流程範例

### 從 MMD 文件創建完整的 Grasshopper 定義

```bash
# 1. 解析 MMD 文件並生成 placement_info.json
python GH_WIP/gh_tools_cli.py generate-json GH_WIP/component_info.mmd -o GH_WIP/placement_info.json

# 2. （可選）更新 GUID
python GH_WIP/gh_tools_cli.py update-guids GH_WIP/placement_info.json

# 3. 執行 placement_info.json
python GH_WIP/gh_tools_cli.py execute-placement GH_WIP/placement_info.json --max-workers 10
```

### 批量設置 Slider

```bash
# 設置多個 slider（需要創建腳本或使用循環）
python GH_WIP/gh_tools_cli.py set-slider --component-id SLIDER_WIDTH --value "120.0" --min 0 --max 200
python GH_WIP/gh_tools_cli.py set-slider --component-id SLIDER_LENGTH --value "80.0" --min 0 --max 200
python GH_WIP/gh_tools_cli.py set-slider --component-id SLIDER_TOP_HEIGHT --value "5.0" --min 0 --max 100
```

### 創建多個群組

```bash
python GH_WIP/gh_tools_cli.py group --component-ids "SLIDER_WIDTH,SLIDER_LENGTH,SLIDER_TOP_HEIGHT" --group-name "桌面參數" --color "225,245,255"
python GH_WIP/gh_tools_cli.py group --component-ids "SLIDER_RADIUS_LEG,SLIDER_LEG_HEIGHT" --group-name "桌腳參數" --color "255,244,225"
```

---

## 🔍 查看幫助

查看所有可用命令：

```bash
# 方式 1（推薦）
python GH_WIP/gh_tools_cli.py --help

# 方式 2
cd GH_WIP
python gh_tools_cli.py --help

# 方式 3
cd GH_WIP
python -m grasshopper_tools.cli --help
```

查看特定命令的幫助：

```bash
python GH_WIP/gh_tools_cli.py execute-placement --help
python GH_WIP/gh_tools_cli.py parse-mmd --help
python GH_WIP/gh_tools_cli.py set-slider --help
```

---

## ⚙️ 注意事項

1. **組件 ID 映射**: 使用 `--component-id` 參數創建的組件會自動保存 ID 映射，後續可以使用組件 ID 鍵來引用。

2. **並行執行**: `execute-placement` 命令支持並行執行，可以通過 `--max-workers` 調整線程數。

3. **錯誤處理**: 所有命令在失敗時會返回非零退出碼，可以在腳本中使用 `$?` 檢查。

4. **JSON 輸出**: 許多命令支持 `-o` 參數輸出 JSON 文件，方便後續處理。

---

## 🎯 快速參考

| 命令 | 功能 | 常用場景 |
|------|------|----------|
| `execute-placement` | 執行完整流程 | 從 JSON 創建整個定義 |
| `parse-mmd` | 解析 MMD | 提取組件、連接、subgraph |
| `generate-json` | 生成 JSON | 從 MMD 生成執行序列 |
| `add-component` | 創建組件 | 單個組件創建 |
| `set-slider` | 設置 Slider | 調整參數值 |
| `connect` | 連接組件 | 建立組件連接 |
| `group` | 創建群組 | 組織組件 |
| `get-errors` | 獲取錯誤 | 檢查文檔問題 |

---

## 💡 提示

- 所有命令都支持 `--help` 查看詳細參數說明
- 使用組件 ID 鍵（如 `SLIDER_WIDTH`）比使用實際 ID 更方便
- 可以將命令組合到批處理文件（.bat）或腳本中自動化執行

