# Grasshopper Tools

統一的 Grasshopper MCP 操作接口，提供組件管理、連接管理、參數設置、群組管理等功能。

## 📚 文檔

所有詳細文檔都在 [docs/](docs/) 目錄中：

- **[README.md](docs/README.md)** - 完整的使用說明和 API 文檔
- **[工具使用指南.md](docs/工具使用指南.md)** - 詳細的工具使用說明
- **[CLI使用說明.md](docs/CLI使用說明.md)** - 命令行接口使用說明
- **[快速使用指南.md](docs/快速使用指南.md)** - 快速入門指南
- **[使用說明.txt](docs/使用說明.txt)** - 簡要使用說明
- **[README_頂層目錄說明.md](docs/README_頂層目錄說明.md)** - 頂層目錄使用說明
- **[遷移完成說明.md](docs/遷移完成說明.md)** - 遷移完成說明

## 🚀 快速開始

### 導入模組

```python
from grasshopper_tools import (
    GrasshopperClient,
    ComponentManager,
    ConnectionManager,
    ParameterSetter,
    GroupManager,
    MMDParser,
    JSONGenerator,
    PlacementExecutor
)
```

### 基本使用

```python
# 創建客戶端
client = GrasshopperClient(host="localhost", port=8080)

# 創建組件管理器
comp_mgr = ComponentManager(client)

# 創建組件
component_id = comp_mgr.add_component(
    guid="e2bb9b8d-0d80-44e7-aa2d-2e446f5c61da",  # Number Slider GUID
    x=100,
    y=200,
    component_id="SLIDER_WIDTH"
)
```

### 命令行使用

```bash
# 查看幫助
python -m grasshopper_tools.cli --help

# 執行 placement_info.json
python -m grasshopper_tools.cli execute-placement GH_WIP/placement_info.json
```

## 📦 目錄結構

```
grasshopper_tools/
├── __init__.py              # 模組初始化
├── client.py                # Grasshopper MCP 通信客戶端
├── component_manager.py     # 組件管理工具
├── connection_manager.py    # 連接管理工具
├── parameter_setter.py      # 參數設置工具
├── group_manager.py         # 群組管理工具
├── parser_utils.py          # MMD/JSON 解析工具
├── placement_executor.py    # Placement 執行器
├── utils.py                 # 通用工具函數
├── cli.py                   # 命令行接口
├── example_usage.py         # 使用範例
├── gh_cli.py               # CLI 快捷腳本
└── docs/                    # 文檔目錄
    ├── README.md
    ├── 工具使用指南.md
    ├── CLI使用說明.md
    └── ...
```

## ⚙️ 依賴

**無外部依賴** - 本模組只使用 Python 標準庫，無需安裝額外的包。

## 📝 更多信息

請查看 [docs/](docs/) 目錄中的詳細文檔。

