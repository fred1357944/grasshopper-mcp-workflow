#!/usr/bin/env python3
"""
智能部署腳本 - Smart Deploy Script

整合三層防護機制的完整部署流程：
1. 載入配置
2. Smart Resolver 解析缺失 GUID
3. Registry 驗證和自動修正
4. 部署到 Grasshopper

使用方式：
    python scripts/smart_deploy.py GH_WIP/placement_info.json

2026-01-23
"""

import json
import sys
import time
from pathlib import Path

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from grasshopper_mcp.client_optimized import GH_MCP_ClientOptimized
from grasshopper_mcp.guid_registry import GUIDRegistry
from grasshopper_mcp.smart_resolver import SmartResolver


def smart_deploy(
    config_path: str,
    clear_canvas: bool = True,
    interactive: bool = True,
    dry_run: bool = False
) -> bool:
    """
    智能部署流程

    Args:
        config_path: placement_info.json 路徑
        clear_canvas: 是否清空畫布
        interactive: 是否啟用互動模式（詢問用戶）
        dry_run: 只驗證不部署

    Returns:
        是否成功
    """
    print(f"\n{'='*60}")
    print(f"GH_MCP 智能部署系統 v0.2.0")
    print(f"{'='*60}\n")

    # === Phase 1: 載入配置 ===
    print("【Phase 1: 載入配置】")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    meta = config.get('_meta', {})
    print(f"   專案: {meta.get('project', 'unknown')}")
    print(f"   組件: {meta.get('component_count', len(config.get('components', [])))} 個")
    print(f"   連接: {meta.get('connection_count', len(config.get('connections', [])))} 條")

    # === Phase 2: Smart Resolver ===
    print("\n【Phase 2: 智能組件解析】")
    resolver = SmartResolver(interactive=interactive)

    # 統計缺少 GUID 的組件
    missing_guid = [
        c for c in config.get('components', [])
        if c.get('type') != 'Number Slider' and not c.get('guid')
    ]

    if missing_guid:
        print(f"   發現 {len(missing_guid)} 個組件缺少 GUID，開始解析...\n")
        config = resolver.resolve_placement_info(config)
        resolver.print_summary()
    else:
        print("   ✓ 所有組件都已有 GUID")

    # === Phase 3: Registry 驗證 ===
    print("\n【Phase 3: GUID Registry 驗證】")
    registry = GUIDRegistry()
    issues = registry.validate_placement_info(config)

    if issues:
        print(f"   ⚠️ 發現 {len(issues)} 個潛在問題:")
        for issue in issues[:5]:
            print(f"      • {issue['message']}")
        if len(issues) > 5:
            print(f"      ... 還有 {len(issues) - 5} 個")

        print("\n   自動修正中...")
        config = registry.auto_fix_placement_info(config)
        print("   ✓ 已自動修正")
    else:
        print("   ✓ 驗證通過")

    # Dry run 模式
    if dry_run:
        print(f"\n{'='*60}")
        print("🔍 Dry Run 模式 - 只驗證不部署")
        print(f"{'='*60}\n")

        # 輸出修正後的配置
        output_path = config_path.replace('.json', '_validated.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"   已輸出驗證後配置: {output_path}")
        return True

    # === Phase 4: 連接測試 ===
    print("\n【Phase 4: 連接 GH_MCP】")
    client = GH_MCP_ClientOptimized(debug=True)

    if not client.test_connection():
        print("   ❌ 無法連接到 GH_MCP")
        print("   請確認 Grasshopper 已啟動且 GH_MCP 插件已載入")
        return False

    print("   ✓ 連接成功")

    # === Phase 5: 清空畫布 ===
    if clear_canvas:
        print("\n【Phase 5: 清空畫布】")
        client.clear_canvas()
        time.sleep(0.3)
        print("   ✓ 畫布已清空")

    # === Phase 6: 創建組件 ===
    print("\n【Phase 6: 創建組件】")
    components = config.get('components', [])
    trusted_guids = config.get('trusted_guids', {})

    created = 0
    failed = 0

    for comp in components:
        comp_id = comp.get('id')
        comp_type = comp.get('type')
        x = comp.get('x', 0)
        y = comp.get('y', 0)
        guid = comp.get('guid') or trusted_guids.get(comp_type)

        col = int(x / client.COL_WIDTH)
        row = int(y / client.ROW_HEIGHT)
        track_name = comp_id

        if comp_type == 'Number Slider':
            value = comp.get('value', 0)
            min_val = comp.get('min', 0)
            max_val = comp.get('max', 100)

            result = client.add_slider(
                nickname=track_name,
                col=col,
                row=row,
                value=value,
                min_val=min_val,
                max_val=max_val
            )
        else:
            if guid:
                result = client.add_component(
                    comp_type=comp_type,
                    nickname=track_name,
                    col=col,
                    row=row,
                    guid=guid
                )
            else:
                # 最後才讓 GH_MCP 自動搜索
                result = client.add_component(
                    comp_type=comp_type,
                    nickname=track_name,
                    col=col,
                    row=row
                )

        if result:
            created += 1
        else:
            failed += 1
            print(f"   ❌ 失敗: {comp_id} ({comp_type})")

        time.sleep(0.05)

    print(f"\n   組件創建: {created} 成功, {failed} 失敗")

    # === Phase 7: 建立連接 ===
    print("\n【Phase 7: 建立連接】")
    connections = config.get('connections', [])

    conn_tuples = [
        (c.get('from'), c.get('fromParam'), c.get('to'), c.get('toParam'))
        for c in connections
    ]

    success, fail, failed_list = client.smart_connect_batch(conn_tuples)
    print(f"\n   連接完成: {success} 成功, {fail} 失敗")

    if failed_list:
        print(f"\n   失敗的連接:")
        for fc in failed_list[:10]:
            print(f"      - {fc['from']} → {fc['to']}")

    # === 摘要 ===
    client.print_summary()

    print(f"\n{'='*60}")
    if fail == 0 and failed == 0:
        print("✅ 部署完成！所有組件和連接都成功建立")
    else:
        print(f"⚠️ 部署完成，但有 {failed} 個組件和 {fail} 個連接失敗")
    print(f"{'='*60}\n")

    return fail == 0 and failed == 0


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='GH_MCP 智能部署系統',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python scripts/smart_deploy.py GH_WIP/placement_info.json
    python scripts/smart_deploy.py GH_WIP/placement_info.json --dry-run
    python scripts/smart_deploy.py GH_WIP/placement_info.json --no-clear --non-interactive
        """
    )
    parser.add_argument('config', help='placement_info.json 路徑')
    parser.add_argument('--no-clear', action='store_true', help='不清空畫布')
    parser.add_argument('--non-interactive', action='store_true', help='非互動模式（不詢問用戶）')
    parser.add_argument('--dry-run', action='store_true', help='只驗證不部署')

    args = parser.parse_args()

    success = smart_deploy(
        args.config,
        clear_canvas=not args.no_clear,
        interactive=not args.non_interactive,
        dry_run=args.dry_run
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
