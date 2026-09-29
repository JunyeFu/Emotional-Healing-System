using System;

namespace SRP.U01
{
    [Serializable]
    public sealed class ManifestDto
    {
        public string runtime_mode;
    }

    [Serializable]
    public sealed class ControlPayloadDto
    {
        public ManifestDto manifest;
        public string module_id;
        public int module_position;
        public string segment;
    }

    [Serializable]
    public sealed class ControlEventDto
    {
        public string schema_version;
        public string message_type;
        public string session_id;
        public string event_id;
        public long control_seq;
        public string event_type;
        public long issued_monotonic_ns;
        public long effective_monotonic_ns;
        public string clock_domain_id;
        public ControlPayloadDto payload;
    }

    [Serializable]
    public sealed class SignalQualityDto
    {
        public float resp;
        public float ecg;
    }

    [Serializable]
    public sealed class TelemetryFrameDto
    {
        public string schema_version;
        public string message_type;
        public string session_id;
        public long frame_seq;
        public string clock_domain_id;
        public long source_monotonic_ns;
        public long received_monotonic_ns;
        public long sent_monotonic_ns;
        public double clock_offset_ns;
        public double clock_drift_ppm;
        public double sync_uncertainty_ns;
        public string module_id;
        public int module_position;
        public string segment;
        public string target_phase;
        public float target_progress;
        public string actual_phase;
        public float actual_progress;
        public float actual_confidence;
        public float recovery_value;
        public bool recovery_locked;
        public SignalQualityDto signal_quality;
        public string fallback_state;
        public string fallback_reason;
        public string resp_device_state;
        public string ecg_device_state;
        public string cue_mode;
        public string runtime_mode;
        public string policy_decision_id;
        public int target_cycle_index;
        public string target_step_id;
        public int actual_cycle_index;
        public string actual_step_id;

        [NonSerialized] public bool target_cycle_index_is_null;
        [NonSerialized] public bool actual_cycle_index_is_null;

        public int? TargetCycleIndex => target_cycle_index_is_null ? null : target_cycle_index;
        public int? ActualCycleIndex => actual_cycle_index_is_null ? null : actual_cycle_index;
    }

    [Serializable]
    public sealed class AckDto
    {
        public string schema_version;
        public string message_type = "ack";
        public string session_id;
        public string event_id;
        public long received_monotonic_ns;
        public long applied_monotonic_ns;
        public int unity_frame;
        public string result;
        public string error_code;
    }

    [Serializable]
    public sealed class RenderReceiptDto
    {
        public string schema_version;
        public string message_type = "render_receipt";
        public string receipt_id;
        public string session_id;
        public string event_id;
        public long frame_seq;
        public int unity_frame;
        public long rendered_monotonic_ns;
        public string module_id;
        public string segment;
        public string result;
        public string error_code;
    }

    [Serializable]
    public sealed class WelcomeDto
    {
        public string transport_type;
        public string transport_version;
        public string schema_version;
        public string role;
        public string client_instance_id;
        public bool accepted;
        public string error_code;
    }

    public readonly struct ApplyResult
    {
        public ApplyResult(string result, string errorCode = null)
        {
            Result = result;
            ErrorCode = errorCode;
        }

        public string Result { get; }
        public string ErrorCode { get; }
        public bool Accepted => Result == "applied" || Result == "duplicate_ignored";
    }
}
