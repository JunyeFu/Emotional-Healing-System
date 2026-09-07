// U01 — ReliableControlClient: TCP client connecting to the Python control
// server on port 5010 using JSON Lines protocol.  Runs a receive thread;
// marshals incoming control_events to the main thread for processing.
//
// P0-3: Protocol errors (handshake rejection, schema mismatch) are fatal
//       — fail-closed, do NOT retry.  Only network errors trigger reconnect.
// P0-4: Wired ReconnectHandler and RenderReceiptManager.
// P0-5: Reconnect state sync (discard old receipts, wait for manifest).

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

namespace SRP.U01
{
    /// <summary>
    /// Fatal protocol error codes — when received, the client stops
    /// reconnecting and enters UNUSABLE state (P0-3 fail-closed).
    /// These match transport.py's handshake-phase error codes.
    /// </summary>
    public static class FatalProtocolErrors
    {
        public static readonly HashSet<string> Codes = new HashSet<string>
        {
            "SCHEMA_VERSION_MISMATCH",
            "TRANSPORT_VERSION_MISMATCH",
            "TRANSPORT_HANDSHAKE_INVALID",
            "TRANSPORT_ROLE_INVALID",
            "CLIENT_INSTANCE_ID_INVALID",
            "UNITY_CLIENT_ALREADY_CONNECTED"
        };
    }

    /// <summary>
    /// Connection state for external consumers.
    /// </summary>
    public enum ConnectionState
    {
        Disconnected,
        Connecting,
        Connected,
        Reconnecting,
        Unusable  // fatal protocol error — will not reconnect
    }

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
        [SerializeField] private int _connectTimeoutMs = 5000;
        [SerializeField] private int _receiveTimeoutMs = 5000;
        [SerializeField] private int _sendTimeoutMs = 2000;

        [Header("Handshake")]
        [SerializeField] private string _schemaVersion = "2.2";
        [SerializeField] private string _transportVersion = "1.0";
        [SerializeField] private string _clientInstanceId = "";

        // ── Dependencies ──────────────────────────────────────────────────
        [Header("Components (set via code in Awake)")]
        [SerializeField] private SessionMirror _sessionMirror;

        // R2-4: UDP5006Gate reference — wired in Awake via GetComponent.
        // ProcessSessionManifest calls _gate.ResetSession(newSessionId)
        // when session_id changes so frame_seq baseline resets.
        [SerializeField] private UDP5006Gate _gate;

        // P0-1: AckManager (idempotent ACK sender)
        private AckManager _ackManager;

        // P0-4: RenderReceiptManager wired in
        private RenderReceiptManager _renderReceiptManager;

        // P0-4: ReconnectHandler wired in (replaces manual Thread.Sleep backoff)
        private ReconnectHandler _reconnectHandler;

        // ── Internal state ────────────────────────────────────────────────
        private TcpClient _tcpClient;
        private System.IO.Stream _stream;
        private Thread _receiveThread;
        private Thread _sendThread;
        private volatile bool _isConnected;
        private volatile bool _isRunning;
        private int _generation;

        // P0-3: Track whether we are in an unusable (fatal) state
        private volatile bool _isUnusable;
        private string _fatalErrorCode;

        // R2-5: Consecutive unknown error-code / JSON-parse-failure counter.
        // When this reaches UnknownErrorCodeThreshold the client degrades
        // to unusable state (same as fatal protocol error).
        private const int UnknownErrorCodeThreshold = 5;
        private volatile int _consecutiveUnknownErrorCount = 0;

        // Thread-safe queues
        private readonly ConcurrentQueue<string> _incomingLines = new();
        private readonly ConcurrentQueue<byte[]> _outgoingLines = new();

        // P0-4: Fault injection via ReconnectHandler
        private bool _faultDropEnabled;
        private int _faultDropCounter;
        private int _faultDropEveryN;
        private bool _faultCorruptEnabled;
        private int _faultCorruptCounter;
        private int _faultCorruptEveryN;

        // ── Events ────────────────────────────────────────────────────────
        /// <summary>Fired on main thread when a valid control_event arrives.</summary>
        public event Action<ControlEvent> OnControlEvent;

        /// <summary>Fired on main thread when a session_manifest arrives.</summary>
        public event Action<SessionManifest> OnSessionManifest;

        /// <summary>Fired when connection state changes.</summary>
        public event Action<bool> OnConnectionChanged;

        /// <summary>Fired on main thread when a transport error arrives.</summary>
        public event Action<string> OnTransportError;

        /// <summary>Fired when a render receipt is ready to send.</summary>
        public event Action<RenderReceipt> OnRenderReceiptReady;

        /// <summary>Fired when connection state enum changes.</summary>
        public event Action<ConnectionState> OnConnectionStateChanged;

        // ── Properties ────────────────────────────────────────────────────
        public bool IsConnected => _isConnected;
        public bool IsUnusable => _isUnusable;
        public int Generation => _generation;
        public string Host { get => _host; set => _host = value; }
        public int Port { get => _port; set => _port = value; }
        public string ClientInstanceId => _clientInstanceId;
        public AckManager AckMgr => _ackManager;
        public RenderReceiptManager ReceiptMgr => _renderReceiptManager;
        public ReconnectHandler ReconnectHdl => _reconnectHandler;
        public UDP5006Gate Gate => _gate;

        // R2-12: Clock sync values from welcome handshake
        private long _clockOffsetNs;
        private long _syncUncertaintyNs;

        /// <summary>Server-reported clock offset in nanoseconds.</summary>
        public long ClockOffsetNs => _clockOffsetNs;

        /// <summary>Server-reported sync uncertainty in nanoseconds.</summary>
        public long SyncUncertaintyNs => _syncUncertaintyNs;

        // ── Lifecycle ─────────────────────────────────────────────────────

        void Awake()
        {
            if (string.IsNullOrEmpty(_clientInstanceId))
                _clientInstanceId = Guid.NewGuid().ToString("N");

            // P0-4: Construct components in code (P1-1 fix: can't SerializeField
            // plain C# classes in Unity).
            _ackManager = new AckManager();
            _renderReceiptManager = new RenderReceiptManager();

            // R2-2: Do NOT send here — FlushPendingReceipts is the single send path.
            // The event handler only forwards to external subscribers for logging/UI.
            _renderReceiptManager.OnReceiptReady += receipt =>
            {
                OnRenderReceiptReady?.Invoke(receipt);
            };

            // R2-4: Wire UDP5006Gate reference if not inspector-assigned.
            // Same GameObject assumption — both are network components.
            if (_gate == null)
                _gate = GetComponent<UDP5006Gate>();
            if (_gate != null)
                Log($"R2-4: Gate reference wired — UDP5006Gate.ResetSession available");
            else
                Log("R2-4: WARNING — UDP5006Gate not found on this GameObject. " +
                    "ResetSession will not be called on session change.");

            // P0-4: ReconnectHandler (uses this MonoBehaviour as coroutine runner)
            var policy = new ReconnectPolicy
            {
                InitialBackoffMs = 500,
                MaxBackoffMs = 10000,
                BackoffMultiplier = 2.0f,
                MaxReconnectAttempts = 20,
                JitterMaxMs = 200
            };
            _reconnectHandler = new ReconnectHandler(policy, this);
            _reconnectHandler.OnReconnectFailed += () =>
            {
                Log("Reconnect exhausted — entering UNUSABLE");
                _isUnusable = true;
                OnConnectionStateChanged?.Invoke(ConnectionState.Unusable);
            };
            _reconnectHandler.OnReconnected += () =>
            {
                Log("Reconnected successfully");
                OnConnectionStateChanged?.Invoke(ConnectionState.Connected);
            };
            _reconnectHandler.OnGenerationChanged += gen =>
            {
                _generation = gen;
                Log($"Generation changed to {gen}");
            };
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
            _isUnusable = false;
            _fatalErrorCode = null;
            _consecutiveUnknownErrorCount = 0;

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

            OnConnectionStateChanged?.Invoke(ConnectionState.Connecting);
            Log($"Connecting to {_host}:{_port}...");
        }

        /// <summary>Gracefully disconnect.</summary>
        public void Disconnect()
        {
            _isRunning = false;
            _isConnected = false;
            _reconnectHandler?.Abort();

            try { _stream?.Close(); } catch { }
            try { _tcpClient?.Close(); } catch { }

            _receiveThread?.Join(1000);
            _sendThread?.Join(1000);

            _stream = null;
            _tcpClient = null;
            OnConnectionStateChanged?.Invoke(ConnectionState.Disconnected);
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

        // ── P0-4: Fault injection for testing ────────────────────────────

        /// <summary>Enable message drop fault injection (every Nth receive).</summary>
        public void EnableDropFault(int everyN)
        {
            _faultDropEveryN = everyN;
            _faultDropEnabled = everyN > 0;
            _faultDropCounter = 0;
        }

        /// <summary>Enable message corruption fault injection.</summary>
        public void EnableCorruptFault(int everyN)
        {
            _faultCorruptEveryN = everyN;
            _faultCorruptEnabled = everyN > 0;
            _faultCorruptCounter = 0;
        }

        /// <summary>Clear all fault injection.</summary>
        public void ClearFaults()
        {
            _faultDropEnabled = false;
            _faultCorruptEnabled = false;
        }

        // ── Network thread: connect + handshake ───────────────────────────

        private void ReceiveLoop()
        {
            while (_isRunning)
            {
                // P0-3: Stop immediately if in unusable (fatal) state
                if (_isUnusable)
                {
                    Log("In unusable state — receive loop exiting");
                    break;
                }

                try
                {
                    ConnectAndHandshake();
                    if (!_isRunning || _isUnusable) break;
                    ReadLoop();
                }
                catch (Exception ex)
                {
                    if (!_isRunning) break;

                    // P0-3: Check if this is a fatal protocol error
                    string errorCode = ExtractErrorCode(ex);
                    if (errorCode != null && FatalProtocolErrors.Codes.Contains(errorCode))
                    {
                        Log($"FATAL protocol error: {errorCode} — failing closed");
                        _isUnusable = true;
                        _fatalErrorCode = errorCode;
                        OnTransportError?.Invoke(errorCode);
                        OnConnectionStateChanged?.Invoke(ConnectionState.Unusable);
                        break;  // Do NOT retry — fail-closed per contract
                    }

                    Log($"Receive error (retryable): {ex.Message}");
                }
                finally
                {
                    bool wasConnected = _isConnected;
                    _isConnected = false;
                    if (wasConnected)
                    {
                        _incomingLines.Enqueue("__DISCONNECTED__");
                    }
                }

                // P0-4: Use ReconnectHandler for backoff (not fixed Thread.Sleep)
                if (_isRunning && !_isUnusable)
                {
                    OnConnectionStateChanged?.Invoke(ConnectionState.Reconnecting);
                    // P0-5: Sync state on disconnect
                    SyncReconnectState();

                    // R2-3 fix: Only the network thread reconnects (ConnectAndHandshake).
                    // ReconnectHandler is only used for CurrentBackoffMs (backoff timing).
                    // Deleted fake SignalDisconnected(() => true) — it triggered a
                    // coroutine path that returned success immediately without a real
                    // TCP connection, causing double generation increment.
                    int backoffMs = _reconnectHandler.CurrentBackoffMs;
                    int jitter = UnityEngine.Random.Range(0, 200);
                    Thread.Sleep(backoffMs + jitter);
                }
            }
        }

        private void ConnectAndHandshake()
        {
            _tcpClient = new TcpClient();
            _tcpClient.NoDelay = true;
            _tcpClient.ReceiveTimeout = _receiveTimeoutMs;
            _tcpClient.SendTimeout = _sendTimeoutMs;

            // P0-4: Fault injection — force connect failure
            if (_reconnectHandler != null && _reconnectHandler.ShouldInjectFault())
            {
                throw new IOException("Fault injection — connect forced to fail");
            }

            // R2-10: Use ConnectAsync with timeout instead of sync Connect
            var connectTask = _tcpClient.ConnectAsync(_host, _port);
            if (!connectTask.Wait(_connectTimeoutMs))
            {
                _tcpClient?.Close();
                _tcpClient?.Dispose();
                _tcpClient = null;
                throw new IOException(
                    $"Connection to {_host}:{_port} timed out after {_connectTimeoutMs}ms");
            }
            connectTask.GetAwaiter().GetResult(); // propagate exceptions
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

            // Check for transport error frame
            if (welcome.TryGetValue("transport_type", out var tt) && tt?.ToString() == "error")
            {
                string errCode = welcome.TryGetValue("error_code", out var ec) ? ec?.ToString() : "UNKNOWN";
                // P0-3: Wrap error code so ReceiveLoop can classify it
                throw new ProtocolErrorException(errCode,
                    $"Server error: {errCode}");
            }

            // Check for handshake rejection (accepted=false)
            if (welcome.TryGetValue("accepted", out var acc) && acc is bool accepted && !accepted)
            {
                string errCode = welcome.TryGetValue("error_code", out var ec) ? ec?.ToString() : "UNKNOWN";
                throw new ProtocolErrorException(errCode,
                    $"Handshake rejected: {errCode}");
            }

            _isConnected = true;
            _incomingLines.Enqueue("__CONNECTED__");

            // R2-12: Extract clock sync values from welcome
            if (welcome.TryGetValue("clock_offset_ns", out var cOff) && cOff is long cOffVal)
                _clockOffsetNs = cOffVal;
            else if (welcome.TryGetValue("clock_offset_ns", out var cOffObj) && cOffObj != null)
                long.TryParse(cOffObj.ToString(), out _clockOffsetNs);

            if (welcome.TryGetValue("sync_uncertainty_ns", out var sUnc) && sUnc is long sUncVal)
                _syncUncertaintyNs = sUncVal;
            else if (welcome.TryGetValue("sync_uncertainty_ns", out var sUncObj) && sUncObj != null)
                long.TryParse(sUncObj.ToString(), out _syncUncertaintyNs);

            // R2-12: Warn if sync uncertainty exceeds 50ms (50,000,000 ns)
            const long SyncUncertaintyWarningNs = 50_000_000L;
            if (_syncUncertaintyNs > SyncUncertaintyWarningNs)
            {
                Debug.LogWarning(
                    $"[U01.ReliableControlClient] R2-12: sync_uncertainty_ns={_syncUncertaintyNs} " +
                    $"exceeds 50ms threshold ({SyncUncertaintyWarningNs} ns)");
            }

            // P0-4: Signal reconnect handler that we are connected
            _reconnectHandler.SignalConnected();

            Log($"Handshake OK — connected (gen {_generation})");
        }

        private void ReadLoop()
        {
            while (_isRunning && _isConnected)
            {
                string line = ReadLine();
                if (line == null) break; // server closed

                // P0-4: Fault injection — drop every Nth message
                if (_faultDropEnabled)
                {
                    _faultDropCounter++;
                    if (_faultDropEveryN > 0 && _faultDropCounter % _faultDropEveryN == 0)
                    {
                        Log($"Fault injection: dropping message #{_faultDropCounter}");
                        continue;
                    }
                }

                // P0-4: Fault injection — corrupt every Nth message
                if (_faultCorruptEnabled)
                {
                    _faultCorruptCounter++;
                    if (_faultCorruptEveryN > 0 && _faultCorruptCounter % _faultCorruptEveryN == 0)
                    {
                        Log($"Fault injection: corrupting message #{_faultCorruptCounter}");
                        line = "{invalid json content!!";
                    }
                }

                _incomingLines.Enqueue(line);
            }
        }

        private string ReadLine()
        {
            if (_stream == null) return null;

            // P1-5 fix: read bytes then decode as UTF-8 to avoid per-byte
            // (char)b corruption of multi-byte characters.
            var buffer = new List<byte>();
            int b;
            while (true)
            {
                b = _stream.ReadByte();
                if (b < 0) return null; // EOF
                if (b == '\n') break;
                buffer.Add((byte)b);
            }
            if (buffer.Count == 0) return "";
            return Encoding.UTF8.GetString(buffer.ToArray());
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
                    OnConnectionStateChanged?.Invoke(ConnectionState.Connected);
                    continue;
                }
                if (line == "__DISCONNECTED__")
                {
                    OnConnectionChanged?.Invoke(false);
                    if (!_isUnusable)
                        OnConnectionStateChanged?.Invoke(ConnectionState.Reconnecting);
                    continue;
                }

                ProcessIncomingLine(line);
            }

            // P0-4: Flush any pending render receipts
            FlushPendingReceipts();
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
                // R2-5: JSON parse failure — count and degrade at threshold
                Log($"JSON parse error: {ex.Message}");
                OnTransportError?.Invoke("TRANSPORT_FRAME_INVALID");
                _consecutiveUnknownErrorCount++;
                if (_consecutiveUnknownErrorCount >= UnknownErrorCodeThreshold)
                {
                    Log($"TRANSPORT_FRAME_INVALID consecutive count >= {UnknownErrorCodeThreshold} — " +
                        "degrading to unusable");
                    _isUnusable = true;
                    _fatalErrorCode = "TRANSPORT_FRAME_INVALID";
                    OnConnectionStateChanged?.Invoke(ConnectionState.Unusable);
                }
                return;
            }

            if (!msg.TryGetValue("message_type", out var mtRaw))
            {
                // Could be transport-level (welcome, error, etc.)
                if (msg.TryGetValue("transport_type", out var ttt) && ttt?.ToString() == "error")
                {
                    // R2-5: Classify error frame by error_code per transport.py semantics
                    string errorCode = msg.TryGetValue("error_code", out var ec2)
                        ? ec2?.ToString() : "UNKNOWN";
                    ClassifyRuntimeError(errorCode);
                }
                return;
            }

            string messageType = mtRaw?.ToString();

            // R2-13: schema_version==2.2 gate for business frames
            // Transport-level frames (welcome, error) don't carry schema_version.
            if (messageType == "session_manifest" || messageType == "control_event"
                || messageType == "ack" || messageType == "render_receipt")
            {
                if (!msg.TryGetValue("schema_version", out var svRaw)
                    || svRaw?.ToString() != "2.2")
                {
                    string sv = svRaw?.ToString() ?? "(missing)";
                    Log($"R2-13: schema_version mismatch on {messageType} — " +
                        $"expected '2.2', got '{sv}', rejecting");
                    OnTransportError?.Invoke("SCHEMA_VERSION_MISMATCH");
                    _consecutiveUnknownErrorCount++;
                    if (_consecutiveUnknownErrorCount >= UnknownErrorCodeThreshold)
                    {
                        Log($"R2-13: schema_version mismatch count >= " +
                            $"{UnknownErrorCodeThreshold} — degrading to unusable");
                        _isUnusable = true;
                        _fatalErrorCode = "SCHEMA_VERSION_MISMATCH";
                        OnConnectionStateChanged?.Invoke(ConnectionState.Unusable);
                    }
                    return;
                }
                // Reset counter for valid schema_version
                _consecutiveUnknownErrorCount = 0;
            }

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

        // ── R2-5: Runtime error frame classification ────────────────────

        /// <summary>
        /// R2-5: Classify a runtime error frame by its error_code.
        ///
        /// transport.py semantics (reference: _handle_client / _handle_unity_message):
        ///   CONNECTION_MISMATCH → generation mismatch; client must close socket and
        ///       reconnect (triggers the same path as a network disconnect).
        ///   NOT_PENDING         → duplicate/unknown ACK or receipt; log + count only.
        ///   REJECTED / TIMEOUT  → server-side rejection or ACK timeout; log only.
        ///   Unknown error_code  → log + consecutive threshold degradation.
        /// </summary>
        private void ClassifyRuntimeError(string errorCode)
        {
            switch (errorCode)
            {
                case "CONTROL_ACK_CONNECTION_MISMATCH":
                    Log($"CONNECTION_MISMATCH received — closing socket and reconnecting");
                    OnTransportError?.Invoke(errorCode);
                    CloseSocketForReconnect();
                    break;

                case "CONTROL_ACK_NOT_PENDING":
                    // Repeated receipt / unknown event_id — log + count, do NOT reconnect
                    Debug.LogWarning(
                        $"[U01.ReliableControlClient] NOT_PENDING: {errorCode}");
                    OnTransportError?.Invoke(errorCode);
                    break;

                case "CONTROL_ACK_REJECTED":
                case "CONTROL_ACK_TIMEOUT":
                    // Server-side rejection or ACK timeout — informational only
                    Log($"Transport error (no action): {errorCode}");
                    OnTransportError?.Invoke(errorCode);
                    break;

                default:
                    // Unknown error code — log and degrade at consecutive threshold
                    Log($"Unknown transport error: {errorCode} " +
                        $"(count={_consecutiveUnknownErrorCount + 1}/{UnknownErrorCodeThreshold})");
                    OnTransportError?.Invoke(errorCode);
                    _consecutiveUnknownErrorCount++;
                    if (_consecutiveUnknownErrorCount >= UnknownErrorCodeThreshold)
                    {
                        Log($"Unknown error codes consecutive count >= {UnknownErrorCodeThreshold} " +
                            $"— degrading to unusable");
                        _isUnusable = true;
                        _fatalErrorCode = errorCode;
                        OnConnectionStateChanged?.Invoke(ConnectionState.Unusable);
                    }
                    break;
            }

            // Reset counter for known error codes (only unknown codes increment)
            if (errorCode != "CONTROL_ACK_CONNECTION_MISMATCH"
                && errorCode != "CONTROL_ACK_NOT_PENDING"
                && errorCode != "CONTROL_ACK_REJECTED"
                && errorCode != "CONTROL_ACK_TIMEOUT")
            {
                // Unknown — already incremented above; do NOT reset here
            }
            else
            {
                _consecutiveUnknownErrorCount = 0;
            }
        }

        /// <summary>
        /// R2-5: Close the TCP socket from the main thread so that the network
        /// thread's ReadLoop sees an IOException and enters the reconnect path
        /// in ReceiveLoop.  This is the same action as a server-initiated drop.
        /// Called when CONNECTION_MISMATCH indicates our generation is stale.
        /// </summary>
        private void CloseSocketForReconnect()
        {
            try { _stream?.Close(); } catch { }
            try { _tcpClient?.Close(); } catch { }
        }

        private void ProcessSessionManifest(Dictionary<string, object> raw)
        {
            try
            {
                var manifest = DeserializeSessionManifest(raw);

                // R2-4: Detect session_id change and reset UDP gate frame_seq.
                // _appliedEventIds is PRESERVED across sessions (per contract),
                // but frame_seq baseline must restart so new session frames
                // are not rejected as "stale".
                string newSessionId = manifest.session_id;
                string previousSessionId = _sessionMirror?.Snapshot?.SessionId;

                bool sessionChanged = !string.IsNullOrEmpty(newSessionId)
                    && newSessionId != previousSessionId;

                if (sessionChanged)
                {
                    Log($"R2-4: Session changed ({previousSessionId} -> {newSessionId})");
                    _gate?.ResetSession(newSessionId);

                    // Cross-session: reset AckManager tracking so old session
                    // event_ids do not cause false "duplicate" rejections.
                    _ackManager?.Reset();

                    // Cross-session: discard old render receipts.
                    _renderReceiptManager?.DiscardAll();
                }

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

                // R2-9: Validate session_id matches current session
                var snap = _sessionMirror?.Snapshot;
                if (snap != null && snap.HasSession
                    && evt.session_id != snap.SessionId)
                {
                    Log($"R2-9: control_event session_id mismatch — " +
                        $"event='{evt.session_id}' vs expected='{snap.SessionId}', rejecting");
                    OnTransportError?.Invoke("SESSION_ID_MISMATCH");
                    return;
                }

                // Capture received timestamp (P1-2: ideally from receive thread,
                // but this is the best we can do from the main thread).
                long receivedNs = AckManagerTimestampNow();
                string sessionId = snap?.SessionId ?? "";
                int unityFrame = Time.frameCount;

                if (_ackManager == null)
                {
                    Log("AckManager is null — cannot process control_event");
                    return;
                }

                if (_ackManager.IsApplied(evt.event_id))
                {
                    // P0-1: Duplicate event — do NOT re-apply
                    var dupAck = _ackManager.CreateAck(
                        sessionId, evt.event_id, unityFrame,
                        AckResult.duplicate_ignored, receivedNs);
                    SendAck(dupAck);
                    return;
                }

                // New event — apply to session mirror
                _sessionMirror?.ApplyControlEvent(evt);

                // Mark as applied *after* successful application
                _ackManager.MarkApplied(evt.event_id);

                // Send applied ACK
                var ack = _ackManager.CreateAck(
                    sessionId, evt.event_id, unityFrame,
                    AckResult.applied, receivedNs);
                SendAck(ack);

                // P0-4: Register for render receipt — ONLY for segment events.
                // Server core.py _confirm_receipt rejects non-segment receipts
                // with RENDER_RECEIPT_CONTROL_TYPE_INVALID.
                // For segment: skipped/failed receipts are FATAL — server marks
                // the session as transport_failure (core.py L660-663).
                // pause/abort/prepare/start/module/end events send NO receipts;
                // any pending receipts for them are discarded at session end.
                if (evt.event_type == "segment")
                {
                    string moduleId = "";
                    string segment = "";
                    if (evt.payload != null)
                    {
                        if (evt.payload.TryGetValue("module_id", out var mid))
                            moduleId = mid?.ToString() ?? "";
                        if (evt.payload.TryGetValue("segment", out var seg))
                            segment = seg?.ToString() ?? "";
                    }
                    _renderReceiptManager?.RegisterEvent(evt, moduleId, segment);

                    // R3-1: DEV-only auto-confirm for segment events.
                    // In dev_mock/dev_replay there is no real visual layer (U-02) to call
                    // ConfirmRendered. Simulate successful render so render receipts flow
                    // end-to-end. Formal modes (formal_level_c / formal_stage_1 /
                    // formal_stage_3) MUST NOT auto-confirm — they rely on real rendering.
                    var snapMode = _sessionMirror?.Snapshot;
                    string runtimeMode = snapMode?.RuntimeMode ?? "";
                    if (runtimeMode == "dev_mock" || runtimeMode == "dev_replay")
                    {
                        ConfirmRendered(evt.event_id);
                    }
                }

                // Notify main thread
                OnControlEvent?.Invoke(evt);
            }
            catch (Exception ex)
            {
                Log($"Failed to process control_event: {ex.Message}");
            }
        }

        /// <summary>
        /// P0-4: Flush any pending render receipts to the send queue.
        /// Called from main thread (Update).
        /// </summary>
        private void FlushPendingReceipts()
        {
            if (_renderReceiptManager == null) return;

            var snap = _sessionMirror?.Snapshot;
            string sessionId = snap?.SessionId ?? "";
            if (string.IsNullOrEmpty(sessionId)) return;

            var unsent = _renderReceiptManager.GetUnsentReceipts(sessionId);
            foreach (var receipt in unsent)
            {
                SendRenderReceipt(receipt);
                _renderReceiptManager.MarkSent(receipt.event_id);
                OnRenderReceiptReady?.Invoke(receipt);
            }
        }

        /// <summary>
        /// P0-4: Complete a render receipt for a rendered frame.
        /// Should be called from the visual layer after rendering is confirmed.
        /// </summary>
        public void ConfirmRendered(string eventId)
        {
            var snap = _sessionMirror?.Snapshot;
            string sessionId = snap?.SessionId ?? "";
            _renderReceiptManager?.CompleteRendered(eventId, sessionId);
        }

        /// <summary>
        /// P0-4/R3-3: Complete a render receipt as skipped (no render needed).
        /// Only applicable to segment events — non-segment events are never registered.
        /// WARNING: A skipped receipt for a segment event is FATAL — server core.py
        /// marks the session as transport_failure (L660-663).
        /// </summary>
        public void ConfirmRenderSkipped(string eventId, string reason = null)
        {
            var snap = _sessionMirror?.Snapshot;
            string sessionId = snap?.SessionId ?? "";
            _renderReceiptManager?.CompleteSkipped(eventId, sessionId, reason);
        }

        /// <summary>
        /// P0-4/R3-3: Complete a render receipt as failed.
        /// Only applicable to segment events — non-segment events are never registered.
        /// WARNING: A failed receipt for a segment event is FATAL — server core.py
        /// marks the session as transport_failure (L660-663).
        /// </summary>
        public void ConfirmRenderFailed(string eventId, string errorCode)
        {
            var snap = _sessionMirror?.Snapshot;
            string sessionId = snap?.SessionId ?? "";
            _renderReceiptManager?.CompleteFailed(eventId, sessionId, errorCode);
        }

        // ── P0-5: Reconnect state sync ──────────────────────────────────

        /// <summary>
        /// P0-5: Synchronize state when reconnect is triggered.
        /// - Discard pending render receipts (mark as failed)
        /// - _appliedEventIds is PRESERVED (per contract)
        /// - UDP gate frame_seq will be reset when new session_manifest arrives
        /// </summary>
        private void SyncReconnectState()
        {
            // P0-5: Mark all pending render receipts as failed
            // (don't send old-generation receipts)
            _renderReceiptManager?.DiscardAll();

            Log($"Reconnect state sync: gen={_generation}, " +
                $"applied={_ackManager?.AppliedCount ?? 0}");
        }

        // ── Error classification helpers ──────────────────────────────────

        /// <summary>
        /// Extract error code from an exception.  Handles
        /// ProtocolErrorException (thrown during handshake) and
        /// IOException messages containing known error codes.
        /// </summary>
        private static string ExtractErrorCode(Exception ex)
        {
            if (ex is ProtocolErrorException pex)
                return pex.ErrorCode;

            // Check if the exception message contains a known error code
            string msg = ex.Message;
            foreach (var code in FatalProtocolErrors.Codes)
            {
                if (msg.Contains(code))
                    return code;
            }
            return null;
        }

        /// <summary>
        /// P0-3: Exception type for fatal protocol errors during handshake.
        /// Carries the error code for classification in ReceiveLoop.
        /// </summary>
        private sealed class ProtocolErrorException : Exception
        {
            public string ErrorCode { get; }

            public ProtocolErrorException(string errorCode, string message)
                : base(message)
            {
                ErrorCode = errorCode;
            }
        }

        // ── Timestamp helpers ────────────────────────────────────────────

        /// <summary>
        /// Get monotonic timestamp in nanoseconds.  Uses Stopwatch for
        /// monotonicity (P1-1 alignment).
        /// </summary>
        private static long AckManagerTimestampNow()
        {
            return (long)(System.Diagnostics.Stopwatch.GetTimestamp()
                * (1_000_000_000.0 / System.Diagnostics.Stopwatch.Frequency));
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
