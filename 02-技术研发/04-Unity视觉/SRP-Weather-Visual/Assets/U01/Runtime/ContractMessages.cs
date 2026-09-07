// U01 — SRP Runtime Contract v2.2 C# message types.
// Auto-derived from runtime-contract-v2.2.schema.json.
// All messages are serialized as compact JSON Lines over TCP/UDP.

using System;
using System.Collections.Generic;

namespace SRP.U01
{
    /// <summary>All supported <c>message_type</c> values.</summary>
    public enum MessageType
    {
        session_manifest,
        control_event,
        ack,
        telemetry_frame,
        policy_decision,
        render_receipt
    }

    /// <summary>All supported <c>event_type</c> values for control_event.</summary>
    public enum ControlEventType
    {
        prepare,
        start,
        pause,
        abort,
        segment,
        module,
        end
    }

    /// <summary>All supported <c>result</c> values for ack.</summary>
    public enum AckResult
    {
        applied,
        duplicate_ignored,
        rejected,
        failed
    }

    /// <summary>All supported <c>result</c> values for render_receipt.</summary>
    public enum RenderResult
    {
        rendered,
        skipped,
        failed
    }

    /// <summary>All supported <c>segment</c> values.</summary>
    public enum Segment
    {
        demo,
        closed_loop,
        lock_transition
    }

    /// <summary>All supported <c>runtime_mode</c> values.</summary>
    public enum RuntimeMode
    {
        dev_mock,
        dev_replay,
        formal_level_c,
        formal_stage_1,
        formal_stage_3
    }

    /// <summary>All supported <c>study_stage</c> values.</summary>
    public enum StudyStage
    {
        level_c,
        stage_1,
        stage_3
    }

    /// <summary>All supported <c>cue_mode</c> values.</summary>
    public enum CueMode
    {
        scene_native,
        abstract_pacer
    }

    /// <summary>Module identifiers matching weather_sequence items.</summary>
    public enum ModuleId
    {
        storm,
        heat,
        snow,
        fade
    }

    // ── Transport-level messages (not in schema but in transport.py) ──────

    /// <summary>Transport hello sent by the client on connect.</summary>
    public sealed class TransportHello
    {
        public const string transport_type = "hello";
        public const string transport_version = "1.0";
        public string role;
        public string schema_version;
        public string client_instance_id;
    }

    /// <summary>Transport welcome sent by the server after hello.</summary>
    public sealed class TransportWelcome
    {
        public const string transport_type = "welcome";
        public const string transport_version = "1.0";
        public string schema_version;
        public string role;
        public string client_instance_id;
        public bool accepted;
        public string error_code; // null when accepted
    }

    /// <summary>Transport error sent by the server.</summary>
    public sealed class TransportErrorFrame
    {
        public const string transport_type = "error";
        public const string transport_version = "1.0";
        public string schema_version;
        public string error_code;
    }

    // ── Schema message types ──────────────────────────────────────────────

    /// <summary>Module durations inside session_manifest.</summary>
    [Serializable]
    public sealed class ModuleDurations
    {
        public double demo;
        public double closed_loop;
        public double lock_transition;
    }

    /// <summary>Device config — resp and ecg.</summary>
    [Serializable]
    public sealed class DeviceSensorConfig
    {
        public string source; // plux_respiban|mock|none or polar_h10|mock|none
        public string serial;
    }

    [Serializable]
    public sealed class DeviceConfig
    {
        public DeviceSensorConfig resp;
        public DeviceSensorConfig ecg;
    }

    /// <summary>session_manifest message per v2.2 schema.</summary>
    [Serializable]
    public sealed class SessionManifest
    {
        public const string schema_version = "2.2";
        public const string message_type_val = "session_manifest";

        public string research_id;
        public string session_id;
        public string study_stage;
        public string runtime_mode;
        public string cue_mode;
        public string assignment_arm;
        public int allocation_index;
        public string randomization_stratum;
        public int randomization_block;
        public string randomization_list_hash;
        public string[] weather_sequence; // exactly 4 unique items
        public ModuleDurations module_durations;
        public string protocol_config_version;
        public string randomization_version;
        public string strategy_version;
        public DeviceConfig device_config;
        public string unity_build_hash;
        public string python_commit;
        public string td_build_hash;
        public string source_policy;
        public string created_utc;
        public string breath_protocol_config_version;
        public string breath_protocol_config_hash;
    }

    /// <summary>control_event message per v2.2 schema.</summary>
    [Serializable]
    public sealed class ControlEvent
    {
        public const string schema_version = "2.2";
        public const string message_type_val = "control_event";

        public string session_id;
        public string event_id;
        public int control_seq;
        public string event_type; // prepare|start|pause|abort|segment|module|end
        public long issued_monotonic_ns;
        public long effective_monotonic_ns;
        public string clock_domain_id;
        public Dictionary<string, object> payload; // flexible per event_type
    }

    /// <summary>ack message sent by Unity back to the control server.</summary>
    [Serializable]
    public sealed class AckMessage
    {
        public const string schema_version = "2.2";
        public const string message_type_val = "ack";

        public string session_id;
        public string event_id;
        public long received_monotonic_ns;
        public long applied_monotonic_ns;
        public int unity_frame;
        public string result; // applied|duplicate_ignored|rejected|failed
        public string error_code; // null when applied
    }

    /// <summary>render_receipt message sent by Unity after rendering a frame.</summary>
    [Serializable]
    public sealed class RenderReceipt
    {
        public const string schema_version = "2.2";
        public const string message_type_val = "render_receipt";

        public string receipt_id;
        public string session_id;
        public string event_id;
        public int frame_seq;
        public int unity_frame;
        public long rendered_monotonic_ns;
        public string module_id;
        public string segment;
        public string result; // rendered|skipped|failed
        public string error_code; // null when rendered
    }

    /// <summary>
    /// Minimal JSON-compatible wrapper used for dynamic serialization.
    /// Unity's JsonUtility cannot handle Dictionary<string,object> natively,
    /// so all serialization uses JsonSerializable / manual Newtonsoft or
    /// a lightweight hand-rolled serializer.  For the probe implementation
    /// we use a Dictionary-based approach that a custom JsonWriter can emit.
    /// </summary>
    public static class JsonLines
    {
        /// <summary>Encode a dictionary as a single compact JSON line + '\n'.</summary>
        public static byte[] Encode(Dictionary<string, object> msg)
        {
            return System.Text.Encoding.UTF8.GetBytes(Serialize(msg) + "\n");
        }

        /// <summary>Decode a JSON line (without trailing \n) into a dictionary.</summary>
        public static Dictionary<string, object> Decode(string line)
        {
            return Deserialize(line);
        }

        // ── Lightweight JSON serializer/deserializer ──────────────────────
        // Sufficient for the flat, well-known contract messages.  Handles
        // string, int, long, double, bool, null, Dictionary, List, and arrays.

        public static string Serialize(object value)
        {
            if (value == null) return "null";
            if (value is string s) return "\"" + EscapeJsonString(s) + "\"";
            if (value is bool b) return b ? "true" : "false";
            if (value is int i) return i.ToString();
            if (value is long l) return l.ToString();
            if (value is float f) return f.ToString("R");
            if (value is double d) return d.ToString("R");
            if (value is Dictionary<string, object> dict)
            {
                var parts = new List<string>();
                foreach (var kv in dict)
                    parts.Add("\"" + EscapeJsonString(kv.Key) + "\":" + Serialize(kv.Value));
                return "{" + string.Join(",", parts) + "}";
            }
            if (value is IList<object> list)
            {
                var parts = new List<string>();
                foreach (var item in list)
                    parts.Add(Serialize(item));
                return "[" + string.Join(",", parts) + "]";
            }
            if (value is object[] arr)
            {
                var parts = new List<string>();
                foreach (var item in arr)
                    parts.Add(Serialize(item));
                return "[" + string.Join(",", parts) + "]";
            }
            // Fallback — enum/int/string from a typed object serialized via reflection
            return "\"" + EscapeJsonString(value.ToString()) + "\"";
        }

        public static Dictionary<string, object> Deserialize(string json)
        {
            var reader = new JsonReader(json);
            return reader.ReadObject();
        }

        private static string EscapeJsonString(string s)
        {
            if (s == null) return "";
            return s.Replace("\\", "\\\\")
                    .Replace("\"", "\\\"")
                    .Replace("\n", "\\n")
                    .Replace("\r", "\\r")
                    .Replace("\t", "\\t");
        }

        // ── Minimal recursive-descent JSON parser ─────────────────────────

        private sealed class JsonReader
        {
            private readonly string _s;
            private int _pos;

            public JsonReader(string s) { _s = s; _pos = 0; }

            public Dictionary<string, object> ReadObject()
            {
                SkipWhitespace();
                Expect('{');
                var dict = new Dictionary<string, object>();
                if (Peek() == '}') { _pos++; return dict; }
                while (true)
                {
                    SkipWhitespace();
                    string key = ReadString();
                    SkipWhitespace();
                    Expect(':');
                    object val = ReadValue();
                    dict[key] = val;
                    SkipWhitespace();
                    if (Peek() == ',') { _pos++; continue; }
                    break;
                }
                Expect('}');
                return dict;
            }

            private object ReadValue()
            {
                SkipWhitespace();
                char c = Peek();
                if (c == '"') return ReadString();
                if (c == '{') return ReadObject();
                if (c == '[') return ReadArray();
                if (c == 't') { _pos += 4; return true; }
                if (c == 'f') { _pos += 5; return false; }
                if (c == 'n') { _pos += 4; return null; }
                return ReadNumber();
            }

            private string ReadString()
            {
                Expect('"');
                var sb = new System.Text.StringBuilder();
                while (_pos < _s.Length)
                {
                    char c = _s[_pos++];
                    if (c == '"') break;
                    if (c == '\\')
                    {
                        char esc = _pos < _s.Length ? _s[_pos++] : '\0';
                        switch (esc)
                        {
                            case '"': sb.Append('"'); break;
                            case '\\': sb.Append('\\'); break;
                            case '/': sb.Append('/'); break;
                            case 'n': sb.Append('\n'); break;
                            case 'r': sb.Append('\r'); break;
                            case 't': sb.Append('\t'); break;
                            case 'u':
                                if (_pos + 4 <= _s.Length)
                                {
                                    string hex = _s.Substring(_pos, 4);
                                    sb.Append((char)Convert.ToInt32(hex, 16));
                                    _pos += 4;
                                }
                                break;
                            default: sb.Append(esc); break;
                        }
                    }
                    else sb.Append(c);
                }
                return sb.ToString();
            }

            private object ReadArray()
            {
                Expect('[');
                var list = new List<object>();
                if (Peek() == ']') { _pos++; return list.ToArray(); }
                while (true)
                {
                    list.Add(ReadValue());
                    SkipWhitespace();
                    if (Peek() == ',') { _pos++; continue; }
                    break;
                }
                Expect(']');
                return list.ToArray();
            }

            private object ReadNumber()
            {
                int start = _pos;
                bool isFloat = false;
                if (Peek() == '-' || Peek() == '+') _pos++;
                while (_pos < _s.Length && char.IsDigit(_s[_pos])) _pos++;
                if (_pos < _s.Length && _s[_pos] == '.') { isFloat = true; _pos++; }
                while (_pos < _s.Length && char.IsDigit(_s[_pos])) _pos++;
                if (_pos < _s.Length && (_s[_pos] == 'e' || _s[_pos] == 'E'))
                {
                    isFloat = true; _pos++;
                    if (_pos < _s.Length && (_s[_pos] == '+' || _s[_pos] == '-')) _pos++;
                    while (_pos < _s.Length && char.IsDigit(_s[_pos])) _pos++;
                }
                string num = _s.Substring(start, _pos - start);
                if (isFloat)
                    return double.Parse(num, System.Globalization.CultureInfo.InvariantCulture);
                if (long.TryParse(num, out long lv))
                    return lv;
                return double.Parse(num, System.Globalization.CultureInfo.InvariantCulture);
            }

            private void SkipWhitespace()
            {
                while (_pos < _s.Length && char.IsWhiteSpace(_s[_pos])) _pos++;
            }

            private char Peek()
            {
                if (_pos >= _s.Length) throw new FormatException("Unexpected end of JSON");
                return _s[_pos];
            }

            private void Expect(char ch)
            {
                SkipWhitespace();
                if (_pos >= _s.Length || _s[_pos] != ch)
                    throw new FormatException($"Expected '{ch}' at position {_pos}, got '{(_pos < _s.Length ? _s[_pos] : '\0')}'");
                _pos++;
            }
        }
    }
}
