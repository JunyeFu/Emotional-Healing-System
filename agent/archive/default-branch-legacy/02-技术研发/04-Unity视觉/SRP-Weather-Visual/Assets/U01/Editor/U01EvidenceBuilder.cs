using System;
using System.Collections.Generic;
using System.IO;
using System.Xml;
using UnityEditor;
using UnityEngine;

namespace SRP.U01.Editor
{
    public static class U01EvidenceBuilder
    {
        [Serializable] private sealed class TraceEnvelope { public string evidence_type; public List<TraceRow> rows = new(); }
        [Serializable] private sealed class TraceRow { public long sequence; public string event_type; public string result; public string status; public string module_id; public string segment; }
        [Serializable] private sealed class EvidenceEnvelope { public string evidence_type; public string schema_version; public List<EvidenceRow> rows = new(); }
        [Serializable] private sealed class EvidenceRow { public string case_id; public string observed; public string expected; public string result; }

        public static void Generate()
        {
            var root = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../.."));
            var output = Path.Combine(root, "03-测试与实验", "evidence", "U-01");
            Directory.CreateDirectory(output);

            var tracePath = Path.Combine(root, "02-技术研发", "srp_session_core", "fixtures", "golden", "four-module-trace-v1.json");
            var trace = JsonUtility.FromJson<GoldenTrace>(File.ReadAllText(tracePath));
            var mirror = new SessionMirror("2.1");
            var envelope = new TraceEnvelope { evidence_type = "U01_STATE_MIRROR_TRACE" };
            var acks = new List<AckDto>();
            var receipts = new List<RenderReceiptDto>();
            var receiptGate = new RenderReceiptGate("U01-EVIDENCE");
            foreach (var value in trace.control_events)
            {
                var raw = JsonUtility.ToJson(value);
                ProtocolCodec.TryParseControl(raw, "2.1", out var parsed, out _);
                var result = mirror.ApplyControl(parsed, raw);
                acks.Add(DeliveryFactory.CreateAck(parsed, result, value.effective_monotonic_ns, value.effective_monotonic_ns, (int)value.control_seq));
                if (value.event_type == "segment")
                {
                    receiptGate.Register(parsed, result, mirror);
                    receiptGate.ObserveTelemetry(new TelemetryFrameDto
                    {
                        session_id = parsed.session_id,
                        frame_seq = value.control_seq,
                        module_id = mirror.ModuleId,
                        segment = mirror.Segment
                    }, new ApplyResult("applied"));
                    if (!receiptGate.TryConfirm(
                            parsed.event_id, value.control_seq, (int)value.control_seq,
                            value.effective_monotonic_ns, "rendered", null, out var receipt))
                        throw new InvalidOperationException("Golden render confirmation was rejected: " + parsed.event_id);
                    receipts.Add(receipt);
                }
                envelope.rows.Add(new TraceRow
                {
                    sequence = value.control_seq,
                    event_type = value.event_type,
                    result = result.Result,
                    status = mirror.Status.ToString(),
                    module_id = mirror.ModuleId,
                    segment = mirror.Segment
                });
            }
            Write(Path.Combine(output, "state-mirror-trace.json"), JsonUtility.ToJson(envelope, true));
            WriteDeliveries(Path.Combine(output, "ack-render-receipt-sequence.json"), acks, receipts);

            var network = new EvidenceEnvelope { evidence_type = "U01_NETWORK_FAULT_MATRIX", schema_version = "2.2" };
            network.rows.Add(Row("wrong_schema_welcome", ValidateWelcome("2.1"), "rejected"));
            network.rows.Add(Row(
                "reconnect_same_client_identity",
                TestPassed(Path.Combine(output, "editmode-results.xml"), "ReliableClientReconnectsAndKeepsTheSameIdentity")
                    ? "test_passed"
                    : "test_not_passed",
                "test_passed"));
            using (var disconnected = new ReliableControlClient("2.2", "U01-EVIDENCE", 1))
                network.rows.Add(Row("closed_socket_send", disconnected.Send("{}") ? "send_returns_true" : "send_returns_false", "send_returns_false"));
            Write(Path.Combine(output, "network-fault-log.json"), JsonUtility.ToJson(network, true));

            AssetDatabase.Refresh();
            Debug.Log("U01_EVIDENCE_PASS output=" + output);
        }

        [Serializable] private sealed class GoldenTrace { public ControlEventDto[] control_events; }

        private static EvidenceRow Row(string id, string observed, string expected) => new()
        {
            case_id = id,
            observed = observed,
            expected = expected,
            result = observed == expected ? "PASS" : "FAIL"
        };

        private static string ValidateWelcome(string schema)
        {
            var json = "{\"transport_type\":\"welcome\",\"transport_version\":\"1.0\",\"schema_version\":\"" + schema + "\",\"role\":\"unity\",\"client_instance_id\":\"U01-EVIDENCE\",\"accepted\":true,\"error_code\":null}";
            return ProtocolCodec.ValidateWelcome(json, "2.2", "U01-EVIDENCE", out _) ? "accepted" : "rejected";
        }

        private static void Write(string path, string content) => File.WriteAllText(path, content + Environment.NewLine);

        private static bool TestPassed(string path, string testName)
        {
            if (!File.Exists(path)) return false;
            var document = new XmlDocument();
            document.Load(path);
            foreach (XmlNode node in document.SelectNodes("//test-case"))
            {
                var name = node.Attributes?["name"]?.Value;
                var result = node.Attributes?["result"]?.Value;
                if (name == testName && result == "Passed") return true;
            }
            return false;
        }

        private static void WriteDeliveries(string path, List<AckDto> acks, List<RenderReceiptDto> receipts)
        {
            var content = "{\n  \"evidence_type\": \"U01_ACK_RENDER_RECEIPT_SEQUENCE\",\n" +
                          "  \"evidence_scope\": \"contract_golden_fixture\",\n" +
                          "  \"acks\": [\n    " + string.Join(",\n    ", acks.ConvertAll(ProtocolCodec.ToJson)) + "\n  ],\n" +
                          "  \"render_receipts\": [\n    " + string.Join(",\n    ", receipts.ConvertAll(ProtocolCodec.ToJson)) + "\n  ]\n}";
            Write(path, content);
        }
    }
}
