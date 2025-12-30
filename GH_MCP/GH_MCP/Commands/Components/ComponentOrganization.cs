using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using GrasshopperMCP.Models;
using Grasshopper;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Special;
using Rhino;

namespace GH_MCP.Commands.Components
{
    /// <summary>
    /// 處理組件組織相關的命令
    /// </summary>
    public static class ComponentOrganization
    {
        /// <summary>
        /// 將多個元件群組起來
        /// </summary>
        /// <param name="command">包含 componentIds 的命令</param>
        /// <returns>群組資訊</returns>
        public static object GroupComponents(Command command)
        {
            var ids = command.GetParameter<List<string>>("componentIds");
            if (ids == null || ids.Count == 0)
                throw new ArgumentException("componentIds 參數不可為空");

            // 獲取可選參數
            var groupName = command.GetParameter<string>("groupName");
            var colorHex = command.GetParameter<string>("color");
            
            // 處理 RGB 參數，可能從 JSON 解析為 long 類型
            int? colorR = null;
            int? colorG = null;
            int? colorB = null;
            
            if (command.Parameters.TryGetValue("colorR", out object rValue))
            {
                if (rValue is int rInt) colorR = rInt;
                else if (rValue is long rLong) colorR = (int)rLong;
                else if (rValue != null) colorR = Convert.ToInt32(rValue);
            }
            
            if (command.Parameters.TryGetValue("colorG", out object gValue))
            {
                if (gValue is int gInt) colorG = gInt;
                else if (gValue is long gLong) colorG = (int)gLong;
                else if (gValue != null) colorG = Convert.ToInt32(gValue);
            }
            
            if (command.Parameters.TryGetValue("colorB", out object bValue))
            {
                if (bValue is int bInt) colorB = bInt;
                else if (bValue is long bLong) colorB = (int)bLong;
                else if (bValue != null) colorB = Convert.ToInt32(bValue);
            }
            
            // 記錄接收到的參數
            RhinoApp.WriteLine($"GroupComponents received parameters:");
            RhinoApp.WriteLine($"  groupName: {groupName}");
            RhinoApp.WriteLine($"  colorHex: {colorHex}");
            RhinoApp.WriteLine($"  colorR: {colorR}");
            RhinoApp.WriteLine($"  colorG: {colorG}");
            RhinoApp.WriteLine($"  colorB: {colorB}");

            object result = null;
            Exception exception = null;
            var doneEvent = new ManualResetEvent(false);

            RhinoApp.InvokeOnUiThread(new Action(() =>
            {
                try
                {
                    var doc = Grasshopper.Instances.ActiveCanvas?.Document;
                    if (doc == null)
                        throw new InvalidOperationException("No active Grasshopper document");

                    // 找到所有指定的元件
                    var objectsToGroup = doc.Objects.Where(obj => ids.Contains(obj.InstanceGuid.ToString())).ToList();
                    if (objectsToGroup.Count == 0)
                        throw new InvalidOperationException("找不到指定的元件");

                    // 建立群組
                    var group = new GH_Group();
                    foreach (var obj in objectsToGroup)
                        group.AddObject(obj.InstanceGuid);

                    // 設定群組名稱
                    group.NickName = string.IsNullOrEmpty(groupName) ? "Group" : groupName;

                    // 設定群組顏色
                    System.Drawing.Color groupColor = System.Drawing.Color.FromArgb(150, 255, 0, 0); // 預設紅色，alpha=150
                    bool colorSet = false;
                    
                    // 優先使用十六進制顏色代碼
                    if (!string.IsNullOrEmpty(colorHex))
                    {
                        try
                        {
                            string hex = colorHex;
                            if (hex.StartsWith("#"))
                                hex = hex.Substring(1);
                            
                            if (hex.Length == 6)
                            {
                                int r = Convert.ToInt32(hex.Substring(0, 2), 16);
                                int g = Convert.ToInt32(hex.Substring(2, 2), 16);
                                int b = Convert.ToInt32(hex.Substring(4, 2), 16);
                                groupColor = System.Drawing.Color.FromArgb(150, r, g, b);
                                colorSet = true;
                                RhinoApp.WriteLine($"Setting group color from hex: R={r}, G={g}, B={b}, Alpha=150");
                            }
                        }
                        catch (Exception ex)
                        {
                            RhinoApp.WriteLine($"Warning: Invalid color hex format '{colorHex}', will try RGB. Error: {ex.Message}");
                        }
                    }
                    
                    // 如果沒有使用 hex，則使用 RGB 值
                    if (!colorSet && colorR.HasValue && colorG.HasValue && colorB.HasValue)
                    {
                        try
                        {
                            int r = Math.Max(0, Math.Min(255, colorR.Value));
                            int g = Math.Max(0, Math.Min(255, colorG.Value));
                            int b = Math.Max(0, Math.Min(255, colorB.Value));
                            
                            groupColor = System.Drawing.Color.FromArgb(150, r, g, b);
                            colorSet = true;
                            RhinoApp.WriteLine($"Setting group color from RGB: R={r}, G={g}, B={b}, Alpha=150");
                        }
                        catch (Exception ex)
                        {
                            RhinoApp.WriteLine($"Warning: Invalid RGB color values, using default red color. Error: {ex.Message}");
                        }
                    }
                    
                    if (!colorSet)
                    {
                        RhinoApp.WriteLine($"No color specified, using default red color");
                    }

                    group.Colour = groupColor;

                    // 加入到文件
                    doc.AddObject(group, false);

                    result = new {
                        success = true,
                        groupId = group.InstanceGuid.ToString(),
                        groupName = group.NickName,
                        groupColor = string.Format("#{0:X2}{1:X2}{2:X2}", groupColor.R, groupColor.G, groupColor.B),
                        groupedComponentIds = objectsToGroup.Select(o => o.InstanceGuid.ToString()).ToList()
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in GroupComponents: {ex.Message}\n{ex.StackTrace}");
                }
                finally
                {
                    doneEvent.Set();
                }
            }));

            doneEvent.WaitOne();

            if (exception != null)
                throw exception;

            return result;
        }
    }
}

