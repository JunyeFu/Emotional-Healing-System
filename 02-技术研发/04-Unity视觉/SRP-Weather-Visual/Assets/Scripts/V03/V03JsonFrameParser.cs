using System;
using System.Globalization;

namespace SRP.V03
{
    /// <summary>
    /// F-05 v2.2 telemetry_frame JSON 解析器（零第三方依赖）。
    /// 支持范围：扁平对象 + signal_quality 嵌套对象；未知字段跳过（前向兼容）。
    /// 关键点：cycle_index 的 JSON null 与数字 0 必须可区分（09 迁移指南规则2），
    /// 因此不走 JsonUtility（其无法区分缺失与默认值），由本解析器显式处理。
    /// </summary>
    public static class V03JsonFrameParser
    {
        public static bool TryParse(string json, out V03FrameDto frame, out string error)
        {
            frame = null;
            error = null;
            if (string.IsNullOrWhiteSpace(json))
            {
                error = "E_EMPTY_INPUT";
                return false;
            }

            try
            {
                var scanner = new JsonScanner(json);
                frame = ParseObject(ref scanner);
                return true;
            }
            catch (V03JsonException ex)
            {
                frame = null;
                error = ex.Message;
                return false;
            }
        }

        private static V03FrameDto ParseObject(ref JsonScanner s)
        {
            if (s.Peek != '{') throw new V03JsonException("E_EXPECT_OBJECT_START");
            s.Advance();

            var dto = new V03FrameDto();
            float? resp = null, ecg = null;
            bool recoveryLocked = false;

            if (s.Peek == '}')
            {
                s.Advance();
                return dto;
            }

            while (true)
            {
                if (s.Peek != '"') throw new V03JsonException("E_EXPECT_KEY");
                var key = s.ParseString();

                if (s.Peek != ':') throw new V03JsonException("E_EXPECT_COLON");
                s.Advance();

                switch (key)
                {
                    case "schema_version": dto.SchemaVersion = ExpectString(ref s); break;
                    case "message_type": dto.MessageType = ExpectString(ref s); break;
                    case "session_id": dto.SessionId = ExpectString(ref s); break;
                    case "frame_seq": dto.FrameSeq = ExpectLong(ref s); break;

                    case "clock_domain_id": dto.ClockDomainId = ExpectString(ref s); break;
                    case "source_monotonic_ns": dto.SourceMonotonicNs = ExpectLong(ref s); break;
                    case "received_monotonic_ns": dto.ReceivedMonotonicNs = ExpectLong(ref s); break;
                    case "sent_monotonic_ns": dto.SentMonotonicNs = ExpectLong(ref s); break;
                    case "clock_offset_ns": dto.ClockOffsetNs = ExpectLong(ref s); break;
                    case "clock_drift_ppm": dto.ClockDriftPpm = ExpectDouble(ref s); break;
                    case "sync_uncertainty_ns": dto.SyncUncertaintyNs = ExpectLong(ref s); break;

                    case "module_id": dto.ModuleId = ExpectString(ref s); break;
                    case "module_position": dto.ModulePosition = (int)ExpectLong(ref s); break;
                    case "segment": dto.Segment = ExpectString(ref s); break;
                    case "cue_mode": dto.CueMode = ExpectString(ref s); break;
                    case "runtime_mode": dto.RuntimeMode = ExpectString(ref s); break;
                    case "policy_decision_id": dto.PolicyDecisionId = ExpectString(ref s); break;

                    case "target_phase": dto.TargetPhase = ExpectString(ref s); break;
                    case "target_progress": dto.TargetProgress = (float)ExpectDouble(ref s); break;
                    case "target_cycle_index": dto.TargetCycleIndex = ExpectNullableInt(ref s); break;
                    case "target_step_id": dto.TargetStepId = ExpectNullableString(ref s); break;

                    case "actual_phase": dto.ActualPhase = ExpectString(ref s); break;
                    case "actual_progress": dto.ActualProgress = (float)ExpectDouble(ref s); break;
                    case "actual_cycle_index": dto.ActualCycleIndex = ExpectNullableInt(ref s); break;
                    case "actual_step_id": dto.ActualStepId = ExpectNullableString(ref s); break;
                    case "actual_confidence": dto.ActualConfidence = (float)ExpectDouble(ref s); break;

                    case "recovery_value": dto.RecoveryValue = (float)ExpectDouble(ref s); break;
                    case "recovery_locked": recoveryLocked = ExpectBool(ref s); break;

                    case "signal_quality":
                        // 嵌套对象 {"resp":0.92,"ecg":0.88}
                        ParseSignalQuality(ref s, out resp, out ecg);
                        break;

                    case "fallback_state": dto.FallbackState = ExpectString(ref s); break;
                    case "fallback_reason": dto.FallbackReason = ExpectNullableString(ref s); break;
                    case "resp_device_state": dto.RespDeviceState = ExpectString(ref s); break;
                    case "ecg_device_state": dto.EcgDeviceState = ExpectString(ref s); break;

                    default:
                        SkipValue(ref s); // 前向兼容：未知字段跳过
                        break;
                }

                if (s.Peek == ',') { s.Advance(); continue; }
                if (s.Peek == '}') { s.Advance(); break; }
                throw new V03JsonException("E_EXPECT_COMMA_OR_END");
            }

            dto.RecoveryLocked = recoveryLocked;
            dto.SignalQualityResp = resp ?? 0f;
            dto.SignalQualityEcg = ecg ?? 0f;
            return dto;
        }

        private static void ParseSignalQuality(ref JsonScanner s, out float? resp, out float? ecg)
        {
            // 嵌套对象的闭合 '}' 必须由本方法自行消费：
            // 外层 ParseObject 无法区分嵌套对象的 '}' 与整个帧对象的 '}'。
            resp = null; ecg = null;
            if (s.Peek != '{') throw new V03JsonException("E_EXPECT_OBJECT_START");
            s.Advance();
            if (s.Peek == '}') { s.Advance(); return; }

            while (true)
            {
                if (s.Peek != '"') throw new V03JsonException("E_EXPECT_KEY");
                var key = s.ParseString();
                if (s.Peek != ':') throw new V03JsonException("E_EXPECT_COLON");
                s.Advance();

                switch (key)
                {
                    case "resp": resp = (float)ExpectDouble(ref s); break;
                    case "ecg": ecg = (float)ExpectDouble(ref s); break;
                    default: SkipValue(ref s); break;
                }

                if (s.Peek == ',') { s.Advance(); continue; }
                if (s.Peek == '}') { s.Advance(); break; }
                throw new V03JsonException("E_EXPECT_COMMA_OR_END");
            }
        }

        private static string ExpectString(ref JsonScanner s) =>
            s.Peek == '"' ? s.ParseString() : throw new V03JsonException("E_EXPECT_STRING");

        private static string ExpectNullableString(ref JsonScanner s)
        {
            if (s.IsNull())
            {
                s.ConsumeNull();
                return null;
            }
            return ExpectString(ref s);
        }

        private static int? ExpectNullableInt(ref JsonScanner s)
        {
            if (s.IsNull())
            {
                s.ConsumeNull();
                return null;
            }
            return (int)Math.Round(ExpectDouble(ref s), MidpointRounding.AwayFromZero);
        }

        private static long ExpectLong(ref JsonScanner s) => (long)ExpectDouble(ref s);

        private static double ExpectDouble(ref JsonScanner s) => s.ParseNumber();

        private static bool ExpectBool(ref JsonScanner s) => s.ParseBool();

        private static void SkipValue(ref JsonScanner s) => s.SkipAnyValue();

        private sealed class V03JsonException : Exception
        {
            public V03JsonException(string code) : base(code) { }
        }

        /// <summary>最小 JSON 词法扫描器：仅覆盖帧所需子集（字符串/数字/布尔/null/对象/数组跳过）。</summary>
        private ref struct JsonScanner
        {
            private readonly string _s;
            private int _i;

            public JsonScanner(string s)
            {
                _s = s;
                _i = 0;
            }

            public char Peek
            {
                get
                {
                    SkipWs();
                    return _i < _s.Length ? _s[_i] : '\0';
                }
            }

            public void Advance()
            {
                SkipWs();
                _i++;
            }

            private void SkipWs()
            {
                while (_i < _s.Length)
                {
                    var c = _s[_i];
                    if (c == ' ' || c == '\t' || c == '\n' || c == '\r') _i++;
                    else break;
                }
            }

            public bool IsNull()
            {
                SkipWs();
                return _i + 4 <= _s.Length &&
                       _s[_i] == 'n' && _s[_i + 1] == 'u' && _s[_i + 2] == 'l' && _s[_i + 3] == 'l';
            }

            public int ConsumeNull()
            {
                SkipWs();
                if (!IsNull()) throw new V03JsonException("E_EXPECT_NULL");
                _i += 4;
                return 0;
            }

            public string ParseString()
            {
                SkipWs();
                if (_i >= _s.Length || _s[_i] != '"') throw new V03JsonException("E_EXPECT_STRING");
                _i++;
                var sb = new System.Text.StringBuilder();
                while (_i < _s.Length)
                {
                    var c = _s[_i];
                    if (c == '"')
                    {
                        _i++;
                        return sb.ToString();
                    }
                    if (c == '\\')
                    {
                        _i++;
                        if (_i >= _s.Length) break;
                        var esc = _s[_i];
                        switch (esc)
                        {
                            case '"': sb.Append('"'); break;
                            case '\\': sb.Append('\\'); break;
                            case '/': sb.Append('/'); break;
                            case 'b': sb.Append('\b'); break;
                            case 'f': sb.Append('\f'); break;
                            case 'n': sb.Append('\n'); break;
                            case 'r': sb.Append('\r'); break;
                            case 't': sb.Append('\t'); break;
                            case 'u':
                                if (_i + 4 >= _s.Length) throw new V03JsonException("E_BAD_UNICODE");
                                var hex = _s.Substring(_i + 1, 4);
                                sb.Append((char)int.Parse(hex, NumberStyles.HexNumber, CultureInfo.InvariantCulture));
                                _i += 4;
                                break;
                            default: throw new V03JsonException("E_BAD_ESCAPE");
                        }
                        _i++;
                        continue;
                    }
                    sb.Append(c);
                    _i++;
                }
                throw new V03JsonException("E_UNTERMINATED_STRING");
            }

            public double ParseNumber()
            {
                SkipWs();
                int start = _i;
                while (_i < _s.Length)
                {
                    var c = _s[_i];
                    if (c == '-' || c == '+' || c == '.' || c == 'e' || c == 'E' || (c >= '0' && c <= '9')) _i++;
                    else break;
                }
                if (_i == start) throw new V03JsonException("E_EXPECT_NUMBER");
                var token = _s.Substring(start, _i - start);
                if (!double.TryParse(token, NumberStyles.Float, CultureInfo.InvariantCulture, out var value))
                    throw new V03JsonException("E_BAD_NUMBER");
                return value;
            }

            public bool ParseBool()
            {
                SkipWs();
                if (_i + 4 <= _s.Length && _s[_i] == 't' && _s[_i + 1] == 'r' && _s[_i + 2] == 'u' && _s[_i + 3] == 'e')
                {
                    _i += 4;
                    return true;
                }
                if (_i + 5 <= _s.Length && _s[_i] == 'f' && _s[_i + 1] == 'a' && _s[_i + 2] == 'l' && _s[_i + 3] == 's' && _s[_i + 4] == 'e')
                {
                    _i += 5;
                    return false;
                }
                throw new V03JsonException("E_EXPECT_BOOL");
            }

            public void SkipAnyValue()
            {
                var c = Peek;
                if (c == '"') { ParseString(); return; }
                if (c == 'n') { ConsumeNull(); return; }
                if (c == 't' || c == 'f') { ParseBool(); return; }
                if (c == '{' || c == '[') { SkipContainer(); return; }
                ParseNumber();
            }

            private void SkipContainer()
            {
                // 假定 Peek 是 '{' 或 '['（已 SkipWs）
                int depth = 0;
                while (_i < _s.Length)
                {
                    var c = _s[_i];
                    if (c == '"')
                    {
                        ParseString();
                        continue;
                    }
                    if (c == '{' || c == '[') depth++;
                    else if (c == '}' || c == ']')
                    {
                        depth--;
                        _i++;
                        if (depth == 0) return;
                        continue;
                    }
                    _i++;
                }
                throw new V03JsonException("E_UNTERMINATED_CONTAINER");
            }
        }
    }
}
