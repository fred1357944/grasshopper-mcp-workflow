using System;
using System.Threading;
using GrasshopperMCP.Models;
using Grasshopper;
using Grasshopper.Kernel;
using Grasshopper.Kernel.Special;
using Rhino;

namespace GH_MCP.Commands.Components
{
    /// <summary>
    /// 處理組件屬性設置相關的命令
    /// </summary>
    public static class ComponentProperties
    {
        /// <summary>
        /// 設置 Number Slider 的完整屬性
        /// </summary>
        /// <param name="command">包含組件 ID 和屬性的命令</param>
        /// <returns>操作結果</returns>
        public static object SetSliderProperties(Command command)
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
                    
                    if (!(component is GH_NumberSlider slider))
                    {
                        throw new ArgumentException("Component is not a Number Slider");
                    }
                    
                    // 設置最小值
                    if (minValue.HasValue)
                    {
                        slider.Slider.Minimum = (decimal)minValue.Value;
                    }
                    
                    // 設置最大值
                    if (maxValue.HasValue)
                    {
                        slider.Slider.Maximum = (decimal)maxValue.Value;
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
                    }
                    
                    // 設置值
                    if (!string.IsNullOrEmpty(value))
                    {
                        double doubleValue;
                        if (double.TryParse(value, out doubleValue))
                        {
                            decimal sliderValue = (decimal)doubleValue;
                            if (sliderValue < slider.Slider.Minimum)
                                sliderValue = slider.Slider.Minimum;
                            if (sliderValue > slider.Slider.Maximum)
                                sliderValue = slider.Slider.Maximum;
                            
                            slider.Slider.Value = sliderValue;
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
                    
                    // 刷新畫布
                    doc.NewSolution(false);
                    
                    // 返回操作結果
                    result = new
                    {
                        id = component.InstanceGuid.ToString(),
                        type = component.GetType().Name,
                        value = value,
                        min = minValue,
                        max = maxValue,
                        rounding = rounding
                    };
                }
                catch (Exception ex)
                {
                    exception = ex;
                    RhinoApp.WriteLine($"Error in SetSliderProperties: {ex.Message}");
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
    }
}


