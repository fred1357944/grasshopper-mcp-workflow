# 處理多個同名組件的指南

## 問題說明

在 Grasshopper 中，可能會有多個組件具有相同的名稱（例如來自不同的插件或庫）。當使用 `add_component` 命令時，如果只提供組件名稱，系統可能會無法確定要創建哪一個組件。

## 解決方案

### 1. 使用 GUID（最可靠的方式）

每個 Grasshopper 組件都有一個唯一的 GUID。如果知道組件的 GUID，可以直接使用它來唯一標識組件。

**JSON 格式：**
```json
{
  "type": "add_component",
  "parameters": {
    "type": "Number Slider",
    "x": 100.0,
    "y": 200.0,
    "guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

**Python 調用：**
```python
add_component(
    component_type="Number Slider",
    x=100.0,
    y=200.0,
    guid="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
)
```

### 2. 使用 Category（類別）

如果組件屬於不同的類別，可以使用 `category` 參數來區分。

**JSON 格式：**
```json
{
  "type": "add_component",
  "parameters": {
    "type": "Point",
    "x": 100.0,
    "y": 200.0,
    "category": "Params"
  }
}
```

**Python 調用：**
```python
add_component(
    component_type="Point",
    x=100.0,
    y=200.0,
    category="Params"
)
```

常見的類別包括：
- `"Params"` - 參數組件
- `"Maths"` - 數學運算組件
- `"Vector"` - 向量組件
- `"Curve"` - 曲線組件
- `"Surface"` - 曲面組件

### 3. 使用 Library（庫/插件名稱）

如果組件來自不同的插件或庫，可以使用 `library` 參數來區分。

**JSON 格式：**
```json
{
  "type": "add_component",
  "parameters": {
    "type": "Custom Component",
    "x": 100.0,
    "y": 200.0,
    "library": "MyPlugin"
  }
}
```

**Python 調用：**
```python
add_component(
    component_type="Custom Component",
    x=100.0,
    y=200.0,
    library="MyPlugin"
)
```

### 4. 組合使用多個參數

可以同時使用多個參數來更精確地定位組件：

```json
{
  "type": "add_component",
  "parameters": {
    "type": "Number Slider",
    "x": 100.0,
    "y": 200.0,
    "category": "Params",
    "library": "Grasshopper"
  }
}
```

## 錯誤處理

### 情況 1：只有一個匹配

如果只有一個組件匹配名稱，系統會自動使用它，無需額外參數。

### 情況 2：多個匹配但未提供過濾參數

如果有多個同名組件，但沒有提供過濾參數，系統會**智能選擇**最合適的組件：

1. **優先排除廢棄的組件**：自動過濾掉標記為 Obsolete 或 Deprecated 的組件
2. **優先選擇原生內建組件**：如果有多個候選項，優先選擇來自 Grasshopper 原生庫的組件
3. **如果仍然有多個匹配**：選擇第一個（通常是最常用的）

如果智能選擇後仍然無法確定，系統會返回詳細的錯誤信息，包含：
- **組件名稱和 GUID**
- **類別和子類別**
- **庫名稱**（標記是否為 Built-in）
- **是否廢棄**（標記是否推薦使用）
- **組件描述**
- **輸入參數列表**（名稱、類型、描述）
- **輸出參數列表**（名稱、類型、描述）

示例錯誤信息：
```
Multiple components found with name 'Number Slider' (3 matches). 
Please specify additional parameters (guid, category, or library) to distinguish. 
Recommendation: Prefer non-obsolete, built-in components.
Available candidates:
  - Number Slider (GUID: a1b2c3d4-e5f6-7890-abcd-ef1234567890)
    Category: Params, SubCategory: Primitive
    Library: Grasshopper (Built-in - Recommended)
    Obsolete: No (Recommended)
    Description: Creates a slider for numeric input with adjustable range
    Inputs: (none)
    Outputs: N (Number)
  - Number Slider (GUID: b2c3d4e5-f6a7-8901-bcde-f12345678901)
    Category: Params, SubCategory: Primitive
    Library: CustomPlugin
    Obsolete: No (Recommended)
    Description: Enhanced slider with additional features
    Inputs: (none)
    Outputs: N (Number)
  - Number Slider (GUID: c3d4e5f6-a7b8-9012-cdef-123456789012)
    Category: Params, SubCategory: Legacy
    Library: OldPlugin
    Obsolete: Yes (Not Recommended)
    Description: Legacy slider component (deprecated)
    Inputs: (none)
    Outputs: N (Number)
```

### 情況 3：過濾後沒有匹配

如果提供的過濾參數無法匹配任何組件，系統會返回錯誤並列出所有候選項：

```
Multiple components found with name 'Number Slider' but none match the specified filters 
(category=WrongCategory, guid=, library=). 
Available candidates:
  - Number Slider (GUID: a1b2c3d4-e5f6-7890-abcd-ef1234567890, Category: Params, Library: Grasshopper)
  ...
```

## 智能選擇機制

系統會自動執行以下智能選擇邏輯（當沒有明確指定 GUID 時）：

1. **排除廢棄組件**：自動過濾掉標記為 Obsolete 或 Deprecated 的組件
2. **優先原生內建組件**：優先選擇來自 Grasshopper 原生庫的組件，而不是第三方插件
3. **選擇第一個匹配**：如果仍然有多個候選項，選擇第一個（通常是最常用的）

這意味著在大多數情況下，**您只需要提供組件名稱**，系統會自動選擇最合適的組件。

## 最佳實踐

1. **優先使用 GUID**：如果知道組件的 GUID，這是最可靠的方式
2. **使用 Category**：如果組件屬於不同的類別，使用 category 參數
3. **信任智能選擇**：在大多數情況下，只提供組件名稱即可，系統會自動選擇未廢棄的原生內建組件
4. **檢查錯誤信息**：如果遇到多個匹配的錯誤，查看錯誤信息中列出的候選項，特別注意：
   - **Built-in (Recommended)**：原生內建組件，優先使用
   - **Obsolete: No (Recommended)**：未廢棄的組件，優先使用
   - **Obsolete: Yes (Not Recommended)**：廢棄的組件，避免使用
   - **輸入輸出參數**：幫助判斷組件是否符合需求
5. **測試簡單名稱**：首先嘗試只使用組件名稱，如果只有一個匹配，系統會自動處理

## 示例場景

### 場景 1：標準組件（無重複）

```json
{
  "type": "add_component",
  "parameters": {
    "type": "Circle",
    "x": 100.0,
    "y": 200.0
  }
}
```
✅ 正常工作，因為只有一個 "Circle" 組件

### 場景 2：多個同名組件

假設有兩個 "Custom Point" 組件，一個來自 "PluginA"，一個來自 "PluginB"：

```json
{
  "type": "add_component",
  "parameters": {
    "type": "Custom Point",
    "x": 100.0,
    "y": 200.0,
    "library": "PluginA"
  }
}
```
✅ 使用 library 參數區分

或者使用 GUID：

```json
{
  "type": "add_component",
  "parameters": {
    "type": "Custom Point",
    "x": 100.0,
    "y": 200.0,
    "guid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```
✅ 使用 GUID 精確指定

