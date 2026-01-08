using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using GrasshopperMCP.Models;
using GH_MCP.Models;
using Grasshopper;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Parameters;
using Rhino;
using Newtonsoft.Json;
using GH_MCP.Utils;

namespace GH_MCP.Commands
{
    /// <summary>
    /// 處理組件連接相關的命令
    /// </summary>
    public class ConnectionCommandHandler
    {
        /// <summary>
        /// 連接兩個組件
        /// </summary>
        /// <param name="command">命令對象</param>
        /// <returns>命令執行結果</returns>
        public static object ConnectComponents(Command command)
        {
            // 獲取源組件 ID
            if (!command.Parameters.TryGetValue("sourceId", out object sourceIdObj) || sourceIdObj == null)
            {
                return Response.CreateError("Missing required parameter: sourceId");
            }
            string sourceId = sourceIdObj.ToString();

            // 獲取源參數名稱或索引
            string sourceParam = null;
            int? sourceParamIndex = null;
            if (command.Parameters.TryGetValue("sourceParam", out object sourceParamObj) && sourceParamObj != null)
            {
                sourceParam = sourceParamObj.ToString();
                // 使用模糊匹配獲取標準化的參數名稱
                sourceParam = FuzzyMatcher.GetClosestParameterName(sourceParam);
            }
            else if (command.Parameters.TryGetValue("sourceParamIndex", out object sourceParamIndexObj) && sourceParamIndexObj != null)
            {
                if (int.TryParse(sourceParamIndexObj.ToString(), out int index))
                {
                    sourceParamIndex = index;
                }
            }

            // 獲取目標組件 ID
            if (!command.Parameters.TryGetValue("targetId", out object targetIdObj) || targetIdObj == null)
            {
                return Response.CreateError("Missing required parameter: targetId");
            }
            string targetId = targetIdObj.ToString();

            // 獲取目標參數名稱或索引
            string targetParam = null;
            int? targetParamIndex = null;
            if (command.Parameters.TryGetValue("targetParam", out object targetParamObj) && targetParamObj != null)
            {
                targetParam = targetParamObj.ToString();
                // 使用模糊匹配獲取標準化的參數名稱
                targetParam = FuzzyMatcher.GetClosestParameterName(targetParam);
            }
            else if (command.Parameters.TryGetValue("targetParamIndex", out object targetParamIndexObj) && targetParamIndexObj != null)
            {
                if (int.TryParse(targetParamIndexObj.ToString(), out int index))
                {
                    targetParamIndex = index;
                }
            }

            // 記錄連接信息
            RhinoApp.WriteLine($"Connecting: sourceId={sourceId}, sourceParam={sourceParam}, targetId={targetId}, targetParam={targetParam}");

            // 創建連接對象
            var connection = new ConnectionPairing
            {
                Source = new Connection
                {
                    ComponentId = sourceId,
                    ParameterName = sourceParam,
                    ParameterIndex = sourceParamIndex
                },
                Target = new Connection
                {
                    ComponentId = targetId,
                    ParameterName = targetParam,
                    ParameterIndex = targetParamIndex
                }
            };

            // 檢查連接是否有效
            if (!connection.IsValid())
            {
                return Response.CreateError("Invalid connection parameters");
            }

            // 在 UI 線程上執行連接操作
            object result = null;
            Exception exception = null;

            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    // 獲取當前文檔
                    var doc = Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        exception = new InvalidOperationException("No active Grasshopper document");
                        return;
                    }

                    // 查找源組件
                    Guid sourceGuid;
                    if (!Guid.TryParse(connection.Source.ComponentId, out sourceGuid))
                    {
                        exception = new ArgumentException($"Invalid source component ID: {connection.Source.ComponentId}");
                        return;
                    }

                    var sourceComponent = doc.FindObject(sourceGuid, true);
                    if (sourceComponent == null)
                    {
                        exception = new ArgumentException($"Source component not found: {connection.Source.ComponentId}");
                        return;
                    }

                    // 查找目標組件
                    Guid targetGuid;
                    if (!Guid.TryParse(connection.Target.ComponentId, out targetGuid))
                    {
                        exception = new ArgumentException($"Invalid target component ID: {connection.Target.ComponentId}");
                        return;
                    }

                    var targetComponent = doc.FindObject(targetGuid, true);
                    if (targetComponent == null)
                    {
                        exception = new ArgumentException($"Target component not found: {connection.Target.ComponentId}");
                        return;
                    }

                    // 檢查源組件是否為輸入參數組件
                    if (sourceComponent is IGH_Param && ((IGH_Param)sourceComponent).Kind == GH_ParamKind.input)
                    {
                        exception = new ArgumentException("Source component cannot be an input parameter");
                        return;
                    }

                    // 檢查目標組件是否為輸出參數組件
                    if (targetComponent is IGH_Param && ((IGH_Param)targetComponent).Kind == GH_ParamKind.output)
                    {
                        exception = new ArgumentException("Target component cannot be an output parameter");
                        return;
                    }

                    // 獲取源參數
                    IGH_Param sourceParameter = GetParameter(sourceComponent, connection.Source, false);
                    if (sourceParameter == null)
                    {
                        exception = new ArgumentException($"Source parameter not found: {connection.Source.ParameterName ?? connection.Source.ParameterIndex.ToString()}");
                        return;
                    }

                    // 獲取目標參數
                    IGH_Param targetParameter = GetParameter(targetComponent, connection.Target, true);
                    if (targetParameter == null)
                    {
                        // 收集可用參數名稱供錯誤訊息使用
                        var availableInputs = new List<string>();
                        if (targetComponent is IGH_Component tc)
                        {
                            foreach (var p in tc.Params.Input)
                            {
                                availableInputs.Add($"{p.Name}({p.NickName})");
                            }
                        }
                        string requested = connection.Target.ParameterName ?? connection.Target.ParameterIndex?.ToString() ?? "unknown";
                        string available = availableInputs.Count > 0 ? string.Join(", ", availableInputs) : "none";
                        exception = new ArgumentException($"Target parameter '{requested}' not found. Available inputs: [{available}]");
                        return;
                    }

                    // 檢查參數類型相容性
                    if (!AreParametersCompatible(sourceParameter, targetParameter))
                    {
                        exception = new ArgumentException($"Parameters are not compatible: {sourceParameter.GetType().Name} cannot connect to {targetParameter.GetType().Name}");
                        return;
                    }

                    // 檢查源參數是否已經連接到目標參數（避免重複連接）
                    bool alreadyConnected = false;
                    for (int i = 0; i < targetParameter.SourceCount; i++)
                    {
                        if (targetParameter.Sources[i].Equals(sourceParameter))
                        {
                            alreadyConnected = true;
                            RhinoApp.WriteLine($"Connection already exists from {sourceParameter.Name} to {targetParameter.Name}, skipping duplicate");
                            break;
                        }
                    }

                    // 如果尚未連接，則添加新連接
                    bool connectionCreated = false;
                    if (!alreadyConnected)
                    {
                        int sourceCountBefore = targetParameter.SourceCount;
                        RhinoApp.WriteLine($"[GH_MCP] Before AddSource: SourceCount={sourceCountBefore}");

                        // ====== 修復 v2: 使用 Grasshopper 官方的連線方式 ======
                        // 關鍵: 在 AddSource 之前禁用自動重算
                        doc.Enabled = false;
                        try
                        {
                            // 使用標準的 AddSource 方法
                            targetParameter.AddSource(sourceParameter);
                            RhinoApp.WriteLine($"[GH_MCP] Called AddSource");

                            // 重要: 通知參數已更改
                            targetParameter.ExpireSolution(false);

                            // 檢查是否成功
                            int sourceCountAfter = targetParameter.SourceCount;
                            RhinoApp.WriteLine($"[GH_MCP] After AddSource: SourceCount={sourceCountAfter}");
                            connectionCreated = (sourceCountAfter > sourceCountBefore);

                            if (!connectionCreated)
                            {
                                // 備用方法: 嘗試通過 Attributes 獲取 wire 並添加
                                RhinoApp.WriteLine($"[GH_MCP] AddSource didn't increase count, trying alternative...");

                                // 直接檢查 Sources 列表
                                for (int i = 0; i < targetParameter.SourceCount; i++)
                                {
                                    if (targetParameter.Sources[i].InstanceGuid == sourceParameter.InstanceGuid)
                                    {
                                        connectionCreated = true;
                                        RhinoApp.WriteLine($"[GH_MCP] Connection verified via GUID match");
                                        break;
                                    }
                                }
                            }
                        }
                        finally
                        {
                            // 重新啟用文檔
                            doc.Enabled = true;
                        }

                        if (connectionCreated)
                        {
                            RhinoApp.WriteLine($"SUCCESS: Added connection from {sourceParameter.Name} to {targetParameter.Name}");
                        }
                        else
                        {
                            RhinoApp.WriteLine($"WARNING: Connection may have failed");
                            // 不要拋出異常，讓用戶看到結果
                        }
                    }
                    else
                    {
                        connectionCreated = true;
                        RhinoApp.WriteLine($"[GH_MCP] Connection already exists");
                    }

                    // ====== 修復: 強制觸發重新計算 ======
                    doc.NewSolution(true, GH_SolutionMode.Silent);

                    // 刷新畫布顯示
                    var canvas = Grasshopper.Instances.ActiveCanvas;
                    if (canvas != null)
                    {
                        canvas.Invalidate();
                    }

                    // 返回結果
                    result = new
                    {
                        success = connectionCreated,
                        message = alreadyConnected ? "Connection already exists" : (connectionCreated ? "Connection created successfully" : "Connection may have failed"),
                        sourceId = connection.Source.ComponentId,
                        targetId = connection.Target.ComponentId,
                        sourceParam = sourceParameter.Name,
                        targetParam = targetParameter.Name,
                        sourceType = sourceParameter.GetType().Name,
                        targetType = targetParameter.GetType().Name,
                        sourceDescription = sourceParameter.Description,
                        targetDescription = targetParameter.Description,
                        verified = connectionCreated
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in ConnectComponents: {ex.Message}");
                }
            }));

            // 等待 UI 線程操作完成
            while (result == null && exception == null)
            {
                Thread.Sleep(10);
            }

            // 如果有異常，拋出
            if (exception != null)
            {
                return Response.CreateError($"Error executing command 'connect_components': {exception.Message}");
            }

            return Response.Ok(result);
        }

        /// <summary>
        /// 獲取組件的參數
        /// </summary>
        /// <param name="docObj">文檔對象</param>
        /// <param name="connection">連接信息</param>
        /// <param name="isInput">是否為輸入參數</param>
        /// <returns>參數對象</returns>
        private static IGH_Param GetParameter(IGH_DocumentObject docObj, Connection connection, bool isInput)
        {
            // 處理參數組件
            if (docObj is IGH_Param param)
            {
                return param;
            }
            
            // 處理一般組件
            if (docObj is IGH_Component component)
            {
                // 獲取參數集合
                IList<IGH_Param> parameters = isInput ? component.Params.Input : component.Params.Output;
                
                // 檢查參數集合是否為空
                if (parameters == null || parameters.Count == 0)
                {
                    return null;
                }
                
                // 如果只有一個參數，直接返回（只有在未指定名稱或索引時）
                if (parameters.Count == 1 && string.IsNullOrEmpty(connection.ParameterName) && !connection.ParameterIndex.HasValue)
                {
                    return parameters[0];
                }
                
                // 按名稱查找參數 (優化匹配順序 v2.0)
                if (!string.IsNullOrEmpty(connection.ParameterName))
                {
                    string requestedName = connection.ParameterName;

                    // 1. NickName 精確匹配 (優先 - 腳本最常使用)
                    foreach (var p in parameters)
                    {
                        if (string.Equals(p.NickName, requestedName, StringComparison.OrdinalIgnoreCase))
                        {
                            RhinoApp.WriteLine($"  Matched by NickName: {requestedName} -> {p.Name}");
                            return p;
                        }
                    }

                    // 2. Name 精確匹配
                    foreach (var p in parameters)
                    {
                        if (string.Equals(p.Name, requestedName, StringComparison.OrdinalIgnoreCase))
                        {
                            RhinoApp.WriteLine($"  Matched by Name: {requestedName}");
                            return p;
                        }
                    }

                    // 3. 模糊匹配 (Name 或 NickName 包含請求字串)
                    foreach (var p in parameters)
                    {
                        if (p.Name.IndexOf(requestedName, StringComparison.OrdinalIgnoreCase) >= 0 ||
                            p.NickName.IndexOf(requestedName, StringComparison.OrdinalIgnoreCase) >= 0)
                        {
                            RhinoApp.WriteLine($"  Matched by fuzzy: {requestedName} -> {p.Name} ({p.NickName})");
                            return p;
                        }
                    }

                    // 4. 未找到 - 記錄可用參數
                    var availableParams = string.Join(", ", parameters.Select(p => $"{p.Name}({p.NickName})"));
                    RhinoApp.WriteLine($"  Parameter '{requestedName}' not found. Available: {availableParams}");
                }
                
                // 按索引查找參數
                if (connection.ParameterIndex.HasValue)
                {
                    int index = connection.ParameterIndex.Value;
                    if (index >= 0 && index < parameters.Count)
                    {
                        return parameters[index];
                    }
                }
            }
            
            return null;
        }

        /// <summary>
        /// 檢查兩個參數是否相容
        /// </summary>
        /// <param name="source">源參數</param>
        /// <param name="target">目標參數</param>
        /// <returns>是否相容</returns>
        private static bool AreParametersCompatible(IGH_Param source, IGH_Param target)
        {
            // 如果參數類型完全匹配，則相容
            if (source.GetType() == target.GetType())
            {
                return true;
            }

            // 檢查數據類型是否兼容
            var sourceType = source.Type;
            var targetType = target.Type;
            
            // 記錄參數類型信息，用於調試
            RhinoApp.WriteLine($"Parameter types: source={sourceType.Name}, target={targetType.Name}");
            RhinoApp.WriteLine($"Parameter names: source={source.Name}, target={target.Name}");
            
            // 檢查數字類型的兼容性
            bool isSourceNumeric = IsNumericType(source);
            bool isTargetNumeric = IsNumericType(target);
            
            if (isSourceNumeric && isTargetNumeric)
            {
                return true;
            }

            // 曲線和幾何體之間的特殊處理
            bool isSourceCurve = source is Param_Curve;
            bool isTargetCurve = target is Param_Curve;
            bool isSourceGeometry = source is Param_Geometry;
            bool isTargetGeometry = target is Param_Geometry;

            if ((isSourceCurve && isTargetGeometry) || (isSourceGeometry && isTargetCurve))
            {
                return true;
            }

            // 點和向量之間的特殊處理
            bool isSourcePoint = source is Param_Point;
            bool isTargetPoint = target is Param_Point;
            bool isSourceVector = source is Param_Vector;
            bool isTargetVector = target is Param_Vector;

            if ((isSourcePoint && isTargetVector) || (isSourceVector && isTargetPoint))
            {
                return true;
            }

            // 檢查組件的 GUID，確保連接到正確的元件類型
            // 獲取參數所屬的組件
            var sourceDoc = source.OnPingDocument();
            var targetDoc = target.OnPingDocument();
            
            if (sourceDoc != null && targetDoc != null)
            {
                // 嘗試查找參數所屬的組件
                IGH_Component sourceComponent = FindComponentForParam(sourceDoc, source);
                IGH_Component targetComponent = FindComponentForParam(targetDoc, target);
                
                // 如果找到了源組件和目標組件
                if (sourceComponent != null && targetComponent != null)
                {
                    // 記錄組件信息，用於調試
                    RhinoApp.WriteLine($"Components: source={sourceComponent.Name}, target={targetComponent.Name}");
                    RhinoApp.WriteLine($"Component GUIDs: source={sourceComponent.ComponentGuid}, target={targetComponent.ComponentGuid}");
                    
                    // 特殊處理平面到幾何元件的連接
                    if (IsPlaneComponent(sourceComponent) && RequiresPlaneInput(targetComponent))
                    {
                        RhinoApp.WriteLine("Connecting plane component to geometry component that requires plane input");
                        return true;
                    }
                    
                    // 如果源是滑塊且目標是圓，確保目標是創建圓的組件
                    if (sourceComponent.Name.Contains("Number") && targetComponent.Name.Contains("Circle"))
                    {
                        // 檢查目標是否為正確的圓元件 (使用 GUID 或描述)
                        if (targetComponent.ComponentGuid.ToString() == "d1028c72-ff86-4057-9eb0-36c687a4d98c")
                        {
                            // 這是錯誤的圓元件 (參數容器)
                            RhinoApp.WriteLine("Detected connection to Circle parameter container instead of Circle component");
                            return false;
                        }
                        if (targetComponent.ComponentGuid.ToString() == "807b86e3-be8d-4970-92b5-f8cdcb45b06b")
                        {
                            // 這是正確的圓元件 (創建圓)
                            return true;
                        }
                    }
                    
                    // 如果源是平面且目標是立方體，允許連接
                    if (IsPlaneComponent(sourceComponent) && targetComponent.Name.Contains("Box"))
                    {
                        RhinoApp.WriteLine("Connecting plane component to box component");
                        return true;
                    }
                }
            }

            // 默認允許連接，讓 Grasshopper 在運行時決定是否相容
            return true;
        }

        /// <summary>
        /// 檢查參數是否為數字類型
        /// </summary>
        /// <param name="param">參數</param>
        /// <returns>是否為數字類型</returns>
        private static bool IsNumericType(IGH_Param param)
        {
            return param is Param_Integer || 
                   param is Param_Number || 
                   param is Param_Time;
        }

        /// <summary>
        /// 查找參數所屬的組件
        /// </summary>
        /// <param name="doc">文檔</param>
        /// <param name="param">參數</param>
        /// <returns>參數所屬的組件</returns>
        private static IGH_Component FindComponentForParam(GH_Document doc, IGH_Param param)
        {
            foreach (var obj in doc.Objects)
            {
                if (obj is IGH_Component comp)
                {
                    // 檢查輸出參數
                    foreach (var outParam in comp.Params.Output)
                    {
                        if (outParam.InstanceGuid == param.InstanceGuid)
                        {
                            return comp;
                        }
                    }
                    
                    // 檢查輸入參數
                    foreach (var inParam in comp.Params.Input)
                    {
                        if (inParam.InstanceGuid == param.InstanceGuid)
                        {
                            return comp;
                        }
                    }
                }
            }
            
            return null;
        }
        
        /// <summary>
        /// 檢查組件是否為平面組件
        /// </summary>
        /// <param name="component">組件</param>
        /// <returns>是否為平面組件</returns>
        private static bool IsPlaneComponent(IGH_Component component)
        {
            if (component == null)
                return false;
                
            // 檢查組件名稱
            string name = component.Name.ToLowerInvariant();
            if (name.Contains("plane"))
                return true;
                
            // 檢查 XY Plane 組件的 GUID
            if (component.ComponentGuid.ToString() == "896a1e5e-c2ac-4996-a6d8-5b61157080b3")
                return true;
                
            return false;
        }
        
        /// <summary>
        /// 檢查組件是否需要平面輸入
        /// </summary>
        /// <param name="component">組件</param>
        /// <returns>是否需要平面輸入</returns>
        private static bool RequiresPlaneInput(IGH_Component component)
        {
            if (component == null)
                return false;
                
            // 檢查組件是否有名為 "Plane" 或 "Base" 的輸入參數
            foreach (var param in component.Params.Input)
            {
                string paramName = param.Name.ToLowerInvariant();
                if (paramName.Contains("plane") || paramName.Contains("base"))
                    return true;
            }
            
            // 檢查特定類型的組件
            string name = component.Name.ToLowerInvariant();
            return name.Contains("box") || 
                   name.Contains("rectangle") || 
                   name.Contains("circle") || 
                   name.Contains("cylinder") || 
                   name.Contains("cone");
        }
    }

    public class ConnectionPairing
    {
        public Connection Source { get; set; }
        public Connection Target { get; set; }

        public bool IsValid()
        {
            return Source != null && Target != null;
        }
    }

    public class Connection
    {
        public string ComponentId { get; set; }
        public string ParameterName { get; set; }
        public int? ParameterIndex { get; set; }
    }

    /// <summary>
    /// 處理連接查詢和斷開連接的命令
    /// </summary>
    public class ConnectionQueryHandler
    {
        /// <summary>
        /// 獲取組件的所有連接
        /// </summary>
        public static object GetConnections(Command command)
        {
            if (!command.Parameters.TryGetValue("componentId", out object compIdObj) || compIdObj == null)
            {
                return Response.CreateError("Missing required parameter: componentId");
            }
            string componentId = compIdObj.ToString();

            object result = null;
            Exception exception = null;

            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    var doc = Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        exception = new InvalidOperationException("No active Grasshopper document");
                        return;
                    }

                    Guid compGuid;
                    if (!Guid.TryParse(componentId, out compGuid))
                    {
                        exception = new ArgumentException($"Invalid component ID: {componentId}");
                        return;
                    }

                    var docObj = doc.FindObject(compGuid, true);
                    if (docObj == null)
                    {
                        exception = new ArgumentException($"Component not found: {componentId}");
                        return;
                    }

                    var inputConnections = new List<object>();
                    var outputConnections = new List<object>();

                    if (docObj is IGH_Component component)
                    {
                        // 遍歷輸入參數
                        foreach (var input in component.Params.Input)
                        {
                            var sources = new List<object>();
                            for (int i = 0; i < input.SourceCount; i++)
                            {
                                var source = input.Sources[i];
                                sources.Add(new
                                {
                                    sourceId = source.InstanceGuid.ToString(),
                                    sourceName = source.Name,
                                    sourceNickName = source.NickName,
                                    sourceType = source.GetType().Name
                                });
                            }
                            inputConnections.Add(new
                            {
                                parameterName = input.Name,
                                parameterNickName = input.NickName,
                                parameterIndex = component.Params.Input.IndexOf(input),
                                sourceCount = input.SourceCount,
                                sources = sources
                            });
                        }

                        // 遍歷輸出參數
                        foreach (var output in component.Params.Output)
                        {
                            var recipients = new List<object>();
                            for (int i = 0; i < output.Recipients.Count; i++)
                            {
                                var recipient = output.Recipients[i];
                                recipients.Add(new
                                {
                                    targetId = recipient.InstanceGuid.ToString(),
                                    targetName = recipient.Name,
                                    targetNickName = recipient.NickName,
                                    targetType = recipient.GetType().Name
                                });
                            }
                            outputConnections.Add(new
                            {
                                parameterName = output.Name,
                                parameterNickName = output.NickName,
                                parameterIndex = component.Params.Output.IndexOf(output),
                                recipientCount = output.Recipients.Count,
                                recipients = recipients
                            });
                        }
                    }
                    else if (docObj is IGH_Param param)
                    {
                        // 單獨的參數組件
                        var sources = new List<object>();
                        for (int i = 0; i < param.SourceCount; i++)
                        {
                            var source = param.Sources[i];
                            sources.Add(new
                            {
                                sourceId = source.InstanceGuid.ToString(),
                                sourceName = source.Name,
                                sourceNickName = source.NickName,
                                sourceType = source.GetType().Name
                            });
                        }
                        inputConnections.Add(new
                        {
                            parameterName = param.Name,
                            parameterNickName = param.NickName,
                            sourceCount = param.SourceCount,
                            sources = sources
                        });

                        var recipients = new List<object>();
                        for (int i = 0; i < param.Recipients.Count; i++)
                        {
                            var recipient = param.Recipients[i];
                            recipients.Add(new
                            {
                                targetId = recipient.InstanceGuid.ToString(),
                                targetName = recipient.Name,
                                targetNickName = recipient.NickName,
                                targetType = recipient.GetType().Name
                            });
                        }
                        outputConnections.Add(new
                        {
                            parameterName = param.Name,
                            parameterNickName = param.NickName,
                            recipientCount = param.Recipients.Count,
                            recipients = recipients
                        });
                    }

                    result = new
                    {
                        success = true,
                        componentId = componentId,
                        componentName = docObj is IGH_Component c ? c.Name : (docObj is IGH_Param p ? p.Name : "Unknown"),
                        componentNickName = docObj is IGH_Component cn ? cn.NickName : (docObj is IGH_Param pn ? pn.NickName : "Unknown"),
                        inputs = inputConnections,
                        outputs = outputConnections
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in GetConnections: {ex.Message}");
                }
            }));

            while (result == null && exception == null)
            {
                Thread.Sleep(10);
            }

            if (exception != null)
            {
                return Response.CreateError($"Error getting connections: {exception.Message}");
            }

            return Response.Ok(result);
        }

        /// <summary>
        /// 斷開兩個組件之間的連接
        /// </summary>
        public static object DisconnectComponents(Command command)
        {
            if (!command.Parameters.TryGetValue("sourceId", out object sourceIdObj) || sourceIdObj == null)
            {
                return Response.CreateError("Missing required parameter: sourceId");
            }
            string sourceId = sourceIdObj.ToString();

            if (!command.Parameters.TryGetValue("targetId", out object targetIdObj) || targetIdObj == null)
            {
                return Response.CreateError("Missing required parameter: targetId");
            }
            string targetId = targetIdObj.ToString();

            string sourceParam = null;
            string targetParam = null;
            if (command.Parameters.TryGetValue("sourceParam", out object sp) && sp != null)
                sourceParam = sp.ToString();
            if (command.Parameters.TryGetValue("targetParam", out object tp) && tp != null)
                targetParam = tp.ToString();

            object result = null;
            Exception exception = null;

            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    var doc = Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        exception = new InvalidOperationException("No active Grasshopper document");
                        return;
                    }

                    Guid sourceGuid, targetGuid;
                    if (!Guid.TryParse(sourceId, out sourceGuid))
                    {
                        exception = new ArgumentException($"Invalid source ID: {sourceId}");
                        return;
                    }
                    if (!Guid.TryParse(targetId, out targetGuid))
                    {
                        exception = new ArgumentException($"Invalid target ID: {targetId}");
                        return;
                    }

                    var sourceObj = doc.FindObject(sourceGuid, true);
                    var targetObj = doc.FindObject(targetGuid, true);

                    if (sourceObj == null || targetObj == null)
                    {
                        exception = new ArgumentException("Source or target component not found");
                        return;
                    }

                    // 找到源輸出參數
                    IGH_Param sourceParameter = null;
                    if (sourceObj is IGH_Param sp)
                    {
                        sourceParameter = sp;
                    }
                    else if (sourceObj is IGH_Component sourceComp)
                    {
                        if (!string.IsNullOrEmpty(sourceParam))
                        {
                            foreach (var p in sourceComp.Params.Output)
                            {
                                if (p.Name.Equals(sourceParam, StringComparison.OrdinalIgnoreCase) ||
                                    p.NickName.Equals(sourceParam, StringComparison.OrdinalIgnoreCase))
                                {
                                    sourceParameter = p;
                                    break;
                                }
                            }
                        }
                        else if (sourceComp.Params.Output.Count == 1)
                        {
                            sourceParameter = sourceComp.Params.Output[0];
                        }
                    }

                    // 找到目標輸入參數
                    IGH_Param targetParameter = null;
                    if (targetObj is IGH_Param tp)
                    {
                        targetParameter = tp;
                    }
                    else if (targetObj is IGH_Component targetComp)
                    {
                        if (!string.IsNullOrEmpty(targetParam))
                        {
                            foreach (var p in targetComp.Params.Input)
                            {
                                if (p.Name.Equals(targetParam, StringComparison.OrdinalIgnoreCase) ||
                                    p.NickName.Equals(targetParam, StringComparison.OrdinalIgnoreCase))
                                {
                                    targetParameter = p;
                                    break;
                                }
                            }
                        }
                        else if (targetComp.Params.Input.Count == 1)
                        {
                            targetParameter = targetComp.Params.Input[0];
                        }
                    }

                    if (sourceParameter == null || targetParameter == null)
                    {
                        exception = new ArgumentException("Could not find source or target parameter");
                        return;
                    }

                    // 移除連接 - RemoveSource 返回 void，需要用 SourceCount 檢查
                    int sourceCountBefore = targetParameter.SourceCount;
                    targetParameter.RemoveSource(sourceParameter);
                    int sourceCountAfter = targetParameter.SourceCount;
                    bool removed = (sourceCountAfter < sourceCountBefore);

                    if (removed)
                    {
                        doc.NewSolution(true);
                        RhinoApp.WriteLine($"Disconnected {sourceParameter.Name} from {targetParameter.Name}");
                    }

                    result = new
                    {
                        success = removed,
                        message = removed ? "Connection removed" : "Connection not found or already disconnected",
                        sourceId = sourceId,
                        targetId = targetId,
                        sourceParam = sourceParameter.Name,
                        targetParam = targetParameter.Name
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in DisconnectComponents: {ex.Message}");
                }
            }));

            while (result == null && exception == null)
            {
                Thread.Sleep(10);
            }

            if (exception != null)
            {
                return Response.CreateError($"Error disconnecting: {exception.Message}");
            }

            return Response.Ok(result);
        }

        /// <summary>
        /// 獲取組件的詳細信息
        /// </summary>
        public static object GetComponentDetails(Command command)
        {
            if (!command.Parameters.TryGetValue("componentId", out object compIdObj) || compIdObj == null)
            {
                return Response.CreateError("Missing required parameter: componentId");
            }
            string componentId = compIdObj.ToString();

            object result = null;
            Exception exception = null;

            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    var doc = Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        exception = new InvalidOperationException("No active Grasshopper document");
                        return;
                    }

                    Guid compGuid;
                    if (!Guid.TryParse(componentId, out compGuid))
                    {
                        exception = new ArgumentException($"Invalid component ID: {componentId}");
                        return;
                    }

                    var docObj = doc.FindObject(compGuid, true);
                    if (docObj == null)
                    {
                        exception = new ArgumentException($"Component not found: {componentId}");
                        return;
                    }

                    var inputs = new List<object>();
                    var outputs = new List<object>();

                    string type = "Unknown";
                    string name = "Unknown";
                    string nickName = "Unknown";
                    string description = "";
                    bool isObsolete = false;
                    float posX = 0, posY = 0;

                    if (docObj is IGH_Component component)
                    {
                        type = component.Name;
                        name = component.Name;
                        nickName = component.NickName;
                        description = component.Description;
                        isObsolete = component.Obsolete;
                        posX = component.Attributes.Pivot.X;
                        posY = component.Attributes.Pivot.Y;

                        foreach (var input in component.Params.Input)
                        {
                            inputs.Add(new
                            {
                                name = input.Name,
                                nickname = input.NickName,
                                description = input.Description,
                                type = input.GetType().Name,
                                optional = input.Optional,
                                sourceCount = input.SourceCount,
                                hasData = input.VolatileDataCount > 0
                            });
                        }

                        foreach (var output in component.Params.Output)
                        {
                            outputs.Add(new
                            {
                                name = output.Name,
                                nickname = output.NickName,
                                description = output.Description,
                                type = output.GetType().Name,
                                recipientCount = output.Recipients.Count,
                                hasData = output.VolatileDataCount > 0
                            });
                        }
                    }
                    else if (docObj is IGH_Param param)
                    {
                        type = param.GetType().Name;
                        name = param.Name;
                        nickName = param.NickName;
                        description = param.Description;
                        posX = param.Attributes.Pivot.X;
                        posY = param.Attributes.Pivot.Y;

                        // 參數既是輸入也是輸出
                        outputs.Add(new
                        {
                            name = param.Name,
                            nickname = param.NickName,
                            description = param.Description,
                            type = param.GetType().Name,
                            recipientCount = param.Recipients.Count,
                            hasData = param.VolatileDataCount > 0
                        });
                    }

                    result = new
                    {
                        success = true,
                        id = componentId,
                        type = type,
                        name = name,
                        nickName = nickName,
                        description = description,
                        isObsolete = isObsolete,
                        position = new { x = posX, y = posY },
                        inputs = inputs,
                        outputs = outputs
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in GetComponentDetails: {ex.Message}");
                }
            }));

            while (result == null && exception == null)
            {
                Thread.Sleep(10);
            }

            if (exception != null)
            {
                return Response.CreateError($"Error getting component details: {exception.Message}");
            }

            return Response.Ok(result);
        }
    }
}
