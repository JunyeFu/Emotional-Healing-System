using System;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;

namespace SRP.U01
{
    public enum MirrorStatus { Created, Prepared, Running, Paused, Completed, Aborted }

    public sealed class SessionMirror
    {
        private readonly Dictionary<string, EventIdentity> appliedEvents = new();

        public SessionMirror(string schemaVersion)
        {
            if (schemaVersion != "2.1" && schemaVersion != "2.2") throw new ArgumentException("Unsupported schema", nameof(schemaVersion));
            SchemaVersion = schemaVersion;
        }

        public string SchemaVersion { get; }
        public MirrorStatus Status { get; private set; } = MirrorStatus.Created;
        public string SessionId { get; private set; }
        public long LastControlSeq { get; private set; } = -1;
        public long LastTelemetrySeq { get; private set; } = -1;
        public string ModuleId { get; private set; }
        public int ModulePosition { get; private set; } = -1;
        public string Segment { get; private set; }
        public TelemetryFrameDto LatestTelemetry { get; private set; }

        public ApplyResult ApplyControl(ControlEventDto value, string rawJson)
        {
            if (value == null) return new ApplyResult("rejected", "CONTROL_REQUIRED");
            var identity = new EventIdentity(value.control_seq, Hash(rawJson));
            if (appliedEvents.TryGetValue(value.event_id, out var previous))
            {
                return previous.Equals(identity) && value.session_id == SessionId
                    ? new ApplyResult("duplicate_ignored", "DUPLICATE_CONTROL")
                    : new ApplyResult("rejected", "DUPLICATE_EVENT_MISMATCH");
            }
            if (value.control_seq <= LastControlSeq) return new ApplyResult("rejected", "CONTROL_SEQUENCE_STALE");
            if (Status != MirrorStatus.Created && value.session_id != SessionId) return new ApplyResult("rejected", "SESSION_MISMATCH");

            var transition = ApplyTransition(value);
            if (!transition.Accepted) return transition;

            SessionId ??= value.session_id;
            LastControlSeq = value.control_seq;
            appliedEvents.Add(value.event_id, identity);
            return transition;
        }

        public ApplyResult ApplyTelemetry(TelemetryFrameDto value)
        {
            if (value == null) return new ApplyResult("rejected", "TELEMETRY_REQUIRED");
            if (Status != MirrorStatus.Running && Status != MirrorStatus.Paused && Status != MirrorStatus.Completed)
                return new ApplyResult("rejected", "TELEMETRY_SESSION_NOT_ACTIVE");
            if (value.session_id != SessionId) return new ApplyResult("rejected", "SESSION_MISMATCH");
            if (value.frame_seq <= LastTelemetrySeq) return new ApplyResult("rejected", "TELEMETRY_SEQUENCE_STALE");
            if (value.module_id != ModuleId || value.module_position != ModulePosition || value.segment != Segment)
                return new ApplyResult("rejected", "TELEMETRY_MIRROR_MISMATCH");

            LastTelemetrySeq = value.frame_seq;
            LatestTelemetry = value;
            return new ApplyResult("applied");
        }

        private ApplyResult ApplyTransition(ControlEventDto value)
        {
            switch (value.event_type)
            {
                case "prepare" when Status == MirrorStatus.Created:
                    Status = MirrorStatus.Prepared;
                    return new ApplyResult("applied");
                case "start" when Status == MirrorStatus.Prepared || Status == MirrorStatus.Paused:
                    Status = MirrorStatus.Running;
                    return new ApplyResult("applied");
                case "pause" when Status == MirrorStatus.Running:
                    Status = MirrorStatus.Paused;
                    return new ApplyResult("applied");
                case "abort" when Status == MirrorStatus.Prepared || Status == MirrorStatus.Running || Status == MirrorStatus.Paused:
                    Status = MirrorStatus.Aborted;
                    return new ApplyResult("applied");
                case "end" when Status == MirrorStatus.Running:
                    Status = MirrorStatus.Completed;
                    return new ApplyResult("applied");
                case "module" when Status == MirrorStatus.Running:
                    ModuleId = value.payload.module_id;
                    ModulePosition = value.payload.module_position;
                    Segment = null;
                    return new ApplyResult("applied");
                case "segment" when Status == MirrorStatus.Running && value.payload.module_id == ModuleId &&
                                           value.payload.module_position == ModulePosition:
                    Segment = value.payload.segment;
                    return new ApplyResult("applied");
                default:
                    return new ApplyResult("rejected", "CONTROL_TRANSITION_INVALID");
            }
        }

        private static string Hash(string value)
        {
            using var sha = SHA256.Create();
            return BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(value ?? string.Empty))).Replace("-", string.Empty);
        }

        private readonly struct EventIdentity : IEquatable<EventIdentity>
        {
            public EventIdentity(long sequence, string hash) { Sequence = sequence; Hash = hash; }
            private long Sequence { get; }
            private string Hash { get; }
            public bool Equals(EventIdentity other) => Sequence == other.Sequence && Hash == other.Hash;
        }
    }
}
