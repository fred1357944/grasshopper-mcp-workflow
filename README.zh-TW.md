# Grasshopper MCP workflow

Grasshopper MCP workflow 是一個橋接伺服器，使用模型上下文協議（MCP）標準連接 Grasshopper 和 Cursor。

**語言選擇 / Language Selection**: [English](README.md) | [繁體中文](README.zh-TW.md)

## 功能特色

- **MCP 協議整合**：透過模型上下文協議（MCP）標準連接 Grasshopper 和 Cursor
- **組件管理**：提供直觀的工具函數，用於創建、管理和連接 Grasshopper 組件
- **意圖識別**：支援高階意圖識別，可從簡單描述自動創建複雜的組件模式
- **組件知識庫**：包含完整的知識庫，了解常見組件的參數和連接規則
- **工作流程自動化**：提供工具來執行來自 JSON 和 MMD 檔案的複雜 Grasshopper 工作流程
- **CLI 工具**：用於批次操作和自動化的命令列介面
- **參數管理**：進階的參數設置和管理功能
- **群組管理**：將組件組織成具有自訂顏色和名稱的群組

## 系統架構

系統由以下部分組成：

1. **Grasshopper MCP 組件 (GH_MCP.gha)**：安裝在 Grasshopper 中的 C# 插件，提供 TCP 伺服器來接收命令
2. **Python MCP 橋接伺服器** (`grasshopper_mcp`)：連接 Cursor 和 Grasshopper MCP 組件的橋接伺服器
3. **Grasshopper Tools** (`grasshopper_tools`)：用於管理 Grasshopper 組件、連接、參數和工作流程的完整 Python 函式庫
4. **組件知識庫**：包含組件資訊、模式和意圖的 JSON 檔案
5. **工作流程技能** (`grasshopper-workflow`)：為 Cursor 提供的專業技能，提供進階工作流程自動化功能

## 安裝說明

### 系統需求

- Rhino 7 或更高版本
- Grasshopper
- Python 3.8 或更高版本
- Cursor

### 安裝步驟

1. **安裝 Grasshopper MCP 組件**

   **方法 1：下載預編譯的 GH_MCP.gha 檔案（推薦）**
   
   直接從 GitHub 儲存庫下載 [GH_MCP.gha](https://github.com/alfredatnycu/grasshopper-mcp/raw/master/releases/GH_MCP.gha) 檔案，並複製到 Grasshopper 組件資料夾：
   ```
   %APPDATA%\Grasshopper\Libraries\
   ```

   **方法 2：從原始碼編譯**
   
   如果您偏好從原始碼編譯，請複製儲存庫並使用 Visual Studio 編譯 C# 專案。

2. **安裝 Python MCP 橋接伺服器**

   **方法 1：從 PyPI 安裝（推薦）**
   
   最簡單的方法是使用 pip 直接從 PyPI 安裝：
   ```
   pip install grasshopper-mcp
   ```
   
   **方法 2：從 GitHub 安裝**
   
   您也可以從 GitHub 安裝最新版本：
   ```
   pip install git+https://github.com/alfredatnycu/grasshopper-mcp.git
   ```
   
   **方法 3：從原始碼安裝**
   
   如果您需要修改程式碼或開發新功能，可以複製儲存庫並安裝：
   ```
   git clone https://github.com/alfredatnycu/grasshopper-mcp.git
   cd grasshopper-mcp
   pip install -e .
   ```

## 使用方式

1. **啟動 Rhino 和 Grasshopper**

   啟動 Rhino 並開啟 Grasshopper。

2. **將 GH_MCP 組件添加到畫布**

   在 Grasshopper 組件面板中找到 GH_MCP 組件，並將其添加到畫布上。

3. **啟動 Python MCP 橋接伺服器**

   開啟終端機並執行：
   ```
   python -m grasshopper_mcp.bridge
   ```
   
   > **注意**：由於 Python 腳本路徑問題，`grasshopper-mcp` 命令可能無法直接使用。使用 `python -m grasshopper_mcp.bridge` 是推薦且更可靠的方法。

4. **配置 Cursor MCP 連接**

   在 Cursor 中配置 MCP 伺服器連接，讓 Cursor 能夠與 Grasshopper MCP 橋接伺服器通訊。
   
   **配置步驟：**
   
   1. 找到 Cursor 的 MCP 配置檔案 `mcp.json`，通常位於：
      - Windows: `%APPDATA%\Cursor\User\mcp.json` 或 `~\.cursor\mcp.json`
      - macOS: `~/Library/Application Support/Cursor/User/mcp.json` 或 `~/.cursor/mcp.json`

   
   2. 在 `mcp.json` 檔案中添加以下配置：
   
      ```json
      {
        "mcpServers": {
          "grasshopper": {
            "command": "python",
            "args": ["-m", "grasshopper_mcp.bridge"]
          }
        }
      }
      ```
   
   3. **使用虛擬環境或特定 Python 路徑**：
      
      如果您使用虛擬環境或 conda 環境，請指定完整的 Python 可執行檔路徑：
      
      ```json
      {
        "mcpServers": {
          "grasshopper": {
            "command": "C:\\Users\\YourUsername\\.conda\\envs\\grasshopper-mcp\\python.exe",
            "args": ["-m", "grasshopper_mcp.bridge"]
          }
        }
      }
      ```
      
      > **提示**：在 Windows 上，路徑中的反斜線需要使用雙反斜線 `\\` 或正斜線 `/` 進行轉義。
   
   4. **驗證 Python 路徑**：
      
      您可以使用以下命令找到 Python 可執行檔的完整路徑：
      - Windows: `where python` 或 `where python3`
      - macOS/Linux: `which python` 或 `which python3`
      
      如果使用 conda 環境，可以執行：
      ```
      conda activate grasshopper-mcp
      where python  # Windows
      which python  # macOS/Linux
      ```
   
   5. 儲存配置檔案後，重新啟動 Cursor 以使配置生效。
   
   > **注意**：確保在配置 MCP 之前，您已經完成了步驟 2（將 GH_MCP 組件添加到 Grasshopper 畫布）和步驟 3（啟動 Python MCP 橋接伺服器）。MCP 橋接伺服器需要在 Cursor 連接之前運行。

5. **開始使用 Grasshopper 與 Cursor**

   現在您可以使用 Cursor 透過自然語言命令來控制 Grasshopper。

## 範例命令

以下是一些可以在 Cursor 中使用的範例命令：

- "在點 (0,0,0) 創建一個半徑為 5 的圓"
- "將圓連接到高度為 10 的擠出組件"
- "創建一個 5 行 5 列的點陣列"
- "對所有選取的物件應用隨機旋轉"
- "創建一個矩形組件並將其寬度設為 10"
- "將所有選取的組件群組並命名為 '幾何群組'"

## 使用 Grasshopper Tools

專案包含一個完整的 `grasshopper_tools` 函式庫，用於程式化控制 Grasshopper：

### Python API 使用方式

```python
from grasshopper_tools import (
    GrasshopperClient,
    ComponentManager,
    ConnectionManager,
    ParameterSetter,
    GroupManager
)

# 創建客戶端連接
client = GrasshopperClient(host="localhost", port=8080)

# 創建組件管理器
comp_mgr = ComponentManager(client)

# 添加組件
component_id = comp_mgr.add_component(
    guid="e2bb9b8d-0d80-44e7-aa2d-2e446f5c61da",  # Number Slider GUID
    x=100,
    y=200,
    component_id="SLIDER_WIDTH"
)

# 設置組件參數
param_setter = ParameterSetter(client)
param_setter.set_slider_properties(
    component_id=component_id,
    value="10",
    min_value=0,
    max_value=100
)
```

### CLI 使用方式

```bash
# 從 JSON 執行放置工作流程
python -m grasshopper_tools.cli execute-placement GH_WIP/placement_info.json

# 解析 MMD 檔案
python -m grasshopper_tools.cli parse-mmd GH_WIP/component_info.mmd --action sliders

# 查看說明
python -m grasshopper_tools.cli --help
```

更多詳細文檔，請參閱 [grasshopper_tools 文檔](grasshopper_tools/docs/)。

## 故障排除

如果遇到問題，請檢查以下項目：

1. **GH_MCP 組件無法載入**
   - 確保 .gha 檔案位於正確的位置：`%APPDATA%\Grasshopper\Libraries\`
   - 在 Grasshopper 中，前往 檔案 > 偏好設定 > 函式庫，然後點擊「解除封鎖」以解除封鎖新組件
   - 重新啟動 Rhino 和 Grasshopper
   - 檢查您是否安裝了正確的 .NET 執行階段（net48 或 net7.0）

2. **橋接伺服器無法啟動**
   - 如果 `grasshopper-mcp` 命令無法使用，請改用 `python -m grasshopper_mcp.bridge`
   - 確保已安裝所有必需的 Python 相依套件：`pip install -r requirements.txt`
   - 檢查埠號 8080 是否已被其他應用程式使用
   - 驗證 Python 版本是否為 3.8 或更高：`python --version`

3. **Cursor 無法連接**
   - 確保橋接伺服器正在運行
   - 驗證您使用的是正確的連接設定（localhost:8080）
   - 檢查橋接伺服器的控制台輸出是否有錯誤訊息
   - 確保 GH_MCP 組件已添加到您的 Grasshopper 畫布上
   - 檢查 Cursor 的 MCP 配置是否正確

4. **命令無法執行**
   - 驗證 GH_MCP 組件是否在您的 Grasshopper 畫布上
   - 檢查橋接伺服器控制台是否有錯誤訊息
   - 確保 Cursor 正確連接到橋接伺服器
   - 使用 `grasshopper_tools` 時驗證組件 GUID 是否正確

5. **Grasshopper Tools 問題**
   - 確保您使用正確的主機和埠號（預設：localhost:8080）
   - 在使用工具之前檢查 MCP 橋接伺服器是否正在運行
   - 使用 CLI 命令時驗證檔案路徑
   - 請參閱 [grasshopper_tools 文檔](grasshopper_tools/docs/) 以獲取詳細的故障排除資訊

## 開發

### 專案結構

```
grasshopper-mcp/
├── grasshopper_mcp/           # Python MCP 橋接伺服器
│   ├── __init__.py
│   └── bridge.py              # 主要橋接伺服器實作
├── grasshopper_tools/          # Python 工具函式庫
│   ├── client.py              # MCP 客戶端實作
│   ├── component_manager.py  # 組件管理
│   ├── connection_manager.py  # 連接管理
│   ├── parameter_setter.py    # 參數設置工具
│   ├── group_manager.py       # 群組管理
│   ├── placement_executor.py  # 工作流程執行
│   ├── parser_utils.py        # MMD/JSON 解析
│   ├── cli.py                 # 命令列介面
│   └── docs/                  # 文檔
├── GH_MCP/                    # Grasshopper 組件 (C#)
│   └── GH_MCP/
│       ├── Commands/          # 命令處理器
│       ├── Models/            # 資料模型
│       ├── Utils/             # 工具函數
│       └── Resources/         # 組件知識庫
├── grasshopper-workflow/      # Cursor 工作流程技能
│   ├── references/           # API 參考
│   ├── scripts/              # 工作流程腳本
│   └── SKILL.md              # 技能文檔
├── GH_WIP/                    # 進行中的工作檔案
│   ├── component_info.mmd    # 組件資訊
│   ├── part_info.mmd         # 零件資訊
│   ├── placement_info.json   # 放置工作流程
│   └── gh_tools_cli.py       # CLI 包裝腳本
├── scripts/                   # 工具腳本
├── prompt/                    # 提示範本
├── docs/                      # 專案文檔
├── releases/                  # 預編譯二進位檔
│   └── GH_MCP.gha            # 編譯的 Grasshopper 組件
├── setup.py                   # Python 套件設定
├── requirements.txt           # Python 相依套件
└── README.md                  # 本檔案
```

### 其他資源

- **Grasshopper Tools 文檔**：請參閱 [grasshopper_tools/docs/](grasshopper_tools/docs/) 以獲取詳細的 API 文檔和使用指南
- **工作流程技能**：`grasshopper-workflow` 技能為 Cursor 提供進階工作流程自動化功能
- **範例腳本**：查看 `scripts/` 目錄以獲取使用範例腳本
- **提示範本**：`prompt/` 目錄包含各種工作流程步驟的提示範本

## 貢獻

歡迎貢獻！請隨時提交 Pull Request。

貢獻時請注意：
- 遵循現有的程式碼風格和結構
- 為新功能添加文檔
- 盡可能包含測試
- 如果添加新功能或更改安裝步驟，請更新此 README

## 版本紀錄

### 版本 0.1.0

**發布日期**: 2024-12-19

- Grasshopper MCP Bridge 首次發布
- 支援與 Cursor 的 MCP 協議整合
- 組件管理和連接工具
- 意圖識別功能，可自動創建組件模式
- 完整的組件知識庫
- 從 JSON 和 MMD 檔案執行工作流程自動化
- 用於批次操作的 CLI 工具
- 參數和群組管理功能

## 授權

本專案採用 MIT 授權條款 - 詳見 LICENSE 檔案。

## 致謝

- 感謝 Rhino 和 Grasshopper 社群提供優秀的工具
- 感謝 Cursor 和 MCP 協議的支援

## 聯絡方式

如有問題或需要支援，請在 GitHub 儲存庫中開啟 issue。

