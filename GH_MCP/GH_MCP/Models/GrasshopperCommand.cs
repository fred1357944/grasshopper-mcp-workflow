using System;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace GrasshopperMCP.Models
{
    /// <summary>
    /// 表示從 Python 伺服器發送到 Grasshopper 的命令
    /// </summary>
    public class Command
    {
        /// <summary>
        /// 命令類型
        /// </summary>
        [JsonProperty("type")]
        public string Type { get; set; }

        /// <summary>
        /// 命令參數
        /// </summary>
        [JsonProperty("parameters")]
        public Dictionary<string, object> Parameters { get; set; }

        /// <summary>
        /// 創建一個新的命令實例
        /// </summary>
        /// <param name="type">命令類型</param>
        /// <param name="parameters">命令參數</param>
        public Command(string type, Dictionary<string, object> parameters = null)
        {
            Type = type;
            Parameters = parameters ?? new Dictionary<string, object>();
        }

        /// <summary>
        /// 獲取指定參數的值
        /// </summary>
        /// <typeparam name="T">參數類型</typeparam>
        /// <param name="name">參數名稱</param>
        /// <returns>參數值</returns>
        public T GetParameter<T>(string name)
        {
            if (Parameters.TryGetValue(name, out object value))
            {
                if (value == null)
                {
                    return default;
                }

                if (value is T typedValue)
                {
                    return typedValue;
                }

                // 處理 Nullable 類型
                Type targetType = typeof(T);
                Type underlyingType = Nullable.GetUnderlyingType(targetType);

                if (underlyingType != null)
                {
                    // T 是 Nullable<U>，嘗試轉換為 U
                    try
                    {
                        object converted = ConvertToNumeric(value, underlyingType);
                        if (converted != null)
                        {
                            return (T)converted;
                        }
                    }
                    catch
                    {
                        // 轉換失敗，繼續嘗試其他方法
                    }
                }

                // 嘗試數字類型轉換
                if (IsNumericType(targetType))
                {
                    try
                    {
                        object converted = ConvertToNumeric(value, targetType);
                        if (converted != null)
                        {
                            return (T)converted;
                        }
                    }
                    catch
                    {
                        // 轉換失敗
                    }
                }

                // 嘗試標準轉換
                try
                {
                    return (T)Convert.ChangeType(value, targetType);
                }
                catch
                {
                    // 如果是 Newtonsoft.Json.Linq.JObject，嘗試轉換
                    if (value is Newtonsoft.Json.Linq.JObject jObject)
                    {
                        return jObject.ToObject<T>();
                    }

                    // 如果是 Newtonsoft.Json.Linq.JArray，嘗試轉換
                    if (value is Newtonsoft.Json.Linq.JArray jArray)
                    {
                        return jArray.ToObject<T>();
                    }

                    // 如果是 Newtonsoft.Json.Linq.JValue，提取值後再嘗試
                    if (value is Newtonsoft.Json.Linq.JValue jValue)
                    {
                        return GetParameter<T>(jValue.Value, targetType, underlyingType);
                    }
                }
            }

            // 如果無法獲取或轉換參數，返回默認值
            return default;
        }

        /// <summary>
        /// 內部輔助方法：從 JValue 提取值後再轉換
        /// </summary>
        private T GetParameter<T>(object value, Type targetType, Type underlyingType)
        {
            if (value == null) return default;

            Type actualUnderlyingType = underlyingType ?? targetType;

            try
            {
                object converted = ConvertToNumeric(value, actualUnderlyingType);
                if (converted != null)
                {
                    return (T)converted;
                }
            }
            catch
            {
                // 忽略
            }

            return default;
        }

        /// <summary>
        /// 檢查是否為數字類型
        /// </summary>
        private bool IsNumericType(Type type)
        {
            return type == typeof(int) || type == typeof(long) || type == typeof(float) ||
                   type == typeof(double) || type == typeof(decimal) || type == typeof(short) ||
                   type == typeof(byte) || type == typeof(uint) || type == typeof(ulong);
        }

        /// <summary>
        /// 將任意值轉換為指定的數字類型
        /// </summary>
        private object ConvertToNumeric(object value, Type targetType)
        {
            if (value == null) return null;

            // 處理 JValue
            if (value is Newtonsoft.Json.Linq.JValue jValue)
            {
                value = jValue.Value;
                if (value == null) return null;
            }

            // 處理字符串
            if (value is string str)
            {
                if (targetType == typeof(double) && double.TryParse(str, out double d))
                    return d;
                if (targetType == typeof(int) && int.TryParse(str, out int i))
                    return i;
                if (targetType == typeof(long) && long.TryParse(str, out long l))
                    return l;
                if (targetType == typeof(float) && float.TryParse(str, out float f))
                    return f;
                if (targetType == typeof(decimal) && decimal.TryParse(str, out decimal dec))
                    return dec;
                return null;
            }

            // 處理各種數字類型
            if (targetType == typeof(double))
            {
                if (value is double dVal) return dVal;
                if (value is int iVal) return (double)iVal;
                if (value is long lVal) return (double)lVal;
                if (value is float fVal) return (double)fVal;
                if (value is decimal decVal) return (double)decVal;
                if (value is short sVal) return (double)sVal;
                if (value is byte bVal) return (double)bVal;
                return Convert.ToDouble(value);
            }

            if (targetType == typeof(int))
            {
                if (value is int iVal) return iVal;
                if (value is long lVal) return (int)lVal;
                if (value is double dVal) return (int)dVal;
                if (value is float fVal) return (int)fVal;
                if (value is decimal decVal) return (int)decVal;
                return Convert.ToInt32(value);
            }

            if (targetType == typeof(long))
            {
                if (value is long lVal) return lVal;
                if (value is int iVal) return (long)iVal;
                if (value is double dVal) return (long)dVal;
                return Convert.ToInt64(value);
            }

            if (targetType == typeof(float))
            {
                if (value is float fVal) return fVal;
                if (value is double dVal) return (float)dVal;
                if (value is int iVal) return (float)iVal;
                if (value is long lVal) return (float)lVal;
                return Convert.ToSingle(value);
            }

            if (targetType == typeof(decimal))
            {
                if (value is decimal decVal) return decVal;
                if (value is double dVal) return (decimal)dVal;
                if (value is int iVal) return (decimal)iVal;
                if (value is long lVal) return (decimal)lVal;
                return Convert.ToDecimal(value);
            }

            return Convert.ChangeType(value, targetType);
        }
    }

    /// <summary>
    /// 表示從 Grasshopper 發送到 Python 伺服器的響應
    /// </summary>
    public class Response
    {
        /// <summary>
        /// 響應是否成功
        /// </summary>
        [JsonProperty("success")]
        public bool Success { get; set; }

        /// <summary>
        /// 響應數據
        /// </summary>
        [JsonProperty("data")]
        public object Data { get; set; }

        /// <summary>
        /// 錯誤信息，如果有的話
        /// </summary>
        [JsonProperty("error")]
        public string Error { get; set; }

        /// <summary>
        /// 創建一個成功的響應
        /// </summary>
        /// <param name="data">響應數據</param>
        /// <returns>響應實例</returns>
        public static Response Ok(object data = null)
        {
            return new Response
            {
                Success = true,
                Data = data
            };
        }

        /// <summary>
        /// 創建一個錯誤的響應
        /// </summary>
        /// <param name="errorMessage">錯誤信息</param>
        /// <returns>響應實例</returns>
        public static Response CreateError(string errorMessage)
        {
            return new Response
            {
                Success = false,
                Data = null,
                Error = errorMessage
            };
        }
    }
}
