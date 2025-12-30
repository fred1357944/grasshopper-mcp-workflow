# OpenSkills 使用指南

## 📖 什麼是 OpenSkills？

OpenSkills 是一個用於 AI 編碼代理的通用技能載入器，可以管理與 Claude Code、Cursor、Windsurf 等 AI 代理一起使用的技能（skills）。

參考資料：[OpenSkills GitHub](https://github.com/numman-ali/openskills)

## 🚀 快速開始

### 1. 安裝技能（從 Anthropic 官方技能庫）

```powershell
# 臨時添加 npm 路徑（如果 PATH 未更新）
$npmPath = npm config get prefix
$env:PATH += ";$npmPath"

# 安裝到項目目錄（推薦）
openskills install anthropics/skills

# 或全局安裝（所有項目共享）
openskills install anthropics/skills --global
```

### 2. 查看已安裝的技能

```powershell
openskills list
```

### 3. 同步到 AGENTS.md

安裝技能後，需要同步到 `AGENTS.md` 文件：

```powershell
# 交互式同步（推薦）
openskills sync

# 非交互式同步（用於腳本）
openskills sync -y

# 同步到自定義文件
openskills sync --output .ruler/AGENTS.md
```

## 📚 主要命令

### `openskills install <source>`

安裝技能從各種來源：

```powershell
# 從 GitHub 安裝
openskills install anthropics/skills
openskills install username/repo-name

# 從本地路徑安裝
openskills install ./local-skills/my-skill
openskills install C:\path\to\skill

# 從私有 Git 倉庫安裝
openskills install git@github.com:your-org/private-skills.git

# 全局安裝
openskills install anthropics/skills --global

# 通用模式（多代理環境）
openskills install anthropics/skills --universal
```

**選項：**
- `-g, --global` - 全局安裝到 `~/.claude/skills`
- `-u, --universal` - 安裝到 `.agent/skills/`（適用於多代理環境）
- `-y, --yes` - 跳過交互式選擇，安裝所有找到的技能

### `openskills sync [options]`

更新 AGENTS.md 文件：

```powershell
# 同步到默認 AGENTS.md
openskills sync

# 同步到自定義文件
openskills sync --output .ruler/AGENTS.md

# 非交互模式
openskills sync -y
```

**選項：**
- `-y, --yes` - 跳過所有提示
- `-o, --output <path>` - 自定義輸出文件

### `openskills list`

列出所有已安裝的技能：

```powershell
openskills list
```

### `openskills read <skill-name>`

讀取技能內容（供 AI 代理使用）：

```powershell
openskills read pdf
openskills read xlsx
```

### `openskills manage`

交互式管理（移除）已安裝的技能：

```powershell
openskills manage
```

### `openskills remove <skill-name>`

移除特定技能：

```powershell
openskills remove pdf
```

## 🎯 可用的技能範例

從 Anthropic 官方技能庫可以安裝：

- **xlsx** — 試算表創建、編輯、公式、數據分析
- **docx** — 文檔創建（含追蹤變更和註釋）
- **pdf** — PDF 操作（提取、合併、分割、表單）
- **pptx** — 簡報創建和編輯
- **canvas-design** — 創建海報和視覺設計
- **mcp-builder** — 構建 Model Context Protocol 服務器
- **skill-creator** — 創建技能的詳細指南

瀏覽所有技能：[github.com/anthropics/skills](https://github.com/anthropics/skills)

## 📁 安裝位置

### 項目級安裝（默認）

```
./.claude/skills/          # 項目專用（會被 gitignore）
```

### 全局安裝

```
~/.claude/skills/          # 所有項目共享
```

### 通用模式

```
./.agent/skills/           # 適用於多代理環境
~/.agent/skills/           # 全局通用模式
```

**優先級順序：**
1. `./.agent/skills/` (項目通用)
2. `~/.agent/skills/` (全局通用)
3. `./.claude/skills/` (項目)
4. `~/.claude/skills/` (全局)

## 🔧 完整使用流程範例

### 範例 1：安裝 PDF 處理技能

```powershell
# 1. 添加 npm 路徑（如果 PATH 未更新）
$npmPath = npm config get prefix
$env:PATH += ";$npmPath"

# 2. 安裝技能
openskills install anthropics/skills

# 3. 在交互界面中選擇要安裝的技能（例如：pdf）

# 4. 同步到 AGENTS.md
openskills sync

# 5. 查看已安裝的技能
openskills list

# 6. 讀取技能內容
openskills read pdf
```

### 範例 2：從本地路徑安裝自定義技能

```powershell
# 1. 安裝本地技能
openskills install ./my-custom-skills/pdf-handler

# 2. 同步
openskills sync

# 3. 驗證
openskills list
```

## 🛠️ 故障排除

### 問題：`openskills` 命令無法識別

**解決方案：**

```powershell
# 方法 1：臨時添加到 PATH
$npmPath = npm config get prefix
$env:PATH += ";$npmPath"

# 方法 2：使用 npx
npx openskills install anthropics/skills

# 方法 3：永久添加到 PATH
$npmPath = npm config get prefix
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$npmPath", "User")
# 然後重新啟動 PowerShell
```

### 問題：技能安裝後無法使用

**檢查步驟：**

1. 確認技能已安裝：
   ```powershell
   openskills list
   ```

2. 確認已同步到 AGENTS.md：
   ```powershell
   openskills sync
   ```

3. 檢查 AGENTS.md 文件是否包含技能定義

## 📝 創建自己的技能

### 最小結構

```
my-skill/
└── SKILL.md
    ---
    name: my-skill
    description: What this does and when to use it
    ---

    # Instructions in imperative form

    When the user asks you to X, do Y...
```

### 帶資源的技能

```
my-skill/
├── SKILL.md
├── references/
│   └── api-docs.md      # 支持文檔
├── scripts/
│   └── process.py       # 輔助腳本
└── assets/
    └── template.json    # 模板、配置
```

### 發布技能

1. 推送到 GitHub：`your-username/my-skill`
2. 用戶安裝：`openskills install your-username/my-skill`

## 🔗 相關資源

- [OpenSkills GitHub 倉庫](https://github.com/numman-ali/openskills)
- [Anthropic Skills 倉庫](https://github.com/anthropics/skills)
- [OpenSkills 文檔](https://github.com/numman-ali/openskills#readme)

## 💡 提示

1. **使用項目級安裝**：默認情況下，技能安裝到項目目錄，不會影響其他項目
2. **定期同步**：安裝新技能後記得運行 `openskills sync`
3. **交互式界面**：大多數命令都有漂亮的 TUI 界面，方便選擇
4. **技能優先級**：如果多個位置有同名技能，優先級最高的會被使用

