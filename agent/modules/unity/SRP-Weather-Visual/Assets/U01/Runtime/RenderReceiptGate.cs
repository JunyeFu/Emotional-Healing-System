using System.Collections.Generic;

namespace SRP.U01
{
    public sealed class RenderReceiptGate
    {
        private readonly string clientInstanceId;
        private readonly Dictionary<string, RenderState> states = new();
        private readonly Dictionary<long, TelemetryIdentity> telemetryFrames = new();
        private long lastObservedTelemetryFrameSeq = -1;

        public RenderReceiptGate(string clientInstanceId)
        {
            if (string.IsNullOrEmpty(clientInstanceId))
                throw new System.ArgumentException("Client instance identity is required", nameof(clientInstanceId));
            this.clientInstanceId = clientInstanceId;
        }

        public void Register(ControlEventDto message, ApplyResult result, SessionMirror mirror)
        {
            if (result.Result != "applied" || message.event_type != "segment") return;
            foreach (var state in states.Values)
                if (state.Receipt == null && state.MaximumTelemetryFrameSeq == long.MaxValue)
                    state.MaximumTelemetryFrameSeq = lastObservedTelemetryFrameSeq;
            if (!states.ContainsKey(message.event_id))
                states.Add(message.event_id, new RenderState(
                    message, mirror.ModuleId, mirror.Segment,
                    System.Math.Max(mirror.LastTelemetrySeq, lastObservedTelemetryFrameSeq) + 1));
        }

        public void ObserveTelemetry(TelemetryFrameDto message, ApplyResult result)
        {
            if (message == null || result.Result != "applied") return;
            telemetryFrames[message.frame_seq] = new TelemetryIdentity(
                message.session_id, message.module_id, message.segment);
            if (message.frame_seq > lastObservedTelemetryFrameSeq)
                lastObservedTelemetryFrameSeq = message.frame_seq;
        }

        public bool TryConfirm(
            string eventId,
            long telemetryFrameSeq,
            int unityFrame,
            long renderedNs,
            string result,
            string errorCode,
            out RenderReceiptDto receipt)
        {
            receipt = null;
            if (telemetryFrameSeq < 0 || unityFrame < 0 || renderedNs < 0 ||
                !states.TryGetValue(eventId, out var value) ||
                !telemetryFrames.TryGetValue(telemetryFrameSeq, out var telemetry) ||
                telemetryFrameSeq < value.MinimumTelemetryFrameSeq ||
                telemetryFrameSeq > value.MaximumTelemetryFrameSeq ||
                telemetry.SessionId != value.Message.session_id || telemetry.ModuleId != value.ModuleId ||
                telemetry.Segment != value.Segment) return false;
            if (value.Receipt != null)
            {
                receipt = value.Receipt;
                return true;
            }
            receipt = DeliveryFactory.CreateReceipt(value.Message, clientInstanceId, value.ModuleId, value.Segment, telemetryFrameSeq,
                unityFrame, renderedNs, result, errorCode);
            value.Receipt = receipt;
            return true;
        }

        public bool TryGetConfirmed(string eventId, out RenderReceiptDto receipt)
        {
            receipt = null;
            if (!states.TryGetValue(eventId, out var value) || value.Receipt == null) return false;
            receipt = value.Receipt;
            return true;
        }

        public IEnumerable<RenderReceiptDto> ConfirmedReceipts()
        {
            foreach (var value in states.Values)
                if (value.Receipt != null) yield return value.Receipt;
        }

        private sealed class RenderState
        {
            public RenderState(ControlEventDto message, string moduleId, string segment, long minimumTelemetryFrameSeq)
            {
                Message = message;
                ModuleId = moduleId;
                Segment = segment;
                MinimumTelemetryFrameSeq = minimumTelemetryFrameSeq;
            }

            public ControlEventDto Message { get; }
            public string ModuleId { get; }
            public string Segment { get; }
            public long MinimumTelemetryFrameSeq { get; }
            public long MaximumTelemetryFrameSeq { get; set; } = long.MaxValue;
            public RenderReceiptDto Receipt { get; set; }
        }

        private readonly struct TelemetryIdentity
        {
            public TelemetryIdentity(string sessionId, string moduleId, string segment)
            {
                SessionId = sessionId;
                ModuleId = moduleId;
                Segment = segment;
            }

            public string SessionId { get; }
            public string ModuleId { get; }
            public string Segment { get; }
        }
    }
}
