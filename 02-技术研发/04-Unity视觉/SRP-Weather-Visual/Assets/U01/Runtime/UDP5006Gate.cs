// U01 — UDP5006Gate: enhanced UDP receiver for telemetry_frame messages on
// port 5006 with contract validation, sequence tracking, and rate monitoring.
// Replaces the bare UDPReceiver with schema-aware filtering.
//
// P0-2: Full validation (required fields, schema_version, step instance rules)
// is now merged into the real receive path (ValidateWithTracking), not dead code.

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
    ///   2. Full JSON + schema validation (required fields, schema_version,
    ///      step instance rules) — P0-2 fix: validation is NOT dead code
    ///   3. Track frame_seq per session_id (reset on session change)
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

        // P0-2: frame_seq tracked per session_id, not globally.
        // When session_id changes, the baseline resets.
        private string _currentSessionId;
        private int _lastFrameSeq = -1;
        private long _lastReceiveTicks = -1;
        private int _framesReceived;
        private int _framesDropped;
        private int _framesAccepted;
        private int _framesDuplicate;
        private int _framesStale;
        private int _framesInvalid;
        private int _framesSchemaViolation;

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
        public int FramesSchemaViolation => _framesSchemaViolation;
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
            _currentSessionId = null;
            _lastFrameSeq = -1;
            _lastReceiveTicks = -1;
            _framesReceived = 0;
            _framesDropped = 0;
            _framesAccepted = 0;
            _framesDuplicate = 0;
            _framesStale = 0;
            _framesInvalid = 0;
            _framesSchemaViolation = 0;
        }

        /// <summary>
        /// Reset sequence tracking for a new session.  Called when a new
        /// session_manifest arrives — frame_seq baselines restart per session.
        /// P0-2: (session_id → last_seq) reset.
        /// </summary>
        public void ResetSession(string newSessionId)
        {
            if (_currentSessionId != newSessionId)
            {
                _currentSessionId = newSessionId;
                _lastFrameSeq = -1;
                _lastReceiveTicks = -1;
                Log($"Session changed to {newSessionId} — frame_seq reset");
            }
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
        /// Full validation with sequence tracking and rate limiting.
        /// P0-2 FIX: Now calls the complete validation (required fields,
        /// schema_version, step instance rules) instead of the old
        /// ValidateStatic() which only checked message_type.
        /// Called from the receive thread.
        /// </summary>
        private GateReceipt ValidateWithTracking(byte[] data)
        {
            // ── Step 1: Full validation (replaces old ValidateStatic) ──
            GateReceipt receipt = ValidateFull(data);

            if (receipt.Result != GateResult.Accepted)
                return receipt;

            // ── Step 2: Sequence tracking (per session_id) ────────────
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

            // ── Step 3: Rate limiting ─────────────────────────────────
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

        /// <summary>
        /// Full field + schema validation for a raw UDP datagram.
        /// P0-2: This is now the REAL validation path (was previously dead
        /// code only called by tests).  Merged into ValidateWithTracking.
        ///
        /// Validates:
        ///   1. JSON parseable as object
        ///   2. message_type == "telemetry_frame"
        ///   3. schema_version == "2.2"
        ///   4. ALL required fields present per schema
        ///   5. Step instance rules: target_cycle_index & target_step_id
        ///      must co-occur or both be null (actual_* same rule)
        /// </summary>
        public static GateReceipt ValidateFull(byte[] data)
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
            if (messageType != "telemetry_frame")
            {
                return new GateReceipt
                {
                    Result = GateResult.NotTelemetryFrame,
                    Raw = msg,
                    ErrorMessage = $"Unexpected message_type: {messageType}"
                };
            }

            // 3. Validate schema_version == "2.2"
            if (msg.TryGetValue("schema_version", out var sv) && sv?.ToString() != "2.2")
            {
                return new GateReceipt
                {
                    Result = GateResult.SchemaViolation,
                    Raw = msg,
                    ErrorMessage = $"Unsupported schema_version: {sv}"
                };
            }

            // 4. Validate ALL required fields per schema
            //    (from runtime-contract-v2.2.schema.json telemetry_frame definition)
            string[] requiredFields = {
                "schema_version", "message_type", "session_id", "frame_seq",
                "clock_domain_id", "source_monotonic_ns", "received_monotonic_ns",
                "sent_monotonic_ns", "clock_offset_ns", "clock_drift_ppm",
                "sync_uncertainty_ns", "module_id", "module_position",
                "segment", "target_phase", "target_progress",
                "actual_phase", "actual_progress", "actual_confidence",
                "recovery_value", "recovery_locked", "signal_quality",
                "fallback_state", "resp_device_state", "ecg_device_state",
                "cue_mode", "runtime_mode"
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

            // 5. Step instance rules (v2.2):
            //    target_cycle_index & target_step_id must both be present
            //    or both be null.  Same for actual_cycle_index & actual_step_id.
            bool hasTargetCycle = msg.ContainsKey("target_cycle_index");
            bool hasTargetStep = msg.ContainsKey("target_step_id");
            bool targetCycleNull = hasTargetCycle && msg["target_cycle_index"] == null;
            bool targetStepNull = hasTargetStep && msg["target_step_id"] == null;
            bool targetBothPresent = hasTargetCycle && hasTargetStep && !targetCycleNull && !targetStepNull;
            bool targetBothNull = hasTargetCycle && hasTargetStep && targetCycleNull && targetStepNull;

            if (!targetBothPresent && !targetBothNull)
            {
                return new GateReceipt
                {
                    Result = GateResult.SchemaViolation,
                    Raw = msg,
                    ErrorMessage = "Step instance rule: target_cycle_index and target_step_id must both be present or both null"
                };
            }

            bool hasActualCycle = msg.ContainsKey("actual_cycle_index");
            bool hasActualStep = msg.ContainsKey("actual_step_id");
            bool actualCycleNull = hasActualCycle && msg["actual_cycle_index"] == null;
            bool actualStepNull = hasActualStep && msg["actual_step_id"] == null;
            bool actualBothPresent = hasActualCycle && hasActualStep && !actualCycleNull && !actualStepNull;
            bool actualBothNull = hasActualCycle && hasActualStep && actualCycleNull && actualStepNull;

            if (!actualBothPresent && !actualBothNull)
            {
                return new GateReceipt
                {
                    Result = GateResult.SchemaViolation,
                    Raw = msg,
                    ErrorMessage = "Step instance rule: actual_cycle_index and actual_step_id must both be present or both null"
                };
            }

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
                      $"schema_viol={_framesSchemaViolation} last_seq={_lastFrameSeq}");
        }

        private static void Log(string msg)
        {
            Debug.Log($"[U01.UDP5006Gate] {msg}");
        }
    }
}
