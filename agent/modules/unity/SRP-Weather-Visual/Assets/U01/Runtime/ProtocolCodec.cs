using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;

namespace SRP.U01
{
    public static class ProtocolCodec
    {
        private const string TransportVersion = "1.0";

        private static readonly string[] ControlFields =
        {
            "schema_version", "message_type", "session_id", "event_id", "control_seq",
            "event_type", "issued_monotonic_ns", "effective_monotonic_ns", "clock_domain_id", "payload"
        };

        private static readonly string[] TelemetryFields =
        {
            "schema_version", "message_type", "session_id", "frame_seq", "clock_domain_id",
            "source_monotonic_ns", "received_monotonic_ns", "sent_monotonic_ns", "clock_offset_ns",
            "clock_drift_ppm", "sync_uncertainty_ns", "module_id", "module_position", "segment",
            "target_phase", "target_progress", "actual_phase", "actual_progress", "actual_confidence",
            "recovery_value", "recovery_locked", "signal_quality", "fallback_state", "fallback_reason",
            "resp_device_state", "ecg_device_state", "cue_mode", "runtime_mode", "policy_decision_id"
        };

        private static readonly string[] V22TelemetryFields =
        {
            "target_cycle_index", "target_step_id", "actual_cycle_index", "actual_step_id"
        };

        private static readonly HashSet<string> EventTypes = new()
        {
            "prepare", "start", "pause", "abort", "segment", "module", "end"
        };

        private static readonly HashSet<string> Modules = new() { "storm", "heat", "snow", "fade" };
        private static readonly HashSet<string> Segments = new() { "demo", "closed_loop", "lock_transition" };
        private static readonly HashSet<string> Phases = new() { "inhale", "hold", "exhale", "recovery", "none" };
        private static readonly HashSet<string> FallbackStates = new() { "GOOD", "DEGRADED", "UNUSABLE", "DISCONNECTED" };
        private static readonly HashSet<string> DeviceStates = new() { "CONNECTED", "DEGRADED", "UNUSABLE", "DISCONNECTED" };
        private static readonly HashSet<string> CueModes = new() { "scene_native", "abstract_pacer" };
        private static readonly HashSet<string> RuntimeModes = new()
        {
            "dev_mock", "dev_replay", "formal_level_c", "formal_stage_1", "formal_stage_3"
        };

        private static readonly Dictionary<string, Dictionary<string, string>> Steps = new()
        {
            ["storm"] = new Dictionary<string, string>
            {
                ["inhale_1"] = "inhale", ["hold_1"] = "hold", ["exhale_1"] = "exhale", ["hold_2"] = "hold"
            },
            ["heat"] = new Dictionary<string, string> { ["inhale_1"] = "inhale", ["exhale_1"] = "exhale" },
            ["snow"] = new Dictionary<string, string> { ["inhale_1"] = "inhale", ["exhale_1"] = "exhale" },
            ["fade"] = new Dictionary<string, string>
            {
                ["inhale_1"] = "inhale", ["inhale_2"] = "inhale", ["exhale_1"] = "exhale"
            }
        };

        public static bool TryParseControl(string json, string expectedSchema, out ControlEventDto value, out string error)
        {
            value = null;
            if (!HasFields(json, ControlFields) || HasNonFiniteToken(json))
            {
                error = "CONTROL_SCHEMA_INVALID";
                return false;
            }

            try { value = JsonUtility.FromJson<ControlEventDto>(json); }
            catch (ArgumentException) { error = "CONTROL_JSON_INVALID"; return false; }

            if (value == null || value.schema_version != expectedSchema || value.message_type != "control_event" ||
                string.IsNullOrEmpty(value.session_id) || string.IsNullOrEmpty(value.event_id) ||
                value.control_seq < 0 || value.issued_monotonic_ns < 0 || value.effective_monotonic_ns < 0 ||
                !HasNonNegativeInteger(json, "control_seq") || !HasNonNegativeInteger(json, "issued_monotonic_ns") ||
                !HasNonNegativeInteger(json, "effective_monotonic_ns") ||
                value.effective_monotonic_ns < value.issued_monotonic_ns ||
                string.IsNullOrEmpty(value.clock_domain_id) || value.payload == null || !EventTypes.Contains(value.event_type))
            {
                error = "CONTROL_SCHEMA_INVALID";
                return false;
            }

            if (value.event_type == "prepare" && value.payload.manifest == null)
            {
                error = "PREPARE_MANIFEST_REQUIRED";
                return false;
            }
            if (value.event_type == "prepare" && expectedSchema == "2.1" &&
                value.payload.manifest.runtime_mode != "dev_replay")
            {
                error = "FORMAL_V21_FORBIDDEN";
                return false;
            }
            if (value.event_type == "module" &&
                (!TryGetTopLevelRawValue(json, "payload", out var modulePayload) ||
                 !HasNonNegativeInteger(modulePayload, "module_position") || !Modules.Contains(value.payload.module_id) ||
                 value.payload.module_position < 0 || value.payload.module_position > 3))
            {
                error = "MODULE_PAYLOAD_INVALID";
                return false;
            }
            if (value.event_type == "segment" &&
                (!TryGetTopLevelRawValue(json, "payload", out var segmentPayload) ||
                 !HasNonNegativeInteger(segmentPayload, "module_position") || !Modules.Contains(value.payload.module_id) ||
                 value.payload.module_position < 0 || value.payload.module_position > 3 ||
                 !Segments.Contains(value.payload.segment)))
            {
                error = "SEGMENT_PAYLOAD_INVALID";
                return false;
            }

            error = null;
            return true;
        }

        public static bool TryParseTelemetry(string json, string expectedSchema, out TelemetryFrameDto value, out string error)
        {
            value = null;
            if (!HasFields(json, TelemetryFields) ||
                (expectedSchema == "2.2" && !HasFields(json, V22TelemetryFields)) || HasNonFiniteToken(json))
            {
                error = "TELEMETRY_SCHEMA_INVALID";
                return false;
            }

            try { value = JsonUtility.FromJson<TelemetryFrameDto>(json); }
            catch (ArgumentException) { error = "TELEMETRY_JSON_INVALID"; return false; }

            if (value != null)
            {
                value.target_cycle_index_is_null = IsTopLevelNull(json, "target_cycle_index");
                value.actual_cycle_index_is_null = IsTopLevelNull(json, "actual_cycle_index");
            }

            if (value == null || value.schema_version != expectedSchema || value.message_type != "telemetry_frame" ||
                string.IsNullOrEmpty(value.session_id) || string.IsNullOrEmpty(value.clock_domain_id) || value.frame_seq < 0 ||
                value.source_monotonic_ns < 0 || value.received_monotonic_ns < 0 || value.sent_monotonic_ns < 0 ||
                !HasNonNegativeInteger(json, "frame_seq") || !HasNonNegativeInteger(json, "source_monotonic_ns") ||
                !HasNonNegativeInteger(json, "received_monotonic_ns") || !HasNonNegativeInteger(json, "sent_monotonic_ns") ||
                !HasNonNegativeInteger(json, "module_position", int.MaxValue) || !HasJsonBoolean(json, "recovery_locked") ||
                !HasFiniteNumber(json, "clock_offset_ns") || !HasFiniteNumber(json, "clock_drift_ppm") ||
                !HasFiniteNumber(json, "sync_uncertainty_ns") || !HasFiniteNumber(json, "target_progress") ||
                !HasFiniteNumber(json, "actual_progress") || !HasFiniteNumber(json, "actual_confidence") ||
                !HasFiniteNumber(json, "recovery_value") ||
                !HasNumberInRange(json, "target_progress", 0, 1) ||
                !HasNumberInRange(json, "actual_progress", 0, 1) ||
                !HasNumberInRange(json, "actual_confidence", 0, 1) ||
                !HasNumberInRange(json, "recovery_value", 0, 1) ||
                !Modules.Contains(value.module_id) ||
                value.module_position < 0 || !Segments.Contains(value.segment) || value.signal_quality == null ||
                !Unit(value.target_progress) || !Unit(value.actual_progress) || !Unit(value.actual_confidence) ||
                !Unit(value.recovery_value) || value.sync_uncertainty_ns < 0 ||
                !Phases.Contains(value.target_phase) || !Phases.Contains(value.actual_phase) ||
                !FallbackStates.Contains(value.fallback_state) || !DeviceStates.Contains(value.resp_device_state) ||
                !DeviceStates.Contains(value.ecg_device_state) || !CueModes.Contains(value.cue_mode) ||
                !RuntimeModes.Contains(value.runtime_mode) ||
                (expectedSchema == "2.1" && value.runtime_mode != "dev_replay") ||
                HasTopLevelField(json, "calm_index"))
            {
                error = "TELEMETRY_SCHEMA_INVALID";
                return false;
            }

            if (value.source_monotonic_ns > value.received_monotonic_ns ||
                value.received_monotonic_ns > value.sent_monotonic_ns ||
                (value.fallback_state == "GOOD" && !IsTopLevelNull(json, "fallback_reason")) ||
                (value.fallback_state != "GOOD" && string.IsNullOrEmpty(value.fallback_reason)))
            {
                error = "TELEMETRY_STATE_INVALID";
                return false;
            }

            if (expectedSchema == "2.2" &&
                (!ValidStepState(json, "target", value.module_id, value.target_phase, value.target_progress,
                     value.target_cycle_index, value.target_step_id) ||
                 !ValidStepState(json, "actual", value.module_id, value.actual_phase, value.actual_progress,
                     value.actual_cycle_index, value.actual_step_id)))
            {
                error = "TELEMETRY_STEP_IDENTITY_INVALID";
                return false;
            }

            error = null;
            return true;
        }

        public static string CreateHello(string schemaVersion, string clientInstanceId)
        {
            return "{\"transport_type\":\"hello\",\"transport_version\":\"" + TransportVersion +
                   "\",\"role\":\"unity\",\"schema_version\":\"" + schemaVersion +
                   "\",\"client_instance_id\":\"" + Escape(clientInstanceId) + "\"}";
        }

        public static bool ValidateWelcome(string json, string schemaVersion, string clientInstanceId, out string error)
        {
            WelcomeDto welcome;
            try { welcome = JsonUtility.FromJson<WelcomeDto>(json); }
            catch (ArgumentException) { error = "WELCOME_JSON_INVALID"; return false; }
            if (welcome == null || welcome.transport_type != "welcome" || welcome.transport_version != TransportVersion ||
                welcome.schema_version != schemaVersion || welcome.role != "unity" ||
                welcome.client_instance_id != clientInstanceId || !welcome.accepted)
            {
                error = welcome != null && !string.IsNullOrEmpty(welcome.error_code)
                    ? welcome.error_code
                    : "WELCOME_REJECTED";
                return false;
            }
            error = null;
            return true;
        }

        public static string ToJson(AckDto value)
        {
            return "{\"schema_version\":\"" + Escape(value.schema_version) +
                   "\",\"message_type\":\"ack\",\"session_id\":\"" + Escape(value.session_id) +
                   "\",\"event_id\":\"" + Escape(value.event_id) +
                   "\",\"received_monotonic_ns\":" + value.received_monotonic_ns +
                   ",\"applied_monotonic_ns\":" + value.applied_monotonic_ns +
                   ",\"unity_frame\":" + value.unity_frame +
                   ",\"result\":\"" + Escape(value.result) + "\",\"error_code\":" + NullableString(value.error_code) + "}";
        }

        public static string ToJson(RenderReceiptDto value)
        {
            return "{\"schema_version\":\"" + Escape(value.schema_version) +
                   "\",\"message_type\":\"render_receipt\",\"receipt_id\":\"" + Escape(value.receipt_id) +
                   "\",\"session_id\":\"" + Escape(value.session_id) +
                   "\",\"event_id\":\"" + Escape(value.event_id) +
                   "\",\"frame_seq\":" + value.frame_seq +
                   ",\"unity_frame\":" + value.unity_frame +
                   ",\"rendered_monotonic_ns\":" + value.rendered_monotonic_ns +
                   ",\"module_id\":\"" + Escape(value.module_id) +
                   "\",\"segment\":\"" + Escape(value.segment) +
                   "\",\"result\":\"" + Escape(value.result) + "\",\"error_code\":" + NullableString(value.error_code) + "}";
        }

        private static bool Unit(float value) => !float.IsNaN(value) && !float.IsInfinity(value) && value >= 0f && value <= 1f;

        private static bool ValidStepState(
            string json, string prefix, string module, string phase, float progress, int cycleIndex, string stepId)
        {
            var cycleIsNull = IsTopLevelNull(json, prefix + "_cycle_index");
            var stepIsNull = IsTopLevelNull(json, prefix + "_step_id");
            if (cycleIsNull != stepIsNull) return false;
            if (cycleIsNull) return phase == "none" && progress == 0f && IsJsonNumberZero(json, prefix + "_progress");
            if (cycleIndex < 0 || !HasNonNegativeInteger(json, prefix + "_cycle_index", int.MaxValue)) return false;
            return !string.IsNullOrEmpty(stepId) && Steps[module].TryGetValue(stepId, out var expectedPhase) && expectedPhase == phase;
        }

        private static bool HasFields(string json, IEnumerable<string> fields)
        {
            if (string.IsNullOrWhiteSpace(json) || json.Length > 1024 * 1024) return false;
            foreach (var field in fields)
            {
                if (!HasTopLevelField(json, field)) return false;
            }
            return true;
        }

        private static bool HasNonFiniteToken(string json)
        {
            if (json == null) return false;
            var inString = false;
            for (var index = 0; index < json.Length; index++)
            {
                if (inString)
                {
                    if (json[index] == '\\') index++;
                    else if (json[index] == '"') inString = false;
                    continue;
                }
                if (json[index] == '"')
                {
                    inString = true;
                    continue;
                }
                if (StartsToken(json, index, "NaN") || StartsToken(json, index, "Infinity") ||
                    StartsToken(json, index, "-Infinity")) return true;
            }
            return false;
        }

        private static bool StartsToken(string json, int index, string token)
        {
            if (index + token.Length > json.Length ||
                string.CompareOrdinal(json, index, token, 0, token.Length) != 0) return false;
            var before = index == 0 ? '\0' : json[index - 1];
            var after = index + token.Length == json.Length ? '\0' : json[index + token.Length];
            return !char.IsLetterOrDigit(before) && before != '_' && !char.IsLetterOrDigit(after) && after != '_';
        }

        private static bool HasTopLevelField(string json, string field) =>
            TryGetTopLevelRawValue(json, field, out _);

        private static bool IsTopLevelNull(string json, string field) =>
            TryGetTopLevelRawValue(json, field, out var raw) && raw == "null";

        private static bool HasNonNegativeInteger(string json, string field, long maximum = long.MaxValue)
        {
            if (!TryGetTopLevelRawValue(json, field, out var raw) ||
                !Regex.IsMatch(raw, @"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$")) return false;
            if (!double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var binary) ||
                double.IsInfinity(binary) || binary < 0 || Math.Floor(binary) != binary) return false;
            if (binary > maximum) return false;
            if (maximum == long.MaxValue && binary == (double)long.MaxValue &&
                decimal.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var exact))
                return exact <= long.MaxValue;
            return true;
        }

        private static bool HasFiniteNumber(string json, string field)
        {
            if (!TryGetTopLevelRawValue(json, field, out var raw) ||
                !Regex.IsMatch(raw, @"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$")) return false;
            return double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var value) &&
                   !double.IsNaN(value) && !double.IsInfinity(value);
        }

        private static bool HasNumberInRange(string json, string field, double minimum, double maximum)
        {
            if (!TryGetTopLevelRawValue(json, field, out var raw) ||
                !double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var value)) return false;
            return !double.IsNaN(value) && !double.IsInfinity(value) && value >= minimum && value <= maximum;
        }

        private static bool IsJsonNumberZero(string json, string field)
        {
            if (!TryGetTopLevelRawValue(json, field, out var raw) ||
                !Regex.IsMatch(raw, @"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$")) return false;
            return double.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out var value) &&
                   !double.IsNaN(value) && !double.IsInfinity(value) && value == 0;
        }

        private static bool HasJsonBoolean(string json, string field) =>
            TryGetTopLevelRawValue(json, field, out var raw) && (raw == "true" || raw == "false");

        private static bool TryGetTopLevelRawValue(string json, string field, out string raw)
        {
            raw = null;
            if (string.IsNullOrWhiteSpace(json)) return false;
            var index = 0;
            SkipWhitespace(json, ref index);
            if (index >= json.Length || json[index++] != '{') return false;

            while (index < json.Length)
            {
                SkipWhitespace(json, ref index);
                if (index < json.Length && json[index] == '}') return false;
                if (!TryReadJsonString(json, ref index, out var key)) return false;
                SkipWhitespace(json, ref index);
                if (index >= json.Length || json[index++] != ':') return false;
                SkipWhitespace(json, ref index);
                var start = index;
                if (!SkipJsonValue(json, ref index)) return false;
                if (key == field)
                {
                    raw = json.Substring(start, index - start).Trim();
                    return true;
                }
                SkipWhitespace(json, ref index);
                if (index >= json.Length || json[index++] != ',') return false;
            }
            return false;
        }

        private static bool TryReadJsonString(string json, ref int index, out string value)
        {
            value = null;
            if (index >= json.Length || json[index++] != '"') return false;
            var output = new StringBuilder();
            while (index < json.Length)
            {
                if (json[index] == '\\')
                {
                    index++;
                    if (index >= json.Length) return false;
                    switch (json[index])
                    {
                        case '"': output.Append('"'); break;
                        case '\\': output.Append('\\'); break;
                        case '/': output.Append('/'); break;
                        case 'b': output.Append('\b'); break;
                        case 'f': output.Append('\f'); break;
                        case 'n': output.Append('\n'); break;
                        case 'r': output.Append('\r'); break;
                        case 't': output.Append('\t'); break;
                        case 'u':
                            if (index + 4 >= json.Length ||
                                !ushort.TryParse(json.Substring(index + 1, 4), NumberStyles.HexNumber,
                                    CultureInfo.InvariantCulture, out var codePoint)) return false;
                            output.Append((char)codePoint);
                            index += 4;
                            break;
                        default: return false;
                    }
                    index++;
                    continue;
                }
                if (json[index] == '"')
                {
                    value = output.ToString();
                    index++;
                    return true;
                }
                output.Append(json[index]);
                index++;
            }
            return false;
        }

        private static bool SkipJsonValue(string json, ref int index)
        {
            var depth = 0;
            var inString = false;
            while (index < json.Length)
            {
                var current = json[index];
                if (inString)
                {
                    if (current == '\\') index++;
                    else if (current == '"') inString = false;
                }
                else if (current == '"') inString = true;
                else if (current == '{' || current == '[') depth++;
                else if (current == '}' || current == ']')
                {
                    if (depth == 0) return current == '}';
                    depth--;
                }
                else if (current == ',' && depth == 0) return true;
                index++;
            }
            return !inString && depth == 0;
        }

        private static void SkipWhitespace(string json, ref int index)
        {
            while (index < json.Length && char.IsWhiteSpace(json[index])) index++;
        }

        private static string Escape(string value)
        {
            var output = new StringBuilder();
            foreach (var current in value ?? string.Empty)
            {
                switch (current)
                {
                    case '"': output.Append("\\\""); break;
                    case '\\': output.Append("\\\\"); break;
                    case '\b': output.Append("\\b"); break;
                    case '\f': output.Append("\\f"); break;
                    case '\n': output.Append("\\n"); break;
                    case '\r': output.Append("\\r"); break;
                    case '\t': output.Append("\\t"); break;
                    default:
                        if (current < 0x20) output.Append("\\u").Append(((int)current).ToString("x4"));
                        else output.Append(current);
                        break;
                }
            }
            return output.ToString();
        }
        private static string NullableString(string value) => value == null ? "null" : "\"" + Escape(value) + "\"";
    }
}
