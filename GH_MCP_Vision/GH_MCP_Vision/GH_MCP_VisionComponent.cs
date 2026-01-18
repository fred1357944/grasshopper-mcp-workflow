using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Collections.Generic;
using Grasshopper.Kernel;
using GH_MCP_Vision.Commands;
using GH_MCP_Vision.Models;
using Newtonsoft.Json;
using Rhino;

namespace GH_MCP_Vision
{
    /// <summary>
    /// GH_MCP_Vision 主組件 - TCP Server
    /// 監聽端口 8081（與 GH_MCP 的 8080 分開）
    /// </summary>
    public class GH_MCP_VisionComponent : GH_Component
    {
        private TcpListener _listener;
        private CancellationTokenSource _cancellationTokenSource;
        private bool _isRunning;
        private int _port = 8081;
        private List<string> _logs = new List<string>();

        public GH_MCP_VisionComponent()
            : base("GH_MCP_Vision Server", "VisionMCP",
                "Vision MCP Server for Canvas/Viewport Capture (Port 8081)",
                "Params", "Util")
        {
        }

        protected override void RegisterInputParams(GH_Component.GH_InputParamManager pManager)
        {
            pManager.AddIntegerParameter("Port", "P", "TCP Port (default: 8081)", GH_ParamAccess.item, 8081);
            pManager.AddBooleanParameter("Start", "S", "Start/Stop the server", GH_ParamAccess.item, false);
        }

        protected override void RegisterOutputParams(GH_Component.GH_OutputParamManager pManager)
        {
            pManager.AddTextParameter("Status", "St", "Server status", GH_ParamAccess.item);
            pManager.AddTextParameter("Log", "L", "Server log", GH_ParamAccess.list);
        }

        protected override void SolveInstance(IGH_DataAccess DA)
        {
            int port = 8081;
            bool start = false;

            DA.GetData(0, ref port);
            DA.GetData(1, ref start);

            _port = port;

            if (start && !_isRunning)
            {
                StartServer();
                DA.SetData(0, $"Running on port {_port}");
            }
            else if (!start && _isRunning)
            {
                StopServer();
                DA.SetData(0, "Stopped");
            }
            else if (_isRunning)
            {
                DA.SetData(0, $"Running on port {_port}");
            }
            else
            {
                DA.SetData(0, "Stopped");
            }

            DA.SetDataList(1, _logs);
        }

        private void StartServer()
        {
            if (_isRunning) return;

            try
            {
                // 初始化命令註冊表
                VisionCommandRegistry.Initialize();

                _cancellationTokenSource = new CancellationTokenSource();
                _listener = new TcpListener(IPAddress.Any, _port);
                _listener.Start();
                _isRunning = true;

                AddLog($"Server started on port {_port}");
                RhinoApp.WriteLine($"[GH_MCP_Vision] Server started on port {_port}");

                // 啟動接受連接的任務
                Task.Run(() => AcceptClientsAsync(_cancellationTokenSource.Token));
            }
            catch (Exception ex)
            {
                AddLog($"Failed to start: {ex.Message}");
                RhinoApp.WriteLine($"[GH_MCP_Vision] Failed to start server: {ex.Message}");
                _isRunning = false;
            }
        }

        private void StopServer()
        {
            if (!_isRunning) return;

            try
            {
                _cancellationTokenSource?.Cancel();
                _listener?.Stop();
                _isRunning = false;

                AddLog("Server stopped");
                RhinoApp.WriteLine("[GH_MCP_Vision] Server stopped");
            }
            catch (Exception ex)
            {
                AddLog($"Error stopping: {ex.Message}");
                RhinoApp.WriteLine($"[GH_MCP_Vision] Error stopping server: {ex.Message}");
            }
        }

        private void AddLog(string message)
        {
            _logs.Insert(0, $"[{DateTime.Now:HH:mm:ss}] {message}");
            if (_logs.Count > 50) _logs.RemoveAt(_logs.Count - 1);
        }

        private async Task AcceptClientsAsync(CancellationToken token)
        {
            while (!token.IsCancellationRequested && _isRunning)
            {
                try
                {
                    var client = await _listener.AcceptTcpClientAsync();
                    AddLog($"Client connected");
                    _ = HandleClientAsync(client, token);
                }
                catch (ObjectDisposedException)
                {
                    break;
                }
                catch (Exception ex)
                {
                    if (!token.IsCancellationRequested)
                    {
                        AddLog($"Accept error: {ex.Message}");
                    }
                }
            }
        }

        private async Task HandleClientAsync(TcpClient client, CancellationToken token)
        {
            using (client)
            using (var stream = client.GetStream())
            {
                var buffer = new byte[65536];
                var sb = new StringBuilder();

                try
                {
                    while (!token.IsCancellationRequested)
                    {
                        int bytesRead = await stream.ReadAsync(buffer, 0, buffer.Length, token);
                        if (bytesRead == 0) break;

                        sb.Append(Encoding.UTF8.GetString(buffer, 0, bytesRead));
                        string data = sb.ToString();

                        // 處理每一行命令
                        int newlineIndex;
                        while ((newlineIndex = data.IndexOf('\n')) >= 0)
                        {
                            string line = data.Substring(0, newlineIndex).Trim();
                            data = data.Substring(newlineIndex + 1);
                            sb.Clear();
                            sb.Append(data);

                            if (!string.IsNullOrEmpty(line))
                            {
                                string response = ProcessCommand(line);
                                byte[] responseBytes = Encoding.UTF8.GetBytes(response + "\n");
                                await stream.WriteAsync(responseBytes, 0, responseBytes.Length, token);
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    if (!token.IsCancellationRequested)
                    {
                        AddLog($"Client error: {ex.Message}");
                    }
                }
            }
        }

        private string ProcessCommand(string json)
        {
            try
            {
                AddLog($"Received: {json.Substring(0, Math.Min(50, json.Length))}...");
                var command = JsonConvert.DeserializeObject<VisionCommand>(json);
                var response = VisionCommandRegistry.ExecuteCommand(command);
                return JsonConvert.SerializeObject(response);
            }
            catch (Exception ex)
            {
                var error = VisionResponse.CreateError($"Parse error: {ex.Message}");
                return JsonConvert.SerializeObject(error);
            }
        }

        public override void RemovedFromDocument(GH_Document document)
        {
            StopServer();
            base.RemovedFromDocument(document);
        }

        public override Guid ComponentGuid => new Guid("b2c3d4e5-f6a7-8901-bcde-f12345678901");

        protected override System.Drawing.Bitmap Icon => null;
    }
}
