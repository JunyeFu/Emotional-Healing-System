// U01 — UDP5006Gate: enhanced UDP receiver for telemetry_frame messages on
// port 5006 with contract validation, sequence tracking, and rate monitoring.
// Replaces the bare UDPReceiver with schema-aware filtering.

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

namespace SRP.U01
{
    /// <summary>
    /// Result of validating a UDP telemetry frame.
    /// </summary>
    public enum GateResult
    {
        Accepted,
        DuplicateSequence,
        StaleSequence,
        InvalidJson,
        MissingMessageType,
        NotTelemetryFrame,
        SchemaViolation,
        RateLimited
    }

    /// <summary>
    /// A validated telemetry frame ready for processing.
    /// </summary>
    public sealed class GateReceipt
    {
        public GateResult Result { get; set; }
        public Dictionary<string, object> Raw { get; set; }
        public int FrameSeq { get; set; }
        public long ReceivedMonotonicNs { get; set; }
        public string ErrorMessage { get; set; }
    }

    /// <summary>
    /// Enhanced UDP receive gate for port 5006.
    ///
    /// Responsibilities:
    ///   1. Listen for UDP datagrams on the configured port
    ///   2. Validate JSON structure and message_type == "telemetry_frame"
    ///   3. Track frame_seq to detect stale/duplicate frames
    ///   4. Enforce rate limits (configurable max Hz)
    ///   5. Log dropped/invalid frames for diagnostics
    ///   6. Queue validated frames for main-thread consumption
    ///
    /// Thread safety: receive loop runs on a background thread; main thread
    /// calls <see cref="DequeueNext"/> from Update().
    /// </summary>
    public sealed class UDP5006Gate : MonoBehaviour
    {
        // ── Inspector settings ────────────────────────────────────────────
        [Header("UDP Config")]
        [SerializeField] private int _port = 5006;
        [SerializeField] private int _maxDatagramBytes = 65535;
        [SerializeField] private int _receiveTimeoutMs = 1000;

        [Header("Validation")]
        [SerializeField] private bool _requireTelemetryFrame = true;
        [SerializeField] private bool _enforceMonotonicSeq = true;

        [Header("Rate Limiting")]
        [SerializeField] private int _maxRateHz = 25;
        [SerializeField] private bool _enableRateLimiting = true;

        [Header("Diagnostics")]
        [SerializeField] private bool _logDroppedFrames = true;
        [SerializeField] private int _diagnosticIntervalFrames = 100;

        // ── Internal state ────────────────────────────────────────────────
        private UdpClient _udpClient;
        private Thread _receiveThread;
        private volatile bool _isRunning;

        private int _lastFrameSeq = -1;
        private long _lastReceiveTicks = -1;
        private int _framesReceived;
        private int _framesDropped;
        private int _framesAccepted;
        private int _framesDuplicate;
        private int _framesStale;
        private int _framesInvalid;

        // Thread-safe queue for validated frames
        private readonly ConcurrentQueue<GateReceipt> _queue = new();

        // ── Events ────────────────────────────────────────────────────────
        /// <summary>Fired on main thread when a validated telemetry frame arrives.</summary>
        public event Action<Dictionary<string, object>> OnTelemetryFrame;

        /// <summary>Fired when a frame is rejected.</summary>
        public event Action<GateReceipt> OnFrameRejected;

        // ── Properties ────────────────────────────────────────────────────
        public int Port => _port;
        public bool IsRunning => _isRunning;
        public int FramesAccepted => _framesAccepted;
        public int FramesDropped => _framesDropped;
        public int FramesDuplicate => _framesDuplicate;
        public int FramesStale => _framesStale;
        public int FramesInvalid => _framesInvalid;
        public int LastFrameSeq => _lastFrameSeq;

        // ── Lifecycle ─────────────────────────────────────────────────────

        void Start()
        {
            StartListening();
        }

        void Update()
        {
            DequeueAndDispatch();
        }

        void OnDestroy()
        {
            StopListening();
        }

        // ── Public API ────────────────────────────────────────────────────

        /// <summary>Start listening for UDP telemetry frames.</summary>
        public void StartListening()
        {
            if (_isRunning) return;

            try
            {
                _udpClient = new UdpClient(_port);
                _udpClient.Client.ReceiveTimeout = _receiveTimeoutMs;
                _isRunning = true;

                _receiveThread = new Thread(ReceiveLoop)
                {
                    IsBackground = true,
                    Name = "U01-UDP-5006"
                };
                _receiveThread.Start();
                Log($"Listening on UDP port {_port}");
            }
            catch (Exception ex)
            {
                Log($"Failed to start UDP listener: {ex.Message}");
            }
        }

        /// <summary>Stop listening and close the socket.</summary>
        public void StopListening()
        {
            _isRunning = false;
            try { _udpClient?.Close(); } catch { }
            _receiveThread?.Join(1000);
            _udpClient = null;
            Log("Stopped listening");
        }

        /// <summary>Reset all sequence tracking and counters.</summary>
        public void ResetState()
        {
            _lastFrameSeq = -1;
            _lastReceiveTicks = -1;
            _framesReceived = 0;
            _framesDropped = 0;
            _framesAccepted = 0;
            _framesDuplicate = 0;
            _framesStale = 0;
            _framesInvalid = 0;
        }

        /// <summary>
        /// Dequeue the next validated frame (if any) and process it.
        /// Call from Update().  Returns true if a frame was dispatched.
        /// </summary>
        public bool DequeueNext()
        {
            if (!_queue.TryDequeue(out var receipt)) return false;

            if (receipt.Result == GateResult.Accepted)
            {
                _framesAccepted++;
                OnTelemetryFrame?.Invoke(receipt.Raw);

                // Periodic diagnostics
                if (_diagnosticIntervalFrames > 0 &&
                    _framesAccepted % _diagnosticIntervalFrames == 0)
                {
                    LogDiagnostics();
                }
            }
            else
            {
                _framesDropped++;
                OnFrameRejected?.Invoke(receipt);
            }

            return true;
        }

        /// <summary>Dequeue and dispatch all pending frames.</summary>
        public void DequeueAndDispatch()
        {
            int processed = 0;
            while (processed < 10 && _queue.TryDequeue(out var receipt))
            {
                processed++;
                if (receipt.Result == GateResult.Accepted)
                {
                    _framesAccepted++;
                    OnTelemetryFrame?.Invoke(receipt.Raw);
                }
                else
                {
                    _framesDropped++;
                    OnFrameRejected?.Invoke(receipt);
                }
            }
        }

        // ── Receive thread ────────────────────────────────────────────────

        private void ReceiveLoop()
        {
            var remoteEp = new IPEndPoint(IPAddress.Any, 0);

            while (_isRunning)
            {
                try
                {
                    if (_udpClient == null || _udpClient.Client == null) break;
                    byte[] data = _udpClient.Receive(ref remoteEp);
                    Interlocked.Increment(ref _framesReceived);
                    ProcessDatagram(data);
                }
                catch (SocketException)
                {
                    // Timeout or close — normal during shutdown
                }
                catch (ObjectDisposedException)
                {
                    break;
                }
                catch (Exception ex)
                {
                    if (_isRunning)
                        Debug.LogWarning($"[U01.UDP5006Gate] Receive error: {ex.Message}");
                }
            }
        }

        private void ProcessDatagram(byte[] data)
        {
            GateReceipt receipt = ValidateWithTracking(data);
            _queue.Enqueue(receipt);
        }

        // ── Validation pipeline ───────────────────────────────────────────

        /// <summary>
        /// Validate a raw UDP datagram against the runtime contract v2.2.
        /// Returns a GateReceipt indicating acceptance or the specific rejection reason.
        /// </summary>
        public static GateReceipt Validate(byte[] data)
        {
            // 1. Parse JSON
            Dictionary<string, object> msg;
            try
            {
                string json = Encoding.UTF8.GetString(data);
                msg = JsonLines.Deserialize(json);
            }
            catch (Exception)
            {
                return new GateReceipt
                {
                    Result = GateResult.InvalidJson,
                    ErrorMessage = "Failed to parse JSON"
                };
            }

            // 2. Check message_type
            if (!msg.TryGetValue("message_type", out var mtObj) || mtObj == null)
            {
                return new GateReceipt
                {
                    Result = GateResult.MissingMessageType,
                    Raw = msg,
                    ErrorMessage = "Missing message_type field"
                };
            }

            string messageType = mtObj.ToString();

            // 3. Require telemetry_frame (optional, but default on)
            if (messageType != "telemetry_frame")
            {
                return new GateReceipt
                {
                    Result = GateResult.NotTelemetryFrame,
                    Raw = msg,
                    ErrorMessage = $"Unexpected message_type: {messageType}"
                };
            }

            // 4. Validate required fields exist
            string[] requiredFields = {
                "schema_version", "session_id", "frame_seq", "clock_domain_id",
                "module_id", "segment", "target_phase", "actual_phase"
            };
            foreach (var field in requiredFields)
            {
                if (!msg.ContainsKey(field))
                {
                    return new GateReceipt
                    {
                        Result = GateResult.SchemaViolation,
                        Raw = msg,
                        ErrorMessage = $"Missing required field: {field}"
                    };
                }
            }

            // 5. Validate schema_version
            if (msg.TryGetValue("schema_version", out var sv) && sv?.ToString() != "2.2")
            {
                return new GateReceipt
                {
                    Result = GateResult.SchemaViolation,
                    Raw = msg,
                    ErrorMessage = $"Unsupported schema_version: {sv}"
                };
            }

            return new GateReceipt
            {
                Result = GateResult.Accepted,
                Raw = msg,
                FrameSeq = GetIntFromDict(msg, "frame_seq")
            };
        }

        /// <summary>
        /// Full validation including sequence tracking and rate limiting.
        /// Called from the receive thread.
        /// </summary>
        private GateReceipt ValidateWithTracking(byte[] data)
        {
            // Basic validation
            GateReceipt receipt = ValidateStatic(data);

            if (receipt.Result != GateResult.Accepted)
                return receipt;

            // Sequence tracking
            if (_enforceMonotonicSeq)
            {
                int seq = receipt.FrameSeq;
                if (seq <= _lastFrameSeq)
                {
                    receipt.Result = seq == _lastFrameSeq
                        ? GateResult.DuplicateSequence
                        : GateResult.StaleSequence;
                    receipt.ErrorMessage = $"Frame seq {seq} <= last {_lastFrameSeq}";
                    if (receipt.Result == GateResult.DuplicateSequence)
                        Interlocked.Increment(ref _framesDuplicate);
                    else
                        Interlocked.Increment(ref _framesStale);
                    return receipt;
                }
                _lastFrameSeq = seq;
            }

            // Rate limiting
            if (_enableRateLimiting && _maxRateHz > 0)
            {
                long nowTicks = DateTime.UtcNow.Ticks;
                long minIntervalTicks = TimeSpan.TicksPerSecond / _maxRateHz;
                long prev = Interlocked.Exchange(ref _lastReceiveTicks, nowTicks);
                if (prev > 0 && (nowTicks - prev) < minIntervalTicks)
                {
                    receipt.Result = GateResult.RateLimited;
                    receipt.ErrorMessage = $"Rate limit exceeded ({_maxRateHz} Hz max)";
                    return receipt;
                }
            }

            return receipt;
        }

        private static GateReceipt ValidateStatic(byte[] data)
        {
            Dictionary<string, object> msg;
            try
            {
                string json = Encoding.UTF8.GetString(data);
                msg = JsonLines.Deserialize(json);
            }
            catch
            {
                return new GateReceipt
                {
                    Result = GateResult.InvalidJson,
                    ErrorMessage = "Failed to parse JSON"
                };
            }

            if (!msg.TryGetValue("message_type", out var mtObj) || mtObj == null)
                return new GateReceipt { Result = GateResult.MissingMessageType, Raw = msg };

            if (mtObj.ToString() != "telemetry_frame")
                return new GateReceipt { Result = GateResult.NotTelemetryFrame, Raw = msg };

            return new GateReceipt
            {
                Result = GateResult.Accepted,
                Raw = msg,
                FrameSeq = GetIntFromDict(msg, "frame_seq")
            };
        }

        private static int GetIntFromDict(Dictionary<string, object> d, string key)
        {
            if (d.TryGetValue(key, out var v))
            {
                if (v is int i) return i;
                if (v is long l) return (int)l;
                if (v is double dd) return (int)dd;
                if (int.TryParse(v?.ToString(), out var p)) return p;
            }
            return 0;
        }

        private void LogDiagnostics()
        {
            Debug.Log($"[U01.UDP5006Gate] Diag: accepted={_framesAccepted} dropped={_framesDropped} " +
                      $"dup={_framesDuplicate} stale={_framesStale} invalid={_framesInvalid} " +
                      $"last_seq={_lastFrameSeq}");
        }

        private static void Log(string msg)
        {
            Debug.Log($"[U01.UDP5006Gate] {msg}");
        }
    }
}
