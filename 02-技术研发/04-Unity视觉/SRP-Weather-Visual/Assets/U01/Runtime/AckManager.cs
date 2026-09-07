// U01 — AckManager: creates, tracks, and sends ACK messages for
// control_event delivery.  Runs the ack logic on the network thread.

using System;
using System.Collections.Generic;
using UnityEngine;

namespace SRP.U01
{
    /// <summary>
    /// Tracks a single pending ACK waiting for timeout/expiry.
    /// </summary>
    public sealed class PendingAck
    {
        public string EventId { get; }
        public ControlEvent Event { get; }
        public DateTime IssuedUtc { get; }
        public int AttemptCount { get; set; }
        public bool Acknowledged { get; set; }

        public PendingAck(ControlEvent evt)
        {
            EventId = evt.event_id;
            Event = evt;
            IssuedUtc = DateTime.UtcNow;
            AttemptCount = 0;
            Acknowledged = false;
        }
    }

    /// <summary>
    /// Manages the ACK lifecycle for control events:
    /// - Records when an event is sent
    /// - Creates the ACK message to send back
    /// - Handles timeout and retry escalation
    /// - Tracks delivered vs. pending events
    /// </summary>
    public sealed class AckManager
    {
        // ── Configuration ─────────────────────────────────────────────────
        private readonly int _ackTimeoutMs;
        private readonly int _maxAttempts;
        private readonly string _clockDomainId;
        private readonly Func<long> _nowNs;

        // ── State ─────────────────────────────────────────────────────────
        private readonly Dictionary<string, PendingAck> _pendingAcks = new();
        private readonly HashSet<string> _deliveredEventIds = new();
        private readonly object _lock = new();

        // ── Events ────────────────────────────────────────────────────────
        /// <summary>Fired when an ACK times out after all attempts.</summary>
        public event Action<string> OnAckTimeout;

        /// <summary>Fired when an ACK is successfully received.</summary>
        public event Action<string, AckMessage> OnAckReceived;

        public AckManager(
            int ackTimeoutMs = 2000,
            int maxAttempts = 3,
            string clockDomainId = "unity",
            Func<long> nowNs = null)
        {
            _ackTimeoutMs = ackTimeoutMs;
            _maxAttempts = maxAttempts;
            _clockDomainId = clockDomainId;
            _nowNs = nowNs ?? (() => (long)(DateTime.UtcNow.Ticks - new DateTime(1970, 1, 1).Ticks) * 100L);
        }

        // ── Public API ────────────────────────────────────────────────────

        /// <summary>
        /// Mark an event as sent and start tracking its ACK.
        /// </summary>
        public void TrackEventSent(ControlEvent evt)
        {
            if (evt == null) return;
            lock (_lock)
            {
                _pendingAcks[evt.event_id] = new PendingAck(evt);
            }
        }

        /// <summary>
        /// Check whether an event has already been delivered (duplicate guard).
        /// </summary>
        public bool IsDelivered(string eventId)
        {
            lock (_lock)
            {
                return _deliveredEventIds.Contains(eventId);
            }
        }

        /// <summary>
        /// Check whether an event is pending (awaiting ACK).
        /// </summary>
        public bool IsPending(string eventId)
        {
            lock (_lock)
            {
                return _pendingAcks.ContainsKey(eventId) && !_pendingAcks[eventId].Acknowledged;
            }
        }

        /// <summary>
        /// Create the ACK message to send back for a received control_event.
        /// </summary>
        public AckMessage CreateAck(
            string sessionId,
            string eventId,
            int unityFrame,
            AckResult result,
            string errorCode = null)
        {
            long nowNs = _nowNs();
            return new AckMessage
            {
                session_id = sessionId,
                event_id = eventId,
                received_monotonic_ns = nowNs,
                applied_monotonic_ns = nowNs,
                unity_frame = unityFrame,
                result = result.ToString(),
                error_code = errorCode
            };
        }

        /// <summary>
        /// Process an incoming ACK message (from server echo or round-trip).
        /// Returns true if this was a new, non-duplicate ACK.
        /// </summary>
        public bool ProcessIncomingAck(AckMessage ack)
        {
            if (ack == null) return false;
            lock (_lock)
            {
                if (_deliveredEventIds.Contains(ack.event_id))
                    return false; // already processed

                if (_pendingAcks.TryGetValue(ack.event_id, out var pending))
                {
                    pending.Acknowledged = true;
                    if (ack.result == "applied" || ack.result == "duplicate_ignored")
                        _deliveredEventIds.Add(ack.event_id);
                    _pendingAcks.Remove(ack.event_id);
                }

                OnAckReceived?.Invoke(ack.event_id, ack);
                return true;
            }
        }

        /// <summary>
        /// Check for timed-out pending ACKs.  Returns event IDs that have
        /// exceeded max attempts (caller should trigger reconnect).
        /// </summary>
        public List<string> CheckTimeouts()
        {
            var timedOut = new List<string>();
            var now = DateTime.UtcNow;
            lock (_lock)
            {
                var toRemove = new List<string>();
                foreach (var kv in _pendingAcks)
                {
                    var pending = kv.Value;
                    if (pending.Acknowledged) continue;

                    var elapsed = (now - pending.IssuedUtc).TotalMilliseconds;
                    if (elapsed > _ackTimeoutMs)
                    {
                        pending.AttemptCount++;
                        if (pending.AttemptCount >= _maxAttempts)
                        {
                            timedOut.Add(kv.Key);
                            toRemove.Add(kv.Key);
                        }
                    }
                }
                foreach (var id in toRemove)
                {
                    _pendingAcks.Remove(id);
                    OnAckTimeout?.Invoke(id);
                }
            }
            return timedOut;
        }

        /// <summary>
        /// Fail all pending ACKs for a given connection generation (disconnect).
        /// </summary>
        public void FailAllPending(string reason)
        {
            lock (_lock)
            {
                foreach (var kv in _pendingAcks)
                {
                    if (!kv.Value.Acknowledged)
                    {
                        OnAckTimeout?.Invoke(kv.Key);
                    }
                }
                _pendingAcks.Clear();
            }
            Log($"All pending ACKs failed: {reason}");
        }

        /// <summary>Number of events still awaiting ACK.</summary>
        public int PendingCount
        {
            get { lock (_lock) return _pendingAcks.Count; }
        }

        /// <summary>Number of successfully delivered events.</summary>
        public int DeliveredCount
        {
            get { lock (_lock) return _deliveredEventIds.Count; }
        }

        /// <summary>Reset all tracking state.</summary>
        public void Reset()
        {
            lock (_lock)
            {
                _pendingAcks.Clear();
                _deliveredEventIds.Clear();
            }
        }

        private static void Log(string msg)
        {
            Debug.Log($"[U01.AckManager] {msg}");
        }
    }
}
