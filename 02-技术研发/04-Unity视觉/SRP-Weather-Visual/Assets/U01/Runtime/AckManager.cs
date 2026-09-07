// U01 — AckManager: tracks applied control_event IDs for idempotent ACK
// generation.  Unity is the ACK *sender*: it receives control_events from
// the Python server and sends back ACKs (applied / duplicate_ignored /
// rejected).  This is NOT a server-side retry manager.
//
// Key contract (from transport.py _handle_unity_message):
//   - New event_id  → apply → send ACK result="applied"
//   - Duplicate event_id → do NOT re-apply → send ACK result="duplicate_ignored"
//   - Cannot apply (session mismatch / state error) → send ACK result="rejected"
//
// _appliedEventIds persists across reconnections — the server uses
// _delivered_event_ids to decide what to replay, and we must consistently
// reply duplicate_ignored for any event_id we have already processed.

using System;
using System.Collections.Generic;
using UnityEngine;

namespace SRP.U01
{
    /// <summary>
    /// Manages idempotent ACK generation for control_event messages.
    /// Maintains the set of already-applied event_ids so duplicates
    /// are detected and responded to without re-applying the event.
    /// </summary>
    public sealed class AckManager
    {
        // ── Configuration ─────────────────────────────────────────────────
        private readonly string _clockDomainId;
        private readonly Func<long> _nowNs;

        // ── State ─────────────────────────────────────────────────────────
        // Event IDs that have been successfully applied.  Used for idempotent
        // duplicate detection.  NOT cleared on reconnect (per contract).
        private readonly HashSet<string> _appliedEventIds = new();
        private readonly object _lock = new();

        // ── Events ────────────────────────────────────────────────────────
        /// <summary>Fired when an event is applied for the first time.</summary>
        public event Action<string> OnEventApplied;

        /// <summary>Fired when a duplicate event_id is detected.</summary>
        public event Action<string> OnDuplicateIgnored;

        /// <summary>Fired when an event is rejected (cannot apply).</summary>
        public event Action<string, string> OnEventRejected;

        public AckManager(
            string clockDomainId = "unity",
            Func<long> nowNs = null)
        {
            _clockDomainId = clockDomainId;
            // R2-8: Use Stopwatch for monotonic timestamps instead of DateTime.UtcNow
            _nowNs = nowNs ?? (() => (long)(System.Diagnostics.Stopwatch.GetTimestamp()
                * (1_000_000_000.0 / System.Diagnostics.Stopwatch.Frequency)));
        }

        // ── Public API ────────────────────────────────────────────────────

        /// <summary>
        /// Check whether an event_id has already been applied.
        /// </summary>
        public bool IsApplied(string eventId)
        {
            lock (_lock)
            {
                return _appliedEventIds.Contains(eventId);
            }
        }

        /// <summary>
        /// Record that an event_id has been applied.  Called after the event
        /// has been successfully applied to SessionMirror / OnControlEvent.
        /// </summary>
        public void MarkApplied(string eventId)
        {
            bool isNew;
            lock (_lock)
            {
                isNew = _appliedEventIds.Add(eventId);
            }
            if (isNew)
            {
                OnEventApplied?.Invoke(eventId);
            }
        }

        /// <summary>
        /// Record that a duplicate event_id was detected (already applied).
        /// Invoke OnDuplicateIgnored for subscribers.
        /// </summary>
        public void MarkDuplicate(string eventId)
        {
            OnDuplicateIgnored?.Invoke(eventId);
        }

        /// <summary>
        /// Record that an event was rejected (cannot apply).
        /// Invoke OnEventRejected for subscribers.
        /// </summary>
        /// <param name="eventId">The event_id that was rejected.</param>
        /// <param name="reason">Human-readable rejection reason.</param>
        public void MarkRejected(string eventId, string reason)
        {
            // 保留给未来 reject 路径
            OnEventRejected?.Invoke(eventId, reason);
        }

        /// <summary>
        /// Create the ACK message to send back for a received control_event.
        /// Uses received_monotonic_ns for the time the message was received
        /// (caller should capture this before processing) and
        /// applied_monotonic_ns for the current time after application.
        /// </summary>
        public AckMessage CreateAck(
            string sessionId,
            string eventId,
            int unityFrame,
            AckResult result,
            long receivedMonotonicNs,
            string errorCode = null)
        {
            long appliedNs = _nowNs();
            return new AckMessage
            {
                session_id = sessionId,
                event_id = eventId,
                received_monotonic_ns = receivedMonotonicNs,
                applied_monotonic_ns = appliedNs,
                unity_frame = unityFrame,
                result = result.ToString(),
                error_code = errorCode
            };
        }

        /// <summary>
        /// Reset all tracking state.  Normally NOT called on reconnect
        /// (per contract, _appliedEventIds must persist across reconnections
        /// so the server can correctly identify duplicates).
        /// Only call this on full session teardown.
        /// </summary>
        public void Reset()
        {
            lock (_lock)
            {
                _appliedEventIds.Clear();
            }
        }

        /// <summary>Number of events that have been applied.</summary>
        public int AppliedCount
        {
            get { lock (_lock) return _appliedEventIds.Count; }
        }

        private static void Log(string msg)
        {
            Debug.Log($"[U01.AckManager] {msg}");
        }
    }
}
