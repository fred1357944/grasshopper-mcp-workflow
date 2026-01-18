using System;
using System.Collections.Generic;
using GH_MCP_Vision.Models;
using Rhino;

namespace GH_MCP_Vision.Commands
{
    /// <summary>
    /// Vision MCP 命令註冊表
    /// </summary>
    public static class VisionCommandRegistry
    {
        private static readonly Dictionary<string, Func<VisionCommand, object>> CommandHandlers =
            new Dictionary<string, Func<VisionCommand, object>>();

        /// <summary>
        /// 初始化命令註冊表
        /// </summary>
        public static void Initialize()
        {
            // 截取畫布
            RegisterCommand("capture_canvas", VisionCommandHandler.CaptureCanvas);

            // 截取 Rhino 3D 視圖
            RegisterCommand("capture_rhino_view", VisionCommandHandler.CaptureRhinoView);

            // 縮放到組件
            RegisterCommand("vision_zoom_to_components", VisionCommandHandler.ZoomToComponents);

            // 縮放到全部
            RegisterCommand("vision_zoom_extents", VisionCommandHandler.ZoomExtents);

            // 獲取畫布信息
            RegisterCommand("get_canvas_info", VisionCommandHandler.GetCanvasInfo);

            // 新增：組件連線診斷（學習自 GH_MCP 最佳實踐）
            RegisterCommand("get_connection_diagnostics", VisionCommandHandler.GetConnectionDiagnostics);

            // 新增：驗證組件是否存在
            RegisterCommand("validate_components", VisionCommandHandler.ValidateComponents);

            // 新增：獲取組件詳細信息（包含參數 Name/NickName）
            RegisterCommand("get_component_params", VisionCommandHandler.GetComponentParams);

            // 新增：導出組件庫（核心功能 - 避免 GUID 錯誤）
            RegisterCommand("export_component_library", VisionCommandHandler.ExportComponentLibrary);

            // 新增：搜索組件（智能匹配 - 內建優先、排除過期）
            RegisterCommand("search_components", VisionCommandHandler.SearchComponents);

            // ============ AI 智能診斷命令 ============
            // 診斷連線失敗（調用 Gemini CLI）
            RegisterCommand("diagnose_connection", VisionCommandHandler.DiagnoseConnection);

            // 自動修復連線（AI 建議 + 嘗試連線）
            RegisterCommand("auto_fix_connection", VisionCommandHandler.AutoFixConnection);

            // 從失敗中學習（批量分析 + 模式歸納）
            RegisterCommand("learn_from_failure", VisionCommandHandler.LearnFromFailure);

            RhinoApp.WriteLine("[GH_MCP_Vision] Command registry initialized with 13 commands.");
        }

        /// <summary>
        /// 註冊命令處理器
        /// </summary>
        public static void RegisterCommand(string commandType, Func<VisionCommand, object> handler)
        {
            if (string.IsNullOrEmpty(commandType))
                throw new ArgumentNullException(nameof(commandType));

            if (handler == null)
                throw new ArgumentNullException(nameof(handler));

            CommandHandlers[commandType] = handler;
            RhinoApp.WriteLine($"[GH_MCP_Vision] Registered command: '{commandType}'");
        }

        /// <summary>
        /// 執行命令
        /// </summary>
        public static VisionResponse ExecuteCommand(VisionCommand command)
        {
            if (command == null)
            {
                return VisionResponse.CreateError("Command is null");
            }

            if (string.IsNullOrEmpty(command.Type))
            {
                return VisionResponse.CreateError("Command type is null or empty");
            }

            if (CommandHandlers.TryGetValue(command.Type, out var handler))
            {
                try
                {
                    var result = handler(command);
                    return VisionResponse.Ok(result);
                }
                catch (Exception ex)
                {
                    RhinoApp.WriteLine($"[GH_MCP_Vision] Error executing '{command.Type}': {ex.Message}");
                    return VisionResponse.CreateError($"Error: {ex.Message}");
                }
            }

            return VisionResponse.CreateError($"Unknown command type: '{command.Type}'");
        }

        /// <summary>
        /// 獲取所有已註冊的命令類型
        /// </summary>
        public static List<string> GetRegisteredCommands()
        {
            return new List<string>(CommandHandlers.Keys);
        }

        /// <summary>
        /// 檢查命令是否已註冊
        /// </summary>
        public static bool IsCommandRegistered(string commandType)
        {
            return CommandHandlers.ContainsKey(commandType);
        }
    }
}
