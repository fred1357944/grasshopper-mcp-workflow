using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using Newtonsoft.Json;
using Rhino;

namespace GH_MCP_Vision.AI
{
    /// <summary>
    /// Gemini CLI 調用輔助類
    /// 用於 AI 智能診斷連接失敗、分析模式等
    /// </summary>
    public static class GeminiHelper
    {
        private const int DefaultTimeout = 60000; // 60 秒

        /// <summary>
        /// 調用 Gemini CLI 並獲取回應
        /// </summary>
        /// <param name="prompt">提示詞</param>
        /// <param name="timeoutMs">超時時間（毫秒）</param>
        /// <returns>Gemini 回應，失敗返回 null</returns>
        public static string CallGemini(string prompt, int timeoutMs = DefaultTimeout)
        {
            try
            {
                // 使用 gemini CLI
                var startInfo = new ProcessStartInfo
                {
                    FileName = "gemini",
                    Arguments = $"\"{EscapeForShell(prompt)}\"",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                    StandardOutputEncoding = Encoding.UTF8,
                    StandardErrorEncoding = Encoding.UTF8
                };

                using (var process = new Process { StartInfo = startInfo })
                {
                    process.Start();

                    // 異步讀取輸出
                    var output = new StringBuilder();
                    var error = new StringBuilder();

                    process.OutputDataReceived += (s, e) => { if (e.Data != null) output.AppendLine(e.Data); };
                    process.ErrorDataReceived += (s, e) => { if (e.Data != null) error.AppendLine(e.Data); };

                    process.BeginOutputReadLine();
                    process.BeginErrorReadLine();

                    bool completed = process.WaitForExit(timeoutMs);

                    if (!completed)
                    {
                        try { process.Kill(); } catch { }
                        RhinoApp.WriteLine("[GH_MCP_Vision] Gemini timeout");
                        return null;
                    }

                    if (process.ExitCode != 0)
                    {
                        RhinoApp.WriteLine($"[GH_MCP_Vision] Gemini error: {error}");
                        return null;
                    }

                    return output.ToString().Trim();
                }
            }
            catch (Exception ex)
            {
                RhinoApp.WriteLine($"[GH_MCP_Vision] Gemini call failed: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// 分析連接失敗原因
        /// </summary>
        public static DiagnoseResult DiagnoseConnectionFailure(
            string sourceComponent,
            string targetComponent,
            string errorMessage)
        {
            string prompt = $@"Grasshopper MCP 連線失敗:

來源: {sourceComponent}
目標: {targetComponent}
錯誤: {errorMessage}

請分析:
1. 可能的原因
2. 正確的參數名稱應該是什麼
3. 修復建議

用 JSON 格式回覆:
{{""cause"": ""原因"", ""correct_params"": {{""source"": ""xxx"", ""target"": ""yyy""}}, ""solution"": ""建議""}}";

            string response = CallGemini(prompt);

            if (string.IsNullOrEmpty(response))
            {
                return new DiagnoseResult
                {
                    Success = false,
                    Error = "Gemini 調用失敗"
                };
            }

            // 解析 JSON
            try
            {
                int start = response.IndexOf('{');
                int end = response.LastIndexOf('}') + 1;

                if (start >= 0 && end > start)
                {
                    string json = response.Substring(start, end - start);
                    var result = JsonConvert.DeserializeObject<DiagnoseResult>(json);
                    result.Success = true;
                    result.RawResponse = response;
                    return result;
                }
            }
            catch (Exception ex)
            {
                RhinoApp.WriteLine($"[GH_MCP_Vision] JSON parse error: {ex.Message}");
            }

            return new DiagnoseResult
            {
                Success = true,
                RawResponse = response
            };
        }

        /// <summary>
        /// 批量分析失敗模式
        /// </summary>
        public static PatternAnalysisResult AnalyzeFailurePatterns(List<FailureRecord> failures)
        {
            if (failures == null || failures.Count == 0)
            {
                return new PatternAnalysisResult
                {
                    Success = false,
                    Error = "No failures to analyze"
                };
            }

            // 構建失敗記錄描述
            var sb = new StringBuilder();
            sb.AppendLine("以下是 Grasshopper MCP 的連線失敗記錄:");
            sb.AppendLine();

            int count = Math.Min(failures.Count, 20); // 最多 20 條
            for (int i = 0; i < count; i++)
            {
                var f = failures[i];
                sb.AppendLine($"{i + 1}. {f.SourceComponent}.{f.SourceParam} → {f.TargetComponent}.{f.TargetParam}");
                sb.AppendLine($"   錯誤: {f.ErrorMessage}");
            }

            string prompt = $@"{sb}

請分析這些失敗的共同模式:
1. 常見的錯誤類型
2. 參數命名問題
3. 組件相容性問題
4. 建議的修復策略

用 JSON 格式回覆:
{{
  ""patterns_learned"": [
    {{""pattern"": ""描述"", ""frequency"": 數量, ""fix"": ""修復方式""}}
  ],
  ""suggestions"": [""建議1"", ""建議2""],
  ""common_mistakes"": [""錯誤1"", ""錯誤2""]
}}";

            string response = CallGemini(prompt, 90000); // 90 秒

            if (string.IsNullOrEmpty(response))
            {
                return new PatternAnalysisResult
                {
                    Success = false,
                    Error = "Gemini 調用失敗"
                };
            }

            // 解析 JSON
            try
            {
                int start = response.IndexOf('{');
                int end = response.LastIndexOf('}') + 1;

                if (start >= 0 && end > start)
                {
                    string json = response.Substring(start, end - start);
                    var result = JsonConvert.DeserializeObject<PatternAnalysisResult>(json);
                    result.Success = true;
                    result.RawResponse = response;
                    return result;
                }
            }
            catch { }

            return new PatternAnalysisResult
            {
                Success = true,
                RawResponse = response
            };
        }

        /// <summary>
        /// 轉義 shell 特殊字符
        /// </summary>
        private static string EscapeForShell(string input)
        {
            if (string.IsNullOrEmpty(input))
                return input;

            // 基本轉義：替換引號和反斜線
            return input
                .Replace("\\", "\\\\")
                .Replace("\"", "\\\"")
                .Replace("\n", " ")
                .Replace("\r", " ");
        }
    }

    /// <summary>
    /// 診斷結果
    /// </summary>
    public class DiagnoseResult
    {
        public bool Success { get; set; }
        public string Error { get; set; }
        public string Cause { get; set; }
        public CorrectParams CorrectParams { get; set; }
        public string Solution { get; set; }
        public string RawResponse { get; set; }

        [JsonProperty("correct_params")]
        private CorrectParams CorrectParamsAlias
        {
            set { CorrectParams = value; }
        }
    }

    /// <summary>
    /// 正確的參數名
    /// </summary>
    public class CorrectParams
    {
        public string Source { get; set; }
        public string Target { get; set; }
    }

    /// <summary>
    /// 失敗記錄
    /// </summary>
    public class FailureRecord
    {
        public string SourceComponent { get; set; }
        public string SourceParam { get; set; }
        public string TargetComponent { get; set; }
        public string TargetParam { get; set; }
        public string ErrorMessage { get; set; }
    }

    /// <summary>
    /// 模式分析結果
    /// </summary>
    public class PatternAnalysisResult
    {
        public bool Success { get; set; }
        public string Error { get; set; }

        [JsonProperty("patterns_learned")]
        public List<PatternInfo> PatternsLearned { get; set; }

        public List<string> Suggestions { get; set; }

        [JsonProperty("common_mistakes")]
        public List<string> CommonMistakes { get; set; }

        public string RawResponse { get; set; }
    }

    /// <summary>
    /// 模式信息
    /// </summary>
    public class PatternInfo
    {
        public string Pattern { get; set; }
        public int Frequency { get; set; }
        public string Fix { get; set; }
    }
}
