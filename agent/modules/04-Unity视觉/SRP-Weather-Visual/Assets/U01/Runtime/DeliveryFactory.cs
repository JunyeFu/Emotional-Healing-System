using System;

namespace SRP.U01
{
    public static class DeliveryFactory
    {
        public static AckDto CreateAck(ControlEventDto message, ApplyResult result, long receivedNs, long appliedNs, int unityFrame)
        {
            return new AckDto
            {
                schema_version = message.schema_version,
                session_id = message.session_id,
                event_id = message.event_id,
                received_monotonic_ns = receivedNs,
                applied_monotonic_ns = appliedNs,
                unity_frame = unityFrame,
                result = result.Result,
                error_code = result.ErrorCode
            };
        }

        public static RenderReceiptDto CreateReceipt(
            ControlEventDto message,
            string clientInstanceId,
            string moduleId,
            string segment,
            long telemetryFrameSeq,
            int unityFrame,
            long renderedNs,
            string result,
            string errorCode = null)
        {
            if (string.IsNullOrEmpty(clientInstanceId))
                throw new ArgumentException("Client instance identity is required", nameof(clientInstanceId));
            if (result != "rendered" && result != "skipped" && result != "failed")
                throw new ArgumentException("Invalid receipt result", nameof(result));
            if (result == "failed" && string.IsNullOrEmpty(errorCode))
                throw new ArgumentException("Failed receipt requires an error code", nameof(errorCode));

            return new RenderReceiptDto
            {
                schema_version = message.schema_version,
                receipt_id = "RR-" + clientInstanceId + "-" + message.event_id,
                session_id = message.session_id,
                event_id = message.event_id,
                frame_seq = Math.Max(0, telemetryFrameSeq),
                unity_frame = unityFrame,
                rendered_monotonic_ns = renderedNs,
                module_id = moduleId,
                segment = segment,
                result = result,
                error_code = errorCode
            };
        }
    }
}
