using System;
using System.Collections.Generic;
using GrasshopperMCP.Models;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Parameters;
using Grasshopper.Kernel.Special;
using Rhino;
using Rhino.Geometry;
using Grasshopper;
using System.Linq;
using Grasshopper.Kernel.Components;
using System.Threading;
using GH_MCP.Utils;
using GH_MCP.Commands.Components;

namespace GrasshopperMCP.Commands
{
    /// <summary>
    /// 處理組件相關命令的處理器
    /// </summary>
    public static class ComponentCommandHandler
    {
        /// <summary>
        /// 添加組件
        /// 
        /// 重要：只接受 GUID 參數，不進行任何名稱匹配。
        /// 直接通過 GUID 創建組件，不需要輸入組件名稱或文字。
        /// 使用 'get_component_candidates' 命令來查詢組件的 GUID。
        /// </summary>
        /// <param name="command">包含 GUID 和位置的命令</param>
        /// <returns>添加的組件信息</returns>
        /// <remarks>
        /// 使用步驟：
        /// 1. 首先使用 'get_component_candidates' 查詢組件候選並獲取 GUID
        /// 2. 然後使用獲得的 GUID 來添加組件
        /// 
        /// 如果未提供 GUID 或 GUID 無效，系統將返回錯誤。
        /// </remarks>
        public static object AddComponent(Command command)
        {
            double x = command.GetParameter<double>("x");
            double y = command.GetParameter<double>("y");
            string guid = command.GetParameter<string>("guid");
            string type = command.GetParameter<string>("type"); // 接受 type 參數（可選，用於向後兼容）

            // 必須提供 GUID 或 type 參數之一
            if (string.IsNullOrEmpty(guid) && string.IsNullOrEmpty(type))
            {
                throw new ArgumentException("Either 'guid' or 'type' is required. Use 'get_component_candidates' to find the component GUID, or provide a component type name.");
            }
            
            // 記錄請求信息
            if (!string.IsNullOrEmpty(type))
            {
                RhinoApp.WriteLine($"AddComponent request: guid={guid}, type={type}, x={x}, y={y}");
            }
            else
            {
                RhinoApp.WriteLine($"AddComponent request: guid={guid}, x={x}, y={y}");
            }
            
            object result = null;
            Exception exception = null;
            
            // 在 UI 線程上執行
            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    // 獲取 Grasshopper 文檔
                    var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        throw new InvalidOperationException("No active Grasshopper document");
                    }
                    
                    // 創建組件
                    IGH_DocumentObject component = null;
                    
                    // 如果提供了 type 參數，優先使用組件名稱來查找
                    if (!string.IsNullOrEmpty(type))
                    {
                        // 內建庫列表（優先級高）
                        var builtInLibraries = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
                        {
                            "Grasshopper", "GrasshopperLib",
                            "MathComponents", "CurveComponents", "SurfaceComponents",
                            "MeshComponents", "TransformComponents", "VectorComponents",
                            "SetComponents", "FieldComponents", "IntersectComponents",
                            "DisplayComponents", "ParamsComponents"
                        };

                        // 輔助函數：判斷是否為內建庫
                        Func<Grasshopper.Kernel.IGH_ObjectProxy, bool> isBuiltIn = (p) =>
                        {
                            try
                            {
                                var assembly = Grasshopper.Instances.ComponentServer.FindAssemblyByObject(p.Guid);
                                return assembly != null && builtInLibraries.Contains(assembly.Name);
                            }
                            catch { return false; }
                        };

                        Grasshopper.Kernel.IGH_ObjectProxy proxy = null;

                        // 1. 精確匹配 Name（內建優先、非過期優先）
                        var nameMatches = Grasshopper.Instances.ComponentServer.ObjectProxies
                            .Where(p => p.Desc.Name.Equals(type, StringComparison.OrdinalIgnoreCase))
                            .ToList();

                        if (nameMatches.Count > 0)
                        {
                            // 排序：內建優先 → 非過期優先
                            proxy = nameMatches
                                .OrderByDescending(p => isBuiltIn(p) ? 1 : 0)
                                .ThenBy(p => p.Obsolete ? 1 : 0)
                                .FirstOrDefault();

                            if (nameMatches.Count > 1)
                            {
                                RhinoApp.WriteLine($"[GH_MCP] Found {nameMatches.Count} components named '{type}', selected: {proxy.Desc.Name} from {(isBuiltIn(proxy) ? "built-in" : "plugin")}");
                            }
                        }

                        // 2. 如果 Name 沒找到，嘗試 NickName 精確匹配
                        if (proxy == null)
                        {
                            var nickNameMatches = Grasshopper.Instances.ComponentServer.ObjectProxies
                                .Where(p => p.Desc.NickName.Equals(type, StringComparison.OrdinalIgnoreCase))
                                .ToList();

                            if (nickNameMatches.Count > 0)
                            {
                                proxy = nickNameMatches
                                    .OrderByDescending(p => isBuiltIn(p) ? 1 : 0)
                                    .ThenBy(p => p.Obsolete ? 1 : 0)
                                    .FirstOrDefault();

                                RhinoApp.WriteLine($"[GH_MCP] Matched by NickName: '{type}' -> {proxy.Desc.Name}");
                            }
                        }

                        // 3. 如果還沒找到，使用 FuzzyMatcher 嘗試映射
                        if (proxy == null)
                        {
                            string mappedName = FuzzyMatcher.GetClosestComponentName(type);
                            if (!mappedName.Equals(type, StringComparison.OrdinalIgnoreCase))
                            {
                                proxy = Grasshopper.Instances.ComponentServer.ObjectProxies
                                    .Where(p => p.Desc.Name.Equals(mappedName, StringComparison.OrdinalIgnoreCase))
                                    .OrderByDescending(p => isBuiltIn(p) ? 1 : 0)
                                    .ThenBy(p => p.Obsolete ? 1 : 0)
                                    .FirstOrDefault();

                                if (proxy != null)
                                {
                                    RhinoApp.WriteLine($"[GH_MCP] Fuzzy matched: '{type}' -> {proxy.Desc.Name}");
                                }
                            }
                        }

                        if (proxy != null)
                        {
                            component = proxy.CreateInstance();
                            RhinoApp.WriteLine($"Created component by name: {proxy.Desc.Name} (Type GUID: {proxy.Desc.InstanceGuid})");
                        }
                        else
                        {
                            throw new ArgumentException($"Component with name '{type}' not found. Use 'get_component_candidates' or 'search_components' to find the correct name.");
                        }
                    }
                    else
                    {
                        // 使用 GUID 創建組件（需要類型 GUID，不是實例 GUID）
                        Guid componentGuid;
                        if (!Guid.TryParse(guid, out componentGuid))
                        {
                            throw new ArgumentException($"Invalid GUID format: '{guid}'. Please provide a valid GUID.\n\n" +
                                                      $"To find the appropriate GUID, use 'get_component_candidates' command:\n" +
                                                      $"  Command: get_component_candidates\n" +
                                                      $"  Parameters: {{ \"name\": \"<component_name>\" }}");
                        }
                        
                        // 首先嘗試通過 ObjectProxies 查找（使用類型 GUID）
                        var proxy = Grasshopper.Instances.ComponentServer.ObjectProxies
                            .FirstOrDefault(p => p.Desc.InstanceGuid == componentGuid);
                        
                        if (proxy != null)
                        {
                            // 使用 ObjectProxy 創建組件（這是最可靠的方式）
                            component = proxy.CreateInstance();
                            RhinoApp.WriteLine($"Created component by type GUID via proxy: {component.GetType().Name} (Type GUID: {componentGuid})");
                        }
                        else
                        {
                            // 如果找不到 proxy，嘗試直接使用 EmitObject（需要類型 GUID）
                            component = Grasshopper.Instances.ComponentServer.EmitObject(componentGuid);
                            
                            if (component == null)
                            {
                                throw new ArgumentException($"Component with type GUID '{guid}' not found. " +
                                                          $"Please verify the GUID is correct using 'get_component_candidates' command. " +
                                                          $"Note: You need the component TYPE GUID, not instance GUID.");
                            }
                            else
                            {
                                RhinoApp.WriteLine($"Created component by type GUID: {component.GetType().Name} (Type GUID: {componentGuid})");
                            }
                        }
                    }
                    
                    // 設置組件位置
                    if (component != null)
                    {
                        // 確保組件有有效的屬性對象
                        if (component.Attributes == null)
                        {
                            RhinoApp.WriteLine("Component attributes are null, creating new attributes");
                            component.CreateAttributes();
                        }
                        
                        // 設置位置
                        component.Attributes.Pivot = new System.Drawing.PointF((float)x, (float)y);
                        
                        // 添加到文檔
                        doc.AddObject(component, false);
                        
                        // 刷新畫布
                        doc.NewSolution(false);
                        
                        // 返回組件信息
                        result = new
                        {
                            id = component.InstanceGuid.ToString(),
                            type = component.GetType().Name,
                            name = component.NickName,
                            x = component.Attributes.Pivot.X,
                            y = component.Attributes.Pivot.Y
                        };
                    }
                    else
                    {
                        throw new InvalidOperationException("Failed to create component");
                    }
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in AddComponent: {ex.Message}");
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
                throw exception;
            }
            
            return result;
        }
        
        /// <summary>
        /// 連接組件
        /// </summary>
        /// <param name="command">包含源和目標組件信息的命令</param>
        /// <returns>連接信息</returns>
        public static object ConnectComponents(Command command)
        {
            var fromData = command.GetParameter<Dictionary<string, object>>("from");
            var toData = command.GetParameter<Dictionary<string, object>>("to");
            
            if (fromData == null || toData == null)
            {
                throw new ArgumentException("Source and target component information are required");
            }
            
            object result = null;
            Exception exception = null;
            
            // 在 UI 線程上執行
            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    // 獲取 Grasshopper 文檔
                    var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        throw new InvalidOperationException("No active Grasshopper document");
                    }
                    
                    // 解析源組件信息
                    string fromIdStr = fromData["id"].ToString();
                    string fromParamName = fromData["parameterName"].ToString();
                    
                    // 解析目標組件信息
                    string toIdStr = toData["id"].ToString();
                    string toParamName = toData["parameterName"].ToString();
                    
                    // 將字符串 ID 轉換為 Guid
                    Guid fromId, toId;
                    if (!Guid.TryParse(fromIdStr, out fromId) || !Guid.TryParse(toIdStr, out toId))
                    {
                        throw new ArgumentException("Invalid component ID format");
                    }
                    
                    // 查找源和目標組件
                    IGH_Component fromComponent = doc.FindComponent(fromId) as IGH_Component;
                    IGH_Component toComponent = doc.FindComponent(toId) as IGH_Component;
                    
                    if (fromComponent == null || toComponent == null)
                    {
                        throw new ArgumentException("Source or target component not found");
                    }
                    
                    // 查找源輸出參數
                    IGH_Param fromParam = null;
                    foreach (var param in fromComponent.Params.Output)
                    {
                        if (param.Name.Equals(fromParamName, StringComparison.OrdinalIgnoreCase))
                        {
                            fromParam = param;
                            break;
                        }
                    }
                    
                    // 查找目標輸入參數
                    IGH_Param toParam = null;
                    foreach (var param in toComponent.Params.Input)
                    {
                        if (param.Name.Equals(toParamName, StringComparison.OrdinalIgnoreCase))
                        {
                            toParam = param;
                            break;
                        }
                    }
                    
                    if (fromParam == null || toParam == null)
                    {
                        throw new ArgumentException("Source or target parameter not found");
                    }
                    
                    // 連接參數
                    toParam.AddSource(fromParam);
                    
                    // 刷新畫布
                    doc.NewSolution(false);
                    
                    // 返回連接信息
                    result = new
                    {
                        from = new
                        {
                            id = fromComponent.InstanceGuid.ToString(),
                            name = fromComponent.NickName,
                            parameter = fromParam.Name
                        },
                        to = new
                        {
                            id = toComponent.InstanceGuid.ToString(),
                            name = toComponent.NickName,
                            parameter = toParam.Name
                        }
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
                throw exception;
            }
            
            return result;
        }
        
        /// <summary>
        /// 設置組件值
        /// </summary>
        /// <param name="command">包含組件 ID 和值的命令</param>
        /// <returns>操作結果</returns>
        public static object SetComponentValue(Command command)
        {
            string idStr = command.GetParameter<string>("id");
            string value = command.GetParameter<string>("value");
            double? minValue = command.GetParameter<double?>("min");
            double? maxValue = command.GetParameter<double?>("max");
            double? rounding = command.GetParameter<double?>("rounding");
            
            if (string.IsNullOrEmpty(idStr))
            {
                throw new ArgumentException("Component ID is required");
            }
            
            object result = null;
            Exception exception = null;
            
            // 在 UI 線程上執行
            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    // 獲取 Grasshopper 文檔
                    var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        throw new InvalidOperationException("No active Grasshopper document");
                    }
                    
                    // 將字符串 ID 轉換為 Guid
                    Guid id;
                    if (!Guid.TryParse(idStr, out id))
                    {
                        throw new ArgumentException("Invalid component ID format");
                    }
                    
                    // 查找組件
                    IGH_DocumentObject component = doc.FindObject(id, true);
                    if (component == null)
                    {
                        throw new ArgumentException($"Component with ID {idStr} not found");
                    }
                    
                    // 根據組件類型設置值
                    if (component is GH_Panel panel)
                    {
                        panel.UserText = value;
                        panel.ExpireSolution(true);
                    }
                    else if (component is GH_NumberSlider slider)
                    {
                        // 設置最小值
                        if (minValue.HasValue)
                        {
                            slider.Slider.Minimum = (decimal)minValue.Value;
                            RhinoApp.WriteLine($"  Slider minimum set to: {minValue.Value}");
                        }
                        
                        // 設置最大值
                        if (maxValue.HasValue)
                        {
                            slider.Slider.Maximum = (decimal)maxValue.Value;
                            RhinoApp.WriteLine($"  Slider maximum set to: {maxValue.Value}");
                        }
                        
                        // 設置精度
                        if (rounding.HasValue)
                        {
                            int decimalPlaces = 0;
                            if (rounding.Value > 0)
                            {
                                decimalPlaces = Math.Max(0, (int)Math.Abs(Math.Log10(rounding.Value)));
                            }
                            slider.Slider.DecimalPlaces = decimalPlaces;
                            RhinoApp.WriteLine($"  Slider decimal places set to: {decimalPlaces} (rounding: {rounding.Value})");
                        }
                        
                        // 設置值（必須在設置範圍之後）
                        if (!string.IsNullOrEmpty(value))
                        {
                            double doubleValue;
                            if (double.TryParse(value, out doubleValue))
                            {
                                decimal sliderValue = (decimal)doubleValue;
                                // 確保值在範圍內
                                if (sliderValue < slider.Slider.Minimum)
                                    sliderValue = slider.Slider.Minimum;
                                if (sliderValue > slider.Slider.Maximum)
                                    sliderValue = slider.Slider.Maximum;
                                
                                slider.Slider.Value = sliderValue;
                                RhinoApp.WriteLine($"  Slider value set to: {sliderValue}");
                            }
                            else
                            {
                                throw new ArgumentException("Invalid slider value format");
                            }
                        }
                        
                        // 強制更新
                        try
                        {
                            var expireLayoutMethod = slider.GetType().GetMethod("ExpireLayout");
                            if (expireLayoutMethod != null)
                            {
                                expireLayoutMethod.Invoke(slider, null);
                            }
                        }
                        catch
                        {
                            // ExpireLayout may not exist in all versions
                        }
                        slider.ExpireSolution(true);
                    }
                    else if (component is IGH_Component ghComponent)
                    {
                        // 嘗試設置第一個輸入參數的值
                        if (ghComponent.Params.Input.Count > 0)
                        {
                            var param = ghComponent.Params.Input[0];
                            if (param is Param_String stringParam)
                            {
                                stringParam.PersistentData.Clear();
                                stringParam.PersistentData.Append(new Grasshopper.Kernel.Types.GH_String(value));
                            }
                            else if (param is Param_Number numberParam)
                            {
                                double doubleValue;
                                if (double.TryParse(value, out doubleValue))
                                {
                                    numberParam.PersistentData.Clear();
                                    numberParam.PersistentData.Append(new Grasshopper.Kernel.Types.GH_Number(doubleValue));
                                }
                                else
                                {
                                    throw new ArgumentException("Invalid number value format");
                                }
                            }
                            else
                            {
                                throw new ArgumentException($"Cannot set value for parameter type {param.GetType().Name}");
                            }
                        }
                        else
                        {
                            throw new ArgumentException("Component has no input parameters");
                        }
                    }
                    else
                    {
                        throw new ArgumentException($"Cannot set value for component type {component.GetType().Name}");
                    }
                    
                    // 刷新畫布
                    doc.NewSolution(false);
                    
                    // 返回操作結果
                    result = new
                    {
                        id = component.InstanceGuid.ToString(),
                        type = component.GetType().Name,
                        value = value
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in SetComponentValue: {ex.Message}");
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
                throw exception;
            }
            
            return result;
        }
        
        /// <summary>
        /// 獲取組件信息
        /// </summary>
        /// <param name="command">包含組件 ID 的命令</param>
        /// <returns>組件信息</returns>
        public static object GetComponentInfo(Command command)
        {
            string idStr = command.GetParameter<string>("id");
            
            if (string.IsNullOrEmpty(idStr))
            {
                throw new ArgumentException("Component ID is required");
            }
            
            object result = null;
            Exception exception = null;
            
            // 在 UI 線程上執行
            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    // 獲取 Grasshopper 文檔
                    var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        throw new InvalidOperationException("No active Grasshopper document");
                    }
                    
                    // 將字符串 ID 轉換為 Guid
                    Guid id;
                    if (!Guid.TryParse(idStr, out id))
                    {
                        throw new ArgumentException("Invalid component ID format");
                    }
                    
                    // 查找組件
                    IGH_DocumentObject component = doc.FindObject(id, true);
                    if (component == null)
                    {
                        throw new ArgumentException($"Component with ID {idStr} not found");
                    }
                    
                    // 收集組件信息
                    var componentInfo = new Dictionary<string, object>
                    {
                        { "id", component.InstanceGuid.ToString() },
                        { "type", component.GetType().Name },
                        { "name", component.NickName },
                        { "description", component.Description }
                    };
                    
                    // 如果是 IGH_Component，收集輸入和輸出參數信息
                    if (component is IGH_Component ghComponent)
                    {
                        var inputs = new List<Dictionary<string, object>>();
                        foreach (var param in ghComponent.Params.Input)
                        {
                            inputs.Add(new Dictionary<string, object>
                            {
                                { "name", param.Name },
                                { "nickname", param.NickName },
                                { "description", param.Description },
                                { "type", param.GetType().Name },
                                { "dataType", param.TypeName }
                            });
                        }
                        componentInfo["inputs"] = inputs;
                        
                        var outputs = new List<Dictionary<string, object>>();
                        foreach (var param in ghComponent.Params.Output)
                        {
                            outputs.Add(new Dictionary<string, object>
                            {
                                { "name", param.Name },
                                { "nickname", param.NickName },
                                { "description", param.Description },
                                { "type", param.GetType().Name },
                                { "dataType", param.TypeName }
                            });
                        }
                        componentInfo["outputs"] = outputs;
                        
                        // 收集運行時訊息（錯誤和警告）
                        var runtimeMessages = new List<Dictionary<string, object>>();
                        
                        // 收集錯誤訊息
                        var errorMessages = ghComponent.RuntimeMessages(GH_RuntimeMessageLevel.Error);
                        foreach (var errorText in errorMessages)
                        {
                            runtimeMessages.Add(new Dictionary<string, object>
                            {
                                { "type", "Error" },
                                { "text", errorText },
                                { "description", errorText }
                            });
                        }
                        
                        // 收集警告訊息
                        var warningMessages = ghComponent.RuntimeMessages(GH_RuntimeMessageLevel.Warning);
                        foreach (var warningText in warningMessages)
                        {
                            runtimeMessages.Add(new Dictionary<string, object>
                            {
                                { "type", "Warning" },
                                { "text", warningText },
                                { "description", warningText }
                            });
                        }
                        
                        componentInfo["runtimeMessages"] = runtimeMessages;
                    }
                    
                    // 如果是 GH_Panel，獲取其文本值
                    if (component is GH_Panel panel)
                    {
                        componentInfo["value"] = panel.UserText;
                    }
                    
                    // 如果是 GH_NumberSlider，獲取其值和範圍
                    if (component is GH_NumberSlider slider)
                    {
                        componentInfo["value"] = (double)slider.CurrentValue;
                        componentInfo["minimum"] = (double)slider.Slider.Minimum;
                        componentInfo["maximum"] = (double)slider.Slider.Maximum;
                    }
                    
                    result = componentInfo;
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in GetComponentInfo: {ex.Message}");
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
                throw exception;
            }
            
            return result;
        }
        
        /// <summary>
        /// 查詢組件候選項
        /// </summary>
        /// <param name="command">包含組件名稱的命令</param>
        /// <returns>所有匹配的組件候選項信息</returns>
        public static object GetComponentCandidates(Command command)
        {
            string componentName = command.GetParameter<string>("name");
            if (string.IsNullOrEmpty(componentName))
            {
                throw new ArgumentException("Component name is required");
            }
            
            object result = null;
            Exception exception = null;
            
            // 在 UI 線程上執行
            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    // 使用模糊匹配獲取標準化的元件名稱
                    string normalizedType = FuzzyMatcher.GetClosestComponentName(componentName);
                    
                    // 獲取所有匹配的組件
                    var matchingProxies = Grasshopper.Instances.ComponentServer.ObjectProxies
                        .Where(p => p.Desc.Name.IndexOf(normalizedType, StringComparison.OrdinalIgnoreCase) >= 0 ||
                                   p.Desc.Name.IndexOf(componentName, StringComparison.OrdinalIgnoreCase) >= 0)
                        .ToList();
                    
                    if (matchingProxies.Count == 0)
                    {
                        result = new
                        {
                            query = componentName,
                            normalizedQuery = normalizedType,
                            count = 0,
                            candidates = new List<object>()
                        };
                        return;
                    }
                    
                    // 為每個候選項獲取詳細信息
                    var candidates = matchingProxies.Select(p =>
                    {
                        IGH_DocumentObject tempComponent = null;
                        List<object> inputs = null;
                        List<object> outputs = null;
                        string libraryName = "Unknown";
                        bool isObsolete = false;
                        bool isBuiltIn = false;
                        string description = "No description available";
                        string typeName = "Unknown";
                        
                        try
                        {
                            tempComponent = p.CreateInstance();
                            typeName = tempComponent.GetType().Name;
                            
                            // 獲取庫名稱
                            try
                            {
                                libraryName = tempComponent.GetType().Assembly.GetName().Name ?? "Unknown";
                                isBuiltIn = libraryName.Equals("Grasshopper", StringComparison.OrdinalIgnoreCase) ||
                                           libraryName.IndexOf("Grasshopper", StringComparison.OrdinalIgnoreCase) >= 0;
                            }
                            catch { }
                            
                            // 檢查是否廢棄
                            try
                            {
                                isObsolete = typeName.IndexOf("Obsolete", StringComparison.OrdinalIgnoreCase) >= 0 ||
                                            typeName.IndexOf("Deprecated", StringComparison.OrdinalIgnoreCase) >= 0;
                            }
                            catch { }
                            
                            // 獲取描述
                            try
                            {
                                description = tempComponent.Description ?? "No description available";
                            }
                            catch { }
                            
                            // 獲取輸入輸出參數
                            if (tempComponent is IGH_Component comp)
                            {
                                inputs = comp.Params.Input.Select(ip => new
                                {
                                    name = ip.Name,
                                    nickname = ip.NickName,
                                    type = ip.TypeName,
                                    description = ip.Description ?? ""
                                }).Cast<object>().ToList();
                                
                                outputs = comp.Params.Output.Select(op => new
                                {
                                    name = op.Name,
                                    nickname = op.NickName,
                                    type = op.TypeName,
                                    description = op.Description ?? ""
                                }).Cast<object>().ToList();
                            }
                        }
                        catch (Exception ex)
                        {
                            RhinoApp.WriteLine($"Error getting component info for {p.Desc.Name}: {ex.Message}");
                        }
                        
                        return new
                        {
                            name = p.Desc.Name,
                            fullName = p.Desc.Name,
                            guid = p.Desc.InstanceGuid.ToString(),
                            category = p.Desc.Category?.ToString() ?? "Unknown",
                            subCategory = p.Desc.SubCategory?.ToString() ?? "Unknown",
                            library = libraryName,
                            typeName = typeName,
                            description = description,
                            obsolete = isObsolete,
                            isBuiltIn = isBuiltIn,
                            inputs = inputs ?? new List<object>(),
                            outputs = outputs ?? new List<object>()
                        };
                    }).ToList();
                    
                    result = new
                    {
                        query = componentName,
                        normalizedQuery = normalizedType,
                        count = candidates.Count,
                        candidates = candidates
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in GetComponentCandidates: {ex.Message}");
                }
            }));
            
            // 等待 UI 線程操作完成
            while (result == null && exception == null)
            {
                Thread.Sleep(10);
            }
            
            if (exception != null)
            {
                throw exception;
            }
            
            return result;
        }
        
        /// <summary>
        /// 獲取文檔中所有組件的錯誤訊息
        /// </summary>
        /// <param name="command">命令（此命令不需要參數）</param>
        /// <returns>包含所有錯誤和警告的列表</returns>
        public static object GetDocumentErrors(Command command)
        {
            object result = null;
            Exception exception = null;
            
            // 在 UI 線程上執行
            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    // 獲取 Grasshopper 文檔
                    var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        throw new InvalidOperationException("No active Grasshopper document");
                    }
                    
                    var allErrors = new List<Dictionary<string, object>>();
                    
                    // 遍歷文檔中所有組件
                    foreach (var obj in doc.Objects)
                    {
                        if (obj is IGH_Component component)
                        {
                            // 收集該組件的錯誤訊息
                            var errorMessages = component.RuntimeMessages(GH_RuntimeMessageLevel.Error);
                            foreach (var errorText in errorMessages)
                            {
                                allErrors.Add(new Dictionary<string, object>
                                {
                                    { "componentId", component.InstanceGuid.ToString() },
                                    { "componentName", component.NickName },
                                    { "componentType", component.GetType().Name },
                                    { "messageType", "Error" },
                                    { "message", errorText },
                                    { "description", errorText }
                                });
                            }
                            
                            // 收集該組件的警告訊息
                            var warningMessages = component.RuntimeMessages(GH_RuntimeMessageLevel.Warning);
                            foreach (var warningText in warningMessages)
                            {
                                allErrors.Add(new Dictionary<string, object>
                                {
                                    { "componentId", component.InstanceGuid.ToString() },
                                    { "componentName", component.NickName },
                                    { "componentType", component.GetType().Name },
                                    { "messageType", "Warning" },
                                    { "message", warningText },
                                    { "description", warningText }
                                });
                            }
                        }
                    }
                    
                    result = new Dictionary<string, object>
                    {
                        { "errorCount", allErrors.Count },
                        { "errors", allErrors }
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in GetDocumentErrors: {ex.Message}");
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
                throw exception;
            }
            
            return result;
        }
        
        private static IGH_DocumentObject CreateComponentByName(string name)
        {
            var obj = Grasshopper.Instances.ComponentServer.ObjectProxies
                .FirstOrDefault(p => p.Desc.Name.Equals(name, StringComparison.OrdinalIgnoreCase));
                
            if (obj != null)
            {
                return obj.CreateInstance();
            }
            else
            {
                throw new ArgumentException($"Component with name {name} not found");
            }
        }

        /// <summary>
        /// 將多個元件群組起來
        /// </summary>
        /// <param name="command">包含 componentIds 的命令</param>
        /// <returns>群組資訊</returns>
        public static object GroupComponents(Command command)
        {
            return ComponentOrganization.GroupComponents(command);
        }

        /// <summary>
        /// 設置 Number Slider 的完整屬性
        /// </summary>
        /// <param name="command">包含組件 ID 和屬性的命令</param>
        /// <returns>操作結果</returns>
        public static object SetSliderProperties(Command command)
        {
            return ComponentProperties.SetSliderProperties(command);
        }

        /// <summary>
        /// 刪除組件
        /// </summary>
        /// <param name="command">包含組件ID的命令</param>
        /// <returns>刪除結果</returns>
        public static object DeleteComponent(Command command)
        {
            string componentId = command.GetParameter<string>("componentId");
            
            if (string.IsNullOrEmpty(componentId))
            {
                throw new ArgumentException("Component ID is required");
            }
            
            object result = null;
            Exception exception = null;
            
            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        throw new InvalidOperationException("No active Grasshopper document");
                    }
                    
                    Guid guid;
                    if (!Guid.TryParse(componentId, out guid))
                    {
                        throw new ArgumentException($"Invalid component ID: {componentId}");
                    }
                    
                    var component = doc.FindObject(guid, true);
                    if (component == null)
                    {
                        throw new ArgumentException($"Component not found: {componentId}");
                    }
                    
                    doc.RemoveObject(component, true);
                    doc.NewSolution(false);
                    
                    result = new
                    {
                        success = true,
                        message = "Component deleted successfully",
                        componentId = componentId
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in DeleteComponent: {ex.Message}");
                }
            }));
            
            while (result == null && exception == null)
            {
                Thread.Sleep(10);
            }
            
            if (exception != null)
            {
                throw exception;
            }
            
            return result;
        }

        /// <summary>
        /// 移動組件到指定位置
        /// </summary>
        /// <param name="command">包含組件ID和新位置的命令</param>
        /// <returns>移動結果</returns>
        public static object MoveComponent(Command command)
        {
            string componentId = command.GetParameter<string>("componentId");
            double x = command.GetParameter<double>("x");
            double y = command.GetParameter<double>("y");
            
            if (string.IsNullOrEmpty(componentId))
            {
                throw new ArgumentException("Component ID is required");
            }
            
            object result = null;
            Exception exception = null;
            
            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        throw new InvalidOperationException("No active Grasshopper document");
                    }
                    
                    Guid guid;
                    if (!Guid.TryParse(componentId, out guid))
                    {
                        throw new ArgumentException($"Invalid component ID: {componentId}");
                    }
                    
                    var component = doc.FindObject(guid, true);
                    if (component == null)
                    {
                        throw new ArgumentException($"Component not found: {componentId}");
                    }
                    
                    if (component.Attributes == null)
                    {
                        component.CreateAttributes();
                    }
                    
                    component.Attributes.Pivot = new System.Drawing.PointF((float)x, (float)y);
                    doc.NewSolution(false);
                    
                    result = new
                    {
                        success = true,
                        message = "Component moved successfully",
                        componentId = componentId,
                        x = x,
                        y = y
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in MoveComponent: {ex.Message}");
                }
            }));
            
            while (result == null && exception == null)
            {
                Thread.Sleep(10);
            }
            
            if (exception != null)
            {
                throw exception;
            }
            
            return result;
        }

        /// <summary>
        /// 設置組件可見性
        /// </summary>
        /// <param name="command">包含組件ID和可見性狀態的命令</param>
        /// <returns>操作結果</returns>
        public static object SetComponentVisibility(Command command)
        {
            string componentId = command.GetParameter<string>("componentId");
            bool? hidden = command.GetParameter<bool?>("hidden");
            
            if (string.IsNullOrEmpty(componentId))
            {
                throw new ArgumentException("Component ID is required");
            }
            
            if (!hidden.HasValue)
            {
                throw new ArgumentException("Hidden parameter is required");
            }
            
            object result = null;
            Exception exception = null;
            
            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        throw new InvalidOperationException("No active Grasshopper document");
                    }
                    
                    Guid guid;
                    if (!Guid.TryParse(componentId, out guid))
                    {
                        throw new ArgumentException($"Invalid component ID: {componentId}");
                    }
                    
                    var component = doc.FindObject(guid, true);
                    if (component == null)
                    {
                        throw new ArgumentException($"Component not found: {componentId}");
                    }
                    
                    if (component.Attributes == null)
                    {
                        component.CreateAttributes();
                    }
                    
                    // 設置可見性
#if NETFRAMEWORK
                    component.Attributes.Hidden = hidden.Value;
#else
                    // .NET 7.0: 使用反射嘗試設置 Hidden 屬性
                    try
                    {
                        var hiddenProp = component.Attributes?.GetType().GetProperty("Hidden");
                        if (hiddenProp != null && hiddenProp.CanWrite)
                        {
                            hiddenProp.SetValue(component.Attributes, hidden.Value);
                        }
                        else
                        {
                            RhinoApp.WriteLine($"Warning: Cannot set visibility on macOS (.NET 7.0)");
                        }
                    }
                    catch
                    {
                        RhinoApp.WriteLine($"Warning: SetComponentVisibility not fully supported on this platform");
                    }
#endif
                    
                    // 刷新畫布
                    doc.NewSolution(false);
                    
                    result = new
                    {
                        success = true,
                        message = $"Component visibility set to {(hidden.Value ? "hidden" : "visible")}",
                        componentId = componentId,
                        hidden = hidden.Value
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in SetComponentVisibility: {ex.Message}");
                }
            }));
            
            while (result == null && exception == null)
            {
                Thread.Sleep(10);
            }
            
            if (exception != null)
            {
                throw exception;
            }
            
            return result;
        }

        /// <summary>
        /// 縮放到指定組件
        /// </summary>
        /// <param name="command">包含組件ID列表的命令</param>
        /// <returns>操作結果</returns>
        public static object ZoomToComponents(Command command)
        {
            var componentIds = command.GetParameter<List<string>>("componentIds");
            
            if (componentIds == null || componentIds.Count == 0)
            {
                throw new ArgumentException("At least one component ID is required");
            }
            
            object result = null;
            Exception exception = null;
            
            // 在 UI 線程上執行
            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    // 獲取 Grasshopper 文檔和畫布
                    var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                    var canvas = Grasshopper.Instances.ActiveCanvas;
                    
                    if (doc == null)
                    {
                        throw new InvalidOperationException("No active Grasshopper document");
                    }
                    
                    if (canvas == null)
                    {
                        throw new InvalidOperationException("No active Grasshopper canvas");
                    }
                    
                    // 查找所有指定的組件
                    var components = new List<IGH_DocumentObject>();
                    var notFoundIds = new List<string>();
                    
                    foreach (var idStr in componentIds)
                    {
                        Guid guid;
                        if (!Guid.TryParse(idStr, out guid))
                        {
                            notFoundIds.Add(idStr);
                            continue;
                        }
                        
                        var component = doc.FindObject(guid, true);
                        if (component != null)
                        {
                            components.Add(component);
                        }
                        else
                        {
                            notFoundIds.Add(idStr);
                        }
                    }
                    
                    if (components.Count == 0)
                    {
                        throw new ArgumentException("No valid components found");
                    }
                    
                    // 計算所有組件的邊界框
                    System.Drawing.RectangleF? combinedBounds = null;
                    
                    foreach (var component in components)
                    {
                        if (component.Attributes != null)
                        {
                            var bounds = component.Attributes.Bounds;
                            if (combinedBounds.HasValue)
                            {
                                combinedBounds = System.Drawing.RectangleF.Union(combinedBounds.Value, bounds);
                            }
                            else
                            {
                                combinedBounds = bounds;
                            }
                        }
                    }
                    
                    if (combinedBounds.HasValue)
                    {
                        // 計算中心點和適當的縮放級別
                        var centerX = combinedBounds.Value.X + combinedBounds.Value.Width / 2;
                        var centerY = combinedBounds.Value.Y + combinedBounds.Value.Height / 2;
                        
                        // 添加一些邊距
                        var margin = 100f;
                        var width = combinedBounds.Value.Width + margin * 2;
                        var height = combinedBounds.Value.Height + margin * 2;
                        
                        // 使用 Canvas 的視圖功能
                        try
                        {
#if NETFRAMEWORK
                            // 先選中組件 (Windows only)
                            doc.SelectObjects(components, true);
#else
                            // .NET 7.0 替代：使用 SelectedObjects 集合
                            doc.SelectedObjects().Clear();
                            foreach (var comp in components)
                            {
                                comp.Attributes.Selected = true;
                            }
#endif

                            // 嘗試使用 ZoomExtents 方法
                            var zoomMethod = canvas.GetType().GetMethod("ZoomExtents",
                                System.Reflection.BindingFlags.Public |
                                System.Reflection.BindingFlags.Instance);

                            if (zoomMethod != null)
                            {
                                zoomMethod.Invoke(canvas, null);
                            }
                            else
                            {
                                // 方法2: 手動設置視圖
                                var viewport = canvas.Viewport;
                                if (viewport != null)
                                {
                                    var viewportSize = viewport.Size;
                                    var scaleX = viewportSize.Width / width;
                                    var scaleY = viewportSize.Height / height;
                                    var scale = Math.Min(scaleX, scaleY) * 0.9f; // 90% 以留邊距

#if NETFRAMEWORK
                                    // 設置視圖中心 (Windows only)
                                    viewport.Pan = new System.Drawing.PointF(
                                        -centerX + viewportSize.Width / 2 / scale,
                                        -centerY + viewportSize.Height / 2 / scale
                                    );
#endif
                                    viewport.Zoom = scale;
                                    canvas.Refresh();
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            RhinoApp.WriteLine($"Warning: Could not zoom using standard method: {ex.Message}");
                            // 嘗試替代方法：刷新畫布
#if NETFRAMEWORK
                            doc.SelectObjects(components, true);
#endif
                            canvas.Refresh();
                        }
                    }
                    
                    result = new
                    {
                        success = true,
                        message = $"Zoomed to {components.Count} component(s)",
                        componentCount = components.Count,
                        componentIds = components.Select(c => c.InstanceGuid.ToString()).ToList(),
                        notFoundIds = notFoundIds
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in ZoomToComponents: {ex.Message}");
                }
            }));
            
            // 等待 UI 線程操作完成
            while (result == null && exception == null)
            {
                Thread.Sleep(10);
            }
            
            if (exception != null)
            {
                throw exception;
            }
            
            return result;
        }

        /// <summary>
        /// 通用的可變參數組件設定命令
        ///
        /// 此命令適用於所有實現 IGH_VariableParameterComponent 介面的 Grasshopper 組件，
        /// 包括但不限於：Entwine、Merge、List Item、Sort、Dispatch、Gate、Stream Filter、
        /// Expression、Concatenate、Format、Construct Path、Split Tree 等。
        ///
        /// 支援動態調整 Input 和 Output 兩側的參數數量。
        /// </summary>
        /// <param name="command">命令參數</param>
        /// <returns>操作結果</returns>
        /// <remarks>
        /// 參數說明：
        /// - id (必填): 組件的 InstanceGuid
        /// - side (必填): "input" 或 "output"，指定要調整哪一側的參數
        /// - count (必填): 目標參數數量
        ///
        /// 使用範例：
        /// 1. 設置 Entwine 組件為 6 個輸入分支：
        ///    { "id": "xxx", "side": "input", "count": 6 }
        ///
        /// 2. 設置 Merge 組件為 5 個輸入：
        ///    { "id": "xxx", "side": "input", "count": 5 }
        ///
        /// 3. 設置 Split Tree 組件為 4 個輸出：
        ///    { "id": "xxx", "side": "output", "count": 4 }
        ///
        /// 注意事項：
        /// - 如果組件不支援可變參數（未實現 IGH_VariableParameterComponent），會返回錯誤
        /// - 某些組件可能有最小參數數量限制
        /// - 調整後會自動觸發組件重新計算
        /// </remarks>
        public static object SetVariableParams(Command command)
        {
            string componentId = command.GetParameter<string>("id");
            string side = command.GetParameter<string>("side");
            int? count = command.GetParameter<int?>("count");

            // 參數驗證
            if (string.IsNullOrEmpty(componentId))
            {
                throw new ArgumentException("Component ID ('id') is required");
            }

            if (string.IsNullOrEmpty(side))
            {
                throw new ArgumentException("Parameter side ('side') is required. Use 'input' or 'output'.");
            }

            side = side.ToLowerInvariant();
            if (side != "input" && side != "output")
            {
                throw new ArgumentException($"Invalid side '{side}'. Must be 'input' or 'output'.");
            }

            if (!count.HasValue || count.Value < 0)
            {
                throw new ArgumentException("Parameter count ('count') must be a non-negative integer");
            }

            object result = null;
            Exception exception = null;

            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        throw new InvalidOperationException("No active Grasshopper document");
                    }

                    Guid guid;
                    if (!Guid.TryParse(componentId, out guid))
                    {
                        throw new ArgumentException($"Invalid component ID: {componentId}");
                    }

                    var component = doc.FindObject(guid, true) as IGH_Component;
                    if (component == null)
                    {
                        throw new ArgumentException($"Component not found or is not a component: {componentId}");
                    }

                    // 檢查是否支援可變參數
                    var variableParams = component as Grasshopper.Kernel.IGH_VariableParameterComponent;
                    if (variableParams == null)
                    {
                        throw new ArgumentException(
                            $"Component '{component.Name}' ({component.GetType().Name}) does not support variable parameters. " +
                            "Only components implementing IGH_VariableParameterComponent can use this command."
                        );
                    }

                    GH_ParameterSide paramSide = side == "input" ? GH_ParameterSide.Input : GH_ParameterSide.Output;
                    var paramList = side == "input" ? component.Params.Input : component.Params.Output;

                    int currentCount = paramList.Count;
                    int targetCount = count.Value;

                    int addedCount = 0;
                    int removedCount = 0;
                    var failedOperations = new List<string>();

                    // 添加參數
                    if (targetCount > currentCount)
                    {
                        for (int i = currentCount; i < targetCount; i++)
                        {
                            // 先檢查是否允許插入
                            if (!variableParams.CanInsertParameter(paramSide, i))
                            {
                                failedOperations.Add($"Cannot insert {side} parameter at index {i}");
                                continue;
                            }

                            // 創建新參數
                            var newParam = variableParams.CreateParameter(paramSide, i);
                            if (newParam == null)
                            {
                                failedOperations.Add($"CreateParameter returned null for {side} at index {i}");
                                continue;
                            }

                            // 註冊參數
                            if (side == "input")
                            {
                                component.Params.RegisterInputParam(newParam);
                            }
                            else
                            {
                                component.Params.RegisterOutputParam(newParam);
                            }
                            addedCount++;
                        }
                    }
                    // 移除參數（從後往前移除，避免索引錯位）
                    else if (targetCount < currentCount)
                    {
                        for (int i = currentCount - 1; i >= targetCount; i--)
                        {
                            // 先檢查是否允許移除
                            if (!variableParams.CanRemoveParameter(paramSide, i))
                            {
                                failedOperations.Add($"Cannot remove {side} parameter at index {i}");
                                continue;
                            }

                            // 通知組件即將移除參數
                            variableParams.DestroyParameter(paramSide, i);

                            // 取消註冊參數
                            if (side == "input")
                            {
                                component.Params.UnregisterInputParameter(component.Params.Input[i]);
                            }
                            else
                            {
                                component.Params.UnregisterOutputParameter(component.Params.Output[i]);
                            }
                            removedCount++;
                        }
                    }

                    // 觸發參數維護回調
                    variableParams.VariableParameterMaintenance();

                    // 通知參數變更並重新計算
                    component.Params.OnParametersChanged();
                    component.ExpireSolution(true);
                    doc.NewSolution(false);

                    // 收集更新後的參數資訊
                    var updatedParams = new List<object>();
                    var finalParamList = side == "input" ? component.Params.Input : component.Params.Output;
                    foreach (var param in finalParamList)
                    {
                        updatedParams.Add(new
                        {
                            index = finalParamList.IndexOf(param),
                            name = param.Name,
                            nickName = param.NickName,
                            typeName = param.TypeName
                        });
                    }

                    result = new
                    {
                        success = true,
                        message = $"Variable parameters updated: {addedCount} added, {removedCount} removed",
                        componentId = componentId,
                        componentName = component.Name,
                        componentType = component.GetType().Name,
                        side = side,
                        previousCount = currentCount,
                        targetCount = targetCount,
                        finalCount = finalParamList.Count,
                        addedCount = addedCount,
                        removedCount = removedCount,
                        parameters = updatedParams,
                        warnings = failedOperations.Count > 0 ? failedOperations : null
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in SetVariableParams: {ex.Message}");
                }
            }));

            while (result == null && exception == null)
            {
                Thread.Sleep(10);
            }

            if (exception != null)
            {
                throw exception;
            }

            return result;
        }

        /// <summary>
        /// 查詢組件是否支援可變參數，以及當前的參數狀態
        /// </summary>
        /// <param name="command">命令參數</param>
        /// <returns>組件的可變參數能力和當前狀態</returns>
        /// <remarks>
        /// 參數說明：
        /// - id (必填): 組件的 InstanceGuid
        ///
        /// 返回資訊包括：
        /// - 是否支援可變參數
        /// - 當前輸入/輸出參數數量
        /// - 每個參數是否可以添加/移除
        ///
        /// 使用此命令可以在調用 set_variable_params 之前，
        /// 先了解組件的能力和限制。
        /// </remarks>
        public static object GetVariableParamsInfo(Command command)
        {
            string componentId = command.GetParameter<string>("id");

            if (string.IsNullOrEmpty(componentId))
            {
                throw new ArgumentException("Component ID ('id') is required");
            }

            object result = null;
            Exception exception = null;

            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                    if (doc == null)
                    {
                        throw new InvalidOperationException("No active Grasshopper document");
                    }

                    Guid guid;
                    if (!Guid.TryParse(componentId, out guid))
                    {
                        throw new ArgumentException($"Invalid component ID: {componentId}");
                    }

                    var component = doc.FindObject(guid, true) as IGH_Component;
                    if (component == null)
                    {
                        throw new ArgumentException($"Component not found or is not a component: {componentId}");
                    }

                    var variableParams = component as Grasshopper.Kernel.IGH_VariableParameterComponent;
                    bool supportsVariable = variableParams != null;

                    // 收集輸入參數資訊
                    var inputParams = new List<object>();
                    for (int i = 0; i < component.Params.Input.Count; i++)
                    {
                        var param = component.Params.Input[i];
                        inputParams.Add(new
                        {
                            index = i,
                            name = param.Name,
                            nickName = param.NickName,
                            typeName = param.TypeName,
                            canInsertAfter = supportsVariable && variableParams.CanInsertParameter(GH_ParameterSide.Input, i + 1),
                            canRemove = supportsVariable && variableParams.CanRemoveParameter(GH_ParameterSide.Input, i)
                        });
                    }

                    // 收集輸出參數資訊
                    var outputParams = new List<object>();
                    for (int i = 0; i < component.Params.Output.Count; i++)
                    {
                        var param = component.Params.Output[i];
                        outputParams.Add(new
                        {
                            index = i,
                            name = param.Name,
                            nickName = param.NickName,
                            typeName = param.TypeName,
                            canInsertAfter = supportsVariable && variableParams.CanInsertParameter(GH_ParameterSide.Output, i + 1),
                            canRemove = supportsVariable && variableParams.CanRemoveParameter(GH_ParameterSide.Output, i)
                        });
                    }

                    // 測試是否可以在末尾添加參數
                    bool canAddInput = supportsVariable && variableParams.CanInsertParameter(GH_ParameterSide.Input, component.Params.Input.Count);
                    bool canAddOutput = supportsVariable && variableParams.CanInsertParameter(GH_ParameterSide.Output, component.Params.Output.Count);

                    result = new
                    {
                        componentId = componentId,
                        componentName = component.Name,
                        componentType = component.GetType().Name,
                        supportsVariableParams = supportsVariable,
                        input = new
                        {
                            count = component.Params.Input.Count,
                            canAddMore = canAddInput,
                            parameters = inputParams
                        },
                        output = new
                        {
                            count = component.Params.Output.Count,
                            canAddMore = canAddOutput,
                            parameters = outputParams
                        }
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in GetVariableParamsInfo: {ex.Message}");
                }
            }));

            while (result == null && exception == null)
            {
                Thread.Sleep(10);
            }

            if (exception != null)
            {
                throw exception;
            }

            return result;
        }

        // ========== 向後兼容的別名方法 ==========
        // 這些方法會調用通用的 SetVariableParams，保持 API 向後兼容

        /// <summary>
        /// [向後兼容] 設置 Entwine 組件的輸入數量
        /// 內部調用 SetVariableParams
        /// </summary>
        public static object SetEntwineInputs(Command command)
        {
            // 轉換參數格式
            var id = command.GetParameter<string>("id");
            var branchCount = command.GetParameter<int?>("branchCount");

            // 創建新命令調用通用方法
            var newCommand = new Command(
                "set_variable_params",
                new Dictionary<string, object>
                {
                    { "id", id },
                    { "side", "input" },
                    { "count", branchCount }
                }
            );

            return SetVariableParams(newCommand);
        }

        /// <summary>
        /// [向後兼容] 設置可變參數組件的輸入數量
        /// 內部調用 SetVariableParams
        /// </summary>
        public static object SetMergeInputs(Command command)
        {
            var id = command.GetParameter<string>("id");
            var inputCount = command.GetParameter<int?>("inputCount");

            var newCommand = new Command(
                "set_variable_params",
                new Dictionary<string, object>
                {
                    { "id", id },
                    { "side", "input" },
                    { "count", inputCount }
                }
            );

            return SetVariableParams(newCommand);
        }
    }
}
