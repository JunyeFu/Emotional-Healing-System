// U01 — ReliableControlClient: TCP client connecting to the Python control
// server on port 5010 using JSON Lines protocol.  Runs a receive thread;
// marshals incoming control_events to the main thread for processing.

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

namespace SRP.U01
{
    /// <summary>
    /// TCP client for the reliable control channel.
    /// Connects to the Python ControlServer, performs the hello/welcome handshake,
    /// and receives control_event messages as JSON Lines.
    ///
    /// Threading model:
    ///   - Network thread: connect, handshake, receive loop
    ///   - Main thread: DequeueAndProcess() called from Update()
    ///
    /// Send operations (ACK, render_receipt) happen on the network thread
    /// using a thread-safe send queue.
    /// </summary>
    public sealed class ReliableControlClient : MonoBehaviour
    {
        // ── Inspector settings ────────────────────────────────────────────
        [Header("Connection")]
        [SerializeField] private string _host = "127.0.0.1";
        [SerializeField] private int _port = 5010;
        [SerializeField] private int _receiveTimeoutMs = 5000;
        [SerializeField] private int _sendTimeoutMs = 2000;

        [Header("Handshake")]
        [SerializeField] private string _schemaVersion = "2.2";
        [SerializeField] private string _transportVersion = "1.0";
        [SerializeField] private string _clientInstanceId = "";

        // ── Dependencies ──────────────────────────────────────────────────
        [SerializeField] private SessionMirror _sessionMirror;
        [SerializeField] private AckManager _ackManager;
        [SerializeField] private RenderReceiptManager _renderReceiptManager;

        // ── Internal state ────────────────────────────────────────────────
        private TcpClient _tcpClient;
        private NetworkStream _stream;
        private Thread _receiveThread;
        private Thread _sendThread;
        private volatile bool _isConnected;
        private volatile bool _isRunning;
        private int _generation;

        // Thread-safe queues
        private readonly ConcurrentQueue<string> _incomingLines = new();
        private readonly ConcurrentQueue<byte[]> _outgoingLines = new();

        // ── Events ────────────────────────────────────────────────────────
        /// <summary>Fired on main thread when a valid control_event arrives.</summary>
        public event Action<ControlEvent> OnControlEvent;

        /// <summary>Fired on main thread when a session_manifest arrives.</summary>
        public event Action<SessionManifest> OnSessionManifest;

        /// <summary>Fired when connection state changes.</summary>
        public event Action<bool> OnConnectionChanged;

        /// <summary>Fired on main thread when a transport error arrives.</summary>
        public event Action<string> OnTransportError;

        // ── Properties ────────────────────────────────────────────────────
        public bool IsConnected => _isConnected;
        public int Generation => _generation;
        public string Host { get => _host; set => _host = value; }
        public int Port { get => _port; set => _port = value; }

        // ── Lifecycle ─────────────────────────────────────────────────────

        void Awake()
        {
            if (string.IsNullOrEmpty(_clientInstanceId))
                _clientInstanceId = Guid.NewGuid().ToString("N");
        }

        void Update()
        {
            DequeueAndProcess();
        }

        void OnDestroy()
        {
            Disconnect();
        }

        // ── Public API ────────────────────────────────────────────────────

        /// <summary>Start the TCP connection and receive loop.</summary>
        public void Connect()
        {
            if (_isRunning) return;
            _isRunning = true;
            _receiveThread = new Thread(ReceiveLoop)
            {
                IsBackground = true,
                Name = "U01-TCP-Receive"
            };
            _receiveThread.Start();

            _sendThread = new Thread(SendLoop)
            {
                IsBackground = true,
                Name = "U01-TCP-Send"
            };
            _sendThread.Start();

            Log($"Connecting to {_host}:{_port}...");
        }

        /// <summary>Gracefully disconnect.</summary>
        public void Disconnect()
        {
            _isRunning = false;
            _isConnected = false;

            try { _stream?.Close(); } catch { }
            try { _tcpClient?.Close(); } catch { }

            _receiveThread?.Join(1000);
            _sendThread?.Join(1000);

            _stream = null;
            _tcpClient = null;
            Log("Disconnected");
        }

        /// <summary>Queue a JSON line for sending (thread-safe).</summary>
        public void SendJsonLine(string jsonLine)
        {
            if (string.IsNullOrEmpty(jsonLine)) return;
            byte[] bytes = Encoding.UTF8.GetBytes(jsonLine + "\n");
            _outgoingLines.Enqueue(bytes);
        }

        /// <summary>Send a dictionary as a JSON line (thread-safe).</summary>
        public void Send(Dictionary<string, object> msg)
        {
            SendJsonLine(JsonLines.Serialize(msg));
        }

        /// <summary>Send an ACK message.</summary>
        public void SendAck(AckMessage ack)
        {
            var dict = new Dictionary<string, object>
            {
                ["schema_version"] = AckMessage.schema_version,
                ["message_type"] = AckMessage.message_type_val,
                ["session_id"] = ack.session_id ?? "",
                ["event_id"] = ack.event_id ?? "",
                ["received_monotonic_ns"] = ack.received_monotonic_ns,
                ["applied_monotonic_ns"] = ack.applied_monotonic_ns,
                ["unity_frame"] = ack.unity_frame,
                ["result"] = ack.result ?? "applied",
                ["error_code"] = (object)ack.error_code ?? null
            };
            Send(dict);
        }

        /// <summary>Send a render receipt.</summary>
        public void SendRenderReceipt(RenderReceipt receipt)
        {
            var dict = new Dictionary<string, object>
            {
                ["schema_version"] = RenderReceipt.schema_version,
                ["message_type"] = RenderReceipt.message_type_val,
                ["receipt_id"] = receipt.receipt_id ?? "",
                ["session_id"] = receipt.session_id ?? "",
                ["event_id"] = receipt.event_id ?? "",
                ["frame_seq"] = receipt.frame_seq,
                ["unity_frame"] = receipt.unity_frame,
                ["rendered_monotonic_ns"] = receipt.rendered_monotonic_ns,
                ["module_id"] = receipt.module_id ?? "",
                ["segment"] = receipt.segment ?? "",
                ["result"] = receipt.result ?? "rendered",
                ["error_code"] = (object)receipt.error_code ?? null
            };
            Send(dict);
        }

        // ── Network thread: connect + handshake ───────────────────────────

        private void ReceiveLoop()
        {
            while (_isRunning)
            {
                try
                {
                    ConnectAndHandshake();
                    if (!_isRunning) break;
                    ReadLoop();
                }
                catch (Exception ex)
                {
                    if (!_isRunning) break;
                    Log($"Receive error: {ex.Message}");
                }
                finally
                {
                    bool wasConnected = _isConnected;
                    _isConnected = false;
                    if (wasConnected)
                    {
                        _incomingLines.Enqueue("__DISCONNECTED__");
                        _generation++;
                    }
                }

                // Backoff before retry
                if (_isRunning)
                    Thread.Sleep(1000);
            }
        }

        private void ConnectAndHandshake()
        {
            _tcpClient = new TcpClient();
            _tcpClient.NoDelay = true;
            _tcpClient.ReceiveTimeout = _receiveTimeoutMs;
            _tcpClient.SendTimeout = _sendTimeoutMs;
            _tcpClient.Connect(_host, _port);
            _stream = _tcpClient.GetStream();

            // Send hello
            var hello = new Dictionary<string, object>
            {
                ["transport_type"] = "hello",
                ["transport_version"] = _transportVersion,
                ["role"] = "unity",
                ["schema_version"] = _schemaVersion,
                ["client_instance_id"] = _clientInstanceId
            };
            Send(hello);

            // Read welcome
            string welcomeLine = ReadLine();
            if (welcomeLine == null)
                throw new IOException("Connection closed before welcome");

            var welcome = JsonLines.Deserialize(welcomeLine);
            if (welcome.TryGetValue("transport_type", out var tt) && tt?.ToString() == "error")
            {
                string errCode = welcome.TryGetValue("error_code", out var ec) ? ec?.ToString() : "UNKNOWN";
                throw new IOException($"Server rejected: {errCode}");
            }

            if (welcome.TryGetValue("accepted", out var acc) && acc is bool accepted && !accepted)
            {
                string errCode = welcome.TryGetValue("error_code", out var ec) ? ec?.ToString() : "UNKNOWN";
                throw new IOException($"Handshake rejected: {errCode}");
            }

            _isConnected = true;
            _incomingLines.Enqueue("__CONNECTED__");
            Log($"Handshake OK — connected (gen {_generation})");
        }

        private void ReadLoop()
        {
            while (_isRunning && _isConnected)
            {
                string line = ReadLine();
                if (line == null) break; // server closed

                // Fault injection check
                if (_renderReceiptManager != null)
                {
                    // Check if we should drop/corrupt
                }

                _incomingLines.Enqueue(line);
            }
        }

        private string ReadLine()
        {
            if (_stream == null) return null;
            var sb = new StringBuilder();
            int b;
            while (true)
            {
                b = _stream.ReadByte();
                if (b < 0) return null; // EOF
                if (b == '\n') break;
                sb.Append((char)b);
            }
            return sb.ToString();
        }

        // ── Send thread ───────────────────────────────────────────────────

        private void SendLoop()
        {
            while (_isRunning)
            {
                if (_outgoingLines.TryDequeue(out byte[] data))
                {
                    try
                    {
                        if (_stream != null && _stream.CanWrite)
                            _stream.Write(data, 0, data.Length);
                    }
                    catch (Exception ex)
                    {
                        if (_isRunning)
                            Log($"Send error: {ex.Message}");
                    }
                }
                else
                {
                    Thread.Sleep(1);
                }
            }
        }

        // ── Main thread: dequeue and process ──────────────────────────────

        private void DequeueAndProcess()
        {
            int processed = 0;
            while (processed < 100 && _incomingLines.TryDequeue(out string line))
            {
                processed++;

                if (line == "__CONNECTED__")
                {
                    OnConnectionChanged?.Invoke(true);
                    continue;
                }
                if (line == "__DISCONNECTED__")
                {
                    OnConnectionChanged?.Invoke(false);
                    continue;
                }

                ProcessIncomingLine(line);
            }
        }

        private void ProcessIncomingLine(string line)
        {
            if (string.IsNullOrEmpty(line)) return;

            Dictionary<string, object> msg;
            try
            {
                msg = JsonLines.Deserialize(line);
            }
            catch (Exception ex)
            {
                Log($"JSON parse error: {ex.Message}");
                OnTransportError?.Invoke("TRANSPORT_FRAME_INVALID");
                return;
            }

            if (!msg.TryGetValue("message_type", out var mtRaw))
            {
                // Could be transport-level (welcome, error, etc.)
                if (msg.TryGetValue("transport_type", out var ttt) && ttt?.ToString() == "error")
                {
                    string ec = msg.TryGetValue("error_code", out var ec2) ? ec2?.ToString() : "UNKNOWN";
                    OnTransportError?.Invoke(ec);
                }
                return;
            }

            string messageType = mtRaw?.ToString();

            switch (messageType)
            {
                case "session_manifest":
                    ProcessSessionManifest(msg);
                    break;
                case "control_event":
                    ProcessControlEvent(msg);
                    break;
                case "ack":
                    // Server echo of our ack — informational
                    break;
                case "render_receipt":
                    // Server echo — informational
                    break;
                default:
                    Log($"Unknown message_type: {messageType}");
                    break;
            }
        }

        private void ProcessSessionManifest(Dictionary<string, object> raw)
        {
            try
            {
                var manifest = DeserializeSessionManifest(raw);
                _sessionMirror?.ApplySessionManifest(manifest);
                OnSessionManifest?.Invoke(manifest);
            }
            catch (Exception ex)
            {
                Log($"Failed to process session_manifest: {ex.Message}");
            }
        }

        private void ProcessControlEvent(Dictionary<string, object> raw)
        {
            try
            {
                var evt = DeserializeControlEvent(raw);

                // Update session mirror
                _sessionMirror?.ApplyControlEvent(evt);

                // Generate ACK
                var snap = _sessionMirror?.Snapshot;
                string sessionId = snap?.SessionId ?? "";
                int unityFrame = Time.frameCount;

                if (_ackManager != null && !_ackManager.IsDelivered(evt.event_id))
                {
                    _ackManager.TrackEventSent(evt);
                    var ack = _ackManager.CreateAck(sessionId, evt.event_id, unityFrame,
                        AckResult.applied);
                    SendAck(ack);
                }

                // Notify main thread
                OnControlEvent?.Invoke(evt);
            }
            catch (Exception ex)
            {
                Log($"Failed to process control_event: {ex.Message}");
            }
        }

        // ── Deserialization helpers ───────────────────────────────────────

        private static SessionManifest DeserializeSessionManifest(Dictionary<string, object> raw)
        {
            var m = new SessionManifest();
            m.research_id = GetString(raw, "research_id");
            m.session_id = GetString(raw, "session_id");
            m.study_stage = GetString(raw, "study_stage");
            m.runtime_mode = GetString(raw, "runtime_mode");
            m.cue_mode = GetString(raw, "cue_mode");
            m.assignment_arm = GetString(raw, "assignment_arm");
            m.allocation_index = GetInt(raw, "allocation_index");
            m.randomization_stratum = GetString(raw, "randomization_stratum");
            m.randomization_block = GetInt(raw, "randomization_block");
            m.randomization_list_hash = GetString(raw, "randomization_list_hash");
            m.protocol_config_version = GetString(raw, "protocol_config_version");
            m.randomization_version = GetString(raw, "randomization_version");
            m.strategy_version = GetStringOrNull(raw, "strategy_version");
            m.unity_build_hash = GetString(raw, "unity_build_hash");
            m.python_commit = GetString(raw, "python_commit");
            m.td_build_hash = GetStringOrNull(raw, "td_build_hash");
            m.source_policy = GetString(raw, "source_policy");
            m.created_utc = GetString(raw, "created_utc");
            m.breath_protocol_config_version = GetString(raw, "breath_protocol_config_version");
            m.breath_protocol_config_hash = GetString(raw, "breath_protocol_config_hash");

            // weather_sequence
            if (raw.TryGetValue("weather_sequence", out var ws) && ws is object[] wsArr)
            {
                m.weather_sequence = new string[wsArr.Length];
                for (int i = 0; i < wsArr.Length; i++)
                    m.weather_sequence[i] = wsArr[i]?.ToString();
            }
            else m.weather_sequence = new string[0];

            // module_durations
            if (raw.TryGetValue("module_durations", out var mdObj) && mdObj is Dictionary<string, object> md)
            {
                m.module_durations = new ModuleDurations
                {
                    demo = GetDouble(md, "demo"),
                    closed_loop = GetDouble(md, "closed_loop"),
                    lock_transition = GetDouble(md, "lock_transition")
                };
            }

            // device_config
            if (raw.TryGetValue("device_config", out var dcObj) && dcObj is Dictionary<string, object> dc)
            {
                m.device_config = new DeviceConfig();
                if (dc.TryGetValue("resp", out var respObj) && respObj is Dictionary<string, object> resp)
                    m.device_config.resp = new DeviceSensorConfig
                    {
                        source = GetString(resp, "source"),
                        serial = GetStringOrNull(resp, "serial")
                    };
                if (dc.TryGetValue("ecg", out var ecgObj) && ecgObj is Dictionary<string, object> ecg)
                    m.device_config.ecg = new DeviceSensorConfig
                    {
                        source = GetString(ecg, "source"),
                        serial = GetStringOrNull(ecg, "serial")
                    };
            }

            return m;
        }

        private static ControlEvent DeserializeControlEvent(Dictionary<string, object> raw)
        {
            var e = new ControlEvent();
            e.session_id = GetString(raw, "session_id");
            e.event_id = GetString(raw, "event_id");
            e.control_seq = GetInt(raw, "control_seq");
            e.event_type = GetString(raw, "event_type");
            e.issued_monotonic_ns = GetLong(raw, "issued_monotonic_ns");
            e.effective_monotonic_ns = GetLong(raw, "effective_monotonic_ns");
            e.clock_domain_id = GetString(raw, "clock_domain_id");

            if (raw.TryGetValue("payload", out var payloadObj) && payloadObj is Dictionary<string, object> payload)
                e.payload = new Dictionary<string, object>(payload);
            else
                e.payload = new Dictionary<string, object>();

            return e;
        }

        // ── Dictionary accessors ──────────────────────────────────────────

        private static string GetString(Dictionary<string, object> d, string key)
        {
            return d.TryGetValue(key, out var v) ? v?.ToString() ?? "" : "";
        }

        private static string GetStringOrNull(Dictionary<string, object> d, string key)
        {
            return d.TryGetValue(key, out var v) ? v?.ToString() : null;
        }

        private static int GetInt(Dictionary<string, object> d, string key)
        {
            if (d.TryGetValue(key, out var v))
            {
                if (v is int i) return i;
                if (v is long l) return (int)l;
                if (v is double dd) return (int)dd;
                if (int.TryParse(v?.ToString(), out var parsed)) return parsed;
            }
            return 0;
        }

        private static long GetLong(Dictionary<string, object> d, string key)
        {
            if (d.TryGetValue(key, out var v))
            {
                if (v is long l) return l;
                if (v is int i) return i;
                if (v is double dd) return (long)dd;
                if (long.TryParse(v?.ToString(), out var parsed)) return parsed;
            }
            return 0;
        }

        private static double GetDouble(Dictionary<string, object> d, string key)
        {
            if (d.TryGetValue(key, out var v))
            {
                if (v is double dd) return dd;
                if (v is float f) return f;
                if (v is int i) return i;
                if (v is long l) return l;
                if (double.TryParse(v?.ToString(),
                    System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out var parsed)) return parsed;
            }
            return 0.0;
        }

        private static void Log(string msg)
        {
            Debug.Log($"[U01.ReliableControlClient] {msg}");
        }
    }
}
