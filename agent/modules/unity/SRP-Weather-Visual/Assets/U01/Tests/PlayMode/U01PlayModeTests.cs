using System.Collections;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace SRP.U01.Tests
{
    public sealed class U01PlayModeTests
    {
        [UnityTest]
        public IEnumerator UnityFramesDoNotAdvanceTheSessionMirror()
        {
            var mirror = new SessionMirror("2.2");
            Assert.That(mirror.Status, Is.EqualTo(MirrorStatus.Created));
            Assert.That(mirror.LastControlSeq, Is.EqualTo(-1));

            yield return null;
            yield return null;
            yield return null;

            Assert.That(mirror.Status, Is.EqualTo(MirrorStatus.Created));
            Assert.That(mirror.LastControlSeq, Is.EqualTo(-1));
            Assert.That(mirror.ModuleId, Is.Null);
            Assert.That(mirror.Segment, Is.Null);
        }

        [UnityTest]
        public IEnumerator RenderReceiptRequiresAnExplicitFrameConfirmation()
        {
            var mirror = new SessionMirror("2.2");
            Apply(mirror, Control(1, "prepare", "{\"manifest\":{\"runtime_mode\":\"formal_stage_1\"}}"));
            Apply(mirror, Control(2, "start", "{\"resumed\":false}"));
            Apply(mirror, Control(3, "module", "{\"module_id\":\"storm\",\"module_position\":0}"));
            var json = Control(4, "segment", "{\"module_id\":\"storm\",\"module_position\":0,\"segment\":\"demo\"}");
            Assert.That(ProtocolCodec.TryParseControl(json, "2.2", out var message, out _), Is.True);
            var result = mirror.ApplyControl(message, json);
            var gate = new RenderReceiptGate("unity-playmode");
            gate.Register(message, result, mirror);

            Assert.That(gate.TryConfirm(message.event_id, -1, Time.frameCount, 0, "rendered", null, out _), Is.False);
            Assert.That(gate.TryConfirm(message.event_id, 0, Time.frameCount, 1, "rendered", null, out _), Is.False);
            gate.ObserveTelemetry(new TelemetryFrameDto
            {
                session_id = message.session_id,
                frame_seq = 0,
                module_id = "storm",
                segment = "demo"
            }, new ApplyResult("applied"));
            Assert.That(gate.TryConfirm(message.event_id, 0, -1, 1, "rendered", null, out _), Is.False);
            Assert.That(gate.TryConfirm(message.event_id, 0, Time.frameCount, -1, "rendered", null, out _), Is.False);
            var registeredFrame = Time.frameCount;
            yield return null;
            Assert.That(Time.frameCount, Is.GreaterThan(registeredFrame));
            Assert.That(gate.TryConfirm(message.event_id, 0, Time.frameCount, 1, "rendered", null, out var receipt), Is.True);
            Assert.That(receipt.event_id, Is.EqualTo(message.event_id));
            Assert.That(receipt.module_id, Is.EqualTo("storm"));
            Assert.That(receipt.segment, Is.EqualTo("demo"));
        }

        [UnityTest]
        public IEnumerator DisableAndEnablePreservesTheActiveMirror()
        {
            var host = new GameObject("U01 lifecycle test");
            host.SetActive(false);
            var bridge = host.AddComponent<U01RuntimeBridge>();
            SetPort(bridge, "controlPort", 1);
            SetPort(bridge, "telemetryPort", 0);
            host.SetActive(true);
            yield return null;

            Apply(bridge.Mirror, Control(1, "prepare", "{\"manifest\":{\"runtime_mode\":\"formal_stage_1\"}}"));
            Apply(bridge.Mirror, Control(2, "start", "{\"resumed\":false}"));
            Apply(bridge.Mirror, Control(3, "module", "{\"module_id\":\"storm\",\"module_position\":0}"));
            Apply(bridge.Mirror, Control(4, "segment", "{\"module_id\":\"storm\",\"module_position\":0,\"segment\":\"demo\"}"));
            var original = bridge.Mirror;

            host.SetActive(false);
            yield return null;
            host.SetActive(true);
            yield return null;

            Assert.That(bridge.Mirror, Is.SameAs(original));
            Assert.That(bridge.Mirror.LastControlSeq, Is.EqualTo(4));
            Apply(bridge.Mirror, Control(5, "segment", "{\"module_id\":\"storm\",\"module_position\":0,\"segment\":\"closed_loop\"}"));
            Object.Destroy(host);
        }

        private static void SetPort(U01RuntimeBridge bridge, string field, int value)
        {
            typeof(U01RuntimeBridge).GetField(field, BindingFlags.Instance | BindingFlags.NonPublic)?.SetValue(bridge, value);
        }

        private static void Apply(SessionMirror mirror, string json)
        {
            Assert.That(ProtocolCodec.TryParseControl(json, "2.2", out var message, out var error), Is.True, error);
            Assert.That(mirror.ApplyControl(message, json).Result, Is.EqualTo("applied"));
        }

        private static string Control(long sequence, string type, string payload)
        {
            return "{\"schema_version\":\"2.2\",\"message_type\":\"control_event\",\"session_id\":\"S-U01-PLAY\",\"event_id\":\"S-U01-PLAY:control:" + sequence.ToString("000000") + "\",\"control_seq\":" + sequence + ",\"event_type\":\"" + type + "\",\"issued_monotonic_ns\":0,\"effective_monotonic_ns\":0,\"clock_domain_id\":\"python:S-U01-PLAY\",\"payload\":" + payload + "}";
        }
    }
}
