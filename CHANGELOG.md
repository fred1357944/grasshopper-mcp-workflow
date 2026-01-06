# Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.2.0] - 2026-01-06

### Added
- **Gemini API Mode**: `gemini_caller.py` now supports dual-mode architecture
  - Auto-detection: Uses API if `GEMINI_API_KEY` exists, else falls back to CLI
  - API mode enables: structured JSON outputs, token tracking, semantic convergence
  - New methods: `analyze_design()`, `calculate_convergence()`, `review_proposal()`
- **Security**: `.env.example` template for secure API key configuration
- **LangGraph Integration**: Complete workflow orchestration module
  - Option A: Iterative Design Optimization (Claude-Gemini alternating)
  - Option B: Multi-Variant Exploration (parallel generation)
  - FileCheckpointer for state persistence
  - Human-in-the-loop decision points

### Changed
- `.gitignore` updated to exclude `.env`, `settings.local.json`, `*.local.md`

### Security
- API keys stored in `.env` (never committed)
- Machine-specific settings excluded from version control

---

## [0.1.0] - 2026-01-06

### Added
- Initial release of Grasshopper MCP Workflow
- Core MCP server integration for Grasshopper
- MMD parser for `component_info.mmd` and `part_info.mmd`
- Placement info generator
- Multi-AI Optimizer Plugin structure
- Documentation: Usage guides, design docs

---

## Quick Reference

### Environment Setup
```bash
# Copy template and add your API key
cp .env.example .env
# Edit .env with your GEMINI_API_KEY
```

### Using Gemini Caller
```python
from gemini_caller import GeminiCaller

# Auto-detect mode
caller = GeminiCaller()  # Uses API if key exists

# Force specific mode
caller = GeminiCaller(mode="api")
caller = GeminiCaller(mode="cli")

# Advanced API features
result = caller.analyze_design(design_text, criteria=["structure", "efficiency"])
convergence = caller.calculate_convergence(proposals_list)
```

### Key Files
| File | Purpose |
|------|---------|
| `.env` | Your API keys (local only) |
| `.env.example` | Template for new developers |
| `gemini_caller.py` | Dual-mode Gemini integration |
| `docs/LANGGRAPH_USAGE_GUIDE.md` | Full workflow documentation |
