using System;
using System.Diagnostics;
using UnityEngine;

namespace SRP.U01
{
    public sealed class U01RuntimeBridge : MonoBehaviour
    {
        [SerializeField] private string schemaVersion = "2.2";
        [SerializeField] private int controlPort = 5010;
        [SerializeField] private int telemetryPort = 5006;

        private ReliableControlClient control;
        private TelemetryReceiver telemetry;
        private SessionMirror mirror;
        private RenderReceiptGate receiptGate;
        private string clientInstanceId;
        private int observedConnectionGeneration;

        public SessionMirror Mirror => mirror;
        public string LastFailure { get; private set; }

        private void OnEnable()
        {
            mirror ??= new SessionMirror(schemaVersion);
            clientInstanceId ??= "unity-" + Guid.NewGuid().ToString("N");
            receiptGate ??= new RenderReceiptGate(clientInstanceId);
            observedConnectionGeneration = 0;
            control = new ReliableControlClient(schemaVersion, clientInstanceId, controlPort);
            telemetry = new TelemetryReceiver(telemetryPort);
            control.Start();
            try { telemetry.Start(); }
            catch (System.Net.Sockets.SocketException) { LastFailure = "TELEMETRY_BIND_FAILED"; }
        }

        private void Update()
        {
            while (control.TryDequeue(out var json)) ConsumeControl(json);
            while (telemetry.TryDequeue(out var json)) ConsumeTelemetry(json);
            if (control.ConnectionGeneration != observedConnectionGeneration)
            {
                observedConnectionGeneration = control.ConnectionGeneration;
                foreach (var receipt in receiptGate.ConfirmedReceipts())
                    control.Send(ProtocolCodec.ToJson(receipt));
            }
        }

        private void OnDisable()
        {
            telemetry?.Dispose();
            control?.Dispose();
            telemetry = null;
            control = null;
        }

        public ApplyResult ConsumeControl(string json)
        {
            var received = NowNs();
            if (!ProtocolCodec.TryParseControl(json, mirror.SchemaVersion, out var message, out var parseError))
            {
                LastFailure = parseError;
                return new ApplyResult("rejected", parseError);
            }

            var result = mirror.ApplyControl(message, json);
            var applied = NowNs();
            var ack = DeliveryFactory.CreateAck(message, result, received, applied, Time.frameCount);
            var ackSent = control.Send(ProtocolCodec.ToJson(ack));
            if (!ackSent) LastFailure = "ACK_SEND_FAILED";
            receiptGate.Register(message, result, mirror);
            if (ackSent && result.Result == "duplicate_ignored" &&
                receiptGate.TryGetConfirmed(message.event_id, out var priorReceipt) &&
                !control.Send(ProtocolCodec.ToJson(priorReceipt)))
                LastFailure = "RECEIPT_SEND_FAILED";
            return result;
        }

        public ApplyResult ConsumeTelemetry(string json)
        {
            if (!ProtocolCodec.TryParseTelemetry(json, mirror.SchemaVersion, out var message, out var parseError))
            {
                LastFailure = parseError;
                return new ApplyResult("rejected", parseError);
            }
            var result = mirror.ApplyTelemetry(message);
            receiptGate.ObserveTelemetry(message, result);
            if (!result.Accepted) LastFailure = result.ErrorCode;
            return result;
        }

        public bool ConfirmRendered(string eventId, long telemetryFrameSeq, string result = "rendered", string errorCode = null)
        {
            if (!receiptGate.TryConfirm(
                    eventId, telemetryFrameSeq, Time.frameCount, NowNs(), result, errorCode, out var receipt))
            {
                LastFailure = "RENDER_CONFIRMATION_REJECTED";
                return false;
            }
            if (!control.Send(ProtocolCodec.ToJson(receipt))) LastFailure = "RECEIPT_SEND_FAILED";
            return true;
        }

        private static long NowNs()
        {
            return (long)(Stopwatch.GetTimestamp() * (1_000_000_000.0 / Stopwatch.Frequency));
        }

    }
}
