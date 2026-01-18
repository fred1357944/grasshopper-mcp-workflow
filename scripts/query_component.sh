#!/bin/bash
# 用 jq 查詢組件知識庫
# 用法: ./query_component.sh "Merge"

KNOWLEDGE="GH_WIP/component_knowledge.json"

if [ -z "$1" ]; then
    echo "用法: $0 <組件名稱>"
    echo "範例: $0 Merge"
    exit 1
fi

jq --arg name "$1" '.[$name] // "組件不存在，請檢查名稱"' "$KNOWLEDGE"
