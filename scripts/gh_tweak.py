#!/usr/bin/env python3
"""
GH Tweak - Grasshopper MCP 微調工具

用途：不用每次重建，直接微調現有組件
"""

import socket
import json
import sys
from typing import Optional

# =========================================================================
# MCP 通訊
# =========================================================================

def send_command(cmd_type: str, params: dict = None) -> dict:
    """發送命令到 GH_MCP"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        sock.connect(("127.0.0.1", 8080))

        command = {"type": cmd_type}
        if params:
            command["parameters"] = params

        message = json.dumps(command) + "\n"
        sock.sendall(message.encode("utf-8"))

        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            if b"\n" in response:
                break

        sock.close()
        return json.loads(response.decode("utf-8-sig").strip())

    except Exception as e:
        return {"error": str(e), "success": False}


# =========================================================================
# 微調命令
# =========================================================================

def info(component_id: str) -> None:
    """查詢組件詳情"""
    result = send_command("get_component_details", {"componentId": component_id})
    if result.get("success"):
        data = result["data"]
        print(f"類型: {data.get('type')}")
        print(f"名稱: {data.get('name')}")
        print(f"位置: ({data['position']['x']}, {data['position']['y']})")
        print("輸入:")
        for inp in data.get("inputs", []):
            print(f"  - {inp['name']} ({inp['nickname']})")
        print("輸出:")
        for out in data.get("outputs", []):
            print(f"  - {out['name']} ({out['nickname']})")
    else:
        print(f"錯誤: {result.get('error')}")


def connect(source_id: str, target_id: str,
            source_param: str = None, target_param: str = None) -> None:
    """連接兩個組件"""
    params = {"sourceId": source_id, "targetId": target_id}
    if source_param:
        params["sourceParam"] = source_param
    if target_param:
        params["targetParam"] = target_param

    result = send_command("connect_components", params)
    if result.get("success"):
        inner = result.get("data", {})
        if inner.get("success"):
            print(f"✓ 連接成功")
        else:
            print(f"✗ {inner.get('error', inner)}")
    else:
        print(f"✗ {result.get('error')}")


def disconnect(source_id: str, target_id: str,
               source_param: str = None, target_param: str = None) -> None:
    """斷開連接"""
    params = {"sourceId": source_id, "targetId": target_id}
    if source_param:
        params["sourceParam"] = source_param
    if target_param:
        params["targetParam"] = target_param

    result = send_command("disconnect_components", params)
    print(f"斷開結果: {result}")


def set_slider(component_id: str, value: float) -> None:
    """設定 Slider 值"""
    result = send_command("set_slider_value", {
        "componentId": component_id,
        "value": value
    })
    if result.get("success"):
        print(f"✓ Slider 設為 {value}")
    else:
        print(f"✗ {result.get('error')}")


def add(comp_type: str, x: float, y: float, name: str = None) -> Optional[str]:
    """添加組件"""
    params = {"type": comp_type, "x": x, "y": y}
    if name:
        params["name"] = name

    result = send_command("add_component", params)
    if result.get("success"):
        comp_id = result.get("data", {}).get("componentId") or result.get("data", {}).get("id")
        print(f"✓ 創建 {comp_type}: {comp_id}")
        return comp_id
    else:
        print(f"✗ {result.get('error')}")
        return None


def delete(component_id: str) -> None:
    """刪除組件"""
    result = send_command("delete_component", {"componentId": component_id})
    if result.get("success"):
        print(f"✓ 已刪除 {component_id}")
    else:
        print(f"✗ {result.get('error')}")


def doc_info() -> None:
    """顯示文件資訊"""
    result = send_command("get_document_info")
    if result.get("success"):
        data = result["data"]
        print(f"組件數: {data.get('componentCount', 'N/A')}")
        print(f"文件名: {data.get('fileName', 'N/A')}")
    else:
        print(f"錯誤: {result.get('error')}")


def load_ids(json_path: str = "GH_WIP/component_id_map_v9.json") -> dict:
    """載入組件 ID 映射"""
    try:
        with open(json_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"無法載入 {json_path}: {e}")
        return {}


def sync_from_canvas() -> dict:
    """從 canvas 同步組件 ID（使用 get_document_info）"""
    result = send_command("get_document_info")
    if not result.get("success"):
        print(f"錯誤: {result.get('error')}")
        return {}

    data = result.get("data", {})
    components = data.get("components", [])

    # 建立 name -> id 映射
    ids = {}
    for c in components:
        name = c.get("name", "")
        comp_id = c.get("id", "")
        comp_type = c.get("type", "")

        if name and comp_id:
            # 使用 nickname 作為 key
            ids[name] = comp_id
        elif comp_type and comp_id:
            # 如果沒有 nickname，使用 type + 前 4 碼 ID
            key = f"{comp_type}_{comp_id[:4]}"
            ids[key] = comp_id

    print(f"從 canvas 同步了 {len(ids)} 個組件")
    return ids


# =========================================================================
# 互動模式
# =========================================================================

def interactive():
    """互動式命令行"""
    print("=" * 60)
    print("GH Tweak - Grasshopper MCP 微調工具")
    print("=" * 60)
    print("命令:")
    print("  ids              - 顯示已載入的組件 ID")
    print("  sync             - 從 canvas 同步組件 ID")
    print("  info <id>        - 查詢組件詳情")
    print("  connect <src> <tgt> [src_param] [tgt_param]")
    print("  disconnect <src> <tgt> [src_param] [tgt_param]")
    print("  slider <id> <value>")
    print("  add <type> <x> <y> [name]")
    print("  delete <id>")
    print("  doc              - 文件資訊")
    print("  load [path]      - 載入 ID 映射 (從 JSON 文件)")
    print("  q / quit         - 退出")
    print("=" * 60)

    ids = load_ids()
    print(f"已載入 {len(ids)} 個組件 ID")

    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not line:
            continue

        parts = line.split()
        cmd = parts[0].lower()
        args = parts[1:]

        # 支援用名稱代替 ID
        def resolve_id(name_or_id: str) -> str:
            return ids.get(name_or_id, name_or_id)

        if cmd in ("q", "quit", "exit"):
            break
        elif cmd == "ids":
            for name, comp_id in ids.items():
                print(f"  {name}: {comp_id[:8]}...")
        elif cmd == "info" and len(args) >= 1:
            info(resolve_id(args[0]))
        elif cmd == "connect" and len(args) >= 2:
            src_param = args[2] if len(args) > 2 else None
            tgt_param = args[3] if len(args) > 3 else None
            connect(resolve_id(args[0]), resolve_id(args[1]), src_param, tgt_param)
        elif cmd == "disconnect" and len(args) >= 2:
            src_param = args[2] if len(args) > 2 else None
            tgt_param = args[3] if len(args) > 3 else None
            disconnect(resolve_id(args[0]), resolve_id(args[1]), src_param, tgt_param)
        elif cmd == "slider" and len(args) >= 2:
            set_slider(resolve_id(args[0]), float(args[1]))
        elif cmd == "add" and len(args) >= 3:
            name = args[3] if len(args) > 3 else None
            new_id = add(args[0], float(args[1]), float(args[2]), name)
            if new_id and name:
                ids[name] = new_id
        elif cmd == "delete" and len(args) >= 1:
            delete(resolve_id(args[0]))
        elif cmd == "doc":
            doc_info()
        elif cmd == "load":
            path = args[0] if args else "GH_WIP/component_id_map_v9.json"
            ids = load_ids(path)
            print(f"已載入 {len(ids)} 個組件 ID")
        elif cmd == "sync":
            ids = sync_from_canvas()
            print("提示: 組件需要有 nickname 才能用名稱操作")
        else:
            print(f"未知命令: {cmd}")

    print("\n再見!")


# =========================================================================
# 主程式
# =========================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 命令行模式：直接執行單個命令
        cmd = sys.argv[1]
        args = sys.argv[2:]

        ids = load_ids()
        def resolve_id(name_or_id: str) -> str:
            return ids.get(name_or_id, name_or_id)

        if cmd == "info":
            info(resolve_id(args[0]))
        elif cmd == "connect":
            connect(resolve_id(args[0]), resolve_id(args[1]),
                   args[2] if len(args) > 2 else None,
                   args[3] if len(args) > 3 else None)
        elif cmd == "slider":
            set_slider(resolve_id(args[0]), float(args[1]))
        elif cmd == "doc":
            doc_info()
        else:
            print(f"未知命令: {cmd}")
    else:
        interactive()
