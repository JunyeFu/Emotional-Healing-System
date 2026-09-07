// U01 — RenderReceiptManager: creates, tracks, and sends render_receipt
// messages confirming that Unity has rendered each control_event's frame.

using System;
using System.Collections.Generic;
using System.Threading;
using UnityEngine;

namespace SRP.U01
{
    /// <summary>
    /// Tracks a single render receipt lifecycle.
    /// </summary>
    public sealed class TrackedReceipt
    {
        public string ReceiptId { get; }
        public string EventId { get; }
        public int FrameSeq { get; }
        public int UnityFrame { get; set; }
        public string ModuleId { get; set; }
        public string Segment { get; set; }
        public RenderResult Result { get; set; }
        public string ErrorCode { get; set; }
        public long RenderedMonotonicNs { get; set; }
        public bool Sent { get; set; }

        public TrackedReceipt(string eventId, int frameSeq)
        {
            ReceiptId = Guid.NewGuid().ToString("N");
            EventId = eventId;
            FrameSeq = frameSeq;
            Result = RenderResult.rendered;
            Sent = false;
        }
    }

    /// <summary>
    /// Manages render_receipt lifecycle:
    ///   1. When a control_event triggers rendering, register it
    ///   2. After rendering completes (or fails/skips), update the receipt
    ///   3. Send the receipt back to the control server
    ///
    /// The render receipt is the Unity-side confirmation that the visual
    /// output corresponding to a control event was actually rendered.
    /// </summary>
    public sealed class RenderReceiptManager
    {
        // ── Configuration ─────────────────────────────────────────────────
        private readonly Func<long> _nowNs;
        private readonly Func<int> _unityFrameProvider;

        // ── State ─────────────────────────────────────────────────────────
        private readonly Dictionary<string, TrackedReceipt> _pendingReceipts = new();
        private readonly List<TrackedReceipt> _completedReceipts = new();
        private readonly object _lock = new();
        private int _nextFrameSeq;

        // ── Events ────────────────────────────────────────────────────────
        /// <summary>Fired when a receipt is ready to send.</summary>
        public event Action<RenderReceipt> OnReceiptReady;

        /// <summary>Fired when a receipt tracking entry is completed.</summary>
        public event Action<TrackedReceipt> OnReceiptCompleted;

        // ── Properties ────────────────────────────────────────────────────
        public int PendingCount
        {
            get { lock (_lock) return _pendingReceipts.Count; }
        }

        public int CompletedCount
        {
            get { lock (_lock) return _completedReceipts.Count; }
        }

        public int NextFrameSeq => _nextFrameSeq;

        // ── Constructor ───────────────────────────────────────────────────

        public RenderReceiptManager(
            Func<long> nowNs = null,
            Func<int> unityFrameProvider = null)
        {
            _nowNs = nowNs ?? (() => (long)(DateTime.UtcNow.Ticks - new DateTime(1970, 1, 1).Ticks) * 100L);
            _unityFrameProvider = unityFrameProvider ?? (() => Time.frameCount);
        }

        // ── Public API ────────────────────────────────────────────────────

        /// <summary>
        /// Register a control_event for render receipt tracking.
        /// Call this when the event triggers a render cycle.
        /// </summary>
        public TrackedReceipt RegisterEvent(ControlEvent evt, string moduleId, string segment)
        {
            if (evt == null) throw new ArgumentNullException(nameof(evt));

            int frameSeq = Interlocked.Increment(ref _nextFrameSeq) - 1;
            var receipt = new TrackedReceipt(evt.event_id, frameSeq)
            {
                ModuleId = moduleId,
                Segment = segment,
                UnityFrame = _unityFrameProvider()
            };

            lock (_lock)
            {
                _pendingReceipts[evt.event_id] = receipt;
            }

            Log($"Registered receipt for event {evt.event_id} (seq={frameSeq})");
            return receipt;
        }

        /// <summary>
        /// Mark a receipt as rendered and create the receipt message.
        /// </summary>
        public RenderReceipt CompleteRendered(
            string eventId,
            string sessionId,
            long? overrideMonotonicNs = null)
        {
            return CompleteWithResult(eventId, sessionId, RenderResult.rendered, null,
                overrideMonotonicNs);
        }

        /// <summary>
        /// Mark a receipt as skipped (rendering was not needed).
        /// </summary>
        public RenderReceipt CompleteSkipped(
            string eventId,
            string sessionId,
            string reason = null,
            long? overrideMonotonicNs = null)
        {
            return CompleteWithResult(eventId, sessionId, RenderResult.skipped, reason,
                overrideMonotonicNs);
        }

        /// <summary>
        /// Mark a receipt as failed (rendering attempted but failed).
        /// </summary>
        public RenderReceipt CompleteFailed(
            string eventId,
            string sessionId,
            string errorCode,
            long? overrideMonotonicNs = null)
        {
            return CompleteWithResult(eventId, sessionId, RenderResult.failed, errorCode,
                overrideMonotonicNs);
        }

        /// <summary>
        /// Get all completed receipts that haven't been sent yet.
        /// Caller should send them and mark as sent via <see cref="MarkSent"/>.
        /// </summary>
        public List<RenderReceipt> GetUnsentReceipts(string sessionId)
        {
            var result = new List<RenderReceipt>();
            lock (_lock)
            {
                foreach (var tracked in _completedReceipts)
                {
                    if (tracked.Sent) continue;
                    result.Add(BuildReceipt(tracked, sessionId));
                }
            }
            return result;
        }

        /// <summary>Mark a receipt as sent.</summary>
        public void MarkSent(string eventId)
        {
            lock (_lock)
            {
                foreach (var tracked in _completedReceipts)
                {
                    if (tracked.EventId == eventId)
                    {
                        tracked.Sent = true;
                        break;
                    }
                }
            }
        }

        /// <summary>
        /// Discard all pending receipts for a session (e.g., on abort).
        /// </summary>
        public void DiscardAll()
        {
            lock (_lock)
            {
                _pendingReceipts.Clear();
                _completedReceipts.Clear();
            }
            Log("All receipts discarded");
        }

        /// <summary>Reset all state.</summary>
        public void ResetState()
        {
            lock (_lock)
            {
                _pendingReceipts.Clear();
                _completedReceipts.Clear();
                _nextFrameSeq = 0;
            }
        }

        // ── Internal ──────────────────────────────────────────────────────

        private RenderReceipt CompleteWithResult(
            string eventId,
            string sessionId,
            RenderResult result,
            string errorCode,
            long? overrideMonotonicNs)
        {
            TrackedReceipt tracked;
            lock (_lock)
            {
                if (!_pendingReceipts.TryGetValue(eventId, out tracked))
                {
                    Log($"No pending receipt for event {eventId} — creating ad-hoc");
                    int frameSeq = Interlocked.Increment(ref _nextFrameSeq) - 1;
                    tracked = new TrackedReceipt(eventId, frameSeq)
                    {
                        UnityFrame = _unityFrameProvider()
                    };
                }
                else
                {
                    _pendingReceipts.Remove(eventId);
                }

                tracked.Result = result;
                tracked.ErrorCode = errorCode;
                tracked.RenderedMonotonicNs = overrideMonotonicNs ?? _nowNs();
                tracked.UnityFrame = _unityFrameProvider();
                _completedReceipts.Add(tracked);
            }

            var receipt = BuildReceipt(tracked, sessionId);
            OnReceiptReady?.Invoke(receipt);
            OnReceiptCompleted?.Invoke(tracked);

            Log($"Receipt {eventId}: {result}" +
                (errorCode != null ? $" ({errorCode})" : ""));
            return receipt;
        }

        private static RenderReceipt BuildReceipt(TrackedReceipt tracked, string sessionId)
        {
            return new RenderReceipt
            {
                receipt_id = tracked.ReceiptId,
                session_id = sessionId,
                event_id = tracked.EventId,
                frame_seq = tracked.FrameSeq,
                unity_frame = tracked.UnityFrame,
                rendered_monotonic_ns = tracked.RenderedMonotonicNs,
                module_id = tracked.ModuleId ?? "",
                segment = tracked.Segment ?? "",
                result = tracked.Result.ToString(),
                error_code = tracked.ErrorCode
            };
        }

        private static void Log(string msg)
        {
            Debug.Log($"[U01.RenderReceiptManager] {msg}");
        }
    }
}
