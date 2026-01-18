using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using GH_MCP_Vision.AI;
using GH_MCP_Vision.Models;
using Grasshopper;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Special;
using Newtonsoft.Json;
using Rhino;

namespace GH_MCP_Vision.Commands
{
    /// <summary>
    /// 處理視覺相關命令 - 截圖、縮放等
    /// 優化版：使用 ManualResetEvent 代替輪詢，添加超時機制
    /// </summary>
    public static class VisionCommandHandler
    {
        // 默認超時時間 (毫秒)
        private const int DefaultTimeout = 10000;

        /// <summary>
        /// 執行 UI 線程操作並等待結果（帶超時）
        /// 學習自 GH_MCP 的最佳實踐
        /// </summary>
        private static T ExecuteOnUiThread<T>(Func<T> action, int timeoutMs = DefaultTimeout)
        {
            T result = default;
            Exception exception = null;
            var doneEvent = new ManualResetEvent(false);

            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    result = action();
                }
                catch (Exception ex)
                {
                    exception = ex;
                }
                finally
                {
                    doneEvent.Set();
                }
            }));

            // 等待結果（帶超時）
            if (!doneEvent.WaitOne(timeoutMs))
            {
                throw new TimeoutException($"Operation timed out after {timeoutMs}ms");
            }

            if (exception != null)
            {
                throw exception;
            }

            return result;
        }

        /// <summary>
        /// 截取 Grasshopper 畫布
        /// </summary>
        /// <param name="command">包含可選 bounds 參數的命令</param>
        /// <returns>Base64 編碼的 PNG 圖片</returns>
        public static object CaptureCanvas(VisionCommand command)
        {
            var boundsDict = command.GetParameter<Dictionary<string, object>>("bounds");

            return ExecuteOnUiThread(() =>
            {
                var canvas = Grasshopper.Instances.ActiveCanvas;
                if (canvas == null)
                {
                    throw new InvalidOperationException("No active Grasshopper canvas");
                }

                RectangleF sourceRect;

                // 決定截取區域
                if (boundsDict != null &&
                    boundsDict.ContainsKey("x") && boundsDict.ContainsKey("y") &&
                    boundsDict.ContainsKey("width") && boundsDict.ContainsKey("height"))
                {
                    float x = Convert.ToSingle(boundsDict["x"]);
                    float y = Convert.ToSingle(boundsDict["y"]);
                    float w = Convert.ToSingle(boundsDict["width"]);
                    float h = Convert.ToSingle(boundsDict["height"]);
                    sourceRect = new RectangleF(x, y, w, h);
                }
                else
                {
                    // 默認截取整個文檔內容
                    if (canvas.Document == null || canvas.Document.ObjectCount == 0)
                    {
                        var viewBounds = canvas.Viewport.VisibleRegion;
                        sourceRect = new RectangleF(viewBounds.Left, viewBounds.Top, 1000, 800);
                    }
                    else
                    {
                        sourceRect = canvas.Document.BoundingBox(false);
                        sourceRect.Inflate(50, 50);
                    }
                }

                // 決定輸出尺寸
                int maxDimension = 2000;
                int imgW, imgH;
                float aspect = sourceRect.Width / sourceRect.Height;

                if (sourceRect.Width > sourceRect.Height)
                {
                    imgW = Math.Min((int)(sourceRect.Width * 2.0), maxDimension);
                    if (imgW < 800) imgW = 800;
                    imgH = (int)(imgW / aspect);
                }
                else
                {
                    imgH = Math.Min((int)(sourceRect.Height * 2.0), maxDimension);
                    if (imgH < 600) imgH = 600;
                    imgW = (int)(imgH * aspect);
                }

                Rectangle intSourceRect = Rectangle.Round(sourceRect);
                Bitmap bitmap = null;

                try
                {
                    // 嘗試使用 CreateBitmap 方法
                    var createBitmapMethod = canvas.GetType().GetMethod("CreateBitmap",
                        System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance,
                        null,
                        new[] { typeof(Rectangle), typeof(float) },
                        null);

                    if (createBitmapMethod != null)
                    {
                        float zoom = Math.Max(1.0f, Math.Min((float)imgW / sourceRect.Width, (float)imgH / sourceRect.Height));
                        bitmap = createBitmapMethod.Invoke(canvas, new object[] { intSourceRect, zoom }) as Bitmap;
                    }
                    else
                    {
                        // 備用方案：使用控件截圖
                        bitmap = new Bitmap(canvas.Width, canvas.Height);
                        canvas.DrawToBitmap(bitmap, new Rectangle(0, 0, canvas.Width, canvas.Height));
                    }

                    if (bitmap == null)
                    {
                        throw new Exception("Failed to generate canvas image");
                    }

                    // 轉換為 Base64
                    using (MemoryStream ms = new MemoryStream())
                    {
                        bitmap.Save(ms, ImageFormat.Png);
                        string base64String = Convert.ToBase64String(ms.ToArray());

                        return new
                        {
                            image = base64String,
                            width = bitmap.Width,
                            height = bitmap.Height,
                            format = "png",
                            bounds = new { x = sourceRect.X, y = sourceRect.Y, width = sourceRect.Width, height = sourceRect.Height }
                        };
                    }
                }
                finally
                {
                    bitmap?.Dispose();
                }
            });
        }

        /// <summary>
        /// 截取 Rhino 3D 視圖
        /// </summary>
        public static object CaptureRhinoView(VisionCommand command)
        {
            int width = command.GetParameter<int>("width");
            int height = command.GetParameter<int>("height");

            if (width <= 0) width = 1920;
            if (height <= 0) height = 1080;

            return ExecuteOnUiThread(() =>
            {
                var view = RhinoDoc.ActiveDoc?.Views?.ActiveView;
                if (view == null)
                {
                    throw new InvalidOperationException("No active Rhino view");
                }

                var size = new Size(width, height);

                using (var bitmap = view.CaptureToBitmap(size))
                {
                    if (bitmap == null)
                    {
                        throw new Exception("Failed to capture Rhino view");
                    }

                    using (MemoryStream ms = new MemoryStream())
                    {
                        bitmap.Save(ms, ImageFormat.Png);
                        string base64 = Convert.ToBase64String(ms.ToArray());
                        return new
                        {
                            image = base64,
                            width = bitmap.Width,
                            height = bitmap.Height,
                            format = "png"
                        };
                    }
                }
            });
        }

        /// <summary>
        /// 縮放到指定組件
        /// </summary>
        public static object ZoomToComponents(VisionCommand command)
        {
            var componentIds = command.GetParameter<List<string>>("componentIds");

            if (componentIds == null || componentIds.Count == 0)
            {
                throw new ArgumentException("At least one component ID is required");
            }

            return ExecuteOnUiThread(() =>
            {
                var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                var canvas = Grasshopper.Instances.ActiveCanvas;

                if (doc == null)
                {
                    throw new InvalidOperationException("No active Grasshopper document");
                }

                var components = new List<IGH_DocumentObject>();
                var notFoundIds = new List<string>();

                foreach (var idStr in componentIds)
                {
                    if (!Guid.TryParse(idStr, out Guid guid))
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

                // 計算邊界框
                RectangleF? combinedBounds = null;

                foreach (var component in components)
                {
                    if (component.Attributes != null)
                    {
                        var bounds = component.Attributes.Bounds;
                        combinedBounds = combinedBounds.HasValue
                            ? RectangleF.Union(combinedBounds.Value, bounds)
                            : bounds;
                    }
                }

                if (combinedBounds.HasValue)
                {
                    // 選中組件
                    foreach (var comp in components)
                    {
                        comp.Attributes.Selected = true;
                    }

                    // 嘗試縮放
                    try
                    {
                        var zoomMethod = canvas.GetType().GetMethod("ZoomExtents",
                            System.Reflection.BindingFlags.Public |
                            System.Reflection.BindingFlags.Instance);

                        if (zoomMethod != null)
                        {
                            zoomMethod.Invoke(canvas, null);
                        }
                    }
                    catch { }

                    canvas.Refresh();
                }

                return new
                {
                    success = true,
                    message = $"Zoomed to {components.Count} component(s)",
                    componentCount = components.Count,
                    notFoundIds = notFoundIds
                };
            });
        }

        /// <summary>
        /// 縮放到全部物件
        /// </summary>
        public static object ZoomExtents(VisionCommand command)
        {
            return ExecuteOnUiThread(() =>
            {
                var canvas = Grasshopper.Instances.ActiveCanvas;
                if (canvas == null)
                {
                    throw new InvalidOperationException("No active Grasshopper canvas");
                }

                try
                {
                    var zoomMethod = canvas.GetType().GetMethod("ZoomExtents",
                        System.Reflection.BindingFlags.Public |
                        System.Reflection.BindingFlags.Instance);

                    if (zoomMethod != null)
                    {
                        zoomMethod.Invoke(canvas, null);
                    }
                }
                catch { }

                canvas.Refresh();

                return new
                {
                    success = true,
                    message = "Zoomed to extents"
                };
            });
        }

        /// <summary>
        /// 獲取畫布信息
        /// </summary>
        public static object GetCanvasInfo(VisionCommand command)
        {
            return ExecuteOnUiThread(() =>
            {
                var canvas = Grasshopper.Instances.ActiveCanvas;
                var doc = canvas?.Document;

                if (canvas == null || doc == null)
                {
                    throw new InvalidOperationException("No active Grasshopper canvas");
                }

                var bounds = doc.BoundingBox(false);
                var viewport = canvas.Viewport;

                return new
                {
                    objectCount = doc.ObjectCount,
                    boundsInfo = new { x = bounds.X, y = bounds.Y, width = bounds.Width, height = bounds.Height },
                    viewport = new
                    {
                        zoom = viewport.Zoom,
                        midPoint = new { x = viewport.MidPoint.X, y = viewport.MidPoint.Y }
                    }
                };
            });
        }

        /// <summary>
        /// 獲取組件連線診斷信息（新功能）
        /// 學習自 GH_MCP 的連線驗證邏輯
        /// </summary>
        public static object GetConnectionDiagnostics(VisionCommand command)
        {
            var componentId = command.GetParameter<string>("componentId");

            if (string.IsNullOrEmpty(componentId))
            {
                throw new ArgumentException("Component ID is required");
            }

            return ExecuteOnUiThread(() =>
            {
                var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                if (doc == null)
                {
                    throw new InvalidOperationException("No active Grasshopper document");
                }

                if (!Guid.TryParse(componentId, out Guid guid))
                {
                    throw new ArgumentException($"Invalid GUID format: {componentId}");
                }

                var component = doc.FindObject(guid, true);
                if (component == null)
                {
                    throw new ArgumentException($"Component not found: {componentId}");
                }

                // 收集連線信息
                var inputConnections = new List<object>();
                var outputConnections = new List<object>();

                if (component is IGH_Component ghComp)
                {
                    // 輸入參數的連線
                    foreach (var input in ghComp.Params.Input)
                    {
                        var sources = new List<object>();
                        for (int i = 0; i < input.SourceCount; i++)
                        {
                            var source = input.Sources[i];
                            var sourceOwner = source.Attributes?.GetTopLevel?.DocObject;
                            sources.Add(new
                            {
                                sourceId = source.InstanceGuid.ToString(),
                                sourceName = source.Name,
                                sourceNickName = source.NickName,
                                sourceOwnerId = sourceOwner?.InstanceGuid.ToString(),
                                sourceOwnerName = sourceOwner?.Name
                            });
                        }

                        inputConnections.Add(new
                        {
                            paramName = input.Name,
                            paramNickName = input.NickName,
                            sourceCount = input.SourceCount,
                            sources = sources,
                            hasData = input.VolatileDataCount > 0
                        });
                    }

                    // 輸出參數的連線
                    foreach (var output in ghComp.Params.Output)
                    {
                        var recipients = new List<object>();
                        foreach (var recipient in output.Recipients)
                        {
                            var recipientOwner = recipient.Attributes?.GetTopLevel?.DocObject;
                            recipients.Add(new
                            {
                                targetId = recipient.InstanceGuid.ToString(),
                                targetName = recipient.Name,
                                targetNickName = recipient.NickName,
                                targetOwnerId = recipientOwner?.InstanceGuid.ToString(),
                                targetOwnerName = recipientOwner?.Name
                            });
                        }

                        outputConnections.Add(new
                        {
                            paramName = output.Name,
                            paramNickName = output.NickName,
                            recipientCount = output.Recipients.Count,
                            recipients = recipients,
                            hasData = output.VolatileDataCount > 0
                        });
                    }
                }

                return new
                {
                    componentId = componentId,
                    componentName = component.Name,
                    componentNickName = component.NickName,
                    typeName = component.GetType().Name,
                    inputs = inputConnections,
                    outputs = outputConnections,
                    hasErrors = component is IGH_ActiveObject active && active.RuntimeMessages(GH_RuntimeMessageLevel.Error).Count > 0,
                    hasWarnings = component is IGH_ActiveObject activeW && activeW.RuntimeMessages(GH_RuntimeMessageLevel.Warning).Count > 0
                };
            });
        }

        /// <summary>
        /// 驗證組件是否存在（批量驗證）
        /// 用於在執行操作前先確認組件有效
        /// </summary>
        public static object ValidateComponents(VisionCommand command)
        {
            var componentIds = command.GetParameter<List<string>>("componentIds");

            if (componentIds == null || componentIds.Count == 0)
            {
                throw new ArgumentException("At least one component ID is required");
            }

            return ExecuteOnUiThread(() =>
            {
                var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                if (doc == null)
                {
                    throw new InvalidOperationException("No active Grasshopper document");
                }

                var results = new List<object>();
                int validCount = 0;
                int invalidCount = 0;

                foreach (var idStr in componentIds)
                {
                    bool isValid = false;
                    string status = "invalid";
                    string name = null;
                    string typeName = null;

                    if (Guid.TryParse(idStr, out Guid guid))
                    {
                        var component = doc.FindObject(guid, true);
                        if (component != null)
                        {
                            isValid = true;
                            status = "valid";
                            name = component.Name;
                            typeName = component.GetType().Name;
                            validCount++;
                        }
                        else
                        {
                            status = "not_found";
                            invalidCount++;
                        }
                    }
                    else
                    {
                        status = "invalid_guid";
                        invalidCount++;
                    }

                    results.Add(new
                    {
                        id = idStr,
                        valid = isValid,
                        status = status,
                        name = name,
                        typeName = typeName
                    });
                }

                return new
                {
                    totalCount = componentIds.Count,
                    validCount = validCount,
                    invalidCount = invalidCount,
                    allValid = invalidCount == 0,
                    results = results
                };
            });
        }

        /// <summary>
        /// 獲取組件的參數詳細信息
        /// 包含 Name 和 NickName，用於正確連線
        /// 學習自 GH_MCP 的 get_component_info 命令
        /// </summary>
        public static object GetComponentParams(VisionCommand command)
        {
            var componentId = command.GetParameter<string>("componentId");

            if (string.IsNullOrEmpty(componentId))
            {
                throw new ArgumentException("Component ID is required");
            }

            return ExecuteOnUiThread(() =>
            {
                var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                if (doc == null)
                {
                    throw new InvalidOperationException("No active Grasshopper document");
                }

                if (!Guid.TryParse(componentId, out Guid guid))
                {
                    throw new ArgumentException($"Invalid GUID format: {componentId}");
                }

                var component = doc.FindObject(guid, true);
                if (component == null)
                {
                    throw new ArgumentException($"Component not found: {componentId}");
                }

                var inputs = new List<object>();
                var outputs = new List<object>();

                if (component is IGH_Component ghComp)
                {
                    // 輸入參數
                    for (int i = 0; i < ghComp.Params.Input.Count; i++)
                    {
                        var param = ghComp.Params.Input[i];
                        inputs.Add(new
                        {
                            index = i,
                            name = param.Name,
                            nickName = param.NickName,
                            typeName = param.GetType().Name,
                            description = param.Description,
                            isOptional = param.Optional,
                            sourceCount = param.SourceCount,
                            hasData = param.VolatileDataCount > 0
                        });
                    }

                    // 輸出參數
                    for (int i = 0; i < ghComp.Params.Output.Count; i++)
                    {
                        var param = ghComp.Params.Output[i];
                        outputs.Add(new
                        {
                            index = i,
                            name = param.Name,
                            nickName = param.NickName,
                            typeName = param.GetType().Name,
                            description = param.Description,
                            recipientCount = param.Recipients.Count,
                            hasData = param.VolatileDataCount > 0
                        });
                    }
                }
                else if (component is IGH_Param paramComp)
                {
                    // 獨立參數組件（如 Number Slider）
                    outputs.Add(new
                    {
                        index = 0,
                        name = paramComp.Name,
                        nickName = paramComp.NickName,
                        typeName = paramComp.GetType().Name,
                        description = paramComp.Description,
                        recipientCount = paramComp.Recipients.Count,
                        hasData = paramComp.VolatileDataCount > 0
                    });
                }

                return new
                {
                    componentId = componentId,
                    name = component.Name,
                    nickName = component.NickName,
                    typeName = component.GetType().Name,
                    category = component.Category,
                    subCategory = component.SubCategory,
                    inputs = inputs,
                    outputs = outputs,
                    // 提供連線時推薦使用的參數名
                    connectionTips = new
                    {
                        useNickNameForInputs = true,  // v2.0+ NickName 優先
                        useNickNameForOutputs = true,
                        inputExample = inputs.Count > 0 ? $"targetParam: \"{((dynamic)inputs[0]).nickName}\"" : null,
                        outputExample = outputs.Count > 0 ? $"sourceParam: \"{((dynamic)outputs[0]).nickName}\"" : null
                    }
                };
            });
        }

        /// <summary>
        /// 導出組件庫 - 從 ComponentServer 獲取所有已安裝組件的完整信息
        /// 這是避免 GUID 錯誤和參數名混淆的關鍵功能
        /// </summary>
        public static object ExportComponentLibrary(VisionCommand command)
        {
            // 可選參數
            var outputPath = command.GetParameter<string>("outputPath");
            var categoryFilter = command.GetParameter<string>("category");
            var libraryFilter = command.GetParameter<string>("library");
            var includeObsolete = command.GetParameter<bool>("includeObsolete");
            var limit = command.GetParameter<int>("limit");

            return ExecuteOnUiThread(() =>
            {
                var componentServer = Grasshopper.Instances.ComponentServer;
                if (componentServer == null)
                {
                    throw new InvalidOperationException("ComponentServer not available");
                }

                var allProxies = componentServer.ObjectProxies;
                RhinoApp.WriteLine($"[GH_MCP_Vision] Found {allProxies.Count} object proxies");

                var components = new List<Dictionary<string, object>>();
                var statistics = new Dictionary<string, int>();
                int processedCount = 0;
                int skippedObsolete = 0;
                int errorCount = 0;

                foreach (var proxy in allProxies)
                {
                    try
                    {
                        // 檢查是否為過期組件
                        bool isObsolete = proxy.Obsolete;
                        if (isObsolete && !includeObsolete)
                        {
                            skippedObsolete++;
                            continue;
                        }

                        // 獲取組件描述
                        var desc = proxy.Desc;
                        if (desc == null) continue;

                        // 類別過濾
                        if (!string.IsNullOrEmpty(categoryFilter) &&
                            !desc.Category.Equals(categoryFilter, StringComparison.OrdinalIgnoreCase))
                        {
                            continue;
                        }

                        // 獲取所屬庫
                        string libraryName = null;
                        try
                        {
                            var assembly = componentServer.FindAssemblyByObject(proxy.Guid);
                            libraryName = assembly?.Name;
                        }
                        catch { }

                        // 庫過濾
                        if (!string.IsNullOrEmpty(libraryFilter) &&
                            (libraryName == null || !libraryName.Contains(libraryFilter)))
                        {
                            continue;
                        }

                        // 統計庫數量
                        string libKey = libraryName ?? "Unknown";
                        if (!statistics.ContainsKey(libKey))
                            statistics[libKey] = 0;
                        statistics[libKey]++;

                        // 創建組件實例以獲取參數信息
                        var inputs = new List<Dictionary<string, object>>();
                        var outputs = new List<Dictionary<string, object>>();

                        try
                        {
                            var instance = proxy.CreateInstance();

                            if (instance is IGH_Component ghComp)
                            {
                                // 輸入參數
                                foreach (var param in ghComp.Params.Input)
                                {
                                    inputs.Add(new Dictionary<string, object>
                                    {
                                        ["name"] = param.Name,
                                        ["nickName"] = param.NickName,
                                        ["typeName"] = param.TypeName,
                                        ["description"] = param.Description ?? "",
                                        ["optional"] = param.Optional
                                    });
                                }

                                // 輸出參數
                                foreach (var param in ghComp.Params.Output)
                                {
                                    outputs.Add(new Dictionary<string, object>
                                    {
                                        ["name"] = param.Name,
                                        ["nickName"] = param.NickName,
                                        ["typeName"] = param.TypeName,
                                        ["description"] = param.Description ?? ""
                                    });
                                }
                            }
                            else if (instance is IGH_Param paramComp)
                            {
                                // 獨立參數（如 Number Slider）
                                outputs.Add(new Dictionary<string, object>
                                {
                                    ["name"] = paramComp.Name,
                                    ["nickName"] = paramComp.NickName,
                                    ["typeName"] = paramComp.TypeName,
                                    ["description"] = paramComp.Description ?? ""
                                });
                            }
                        }
                        catch
                        {
                            // 某些組件無法實例化，跳過參數收集
                        }

                        // 構建組件信息
                        var compInfo = new Dictionary<string, object>
                        {
                            ["guid"] = proxy.Guid.ToString(),
                            ["name"] = desc.Name,
                            ["nickName"] = desc.NickName,
                            ["description"] = desc.Description ?? "",
                            ["category"] = desc.Category,
                            ["subCategory"] = desc.SubCategory,
                            ["library"] = libraryName,
                            ["isObsolete"] = isObsolete,
                            ["exposure"] = proxy.Exposure.ToString(),
                            ["inputs"] = inputs,
                            ["outputs"] = outputs
                        };

                        components.Add(compInfo);
                        processedCount++;

                        // 限制數量
                        if (limit > 0 && processedCount >= limit)
                            break;
                    }
                    catch (Exception ex)
                    {
                        errorCount++;
                        RhinoApp.WriteLine($"[GH_MCP_Vision] Error processing proxy: {ex.Message}");
                    }
                }

                RhinoApp.WriteLine($"[GH_MCP_Vision] Processed {processedCount} components, skipped {skippedObsolete} obsolete, {errorCount} errors");

                // 如果指定輸出路徑，寫入 JSON 文件
                string savedPath = null;
                if (!string.IsNullOrEmpty(outputPath))
                {
                    try
                    {
                        var exportData = new Dictionary<string, object>
                        {
                            ["exportTime"] = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
                            ["totalCount"] = components.Count,
                            ["statistics"] = statistics,
                            ["components"] = components
                        };

                        string json = JsonConvert.SerializeObject(exportData, Formatting.Indented);
                        File.WriteAllText(outputPath, json, Encoding.UTF8);
                        savedPath = outputPath;
                        RhinoApp.WriteLine($"[GH_MCP_Vision] Exported to: {outputPath}");
                    }
                    catch (Exception ex)
                    {
                        RhinoApp.WriteLine($"[GH_MCP_Vision] Failed to save file: {ex.Message}");
                    }
                }

                return new
                {
                    success = true,
                    totalProxies = allProxies.Count,
                    processedCount = processedCount,
                    skippedObsolete = skippedObsolete,
                    errorCount = errorCount,
                    statistics = statistics,
                    savedPath = savedPath,
                    // 如果未保存到文件，返回組件列表（注意：可能很大）
                    components = string.IsNullOrEmpty(outputPath) ? components : null,
                    message = $"Exported {processedCount} components from {statistics.Count} libraries"
                };
            }, 60000); // 60 秒超時（組件數量多時需要較長時間）
        }

        /// <summary>
        /// 搜索組件 - 根據名稱搜索並返回候選組件
        /// 優先返回內建組件，標記過期組件
        /// </summary>
        public static object SearchComponents(VisionCommand command)
        {
            var searchName = command.GetParameter<string>("name");
            var maxResults = command.GetParameter<int>("maxResults");
            var preferBuiltIn = command.GetParameter<bool>("preferBuiltIn");

            if (string.IsNullOrEmpty(searchName))
            {
                throw new ArgumentException("Search name is required");
            }

            if (maxResults <= 0) maxResults = 10;

            return ExecuteOnUiThread(() =>
            {
                var componentServer = Grasshopper.Instances.ComponentServer;
                if (componentServer == null)
                {
                    throw new InvalidOperationException("ComponentServer not available");
                }

                var candidates = new List<Dictionary<string, object>>();
                var searchLower = searchName.ToLowerInvariant();

                // 內建庫列表（優先級高）
                var builtInLibraries = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
                {
                    "Grasshopper",
                    "MathComponents",
                    "CurveComponents",
                    "SurfaceComponents",
                    "MeshComponents",
                    "TransformComponents",
                    "VectorComponents",
                    "SetComponents",
                    "FieldComponents",
                    "IntersectComponents",
                    "DisplayComponents"
                };

                foreach (var proxy in componentServer.ObjectProxies)
                {
                    try
                    {
                        var desc = proxy.Desc;
                        if (desc == null) continue;

                        // 檢查名稱匹配（NickName 優先，然後 Name）
                        bool nickNameMatch = desc.NickName.Equals(searchName, StringComparison.OrdinalIgnoreCase);
                        bool nameMatch = desc.Name.Equals(searchName, StringComparison.OrdinalIgnoreCase);
                        bool partialMatch = desc.Name.ToLowerInvariant().Contains(searchLower) ||
                                           desc.NickName.ToLowerInvariant().Contains(searchLower);

                        if (!nickNameMatch && !nameMatch && !partialMatch)
                            continue;

                        // 獲取庫信息
                        string libraryName = null;
                        try
                        {
                            var assembly = componentServer.FindAssemblyByObject(proxy.Guid);
                            libraryName = assembly?.Name;
                        }
                        catch { }

                        bool isBuiltIn = libraryName != null && builtInLibraries.Contains(libraryName);

                        // 計算匹配分數
                        int score = 0;
                        if (nickNameMatch) score += 100;
                        else if (nameMatch) score += 80;
                        else score += 20;

                        if (isBuiltIn) score += 50;
                        if (proxy.Obsolete) score -= 100;

                        candidates.Add(new Dictionary<string, object>
                        {
                            ["guid"] = proxy.Guid.ToString(),
                            ["name"] = desc.Name,
                            ["nickName"] = desc.NickName,
                            ["category"] = desc.Category,
                            ["subCategory"] = desc.SubCategory,
                            ["library"] = libraryName,
                            ["isBuiltIn"] = isBuiltIn,
                            ["isObsolete"] = proxy.Obsolete,
                            ["matchType"] = nickNameMatch ? "exactNickName" : (nameMatch ? "exactName" : "partial"),
                            ["score"] = score
                        });
                    }
                    catch { }
                }

                // 排序：分數高的優先
                var sortedCandidates = candidates
                    .OrderByDescending(c => (int)c["score"])
                    .Take(maxResults)
                    .ToList();

                // 建議最佳選擇
                var recommended = sortedCandidates.FirstOrDefault();

                return new
                {
                    searchName = searchName,
                    totalFound = candidates.Count,
                    returnedCount = sortedCandidates.Count,
                    recommended = recommended,
                    candidates = sortedCandidates,
                    tip = recommended != null && (bool)recommended["isObsolete"]
                        ? "Warning: Recommended component is obsolete, consider alternatives"
                        : null
                };
            });
        }

        // =========================================================================
        // AI 智能診斷功能
        // =========================================================================

        /// <summary>
        /// 診斷連接失敗原因（使用 Gemini AI）
        /// </summary>
        public static object DiagnoseConnection(VisionCommand command)
        {
            var sourceComponent = command.GetParameter<string>("sourceComponent");
            var targetComponent = command.GetParameter<string>("targetComponent");
            var errorMessage = command.GetParameter<string>("errorMessage");

            if (string.IsNullOrEmpty(sourceComponent) || string.IsNullOrEmpty(targetComponent))
            {
                throw new ArgumentException("sourceComponent and targetComponent are required");
            }

            RhinoApp.WriteLine($"[GH_MCP_Vision] AI diagnosing: {sourceComponent} → {targetComponent}");

            var result = GeminiHelper.DiagnoseConnectionFailure(
                sourceComponent,
                targetComponent,
                errorMessage ?? "Unknown error"
            );

            return new
            {
                success = result.Success,
                cause = result.Cause,
                correctParams = result.CorrectParams != null ? new
                {
                    source = result.CorrectParams.Source,
                    target = result.CorrectParams.Target
                } : null,
                solution = result.Solution,
                error = result.Error,
                rawResponse = result.RawResponse
            };
        }

        /// <summary>
        /// 自動修復連接（AI 診斷 + 嘗試重連）
        /// </summary>
        public static object AutoFixConnection(VisionCommand command)
        {
            var sourceId = command.GetParameter<string>("sourceId");
            var targetId = command.GetParameter<string>("targetId");
            var sourceParam = command.GetParameter<string>("sourceParam");
            var targetParam = command.GetParameter<string>("targetParam");
            var errorMessage = command.GetParameter<string>("errorMessage");

            if (string.IsNullOrEmpty(sourceId) || string.IsNullOrEmpty(targetId))
            {
                throw new ArgumentException("sourceId and targetId are required");
            }

            return ExecuteOnUiThread<object>(() =>
            {
                var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                if (doc == null)
                {
                    throw new InvalidOperationException("No active Grasshopper document");
                }

                // 1. 查找組件
                if (!Guid.TryParse(sourceId, out Guid srcGuid) || !Guid.TryParse(targetId, out Guid tgtGuid))
                {
                    throw new ArgumentException("Invalid GUID format");
                }

                var sourceObj = doc.FindObject(srcGuid, true);
                var targetObj = doc.FindObject(tgtGuid, true);

                if (sourceObj == null || targetObj == null)
                {
                    throw new ArgumentException("Component not found");
                }

                string sourceName = sourceObj.Name;
                string targetName = targetObj.Name;

                // 2. 調用 AI 診斷
                RhinoApp.WriteLine($"[GH_MCP_Vision] AI diagnosing: {sourceName}.{sourceParam} → {targetName}.{targetParam}");

                var diagnosis = GeminiHelper.DiagnoseConnectionFailure(
                    $"{sourceName}.{sourceParam}",
                    $"{targetName}.{targetParam}",
                    errorMessage ?? "Connection failed"
                );

                if (!diagnosis.Success || diagnosis.CorrectParams == null)
                {
                    return new
                    {
                        wasFixed = false,
                        message = "AI diagnosis failed or no suggestion",
                        diagnosisResult = new
                        {
                            cause = diagnosis.Cause,
                            solution = diagnosis.Solution
                        }
                    };
                }

                // 3. 獲取建議的參數名
                string suggestedSource = diagnosis.CorrectParams.Source ?? sourceParam;
                string suggestedTarget = diagnosis.CorrectParams.Target ?? targetParam;

                // 4. 嘗試用建議的參數連接
                IGH_Param srcParam = null;
                IGH_Param tgtParam = null;

                // 從源組件獲取輸出參數
                if (sourceObj is IGH_Component srcComp)
                {
                    srcParam = srcComp.Params.Output
                        .FirstOrDefault(p => p.NickName.Equals(suggestedSource, StringComparison.OrdinalIgnoreCase) ||
                                            p.Name.Equals(suggestedSource, StringComparison.OrdinalIgnoreCase));
                }
                else if (sourceObj is IGH_Param srcP)
                {
                    srcParam = srcP;
                }

                // 從目標組件獲取輸入參數
                if (targetObj is IGH_Component tgtComp)
                {
                    tgtParam = tgtComp.Params.Input
                        .FirstOrDefault(p => p.NickName.Equals(suggestedTarget, StringComparison.OrdinalIgnoreCase) ||
                                            p.Name.Equals(suggestedTarget, StringComparison.OrdinalIgnoreCase));
                }

                if (srcParam == null || tgtParam == null)
                {
                    return new
                    {
                        wasFixed = false,
                        message = $"Could not find parameters: source={suggestedSource}, target={suggestedTarget}",
                        diagnosisResult = new
                        {
                            cause = diagnosis.Cause,
                            suggestedParams = new { source = suggestedSource, target = suggestedTarget }
                        }
                    };
                }

                // 5. 嘗試連接
                int countBefore = tgtParam.SourceCount;
                tgtParam.AddSource(srcParam);
                int countAfter = tgtParam.SourceCount;

                bool connected = countAfter > countBefore;

                if (connected)
                {
                    doc.NewSolution(true, GH_SolutionMode.Silent);
                    Grasshopper.Instances.ActiveCanvas?.Invalidate();

                    RhinoApp.WriteLine($"[GH_MCP_Vision] Auto-fix successful: {sourceName}.{suggestedSource} → {targetName}.{suggestedTarget}");
                }

                return new
                {
                    wasFixed = connected,
                    usedParams = new
                    {
                        source = srcParam.NickName,
                        target = tgtParam.NickName
                    },
                    message = connected
                        ? $"Connection fixed using {srcParam.NickName} → {tgtParam.NickName}"
                        : "Connection attempt failed",
                    diagnosisResult = new
                    {
                        cause = diagnosis.Cause,
                        solution = diagnosis.Solution
                    }
                };
            });
        }

        /// <summary>
        /// 從失敗中學習（批量分析模式）
        /// </summary>
        public static object LearnFromFailure(VisionCommand command)
        {
            var failuresRaw = command.GetParameter<List<object>>("failures");

            if (failuresRaw == null || failuresRaw.Count == 0)
            {
                throw new ArgumentException("failures array is required");
            }

            // 轉換為 FailureRecord
            var failures = new List<FailureRecord>();
            foreach (var item in failuresRaw)
            {
                if (item is Dictionary<string, object> dict)
                {
                    failures.Add(new FailureRecord
                    {
                        SourceComponent = dict.TryGetValue("sourceComponent", out var sc) ? sc?.ToString() : "",
                        SourceParam = dict.TryGetValue("sourceParam", out var sp) ? sp?.ToString() : "",
                        TargetComponent = dict.TryGetValue("targetComponent", out var tc) ? tc?.ToString() : "",
                        TargetParam = dict.TryGetValue("targetParam", out var tp) ? tp?.ToString() : "",
                        ErrorMessage = dict.TryGetValue("errorMessage", out var em) ? em?.ToString() : ""
                    });
                }
            }

            if (failures.Count == 0)
            {
                throw new ArgumentException("No valid failure records found");
            }

            RhinoApp.WriteLine($"[GH_MCP_Vision] Learning from {failures.Count} failures...");

            // 調用 Gemini 分析
            var result = GeminiHelper.AnalyzeFailurePatterns(failures);

            // 如果成功，保存到本地知識庫
            if (result.Success && result.PatternsLearned != null)
            {
                try
                {
                    SaveLearnedPatterns(result);
                }
                catch (Exception ex)
                {
                    RhinoApp.WriteLine($"[GH_MCP_Vision] Failed to save patterns: {ex.Message}");
                }
            }

            return new
            {
                success = result.Success,
                patternsLearned = result.PatternsLearned?.Select(p => new
                {
                    pattern = p.Pattern,
                    frequency = p.Frequency,
                    fix = p.Fix
                }).ToList(),
                suggestions = result.Suggestions,
                commonMistakes = result.CommonMistakes,
                error = result.Error
            };
        }

        /// <summary>
        /// 保存學習到的模式到本地文件
        /// </summary>
        private static void SaveLearnedPatterns(PatternAnalysisResult result)
        {
            string baseDir = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            string knowledgeDir = Path.Combine(baseDir, ".gh_mcp_knowledge");

            if (!Directory.Exists(knowledgeDir))
            {
                Directory.CreateDirectory(knowledgeDir);
            }

            string filePath = Path.Combine(knowledgeDir, "learned_patterns.json");

            // 讀取現有模式（如果有）
            var existingPatterns = new List<PatternInfo>();
            if (File.Exists(filePath))
            {
                try
                {
                    string existing = File.ReadAllText(filePath);
                    var data = JsonConvert.DeserializeObject<Dictionary<string, object>>(existing);
                    if (data != null && data.TryGetValue("patterns", out var patterns))
                    {
                        existingPatterns = JsonConvert.DeserializeObject<List<PatternInfo>>(
                            JsonConvert.SerializeObject(patterns)
                        ) ?? new List<PatternInfo>();
                    }
                }
                catch { }
            }

            // 合併新模式
            if (result.PatternsLearned != null)
            {
                existingPatterns.AddRange(result.PatternsLearned);
            }

            // 保存
            var saveData = new Dictionary<string, object>
            {
                ["lastUpdated"] = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"),
                ["totalPatterns"] = existingPatterns.Count,
                ["patterns"] = existingPatterns,
                ["suggestions"] = result.Suggestions ?? new List<string>()
            };

            File.WriteAllText(filePath, JsonConvert.SerializeObject(saveData, Formatting.Indented));
            RhinoApp.WriteLine($"[GH_MCP_Vision] Saved {existingPatterns.Count} patterns to {filePath}");
        }
    }
}
