# Grasshopper Tools - 頂層目錄說明

## 📁 目錄位置

`grasshopper_tools` 現在位於**項目頂層目錄**，可以直接作為 Python 模組使用。

```
grasshopper-mcp-master/
├── grasshopper_tools/          # ← 頂層目錄（可直接導入）
│   ├── __init__.py
│   ├── client.py
│   ├── component_manager.py
│   ├── connection_manager.py
│   ├── parameter_setter.py
│   ├── group_manager.py
│   ├── parser_utils.py
│   ├── placement_executor.py
│   ├── utils.py
│   ├── cli.py
│   ├── example_usage.py
│   ├── README.md
│   ├── 工具使用指南.md
│   ├── CLI使用說明.md
│   └── 快速使用指南.md
├── GH_WIP/
│   └── component_info.mmd
└── ...
```

## 🚀 使用方式

### 方式 1: 直接導入（推薦）

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

# 使用
client = GrasshopperClient()
comp_mgr = ComponentManager(client)
```

### 方式 2: 命令行使用

```bash
# 從項目根目錄
python -m grasshopper_tools.cli --help
python -m grasshopper_tools.cli execute-placement GH_WIP/placement_info.json

# 或使用快捷腳本
cd grasshopper_tools
python gh_cli.py --help
```

## 📦 依賴關係

### Python 標準庫
- `socket` - 網絡通信
- `json` - JSON 處理
- `threading` - 線程安全
- `concurrent.futures` - 並行執行
- `os`, `sys` - 系統操作
- `re` - 正則表達式
- `typing` - 類型提示

### 外部依賴
**無外部依賴** - 本模組只使用 Python 標準庫，無需安裝額外的包。

## 📚 文檔

所有文檔都在 `grasshopper_tools` 目錄內：

- **README.md** - 完整的使用說明和 API 文檔
- **工具使用指南.md** - 詳細的工具使用說明
- **CLI使用說明.md** - 命令行接口使用說明
- **快速使用指南.md** - 快速入門指南

## ⚙️ 配置

### 默認配置

- **Grasshopper MCP 服務器地址**: `localhost:8080`
- **組件 ID 映射文件**: 頂層目錄的 `component_id_map.json`
- **默認並行線程數**: 10

### 自定義配置

```python
# 自定義服務器地址
client = GrasshopperClient(host="192.168.1.100", port=8080)

# 自定義 ID 映射路徑
comp_mgr.save_id_map("custom_path/component_id_map.json")
```

## 🔧 路徑說明

### 組件 ID 映射文件

`component_id_map.json` 會保存在**頂層目錄**（與 `grasshopper_tools` 同級）。

### MMD 文件路徑

如果使用 `example_usage.py`，MMD 文件路徑會自動指向 `GH_WIP/component_info.mmd`。

## ✅ 驗證安裝

測試導入是否成功：

```bash
python -c "from grasshopper_tools import ComponentManager; print('✓ 導入成功')"
```

## 📝 注意事項

1. **頂層目錄**: `grasshopper_tools` 必須在項目頂層，才能正確導入
2. **路徑引用**: 所有相對路徑都基於頂層目錄
3. **ID 映射**: `component_id_map.json` 保存在頂層目錄
4. **文檔**: 所有使用說明都在 `grasshopper_tools` 目錄內

## 🔗 相關文件

- `grasshopper_tools/gh_cli.py` - 命令行快捷腳本
- `GH_WIP/component_info.mmd` - MMD 範例文件
- `GH_WIP/placement_info.json` - JSON 執行序列範例

