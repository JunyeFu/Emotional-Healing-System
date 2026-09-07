// U01 — SessionMirror: thread-safe mirror of the session state from the
// Python control server.  Updated from the TCP receive thread; queried from
// the Unity main thread via atomic snapshot exchange.

using System;
using System.Collections.Generic;
using UnityEngine;

namespace SRP.U01
{
    /// <summary>
    /// Thread-safe snapshot of the session state.  Immutable — replaced atomically.
    /// </summary>
    public sealed class SessionSnapshot
    {
        public bool HasSession { get; }
        public string SessionId { get; }
        public string ResearchId { get; }
        public string RuntimeMode { get; }
        public string StudyStage { get; }
        public string CueMode { get; }
        public string[] WeatherSequence { get; }
        public string CurrentModuleId { get; }
        public int ModulePosition { get; }
        public string CurrentSegment { get; }
        public int ActiveControlSeq { get; }
        public string LastEventId { get; }
        public long LastIssuedNs { get; }
        public long LastEffectiveNs { get; }
        public DateTime LastManifestUtc { get; }
        public Dictionary<string, object> RawManifest { get; }

        private SessionSnapshot() { HasSession = false; }

        public SessionSnapshot(
            SessionManifest manifest,
            int activeControlSeq,
            string lastEventId,
            long lastIssuedNs,
            long lastEffectiveNs)
        {
            HasSession = true;
            SessionId = manifest.session_id;
            ResearchId = manifest.research_id;
            RuntimeMode = manifest.runtime_mode;
            StudyStage = manifest.study_stage;
            CueMode = manifest.cue_mode;
            WeatherSequence = (string[])manifest.weather_sequence.Clone();
            CurrentModuleId = null;
            ModulePosition = 0;
            CurrentSegment = null;
            ActiveControlSeq = activeControlSeq;
            LastEventId = lastEventId;
            LastIssuedNs = lastIssuedNs;
            LastEffectiveNs = lastEffectiveNs;
            RawManifest = null;

            if (DateTime.TryParse(manifest.created_utc,
                System.Globalization.CultureInfo.InvariantCulture,
                System.Globalization.DateTimeStyles.AdjustToUniversal,
                out var utc))
                LastManifestUtc = utc;
        }

        /// <summary>Snapshot reflecting an active module/segment update.</summary>
        public SessionSnapshot(
            SessionSnapshot previous,
            string moduleId,
            int modulePosition,
            string segment,
            int controlSeq,
            string eventId,
            long issuedNs,
            long effectiveNs)
        {
            HasSession = previous.HasSession;
            SessionId = previous.SessionId;
            ResearchId = previous.ResearchId;
            RuntimeMode = previous.RuntimeMode;
            StudyStage = previous.StudyStage;
            CueMode = previous.CueMode;
            WeatherSequence = previous.WeatherSequence;
            CurrentModuleId = moduleId;
            ModulePosition = modulePosition;
            CurrentSegment = segment;
            ActiveControlSeq = controlSeq;
            LastEventId = eventId;
            LastIssuedNs = issuedNs;
            LastEffectiveNs = effectiveNs;
            LastManifestUtc = previous.LastManifestUtc;
            RawManifest = previous.RawManifest;
        }

        public static SessionSnapshot Empty { get; } = new SessionSnapshot();
    }

    /// <summary>
    /// MonoBehaviour that mirrors the Python SessionCore state.
    /// Receives messages from <see cref="ReliableControlClient"/> on the
    /// network thread and exposes an immutable <see cref="SessionSnapshot"/>
    /// for the main thread.  The exchange is lock-free via <see cref="Interlocked"/>
    /// on a reference field.
    /// </summary>
    public sealed class SessionMirror : MonoBehaviour
    {
        // ── Public state (read from main thread) ──────────────────────────
        private volatile SessionSnapshot _snapshot = SessionSnapshot.Empty;

        /// <summary>
        /// Current session snapshot.  Thread-safe — atomic reference swap.
        /// </summary>
        public SessionSnapshot Snapshot => _snapshot;

        /// <summary>Fires on the main thread when the snapshot changes.</summary>
        public event Action<SessionSnapshot> OnSessionUpdated;

        // ── Internal state (written from network thread) ───────────────────
        private int _activeControlSeq;
        private string _lastEventId;
        private long _lastIssuedNs;
        private long _lastEffectiveNs;
        private string _pendingModuleId;
        private int _pendingModulePosition;
        private string _pendingSegment;

        // ── Lifecycle ─────────────────────────────────────────────────────

        void Awake()
        {
            _snapshot = SessionSnapshot.Empty;
        }

        /// <summary>
        /// Apply a session_manifest message received over TCP.
        /// Called from the network thread — thread-safe.
        /// </summary>
        public void ApplySessionManifest(SessionManifest manifest)
        {
            if (manifest == null) throw new ArgumentNullException(nameof(manifest));
            var snap = new SessionSnapshot(
                manifest,
                _activeControlSeq,
                _lastEventId,
                _lastIssuedNs,
                _lastEffectiveNs);
            _snapshot = snap;
            Log($"Session manifested: {manifest.session_id} ({manifest.runtime_mode})");
            // Note: OnSessionUpdated fires on main thread via _pendingEvents
        }

        /// <summary>
        /// Apply a control_event — updates the active control sequence and
        /// module/segment tracking.
        /// </summary>
        public void ApplyControlEvent(ControlEvent evt)
        {
            if (evt == null) throw new ArgumentNullException(nameof(evt));

            _activeControlSeq = evt.control_seq;
            _lastEventId = evt.event_id;
            _lastIssuedNs = evt.issued_monotonic_ns;
            _lastEffectiveNs = evt.effective_monotonic_ns;

            string newModule = _pendingModuleId;
            int newModulePos = _pendingModulePosition;
            string newSegment = _pendingSegment;

            if (evt.event_type == "module" && evt.payload != null)
            {
                if (evt.payload.TryGetValue("module_id", out var mid))
                    newModule = mid?.ToString();
                if (evt.payload.TryGetValue("module_position", out var mpos) && mpos is int mp)
                    newModulePos = mp;
            }
            if (evt.event_type == "segment" && evt.payload != null)
            {
                if (evt.payload.TryGetValue("segment", out var seg))
                    newSegment = seg?.ToString();
            }

            _pendingModuleId = newModule;
            _pendingModulePosition = newModulePos;
            _pendingSegment = newSegment;

            var prev = _snapshot;
            _snapshot = new SessionSnapshot(
                prev,
                newModule,
                newModulePos,
                newSegment,
                _activeControlSeq,
                _lastEventId,
                _lastIssuedNs,
                _lastEffectiveNs);
        }

        /// <summary>
        /// Called from main thread (e.g., LateUpdate) to dispatch pending events.
        /// Since we update _snapshot atomically, consumers just read Snapshot.
        /// This method fires OnSessionUpdated if the reference changed since last check.
        /// </summary>
        private SessionSnapshot _lastDispatched = SessionSnapshot.Empty;

        void LateUpdate()
        {
            var current = _snapshot;
            if (current != _lastDispatched)
            {
                _lastDispatched = current;
                OnSessionUpdated?.Invoke(current);
            }
        }

        /// <summary>Reset mirror state (e.g., on disconnect).</summary>
        public void ResetState()
        {
            _activeControlSeq = 0;
            _lastEventId = null;
            _lastIssuedNs = 0;
            _lastEffectiveNs = 0;
            _pendingModuleId = null;
            _pendingModulePosition = 0;
            _pendingSegment = null;
            _snapshot = SessionSnapshot.Empty;
            _lastDispatched = SessionSnapshot.Empty;
            Log("Session mirror reset");
        }

        private static void Log(string msg)
        {
            Debug.Log($"[U01.SessionMirror] {msg}");
        }
    }
}
