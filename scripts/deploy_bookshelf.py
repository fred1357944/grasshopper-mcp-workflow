#!/usr/bin/env python3
"""
工業風書架部署腳本
Industrial Bookshelf Deployment Script

從 GH_WIP/placement_info.json 讀取配置，部署到 Grasshopper

2026-01-23 - 增加 GUID Registry 驗證
"""

import json
import sys
import time
from pathlib import Path

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from grasshopper_mcp.client_optimized import GH_MCP_ClientOptimized
from grasshopper_mcp.guid_registry import GUIDRegistry


def load_placement_info(path: str) -> dict:
    """載入 placement_info.json"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_and_fix_config(config: dict, registry: GUIDRegistry) -> dict:
    """
    驗證並自動修正配置

    1. 檢查 GUID 是否正確
    2. 修正參數名縮寫
    """
    issues = registry.validate_placement_info(config)

    if issues:
        print(f"\n⚠️ 發現 {len(issues)} 個潛在問題，自動修正中...")
        for issue in issues[:5]:
            print(f"   • {issue['message']}")

        config = registry.auto_fix_placement_info(config)
        print("   ✓ 已自動修正\n")

    return config


def deploy_bookshelf(clear_canvas: bool = True, auto_fix: bool = True):
    """
    部署工業風書架到 Grasshopper

    Args:
        clear_canvas: 是否清空畫布後再部署
        auto_fix: 是否自動修正配置問題
    """
    # 載入配置
    config_path = Path(__file__).parent.parent / 'GH_WIP' / 'placement_info.json'
    config = load_placement_info(str(config_path))

    # 初始化 GUID Registry
    registry = GUIDRegistry()

    # 驗證並修正配置
    if auto_fix:
        config = validate_and_fix_config(config, registry)

    meta = config.get('_meta', {})
    print(f"\n{'='*60}")
    print(f"工業風書架部署")
    print(f"{'='*60}")
    print(f"專案: {meta.get('project', 'unknown')}")
    print(f"描述: {meta.get('description', '')}")
    print(f"組件: {meta.get('component_count', 0)} 個")
    print(f"連接: {meta.get('connection_count', 0)} 條")
    print(f"{'='*60}\n")

    # 創建客戶端
    client = GH_MCP_ClientOptimized(debug=True)

    # 測試連接
    print("【Phase 1: 連接測試】")
    if not client.test_connection():
        print("❌ 無法連接到 GH_MCP，請確認 Grasshopper 已啟動")
        return False

    # 清空畫布
    if clear_canvas:
        print("\n【Phase 2: 清空畫布】")
        client.clear_canvas()
        time.sleep(0.3)

    # 創建組件
    print("\n【Phase 3: 創建組件】")
    components = config.get('components', [])
    trusted_guids = config.get('trusted_guids', {})

    created = 0
    failed = 0

    for comp in components:
        comp_id = comp.get('id')
        comp_type = comp.get('type')
        nickname = comp.get('nickname', comp_id)
        x = comp.get('x', 0)
        y = comp.get('y', 0)
        guid = comp.get('guid') or trusted_guids.get(comp_type)

        # 計算 col, row (從絕對座標反推)
        col = int(x / client.COL_WIDTH)
        row = int(y / client.ROW_HEIGHT)

        # 使用 comp_id 作為內部追蹤鍵 (連接時使用)
        track_name = comp_id

        if comp_type == 'Number Slider':
            value = comp.get('value', 0)
            min_val = comp.get('min', 0)
            max_val = comp.get('max', 100)

            result = client.add_slider(
                nickname=track_name,  # 用 ID 追蹤
                col=col,
                row=row,
                value=value,
                min_val=min_val,
                max_val=max_val
            )
        else:
            # 優先使用配置中的 GUID（已經過 Registry 驗證）
            if guid:
                result = client.add_component(
                    comp_type=comp_type,
                    nickname=track_name,
                    col=col,
                    row=row,
                    guid=guid  # 使用驗證過的 GUID
                )
            else:
                # 沒有 GUID 時，用 Registry 查詢
                verified_guid = registry.get_guid(comp_type)
                if verified_guid:
                    result = client.add_component(
                        comp_type=comp_type,
                        nickname=track_name,
                        col=col,
                        row=row,
                        guid=verified_guid
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

        # 小延遲避免過載
        time.sleep(0.05)

    print(f"\n   組件創建完成: {created} 成功, {failed} 失敗")

    # 建立連接
    print("\n【Phase 4: 建立連接】")
    connections = config.get('connections', [])

    # 轉換格式
    conn_tuples = []
    for conn in connections:
        from_nick = conn.get('from')
        from_param = conn.get('fromParam')
        to_nick = conn.get('to')
        to_param = conn.get('toParam')
        conn_tuples.append((from_nick, from_param, to_nick, to_param))

    # 使用智能連接 (自動嘗試參數別名)
    success, fail, failed_list = client.smart_connect_batch(conn_tuples)

    print(f"\n   連接完成: {success} 成功, {fail} 失敗")

    # 顯示失敗的連接
    if failed_list:
        print(f"\n   失敗的連接:")
        for fc in failed_list[:10]:  # 最多顯示 10 個
            print(f"      - {fc['from']} → {fc['to']}")

    # 打印摘要
    client.print_summary()

    # 最終狀態
    print(f"\n{'='*60}")
    if fail == 0 and failed == 0:
        print("✅ 部署完成！所有組件和連接都成功建立")
    else:
        print(f"⚠️ 部署完成，但有 {failed} 個組件和 {fail} 個連接失敗")
    print(f"{'='*60}\n")

    return fail == 0 and failed == 0


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='部署工業風書架到 Grasshopper')
    parser.add_argument('--no-clear', action='store_true', help='不清空畫布')
    args = parser.parse_args()

    success = deploy_bookshelf(clear_canvas=not args.no_clear)
    sys.exit(0 if success else 1)
