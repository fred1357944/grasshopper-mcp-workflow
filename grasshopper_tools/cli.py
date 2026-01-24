"""
Grasshopper Tools 命令行接口 (CLI)

提供命令行方式使用所有工具功能
"""

import argparse
import sys
import os
import json

# 添加當前目錄到路徑，以便導入模組
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 導入模組（使用相對導入）
try:
    from . import (
        GrasshopperClient,
        ComponentManager,
        ConnectionManager,
        ParameterSetter,
        GroupManager,
        MMDParser,
        JSONGenerator,
        PlacementExecutor,
        load_placement_info,
        update_guids_in_json,
        DEFAULT_GUID_MAP,
    )
except ImportError:
    # 如果相對導入失敗，嘗試絕對導入（當作為腳本直接運行時）
    try:
        from grasshopper_tools import (
            GrasshopperClient,
            ComponentManager,
            ConnectionManager,
            ParameterSetter,
            GroupManager,
            MMDParser,
            JSONGenerator,
            PlacementExecutor,
            load_placement_info,
            update_guids_in_json,
            DEFAULT_GUID_MAP,
        )
    except ImportError:
        # 最後嘗試：添加當前目錄的父目錄到路徑
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "grasshopper_tools",
            os.path.join(current_dir, "__init__.py")
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules["grasshopper_tools"] = module
            spec.loader.exec_module(module)
            # 動態導入模組屬性（mypy 無法正確推斷動態導入）
            GrasshopperClient = module.GrasshopperClient  # type: ignore
            ComponentManager = module.ComponentManager  # type: ignore
            ConnectionManager = module.ConnectionManager  # type: ignore
            ParameterSetter = module.ParameterSetter  # type: ignore
            GroupManager = module.GroupManager  # type: ignore
            MMDParser = module.MMDParser  # type: ignore
            JSONGenerator = module.JSONGenerator  # type: ignore
            PlacementExecutor = module.PlacementExecutor  # type: ignore
            load_placement_info = module.load_placement_info  # type: ignore
            update_guids_in_json = module.update_guids_in_json  # type: ignore
            DEFAULT_GUID_MAP = module.DEFAULT_GUID_MAP  # type: ignore
        else:
            raise ImportError("無法導入 grasshopper_tools 模組")


def cmd_execute_placement(args):
    """執行 placement_info.json"""
    executor = PlacementExecutor()
    result = executor.execute_placement_info(
        json_path=args.json_path,
        max_workers=args.max_workers,
        save_id_map=args.save_id_map,
        clear_first=args.clear_first,
        use_smart_layout=not args.no_smart_layout
    )

    if result["success"]:
        print("\n✓ 所有命令執行成功！")
        sys.exit(0)
    else:
        print("\n⚠️  部分命令失敗")
        sys.exit(1)


def cmd_parse_mmd(args):
    """解析 MMD 文件"""
    parser = MMDParser()
    
    if args.action == "components":
        components, connections = parser.parse_component_info_mmd(args.mmd_path)
        print(f"找到 {len(components)} 個組件")
        print(f"找到 {len(connections)} 個連接")
        
        if args.output:
            data = {
                "components": components,
                "connections": connections
            }
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"已保存到: {args.output}")
    
    elif args.action == "subgraphs":
        subgraphs = parser.parse_subgraphs_from_mmd(args.mmd_path)
        subgraph_names = parser.get_subgraph_names(args.mmd_path)
        
        print(f"找到 {len(subgraphs)} 個 subgraph:")
        for sg_id, comp_ids in subgraphs.items():
            sg_name = subgraph_names.get(sg_id, sg_id)
            print(f"  {sg_name}: {len(comp_ids)} 個組件")
        
        if args.output:
            data = {
                "subgraphs": {sg_id: comp_ids for sg_id, comp_ids in subgraphs.items()},
                "subgraph_names": subgraph_names
            }
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"已保存到: {args.output}")
    
    elif args.action == "sliders":
        sliders = parser.parse_slider_values(args.mmd_path)
        print(f"找到 {len(sliders)} 個 Number Slider:")
        for comp_id, info in sliders.items():
            print(f"  {comp_id}: {info['value']}")
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(sliders, f, indent=2, ensure_ascii=False)
            print(f"已保存到: {args.output}")


def cmd_generate_json(args):
    """生成 placement_info.json"""
    parser = MMDParser()
    components, connections = parser.parse_component_info_mmd(args.mmd_path)
    
    generator = JSONGenerator()
    placement_info = generator.generate_placement_info(
        components,
        connections,
        description=args.description
    )
    
    generator.save_placement_info(placement_info, args.output)
    print(f"已生成 {len(placement_info['commands'])} 個命令")


def cmd_update_guids(args):
    """更新 JSON 文件中的 GUID"""
    guid_map = DEFAULT_GUID_MAP
    if args.guid_map:
        with open(args.guid_map, 'r', encoding='utf-8') as f:
            guid_map = json.load(f)
    
    updated_count = update_guids_in_json(args.json_path, guid_map)
    print(f"總共更新了 {updated_count} 個 GUID")


def cmd_add_component(args):
    """創建組件"""
    comp_mgr = ComponentManager()
    component_id = comp_mgr.add_component(
        guid=args.guid,
        x=args.x,
        y=args.y,
        component_id=args.component_id
    )
    
    if component_id:
        print(f"✓ 組件創建成功，ID: {component_id}")
        if args.component_id:
            comp_mgr.save_id_map()
    else:
        print("✗ 組件創建失敗")
        sys.exit(1)


def cmd_delete_component(args):
    """刪除組件"""
    comp_mgr = ComponentManager()
    if comp_mgr.delete_component(args.component_id):
        print("✓ 組件刪除成功")
    else:
        print("✗ 組件刪除失敗")
        sys.exit(1)


def cmd_set_visibility(args):
    """設置組件可見性"""
    comp_mgr = ComponentManager()
    # 如果指定了 --visible，則 hidden = False；如果指定了 --hidden，則 hidden = True
    # 如果兩者都沒指定，默認為 False（顯示）
    hidden = args.hidden and not args.visible
    if comp_mgr.set_component_visibility(args.component_id, hidden):
        visibility_status = "隱藏" if hidden else "顯示"
        print(f"✓ 組件已設置為 {visibility_status}")
    else:
        print("✗ 設置組件可見性失敗")
        sys.exit(1)


def cmd_zoom_to_components(args):
    """縮放到指定組件"""
    comp_mgr = ComponentManager()
    # 處理組件 ID 列表（可以是逗號分隔的字符串或列表）
    if isinstance(args.component_ids, str):
        component_ids = [cid.strip() for cid in args.component_ids.split(',') if cid.strip()]
    else:
        component_ids = [str(cid).strip() for cid in args.component_ids if str(cid).strip()]
    
    if not component_ids:
        print("✗ 錯誤: 至少需要一個組件 ID")
        sys.exit(1)
    
    if comp_mgr.zoom_to_components(component_ids):
        print(f"✓ 已縮放到 {len(component_ids)} 個組件")
    else:
        print("✗ 縮放失敗")
        sys.exit(1)


def cmd_query_guid(args):
    """查詢組件 GUID"""
    comp_mgr = ComponentManager()
    result = comp_mgr.get_component_guid(args.component_name)
    
    if result:
        print(f"組件名稱: {result['name']}")
        print(f"GUID: {result['guid']}")
        print(f"類別: {result['category']}")
        print(f"內置組件: {result['isBuiltIn']}")
    else:
        print(f"✗ 未找到組件: {args.component_name}")
        sys.exit(1)


def cmd_connect_components(args):
    """連接組件"""
    comp_mgr = ComponentManager()
    conn_mgr = ConnectionManager(component_manager=comp_mgr)
    
    success = conn_mgr.connect_components(
        source_id="",
        target_id="",
        source_param=args.source_param,
        target_param=args.target_param,
        source_id_key=args.source_id,
        target_id_key=args.target_id
    )
    
    if success:
        print("✓ 連接成功")
    else:
        print("✗ 連接失敗")
        sys.exit(1)


def cmd_set_slider(args):
    """設置 Slider"""
    comp_mgr = ComponentManager()
    param_setter = ParameterSetter(component_manager=comp_mgr)
    
    success = param_setter.set_slider(
        component_id_key=args.component_id,
        value=args.value,
        min_value=args.min_value,
        max_value=args.max_value,
        rounding=args.rounding
    )
    
    if success:
        print("✓ Slider 設置成功")
    else:
        print("✗ Slider 設置失敗")
        sys.exit(1)


def cmd_auto_set_sliders(args):
    """自動設置所有 Slider（從 MMD 文件）"""
    from .utils import determine_slider_range
    import json
    from pathlib import Path
    
    # 文件路徑
    mmd_path = Path(args.mmd_path)
    id_map_path = Path(args.id_map) if args.id_map else Path("component_id_map.json")
    
    # 檢查文件是否存在
    if not mmd_path.exists():
        print(f"✗ 錯誤: 找不到文件 {mmd_path}")
        sys.exit(1)
    
    if not id_map_path.exists():
        print(f"✗ 錯誤: 找不到文件 {id_map_path}")
        print("   請先執行: python -m grasshopper_tools.cli execute-placement <placement_info.json>")
        sys.exit(1)
    
    print("=" * 80)
    print("自動設置 Slider 參數")
    print("=" * 80)
    print(f"\n讀取 MMD 文件: {mmd_path}")
    print(f"讀取 ID 映射: {id_map_path}")
    
    # 解析 MMD 文件
    sliders = MMDParser().parse_slider_values(str(mmd_path))
    
    if not sliders:
        print("\n⚠️  未找到任何 Number Slider 組件")
        sys.exit(0)
    
    print(f"\n找到 {len(sliders)} 個 Number Slider:")
    for comp_id, info in sliders.items():
        print(f"  - {comp_id}: {info['value']}")
    
    # 讀取 ID 映射
    with open(id_map_path, 'r', encoding='utf-8') as f:
        id_map = json.load(f)
    
    # 檢查所有 slider 是否都在映射中
    missing_ids = [comp_id for comp_id in sliders.keys() if comp_id not in id_map]
    if missing_ids:
        print("\n⚠️  警告: 以下組件 ID 在映射中不存在:")
        for comp_id in missing_ids:
            print(f"  - {comp_id}")
        print("\n將跳過這些組件")
    
    # 創建客戶端和管理器
    client = GrasshopperClient()
    comp_mgr = ComponentManager(client)
    comp_mgr.load_id_map(str(id_map_path))
    param_setter = ParameterSetter(client, comp_mgr)
    
    # 準備 slider 配置
    slider_configs = []
    for comp_id, info in sliders.items():
        if comp_id not in id_map:
            continue
        
        value = float(info['value'])
        min_val, max_val = determine_slider_range(comp_id, value)
        
        slider_configs.append((
            comp_id,      # component_id_key
            info['value'], # value
            min_val,      # min_value
            max_val,      # max_value
            0.1           # rounding
        ))
    
    if not slider_configs:
        print("\n⚠️  沒有可設置的 Slider")
        sys.exit(0)
    
    print(f"\n準備設置 {len(slider_configs)} 個 Slider...")
    print("\n" + "=" * 80)
    
    # 批量設置
    success_count, fail_count = param_setter.set_sliders_batch(slider_configs)
    
    print("\n" + "=" * 80)
    print("設置總結")
    print("=" * 80)
    print(f"成功: {success_count} 個")
    print(f"失敗: {fail_count} 個")
    
    if fail_count == 0:
        print("\n✓ 所有 Slider 設置成功！")
        sys.exit(0)
    else:
        print("\n⚠️  部分 Slider 設置失敗")
        sys.exit(1)


def cmd_set_vector(args):
    """設置 Vector XYZ"""
    comp_mgr = ComponentManager()
    param_setter = ParameterSetter(component_manager=comp_mgr)
    
    success = param_setter.set_vector_xyz(
        component_id_key=args.component_id,
        x=args.x,
        y=args.y,
        z=args.z
    )
    
    if success:
        print("✓ Vector XYZ 設置成功")
    else:
        print("✗ Vector XYZ 設置失敗")
        sys.exit(1)


def cmd_auto_group_components(args):
    """自動群組所有組件（從 MMD 文件）"""
    import json
    from pathlib import Path
    
    # 文件路徑
    mmd_path = Path(args.mmd_path)
    id_map_path = Path(args.id_map) if args.id_map else Path("component_id_map.json")
    
    # 檢查文件是否存在
    if not mmd_path.exists():
        print(f"✗ 錯誤: 找不到文件 {mmd_path}")
        sys.exit(1)
    
    if not id_map_path.exists():
        print(f"✗ 錯誤: 找不到文件 {id_map_path}")
        print("   請先執行: python -m grasshopper_tools.cli execute-placement <placement_info.json>")
        sys.exit(1)
    
    print("=" * 80)
    print("自動群組組件")
    print("=" * 80)
    print(f"\n讀取 MMD 文件: {mmd_path}")
    print(f"讀取 ID 映射: {id_map_path}")
    
    # 解析 MMD 文件
    subgraphs = MMDParser().parse_subgraphs_from_mmd(str(mmd_path))
    subgraph_names = MMDParser().get_subgraph_names(str(mmd_path))
    
    if not subgraphs:
        print("\n⚠️  未找到任何 subgraph")
        sys.exit(0)
    
    print(f"\n找到 {len(subgraphs)} 個 subgraph:")
    for sg_id, comp_ids in subgraphs.items():
        name = subgraph_names.get(sg_id, sg_id)
        print(f"  - {sg_id} ({name}): {len(comp_ids)} 個組件")
    
    # 讀取 ID 映射
    with open(id_map_path, 'r', encoding='utf-8') as f:
        id_map = json.load(f)
    
    # 檢查所有組件是否都在映射中
    missing_components = {}
    for sg_id, comp_ids in subgraphs.items():
        missing = [comp_id for comp_id in comp_ids if comp_id not in id_map]
        if missing:
            missing_components[sg_id] = missing
    
    if missing_components:
        print("\n⚠️  警告: 以下組件 ID 在映射中不存在:")
        for sg_id, missing in missing_components.items():
            print(f"  - {sg_id}: {len(missing)} 個組件缺失")
        print("\n將跳過這些組件")
    
    # 創建客戶端和管理器
    client = GrasshopperClient()
    comp_mgr = ComponentManager(client)
    comp_mgr.load_id_map(str(id_map_path))
    group_mgr = GroupManager(client, comp_mgr)
    
    # 顏色映射函數
    def get_subgraph_color(sg_id: str) -> tuple:
        color_map = {
            "TOP": (225, 245, 255),        # 淺藍色 - 桌面
            "LEG_BASE": (255, 244, 225),  # 淺橙色 - 桌腳基礎
            "LEG_PLANES": (232, 245, 233), # 淺綠色 - 桌腳位置平面
            "ORIENT_GROUP": (255, 235, 238), # 淺紅色 - Orient 複製組
        }
        for key, color in color_map.items():
            if key in sg_id:
                return color
        return (240, 240, 240)  # 默認淺灰色
    
    # 準備群組配置
    groups = []
    for sg_id, comp_ids in subgraphs.items():
        # 過濾掉不存在的組件
        valid_comp_ids = [comp_id for comp_id in comp_ids if comp_id in id_map]
        
        if not valid_comp_ids:
            print(f"\n⚠️  跳過 {sg_id}: 沒有有效的組件")
            continue
        
        name = subgraph_names.get(sg_id, sg_id)
        color = get_subgraph_color(sg_id)
        
        groups.append({
            "name": name,
            "componentIdKeys": valid_comp_ids,
            "color": color
        })
    
    if not groups:
        print("\n⚠️  沒有可創建的群組")
        sys.exit(0)
    
    print(f"\n準備創建 {len(groups)} 個群組...")
    print("\n" + "=" * 80)
    
    # 批量創建群組
    success_count, fail_count = group_mgr.group_components_batch(groups)
    
    print("\n" + "=" * 80)
    print("群組創建總結")
    print("=" * 80)
    print(f"成功: {success_count} 個")
    print(f"失敗: {fail_count} 個")
    
    if fail_count == 0:
        print("\n✓ 所有群組創建成功！")
        sys.exit(0)
    else:
        print("\n⚠️  部分群組創建失敗")
        sys.exit(1)


def cmd_group_components(args):
    """創建群組"""
    comp_mgr = ComponentManager()
    group_mgr = GroupManager(component_manager=comp_mgr)
    
    # 解析組件 ID 列表
    component_ids = args.component_ids.split(',') if args.component_ids else []
    
    # 處理顏色
    color = None
    if args.color:
        r, g, b = map(int, args.color.split(','))
        color = (r, g, b)
    
    success = group_mgr.group_components(
        component_ids=[],
        group_name=args.group_name,
        color=color,
        color_hex=args.color_hex,
        component_id_keys=component_ids
    )
    
    if success:
        print("✓ 群組創建成功")
    else:
        print("✗ 群組創建失敗")
        sys.exit(1)


def cmd_get_errors(args):
    """獲取文檔錯誤"""
    conn_mgr = ConnectionManager()
    errors = conn_mgr.get_document_errors()
    
    print(f"找到 {len(errors)} 個錯誤:")
    for i, error in enumerate(errors, 1):
        print(f"  {i}. {error}")
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump({"errors": errors}, f, indent=2, ensure_ascii=False)
        print(f"已保存到: {args.output}")


def cmd_execute_full_workflow(args):
    """執行完整工作流程：放置組件 -> 設置 Slider -> 群組組件 -> 檢查錯誤"""
    from pathlib import Path
    
    print("=" * 80)
    print("執行完整工作流程")
    print("=" * 80)
    
    # 文件路徑
    placement_json = Path(args.placement_json)
    mmd_path = Path(args.mmd_path) if args.mmd_path else Path("GH_WIP/component_info.mmd")
    id_map_path = Path(args.id_map) if args.id_map else Path("component_id_map.json")
    
    # 檢查文件是否存在
    if not placement_json.exists():
        print(f"✗ 錯誤: 找不到文件 {placement_json}")
        sys.exit(1)
    
    if not mmd_path.exists():
        print(f"✗ 錯誤: 找不到文件 {mmd_path}")
        sys.exit(1)
    
    all_success = True
    
    # 步驟 1: 清理文檔（可選）
    if args.clear_first:
        print("\n" + "=" * 80)
        print("步驟 0: 清理 Grasshopper 文檔")
        print("=" * 80)
        from .client import GrasshopperClient
        client = GrasshopperClient()
        response = client.send_command("clear_document", {})
        if response.get("success"):
            print("✓ 文檔已清理")
        else:
            print("⚠️  清理文檔失敗，繼續執行...")
    
    # 步驟 1: 執行 placement_info.json
    print("\n" + "=" * 80)
    print("步驟 1: 執行 placement_info.json（創建組件和連接）")
    print("=" * 80)
    executor = PlacementExecutor()
    result = executor.execute_placement_info(
        json_path=str(placement_json),
        max_workers=args.max_workers,
        save_id_map=True,
        id_map_path=str(id_map_path) if args.id_map else None
    )
    
    if not result["success"]:
        print("\n✗ 步驟 1 失敗，停止執行")
        sys.exit(1)
    
    # 步驟 2: 自動設置 Slider
    print("\n" + "=" * 80)
    print("步驟 2: 自動設置 Slider 參數")
    print("=" * 80)
    
    from .utils import determine_slider_range
    
    # 解析 MMD 文件
    sliders = MMDParser().parse_slider_values(str(mmd_path))
    
    if sliders:
        # 讀取 ID 映射
        if not id_map_path.exists():
            print(f"✗ 錯誤: 找不到 ID 映射文件 {id_map_path}")
            all_success = False
        else:
            with open(id_map_path, 'r', encoding='utf-8') as f:
                id_map = json.load(f)
            
            # 創建客戶端和管理器
            client = GrasshopperClient()
            comp_mgr = ComponentManager(client)
            comp_mgr.load_id_map(str(id_map_path))
            param_setter = ParameterSetter(client, comp_mgr)
            
            # 準備 slider 配置
            slider_configs = []
            for comp_id, info in sliders.items():
                if comp_id not in id_map:
                    continue
                
                value = float(info['value'])
                min_val, max_val = determine_slider_range(comp_id, value)
                
                slider_configs.append((
                    comp_id,
                    info['value'],
                    min_val,
                    max_val,
                    0.1
                ))
            
            if slider_configs:
                success_count, fail_count = param_setter.set_sliders_batch(slider_configs)
                if fail_count > 0:
                    all_success = False
                    print(f"\n⚠️  步驟 2 部分失敗: {fail_count} 個 Slider 設置失敗")
                else:
                    print(f"\n✓ 步驟 2 完成: 成功設置 {success_count} 個 Slider")
            else:
                print("\n⚠️  步驟 2 跳過: 沒有可設置的 Slider")
    else:
        print("\n⚠️  步驟 2 跳過: 未找到任何 Number Slider")
    
    # 步驟 3: 自動群組組件
    print("\n" + "=" * 80)
    print("步驟 3: 自動群組組件")
    print("=" * 80)
    
    subgraphs = MMDParser().parse_subgraphs_from_mmd(str(mmd_path))
    subgraph_names = MMDParser().get_subgraph_names(str(mmd_path))
    
    if subgraphs:
        if not id_map_path.exists():
            print(f"✗ 錯誤: 找不到 ID 映射文件 {id_map_path}")
            all_success = False
        else:
            with open(id_map_path, 'r', encoding='utf-8') as f:
                id_map = json.load(f)
            
            # 創建客戶端和管理器
            client = GrasshopperClient()
            comp_mgr = ComponentManager(client)
            comp_mgr.load_id_map(str(id_map_path))
            group_mgr = GroupManager(client, comp_mgr)
            
            # 顏色映射函數
            def get_subgraph_color(sg_id: str) -> tuple:
                color_map = {
                    "TOP": (225, 245, 255),
                    "LEG_BASE": (255, 244, 225),
                    "LEG_PLANES": (232, 245, 233),
                    "ORIENT_GROUP": (255, 235, 238),
                }
                for key, color in color_map.items():
                    if key in sg_id:
                        return color
                return (240, 240, 240)
            
            # 準備群組配置
            groups = []
            for sg_id, comp_ids in subgraphs.items():
                valid_comp_ids = [comp_id for comp_id in comp_ids if comp_id in id_map]
                
                if not valid_comp_ids:
                    continue
                
                name = subgraph_names.get(sg_id, sg_id)
                color = get_subgraph_color(sg_id)
                
                groups.append({
                    "name": name,
                    "componentIdKeys": valid_comp_ids,
                    "color": color
                })
            
            if groups:
                success_count, fail_count = group_mgr.group_components_batch(groups)
                if fail_count > 0:
                    all_success = False
                    print(f"\n⚠️  步驟 3 部分失敗: {fail_count} 個群組創建失敗")
                else:
                    print(f"\n✓ 步驟 3 完成: 成功創建 {success_count} 個群組")
            else:
                print("\n⚠️  步驟 3 跳過: 沒有可創建的群組")
    else:
        print("\n⚠️  步驟 3 跳過: 未找到任何 subgraph")
    
    # 步驟 4: 檢查錯誤
    print("\n" + "=" * 80)
    print("步驟 4: 檢查文檔錯誤")
    print("=" * 80)
    
    conn_mgr = ConnectionManager()
    errors = conn_mgr.get_document_errors()
    
    error_count = len(errors)
    if error_count > 0:
        print(f"\n⚠️  找到 {error_count} 個錯誤/警告:")
        for i, error in enumerate(errors[:10], 1):  # 只顯示前 10 個
            error_type = error.get("messageType", "Error")
            component_name = error.get("componentName", "未知組件")
            message = error.get("message", "未知錯誤")
            print(f"  {i}. [{error_type}] {component_name}: {message}")
        if error_count > 10:
            print(f"  ... 還有 {error_count - 10} 個錯誤")
        all_success = False
    else:
        print("\n✓ 步驟 4 完成: 沒有發現錯誤")
    
    # 總結
    print("\n" + "=" * 80)
    print("工作流程總結")
    print("=" * 80)
    
    if all_success and error_count == 0:
        print("\n✓ 所有步驟執行成功，沒有錯誤！")
        sys.exit(0)
    else:
        print("\n⚠️  工作流程完成，但有部分問題")
        if error_count > 0:
            print(f"   - 發現 {error_count} 個錯誤/警告")
        sys.exit(1)


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description="Grasshopper Tools 命令行接口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 執行 placement_info.json（文件在 GH_WIP 目錄下）
  python -m grasshopper_tools.cli execute-placement GH_WIP/placement_info.json

  # 執行完整工作流程（放置 -> 設置 Slider -> 群組 -> 檢查錯誤）
  python -m grasshopper_tools.cli execute-full-workflow GH_WIP/placement_info.json --clear-first

  # 解析 MMD 文件（文件在 GH_WIP 目錄下）
  python -m grasshopper_tools.cli parse-mmd GH_WIP/component_info.mmd --action components -o output.json

  # 解析 subgraph
  python -m grasshopper_tools.cli parse-mmd GH_WIP/component_info.mmd --action subgraphs -o subgraphs.json

  # 解析 slider 值
  python -m grasshopper_tools.cli parse-mmd GH_WIP/component_info.mmd --action sliders -o sliders.json

  # 生成 placement_info.json
  python -m grasshopper_tools.cli generate-json GH_WIP/component_info.mmd -o GH_WIP/placement_info.json

  # 更新 JSON 文件中的 GUID
  python -m grasshopper_tools.cli update-guids GH_WIP/placement_info.json --guid-map custom_guid_map.json

  # 創建組件
  python -m grasshopper_tools.cli add-component --guid "3e0451ca-da24-452d-a6b1-a6877453d4e4" --x 100 --y 200 --component-id SLIDER_WIDTH

  # 查詢組件 GUID
  python -m grasshopper_tools.cli query-guid "Number Slider"

  # 設置 Slider
  python -m grasshopper_tools.cli set-slider --component-id SLIDER_WIDTH --value "120.0" --min 0 --max 200
  
  # 自動設置所有 Slider（從 MMD 文件）
  python -m grasshopper_tools.cli auto-set-sliders GH_WIP/component_info.mmd

  # 設置 Vector XYZ
  python -m grasshopper_tools.cli set-vector --component-id VECTOR_LEG1 --x 10 --y 20 --z 30

  # 連接組件
  python -m grasshopper_tools.cli connect --source-id SLIDER_WIDTH --target-id DIVISION_X --source-param Number --target-param A

  # 創建群組
  python -m grasshopper_tools.cli group --component-ids "SLIDER_WIDTH,SLIDER_LENGTH" --group-name "桌面參數" --color-hex "#FF0000"
  
  # 自動群組所有組件（從 MMD 文件）
  python -m grasshopper_tools.cli auto-group-components GH_WIP/component_info.mmd

  # 獲取文檔錯誤
  python -m grasshopper_tools.cli get-errors -o errors.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # execute-placement 命令
    parser_execute = subparsers.add_parser('execute-placement', help='執行 placement_info.json')
    parser_execute.add_argument('json_path', help='placement_info.json 文件路徑（例如: GH_WIP/placement_info.json）')
    parser_execute.add_argument('--max-workers', type=int, default=10, help='最大並行線程數')
    parser_execute.add_argument('--no-save-id-map', dest='save_id_map', action='store_false', help='不保存 ID 映射')
    parser_execute.add_argument('--clear-first', action='store_true', help='執行前先清空畫布')
    parser_execute.add_argument('--no-smart-layout', action='store_true', help='不使用智能佈局（預設使用）')
    parser_execute.set_defaults(func=cmd_execute_placement)
    
    # execute-full-workflow 命令
    parser_full_workflow = subparsers.add_parser('execute-full-workflow', help='執行完整工作流程：放置組件 -> 設置 Slider -> 群組組件 -> 檢查錯誤')
    parser_full_workflow.add_argument('placement_json', help='placement_info.json 文件路徑（例如: GH_WIP/placement_info.json）')
    parser_full_workflow.add_argument('--mmd-path', default='GH_WIP/component_info.mmd', help='MMD 文件路徑（默認: GH_WIP/component_info.mmd）')
    parser_full_workflow.add_argument('--id-map', default='component_id_map.json', help='組件 ID 映射文件路徑（默認: component_id_map.json）')
    parser_full_workflow.add_argument('--max-workers', type=int, default=5, help='最大並行線程數（默認: 5）')
    parser_full_workflow.add_argument('--clear-first', action='store_true', help='執行前先清理 Grasshopper 文檔')
    parser_full_workflow.set_defaults(func=cmd_execute_full_workflow)
    
    # parse-mmd 命令
    parser_parse = subparsers.add_parser('parse-mmd', help='解析 MMD 文件')
    parser_parse.add_argument('mmd_path', help='MMD 文件路徑（例如: GH_WIP/component_info.mmd）')
    parser_parse.add_argument('--action', choices=['components', 'subgraphs', 'sliders'], required=True,
                             help='解析動作: components(組件和連接), subgraphs(subgraph), sliders(slider值)')
    parser_parse.add_argument('-o', '--output', help='輸出 JSON 文件路徑')
    parser_parse.set_defaults(func=cmd_parse_mmd)
    
    # generate-json 命令
    parser_gen = subparsers.add_parser('generate-json', help='生成 placement_info.json')
    parser_gen.add_argument('mmd_path', help='MMD 文件路徑（例如: GH_WIP/component_info.mmd）')
    parser_gen.add_argument('-o', '--output', default='placement_info.json', help='輸出 JSON 文件路徑')
    parser_gen.add_argument('--description', default='自動生成', help='描述信息')
    parser_gen.set_defaults(func=cmd_generate_json)
    
    # update-guids 命令
    parser_update = subparsers.add_parser('update-guids', help='更新 JSON 文件中的 GUID')
    parser_update.add_argument('json_path', help='JSON 文件路徑')
    parser_update.add_argument('--guid-map', help='自定義 GUID 映射文件（JSON）')
    parser_update.set_defaults(func=cmd_update_guids)
    
    # add-component 命令
    parser_add = subparsers.add_parser('add-component', help='創建組件')
    parser_add.add_argument('--guid', required=True, help='組件類型 GUID')
    parser_add.add_argument('--x', type=float, required=True, help='X 座標')
    parser_add.add_argument('--y', type=float, required=True, help='Y 座標')
    parser_add.add_argument('--component-id', help='組件 ID 鍵（用於映射）')
    parser_add.set_defaults(func=cmd_add_component)
    
    # delete-component 命令
    parser_del = subparsers.add_parser('delete-component', help='刪除組件')
    parser_del.add_argument('component_id', help='組件實際 ID')
    parser_del.set_defaults(func=cmd_delete_component)
    
    # set-visibility 命令
    parser_visibility = subparsers.add_parser('set-visibility', help='設置組件可見性')
    parser_visibility.add_argument('component_id', help='組件 ID（實際 ID 或映射鍵）')
    parser_visibility.add_argument('--hidden', action='store_true', help='隱藏組件（默認為顯示）')
    parser_visibility.add_argument('--visible', action='store_true', help='顯示組件（默認為顯示）')
    parser_visibility.set_defaults(func=cmd_set_visibility)
    
    # zoom-to-components 命令
    parser_zoom = subparsers.add_parser('zoom-to-components', help='縮放到指定組件')
    parser_zoom.add_argument('component_ids', help='組件 ID 列表（逗號分隔，可以是實際 ID 或映射鍵）')
    parser_zoom.set_defaults(func=cmd_zoom_to_components)
    
    # query-guid 命令
    parser_query = subparsers.add_parser('query-guid', help='查詢組件 GUID')
    parser_query.add_argument('component_name', help='組件名稱，如 "Number Slider"')
    parser_query.set_defaults(func=cmd_query_guid)
    
    # connect 命令
    parser_conn = subparsers.add_parser('connect', help='連接組件')
    parser_conn.add_argument('--source-id', required=True, help='源組件 ID 鍵')
    parser_conn.add_argument('--target-id', required=True, help='目標組件 ID 鍵')
    parser_conn.add_argument('--source-param', help='源組件參數名稱')
    parser_conn.add_argument('--target-param', help='目標組件參數名稱')
    parser_conn.set_defaults(func=cmd_connect_components)
    
    # set-slider 命令
    parser_slider = subparsers.add_parser('set-slider', help='設置 Slider')
    parser_slider.add_argument('--component-id', required=True, help='組件 ID 鍵')
    parser_slider.add_argument('--value', required=True, help='當前值')
    parser_slider.add_argument('--min', type=float, dest='min_value', help='最小值')
    parser_slider.add_argument('--max', type=float, dest='max_value', help='最大值')
    parser_slider.add_argument('--rounding', type=float, default=0.1, help='精度')
    parser_slider.set_defaults(func=cmd_set_slider)
    
    # auto-set-sliders 命令
    parser_auto_sliders = subparsers.add_parser('auto-set-sliders', help='自動設置所有 Slider（從 MMD 文件）')
    parser_auto_sliders.add_argument('mmd_path', help='MMD 文件路徑（如 GH_WIP/component_info.mmd）')
    parser_auto_sliders.add_argument('--id-map', default='component_id_map.json', help='組件 ID 映射文件路徑（默認: component_id_map.json）')
    parser_auto_sliders.set_defaults(func=cmd_auto_set_sliders)
    
    # set-vector 命令
    parser_vector = subparsers.add_parser('set-vector', help='設置 Vector XYZ')
    parser_vector.add_argument('--component-id', required=True, help='組件 ID 鍵')
    parser_vector.add_argument('--x', type=float, required=True, help='X 值')
    parser_vector.add_argument('--y', type=float, required=True, help='Y 值')
    parser_vector.add_argument('--z', type=float, required=True, help='Z 值')
    parser_vector.set_defaults(func=cmd_set_vector)
    
    # group 命令
    parser_group = subparsers.add_parser('group', help='創建群組')
    parser_group.add_argument('--component-ids', required=True, help='組件 ID 鍵列表（逗號分隔）')
    parser_group.add_argument('--group-name', required=True, help='群組名稱')
    parser_group.add_argument('--color', help='RGB 顏色（格式: r,g,b）')
    parser_group.add_argument('--color-hex', help='十六進制顏色（格式: #FF0000）')
    parser_group.set_defaults(func=cmd_group_components)
    
    # auto-group-components 命令
    parser_auto_group = subparsers.add_parser('auto-group-components', help='自動群組所有組件（從 MMD 文件）')
    parser_auto_group.add_argument('mmd_path', help='MMD 文件路徑（如 GH_WIP/component_info.mmd）')
    parser_auto_group.add_argument('--id-map', default='component_id_map.json', help='組件 ID 映射文件路徑（默認: component_id_map.json）')
    parser_auto_group.set_defaults(func=cmd_auto_group_components)
    
    # get-errors 命令
    parser_errors = subparsers.add_parser('get-errors', help='獲取文檔錯誤')
    parser_errors.add_argument('-o', '--output', help='輸出 JSON 文件路徑')
    parser_errors.set_defaults(func=cmd_get_errors)
    
    # 解析參數
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 執行對應的命令函數
    args.func(args)


if __name__ == '__main__':
    main()

