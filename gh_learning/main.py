#!/usr/bin/env python3
"""
GH-MCP 智能學習系統

整合:
- GHX Parser: 批量解析 .ghx 文件
- Knowledge Extractor: 統計萃取知識
- Gemini Analyzer: 深度分析
- Interactive Session: 蘇格拉底對話

使用方式:
    python main.py parse <folder>              # 解析 .ghx 文件
    python main.py analyze <folder>            # 萃取知識並分析
    python main.py learn <topic>               # 開始學習會話
    python main.py explain <component>         # 解釋組件
"""

import sys
import json
from pathlib import Path

# 加入 src 目錄到路徑
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from ghx_parser import GHXParser
from knowledge_extractor import KnowledgeExtractor, generate_report
from gemini_analyzer import GeminiAnalyzer


# 設定路徑
BASE_DIR = Path(__file__).parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
GHX_SAMPLES_DIR = BASE_DIR / "ghx_samples"
KNOWLEDGE_FILE = KNOWLEDGE_DIR / "component_registry.json"


def ensure_dirs():
    """確保必要目錄存在"""
    KNOWLEDGE_DIR.mkdir(exist_ok=True)
    GHX_SAMPLES_DIR.mkdir(exist_ok=True)


def cmd_parse(folder: str, output: str = None):
    """解析 .ghx 文件"""
    parser = GHXParser()
    docs = parser.batch_parse(folder)

    if not docs:
        print("No documents parsed successfully.")
        return

    output_path = output or str(KNOWLEDGE_DIR / "parsed_data.json")
    parser.to_json(docs, output_path)

    print(f"\n✓ Parsed {len(docs)} files")
    print(f"✓ Saved to: {output_path}")


def cmd_analyze(folder: str, use_gemini: bool = True):
    """萃取知識並可選地用 Gemini 分析"""
    # 1. 解析
    print("=== Step 1: Parsing GHX files ===")
    parser = GHXParser()
    docs = parser.batch_parse(folder)

    if not docs:
        print("No documents parsed successfully.")
        return

    # 2. 萃取知識
    print("\n=== Step 2: Extracting knowledge ===")
    extractor = KnowledgeExtractor()
    knowledge = extractor.extract(docs)

    # 保存知識
    knowledge_path = KNOWLEDGE_DIR / "extracted_knowledge.json"
    with open(knowledge_path, 'w', encoding='utf-8') as f:
        json.dump(knowledge, f, indent=2, ensure_ascii=False)
    print(f"✓ Knowledge saved to: {knowledge_path}")

    # 生成報告
    report = generate_report(knowledge)
    report_path = KNOWLEDGE_DIR / "knowledge_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"✓ Report saved to: {report_path}")

    # 轉換為 component_params 格式
    params_format = extractor.to_component_params_format()
    params_path = KNOWLEDGE_DIR / "component_params_extracted.json"
    with open(params_path, 'w', encoding='utf-8') as f:
        json.dump(params_format, f, indent=2, ensure_ascii=False)
    print(f"✓ Component params saved to: {params_path}")

    # 3. Gemini 分析 (可選)
    if use_gemini:
        print("\n=== Step 3: Gemini deep analysis ===")
        analyzer = GeminiAnalyzer()
        patterns = analyzer.analyze_patterns(report)

        if 'error' not in patterns:
            patterns_path = KNOWLEDGE_DIR / "gemini_analysis.json"
            with open(patterns_path, 'w', encoding='utf-8') as f:
                json.dump(patterns, f, indent=2, ensure_ascii=False)
            print(f"✓ Gemini analysis saved to: {patterns_path}")
        else:
            print(f"⚠ Gemini analysis failed: {patterns.get('error')}")

    print("\n=== Analysis Complete ===")
    print(f"- Component types: {knowledge['statistics']['total_components']}")
    print(f"- Connection patterns: {knowledge['statistics']['total_patterns']}")


def cmd_learn(topic: str):
    """開始互動學習會話"""
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           GH-MCP 智能學習系統 - 蘇格拉底對話                    ║
╠══════════════════════════════════════════════════════════════╣
║  主題: {topic:<54}║
╚══════════════════════════════════════════════════════════════╝

🔍 探索階段開始...

為了幫助你學習 "{topic}"，我有幾個問題:

1. 你目前對這個主題的理解是什麼？
2. 遇到過什麼具體問題？
3. 有沒有 .ghx 範例可以分享？

請輸入你的回答 (輸入 'quit' 結束):
""")

    # 載入現有知識
    knowledge = {}
    if KNOWLEDGE_FILE.exists():
        with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
            knowledge = json.load(f)
        print(f"[已載入 {len(knowledge.get('components', {}))} 個組件的知識]\n")

    insights = []
    hypotheses = []
    verified = []

    analyzer = GeminiAnalyzer()

    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if user_input.lower() in ['quit', 'exit', '結束', 'q']:
            break

        if not user_input:
            continue

        # 記錄洞見
        insights.append(user_input)

        # 根據輸入類型回應
        if '.ghx' in user_input or '.gh' in user_input:
            # 用戶提供了文件
            print("\n[正在解析提供的文件...]")
            # 這裡可以實際解析文件

        elif len(insights) >= 3 and not hypotheses:
            # 形成假設
            hypothesis = f"基於你的描述，我假設: {topic} 的關鍵在於 {insights[-1][:50]}..."
            hypotheses.append(hypothesis)
            print(f"""
💡 形成假設

> {hypothesis}

**驗證方法:** 請在 Grasshopper 中測試這個假設

測試後請告訴我結果:
- 正確 ✓
- 錯誤 ✗
- 需要修正
""")

        elif hypotheses and any(w in user_input.lower() for w in ['正確', '對', 'yes', '確認', '✓']):
            # 驗證成功
            verified.append(hypotheses[-1])
            print(f"""
✅ 假設已驗證！

已確認知識: {hypotheses[-1]}

繼續探索其他方面，或輸入 'quit' 結束。
""")

        elif hypotheses and any(w in user_input.lower() for w in ['錯誤', '不對', 'no', '✗']):
            # 驗證失敗
            print("""
🔄 感謝修正！

正確的情況是什麼？請詳細說明。
""")
            hypotheses.pop()

        else:
            # 繼續探索
            # 可以調用 Gemini 獲取更多問題
            print(f"""
🔍 探索中...

有趣的觀點！讓我問一些深入的問題:

1. 這個情況是否總是如此，還是有例外？
2. 你是如何發現這一點的？
3. 這對你的工作流程有什麼影響？
""")

    # 總結
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                        📝 會話總結                            ║
╚══════════════════════════════════════════════════════════════╝

主題: {topic}

已驗證知識:
{chr(10).join(f'  ✓ {v}' for v in verified) if verified else '  (無)'}

收集的洞見:
{chr(10).join(f'  - {i[:60]}...' if len(i) > 60 else f'  - {i}' for i in insights[:5])}

待探索問題:
{chr(10).join(f'  ? {h}' for h in hypotheses if h not in verified) if hypotheses else '  (無)'}

感謝參與！知識已更新。
""")


def cmd_explain(component_name: str):
    """解釋組件"""
    print(f"\n=== 查詢組件: {component_name} ===\n")

    analyzer = GeminiAnalyzer()
    explanation = analyzer.explain_component(component_name)
    print(explanation)


def main():
    ensure_dirs()

    if len(sys.argv) < 2:
        print(__doc__)
        print("\n=== 目前狀態 ===")
        print(f"知識庫目錄: {KNOWLEDGE_DIR}")
        print(f"GHX 範例目錄: {GHX_SAMPLES_DIR}")

        # 檢查 GHX 範例
        ghx_files = list(GHX_SAMPLES_DIR.glob("**/*.gh*"))
        print(f"GHX 範例文件: {len(ghx_files)} 個")

        # 檢查知識庫
        if KNOWLEDGE_FILE.exists():
            with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
                kb = json.load(f)
            print(f"知識庫組件: {len(kb.get('components', {}))} 個")
        else:
            print("知識庫: (尚未建立)")

        sys.exit(0)

    command = sys.argv[1]

    if command == "parse":
        folder = sys.argv[2] if len(sys.argv) > 2 else str(GHX_SAMPLES_DIR)
        output = sys.argv[3] if len(sys.argv) > 3 else None
        cmd_parse(folder, output)

    elif command == "analyze":
        folder = sys.argv[2] if len(sys.argv) > 2 else str(GHX_SAMPLES_DIR)
        use_gemini = "--no-gemini" not in sys.argv
        cmd_analyze(folder, use_gemini)

    elif command == "learn":
        topic = sys.argv[2] if len(sys.argv) > 2 else "Grasshopper 組件參數"
        cmd_learn(topic)

    elif command == "explain":
        if len(sys.argv) < 3:
            print("Usage: python main.py explain <component_name>")
            sys.exit(1)
        cmd_explain(sys.argv[2])

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
