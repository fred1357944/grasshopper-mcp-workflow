using System;
using System.Collections.Generic;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace GH_MCP_Vision.Models
{
    /// <summary>
    /// Vision MCP 命令模型
    /// </summary>
    public class VisionCommand
    {
        [JsonProperty("type")]
        public string Type { get; set; }

        [JsonProperty("parameters")]
        public JObject Parameters { get; set; }

        /// <summary>
        /// 獲取參數值
        /// </summary>
        public T GetParameter<T>(string name)
        {
            if (Parameters == null || !Parameters.ContainsKey(name))
            {
                return default(T);
            }

            try
            {
                var value = Parameters[name];
                if (value == null || value.Type == JTokenType.Null)
                {
                    return default(T);
                }

                Type targetType = typeof(T);

                // 處理 Nullable 類型
                Type underlyingType = Nullable.GetUnderlyingType(targetType);
                if (underlyingType != null)
                {
                    object converted = ConvertToNumeric(value, underlyingType);
                    if (converted != null)
                    {
                        return (T)converted;
                    }
                }

                // 一般類型轉換
                if (value is JValue jValue)
                {
                    object rawValue = jValue.Value;
                    if (rawValue != null && targetType.IsAssignableFrom(rawValue.GetType()))
                    {
                        return (T)rawValue;
                    }

                    // 數值類型轉換
                    if (targetType == typeof(double) || targetType == typeof(float) ||
                        targetType == typeof(int) || targetType == typeof(long))
                    {
                        object numericResult = ConvertToNumeric(value, targetType);
                        if (numericResult != null)
                        {
                            return (T)numericResult;
                        }
                    }
                }

                return value.ToObject<T>();
            }
            catch
            {
                return default(T);
            }
        }

        /// <summary>
        /// 將 JToken 轉換為數值類型
        /// </summary>
        private static object ConvertToNumeric(JToken value, Type targetType)
        {
            if (value == null) return null;

            try
            {
                if (value is JValue jValue)
                {
                    object rawValue = jValue.Value;

                    if (targetType == typeof(double))
                    {
                        if (rawValue is double d) return d;
                        if (rawValue is int i) return (double)i;
                        if (rawValue is long l) return (double)l;
                        if (rawValue is float f) return (double)f;
                        if (rawValue is decimal dec) return (double)dec;
                        if (rawValue is string s && double.TryParse(s, out double result)) return result;
                    }
                    else if (targetType == typeof(float))
                    {
                        if (rawValue is float f) return f;
                        if (rawValue is double d) return (float)d;
                        if (rawValue is int i) return (float)i;
                        if (rawValue is long l) return (float)l;
                    }
                    else if (targetType == typeof(int))
                    {
                        if (rawValue is int i) return i;
                        if (rawValue is long l) return (int)l;
                        if (rawValue is double d) return (int)d;
                    }
                    else if (targetType == typeof(long))
                    {
                        if (rawValue is long l) return l;
                        if (rawValue is int i) return (long)i;
                        if (rawValue is double d) return (long)d;
                    }
                }

                return Convert.ChangeType(value.ToObject<object>(), targetType);
            }
            catch
            {
                return null;
            }
        }
    }

    /// <summary>
    /// Vision MCP 回應模型
    /// </summary>
    public class VisionResponse
    {
        [JsonProperty("success")]
        public bool Success { get; set; }

        [JsonProperty("data")]
        public object Data { get; set; }

        [JsonProperty("error")]
        public string Error { get; set; }

        public static VisionResponse Ok(object data)
        {
            return new VisionResponse { Success = true, Data = data };
        }

        public static VisionResponse CreateError(string error)
        {
            return new VisionResponse { Success = false, Error = error };
        }
    }
}
