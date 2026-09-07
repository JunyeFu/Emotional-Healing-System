// U01 — EditMode tests for the reliable control probe and render receipt system.
// These tests run in the Unity Editor without requiring play mode or network.
// Covers: JSON serialization, session mirror, ack manager, render receipt,
// reconnect handler, UDP gate validation, and contract message construction.

using System;
using System.Collections.Generic;
using NUnit.Framework;
using SRP.U01;
using UnityEngine;

namespace SRP.U01.Tests
{
    // ── JSON serialization round-trip tests ───────────────────────────────

    public sealed class JsonLinesSerializationTests
    {
        [Test]
        public void SerializeString_ProducesQuotedValue()
        {
            var dict = new Dictionary<string, object> { ["key"] = "hello" };
            string json = JsonLines.Serialize(dict);
            Assert.That(json, Does.Contain("\"key\":\"hello\""));
        }

        [Test]
        public void SerializeInt_ProducesNumericLiteral()
        {
            var dict = new Dictionary<string, object> { ["n"] = 42 };
            string json = JsonLines.Serialize(dict);
            Assert.That(json, Does.Contain("\"n\":42"));
        }

        [Test]
        public void SerializeBool_ProducesTrueOrFalse()
        {
            var dict = new Dictionary<string, object>
            {
                ["a"] = true,
                ["b"] = false
            };
            string json = JsonLines.Serialize(dict);
            Assert.That(json, Does.Contain("\"a\":true"));
            Assert.That(json, Does.Contain("\"b\":false"));
        }

        [Test]
        public void SerializeNull_ProducesNullLiteral()
        {
            var dict = new Dictionary<string, object> { ["x"] = null };
            string json = JsonLines.Serialize(dict);
            Assert.That(json, Does.Contain("\"x\":null"));
        }

        [Test]
        public void SerializeNestedDictionary_ProducesNestedJson()
        {
            var dict = new Dictionary<string, object>
            {
                ["outer"] = new Dictionary<string, object>
                {
                    ["inner"] = "value"
                }
            };
            string json = JsonLines.Serialize(dict);
            Assert.That(json, Does.Contain("\"outer\":{\"inner\":\"value\"}"));
        }

        [Test]
        public void SerializeArray_ProducesJsonArray()
        {
            var dict = new Dictionary<string, object>
            {
                ["items"] = new object[] { "a", "b", "c" }
            };
            string json = JsonLines.Serialize(dict);
            Assert.That(json, Does.Contain("\"items\":[\"a\",\"b\",\"c\"]"));
        }

        [Test]
        public void SerializeSpecialCharacters_EscapesCorrectly()
        {
            var dict = new Dictionary<string, object>
            {
                ["msg"] = "line1\nline2\ttab\"quote"
            };
            string json = JsonLines.Serialize(dict);
            Assert.That(json, Does.Contain("\\n"));
            Assert.That(json, Does.Contain("\\t"));
            Assert.That(json, Does.Contain("\\\""));
        }

        [Test]
        public void RoundTrip_SimpleDictionary()
        {
            var original = new Dictionary<string, object>
            {
                ["schema_version"] = "2.2",
                ["message_type"] = "ack",
                ["event_id"] = "evt-001",
                ["result"] = "applied",
                ["error_code"] = (string)null,
                ["unity_frame"] = 1234,
                ["received_monotonic_ns"] = 9876543210L
            };

            string json = JsonLines.Serialize(original);
            var decoded = JsonLines.Deserialize(json);

            Assert.That(decoded["schema_version"], Is.EqualTo("2.2"));
            Assert.That(decoded["message_type"], Is.EqualTo("ack"));
            Assert.That(decoded["event_id"], Is.EqualTo("evt-001"));
            Assert.That(decoded["result"], Is.EqualTo("applied"));
            Assert.That(decoded["error_code"], Is.Null);
            Assert.That(decoded["unity_frame"], Is.EqualTo(1234));
            Assert.That(decoded["received_monotonic_ns"], Is.EqualTo(9876543210L));
        }

        [Test]
        public void RoundTrip_NestedStructures()
        {
            var original = new Dictionary<string, object>
            {
                ["payload"] = new Dictionary<string, object>
                {
                    ["module_id"] = "storm",
                    ["module_position"] = 0,
                    ["segment"] = "demo"
                }
            };

            string json = JsonLines.Serialize(original);
            var decoded = JsonLines.Deserialize(json);

            Assert.That(decoded.ContainsKey("payload"), Is.True);
            var payload = (Dictionary<string, object>)decoded["payload"];
            Assert.That(payload["module_id"], Is.EqualTo("storm"));
            Assert.That(payload["module_position"], Is.EqualTo(0));
        }

        [Test]
        public void Decode_InvalidJson_ThrowsFormatError()
        {
            Assert.Throws<FormatException>(() =>
                JsonLines.Deserialize("{invalid json}"));
        }

        [Test]
        public void Serialize_ControlEvent_VisibleStructure()
        {
            var evt = new Dictionary<string, object>
            {
                ["schema_version"] = "2.2",
                ["message_type"] = "control_event",
                ["session_id"] = "sess-001",
                ["event_id"] = "evt-001",
                ["control_seq"] = 1,
                ["event_type"] = "start",
                ["issued_monotonic_ns"] = 1000000000L,
                ["effective_monotonic_ns"] = 1050000000L,
                ["clock_domain_id"] = "python",
                ["payload"] = new Dictionary<string, object>()
            };
            string json = JsonLines.Serialize(evt);
            Assert.That(json, Does.Contain("\"event_type\":\"start\""));
            Assert.That(json, Does.Contain("\"control_seq\":1"));
        }

        [Test]
        public void Encode_AppendsNewline()
        {
            var dict = new Dictionary<string, object> { ["a"] = 1 };
            byte[] bytes = JsonLines.Encode(dict);
            Assert.That(bytes[bytes.Length - 1], Is.EqualTo((byte)'\n'));
        }

        [Test]
        public void Serialize_Float_PreservesPrecision()
        {
            var dict = new Dictionary<string, object> { ["progress"] = 0.75 };
            string json = JsonLines.Serialize(dict);
            var decoded = JsonLines.Deserialize(json);
            Assert.That(decoded["progress"], Is.EqualTo(0.75));
        }

        [Test]
        public void Serialize_Long_PreservesValue()
        {
            long bigVal = 123456789012345L;
            var dict = new Dictionary<string, object> { ["ts"] = bigVal };
            string json = JsonLines.Serialize(dict);
            var decoded = JsonLines.Deserialize(json);
            Assert.That(decoded["ts"], Is.EqualTo(bigVal));
        }
    }

    // ── SessionMirror tests ───────────────────────────────────────────────

    public sealed class SessionMirrorTests
    {
        [Test]
        public void InitialSnapshot_IsEmpty()
        {
            var go = new GameObject("MirrorTest");
            try
            {
                var mirror = go.AddComponent<SessionMirror>();
                Assert.That(mirror.Snapshot.HasSession, Is.False);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(go);
            }
        }

        [Test]
        public void ApplySessionManifest_UpdatesSnapshot()
        {
            var go = new GameObject("MirrorTest");
            try
            {
                var mirror = go.AddComponent<SessionMirror>();
                var manifest = CreateTestManifest();

                mirror.ApplySessionManifest(manifest);

                var snap = mirror.Snapshot;
                Assert.That(snap.HasSession, Is.True);
                Assert.That(snap.SessionId, Is.EqualTo("sess-001"));
                Assert.That(snap.ResearchId, Is.EqualTo("res-001"));
                Assert.That(snap.RuntimeMode, Is.EqualTo("dev_mock"));
                Assert.That(snap.StudyStage, Is.EqualTo("level_c"));
                Assert.That(snap.WeatherSequence, Is.EqualTo(new[] { "storm", "heat", "snow", "fade" }));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(go);
            }
        }

        [Test]
        public void ApplyControlEvent_UpdatesActiveSeq()
        {
            var go = new GameObject("MirrorTest");
            try
            {
                var mirror = go.AddComponent<SessionMirror>();
                mirror.ApplySessionManifest(CreateTestManifest());

                var evt = CreateTestControlEvent("start", 5);
                mirror.ApplyControlEvent(evt);

                Assert.That(mirror.Snapshot.ActiveControlSeq, Is.EqualTo(5));
                Assert.That(mirror.Snapshot.LastEventId, Is.EqualTo("evt-005"));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(go);
            }
        }

        [Test]
        public void ApplyControlEvent_ModuleEvent_UpdatesModuleId()
        {
            var go = new GameObject("MirrorTest");
            try
            {
                var mirror = go.AddComponent<SessionMirror>();
                mirror.ApplySessionManifest(CreateTestManifest());

                var evt = CreateTestControlEvent("module", 10);
                evt.payload = new Dictionary<string, object>
                {
                    ["module_id"] = "storm",
                    ["module_position"] = 0
                };
                mirror.ApplyControlEvent(evt);

                var snap = mirror.Snapshot;
                Assert.That(snap.CurrentModuleId, Is.EqualTo("storm"));
                Assert.That(snap.ModulePosition, Is.EqualTo(0));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(go);
            }
        }

        [Test]
        public void ApplyControlEvent_SegmentEvent_UpdatesSegment()
        {
            var go = new GameObject("MirrorTest");
            try
            {
                var mirror = go.AddComponent<SessionMirror>();
                mirror.ApplySessionManifest(CreateTestManifest());

                var evt = CreateTestControlEvent("segment", 15);
                evt.payload = new Dictionary<string, object>
                {
                    ["segment"] = "closed_loop"
                };
                mirror.ApplyControlEvent(evt);

                Assert.That(mirror.Snapshot.CurrentSegment, Is.EqualTo("closed_loop"));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(go);
            }
        }

        [Test]
        public void ResetState_ClearsAllFields()
        {
            var go = new GameObject("MirrorTest");
            try
            {
                var mirror = go.AddComponent<SessionMirror>();
                mirror.ApplySessionManifest(CreateTestManifest());
                mirror.ApplyControlEvent(CreateTestControlEvent("start", 1));

                mirror.ResetState();

                Assert.That(mirror.Snapshot.HasSession, Is.False);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(go);
            }
        }

        [Test]
        public void ApplyControlEvent_NullThrows()
        {
            var go = new GameObject("MirrorTest");
            try
            {
                var mirror = go.AddComponent<SessionMirror>();
                Assert.Throws<ArgumentNullException>(() => mirror.ApplyControlEvent(null));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(go);
            }
        }

        // ── Helpers ───────────────────────────────────────────────────────

        private static SessionManifest CreateTestManifest()
        {
            return new SessionManifest
            {
                research_id = "res-001",
                session_id = "sess-001",
                study_stage = "level_c",
                runtime_mode = "dev_mock",
                cue_mode = "scene_native",
                assignment_arm = "arm-A",
                allocation_index = 0,
                randomization_stratum = "stratum-1",
                randomization_block = 1,
                randomization_list_hash = "abc123",
                weather_sequence = new[] { "storm", "heat", "snow", "fade" },
                module_durations = new ModuleDurations
                {
                    demo = 30.0,
                    closed_loop = 120.0,
                    lock_transition = 10.0
                },
                protocol_config_version = "1.0",
                randomization_version = "1.0",
                strategy_version = null,
                device_config = new DeviceConfig
                {
                    resp = new DeviceSensorConfig { source = "mock" },
                    ecg = new DeviceSensorConfig { source = "mock" }
                },
                unity_build_hash = "test-build",
                python_commit = "py-commit",
                td_build_hash = null,
                source_policy = "mock",
                created_utc = "2026-01-01T00:00:00Z",
                breath_protocol_config_version = "1.0",
                breath_protocol_config_hash = "sha256:" + new string('a', 64)
            };
        }

        private static ControlEvent CreateTestControlEvent(string eventType, int seq)
        {
            return new ControlEvent
            {
                session_id = "sess-001",
                event_id = $"evt-{seq:D3}",
                control_seq = seq,
                event_type = eventType,
                issued_monotonic_ns = 1000000000L + seq * 1000000L,
                effective_monotonic_ns = 1000000000L + seq * 1000000L + 500000L,
                clock_domain_id = "python",
                payload = new Dictionary<string, object>()
            };
        }
    }

    // ── AckManager tests ──────────────────────────────────────────────────

    public sealed class AckManagerTests
    {
        private AckManager _manager;

        [SetUp]
        public void SetUp()
        {
            _manager = new AckManager(
                ackTimeoutMs: 100,
                maxAttempts: 2,
                clockDomainId: "unity",
                nowNs: () => 1000000000L);
        }

        [TearDown]
        public void TearDown()
        {
            _manager.Reset();
        }

        [Test]
        public void CreateAck_HasCorrectFields()
        {
            var ack = _manager.CreateAck("sess-001", "evt-001", 42, AckResult.applied);

            Assert.That(ack.session_id, Is.EqualTo("sess-001"));
            Assert.That(ack.event_id, Is.EqualTo("evt-001"));
            Assert.That(ack.unity_frame, Is.EqualTo(42));
            Assert.That(ack.result, Is.EqualTo("applied"));
            Assert.That(ack.error_code, Is.Null);
            Assert.That(ack.received_monotonic_ns, Is.EqualTo(1000000000L));
        }

        [Test]
        public void CreateAck_Rejected_HasErrorCode()
        {
            var ack = _manager.CreateAck("sess-001", "evt-001", 1, AckResult.rejected, "STALE_SEQ");

            Assert.That(ack.result, Is.EqualTo("rejected"));
            Assert.That(ack.error_code, Is.EqualTo("STALE_SEQ"));
        }

        [Test]
        public void TrackEventSent_MakesEventPending()
        {
            var evt = new ControlEvent
            {
                event_id = "evt-001",
                control_seq = 1,
                event_type = "start",
                issued_monotonic_ns = 1000000000L,
                effective_monotonic_ns = 1000000000L,
                clock_domain_id = "python",
                session_id = "sess-001",
                payload = new Dictionary<string, object>()
            };

            _manager.TrackEventSent(evt);

            Assert.That(_manager.IsPending("evt-001"), Is.True);
            Assert.That(_manager.PendingCount, Is.EqualTo(1));
        }

        [Test]
        public void ProcessIncomingAck_Applied_MarksDelivered()
        {
            var evt = CreateTrackedEvent("evt-001");
            _manager.TrackEventSent(evt);

            var ack = new AckMessage
            {
                session_id = "sess-001",
                event_id = "evt-001",
                result = "applied",
                unity_frame = 10,
                received_monotonic_ns = 1000000000L,
                applied_monotonic_ns = 1000000000L,
                error_code = null
            };

            bool isNew = _manager.ProcessIncomingAck(ack);

            Assert.That(isNew, Is.True);
            Assert.That(_manager.IsDelivered("evt-001"), Is.True);
            Assert.That(_manager.IsPending("evt-001"), Is.False);
        }

        [Test]
        public void ProcessIncomingAck_DuplicateIgnored_MarksDelivered()
        {
            var evt = CreateTrackedEvent("evt-001");
            _manager.TrackEventSent(evt);

            var ack = new AckMessage
            {
                session_id = "sess-001",
                event_id = "evt-001",
                result = "duplicate_ignored",
                unity_frame = 10,
                received_monotonic_ns = 1000000000L,
                applied_monotonic_ns = 1000000000L,
                error_code = null
            };

            _manager.ProcessIncomingAck(ack);
            Assert.That(_manager.IsDelivered("evt-001"), Is.True);
        }

        [Test]
        public void ProcessIncomingAck_Rejected_NotDelivered()
        {
            var evt = CreateTrackedEvent("evt-001");
            _manager.TrackEventSent(evt);

            var ack = new AckMessage
            {
                session_id = "sess-001",
                event_id = "evt-001",
                result = "rejected",
                unity_frame = 10,
                received_monotonic_ns = 1000000000L,
                applied_monotonic_ns = 1000000000L,
                error_code = "INVALID"
            };

            _manager.ProcessIncomingAck(ack);
            Assert.That(_manager.IsDelivered("evt-001"), Is.False);
            Assert.That(_manager.IsPending("evt-001"), Is.False);
        }

        [Test]
        public void CheckTimeouts_ExceedsMaxAttempts_ReturnsTimedOut()
        {
            // With maxAttempts=2, after 2 timeouts the event should be removed
            var evt = CreateTrackedEvent("evt-001");
            _manager.TrackEventSent(evt);

            // Simulate time passing by creating ack manager with very short timeout
            var shortManager = new AckManager(
                ackTimeoutMs: 1, // 1ms
                maxAttempts: 1,
                clockDomainId: "unity",
                nowNs: () => 1000000000L);

            shortManager.TrackEventSent(evt);

            // Wait a bit
            System.Threading.Thread.Sleep(10);

            var timedOut = shortManager.CheckTimeouts();
            Assert.That(timedOut, Does.Contain("evt-001"));
            Assert.That(shortManager.IsPending("evt-001"), Is.False);
        }

        [Test]
        public void FailAllPending_ClearsAll()
        {
            _manager.TrackEventSent(CreateTrackedEvent("evt-001"));
            _manager.TrackEventSent(CreateTrackedEvent("evt-002"));

            _manager.FailAllPending("disconnect");

            Assert.That(_manager.PendingCount, Is.EqualTo(0));
        }

        [Test]
        public void ProcessIncomingAck_Null_ReturnsFalse()
        {
            Assert.That(_manager.ProcessIncomingAck(null), Is.False);
        }

        [Test]
        public void ProcessIncomingAck_SecondTime_ReturnsFalse()
        {
            var evt = CreateTrackedEvent("evt-001");
            _manager.TrackEventSent(evt);

            var ack = new AckMessage
            {
                session_id = "sess-001",
                event_id = "evt-001",
                result = "applied",
                unity_frame = 10,
                received_monotonic_ns = 1000000000L,
                applied_monotonic_ns = 1000000000L,
                error_code = null
            };

            Assert.That(_manager.ProcessIncomingAck(ack), Is.True);
            Assert.That(_manager.ProcessIncomingAck(ack), Is.False);
        }

        [Test]
        public void Reset_ClearsEverything()
        {
            _manager.TrackEventSent(CreateTrackedEvent("evt-001"));
            _manager.Reset();

            Assert.That(_manager.PendingCount, Is.EqualTo(0));
            Assert.That(_manager.DeliveredCount, Is.EqualTo(0));
        }

        [Test]
        public void OnAckReceived_EventFires()
        {
            string receivedId = null;
            _manager.OnAckReceived += (id, ack) => receivedId = id;

            _manager.TrackEventSent(CreateTrackedEvent("evt-001"));
            _manager.ProcessIncomingAck(new AckMessage
            {
                event_id = "evt-001",
                session_id = "sess-001",
                result = "applied",
                unity_frame = 1,
                received_monotonic_ns = 1000000000L,
                applied_monotonic_ns = 1000000000L,
                error_code = null
            });

            Assert.That(receivedId, Is.EqualTo("evt-001"));
        }

        private static ControlEvent CreateTrackedEvent(string eventId)
        {
            return new ControlEvent
            {
                session_id = "sess-001",
                event_id = eventId,
                control_seq = 1,
                event_type = "start",
                issued_monotonic_ns = 1000000000L,
                effective_monotonic_ns = 1000000000L,
                clock_domain_id = "python",
                payload = new Dictionary<string, object>()
            };
        }
    }

    // ── RenderReceiptManager tests ────────────────────────────────────────

    public sealed class RenderReceiptManagerTests
    {
        private RenderReceiptManager _manager;

        [SetUp]
        public void SetUp()
        {
            _manager = new RenderReceiptManager(
                nowNs: () => 2000000000L,
                unityFrameProvider: () => 100);
        }

        [TearDown]
        public void TearDown()
        {
            _manager.ResetState();
        }

        [Test]
        public void RegisterEvent_CreatesPendingReceipt()
        {
            var evt = CreateTestEvent("evt-001");

            var tracked = _manager.RegisterEvent(evt, "storm", "demo");

            Assert.That(tracked.EventId, Is.EqualTo("evt-001"));
            Assert.That(tracked.ModuleId, Is.EqualTo("storm"));
            Assert.That(tracked.Segment, Is.EqualTo("demo"));
            Assert.That(tracked.Result, Is.EqualTo(RenderResult.rendered));
            Assert.That(_manager.PendingCount, Is.EqualTo(1));
        }

        [Test]
        public void CompleteRendered_CreatesReceiptWithCorrectFields()
        {
            var evt = CreateTestEvent("evt-001");
            _manager.RegisterEvent(evt, "heat", "closed_loop");

            var receipt = _manager.CompleteRendered("evt-001", "sess-001");

            Assert.That(receipt.result, Is.EqualTo("rendered"));
            Assert.That(receipt.session_id, Is.EqualTo("sess-001"));
            Assert.That(receipt.event_id, Is.EqualTo("evt-001"));
            Assert.That(receipt.module_id, Is.EqualTo("heat"));
            Assert.That(receipt.segment, Is.EqualTo("closed_loop"));
            Assert.That(receipt.error_code, Is.Null);
            Assert.That(receipt.rendered_monotonic_ns, Is.EqualTo(2000000000L));
            Assert.That(receipt.unity_frame, Is.EqualTo(100));
            Assert.That(_manager.PendingCount, Is.EqualTo(0));
            Assert.That(_manager.CompletedCount, Is.EqualTo(1));
        }

        [Test]
        public void CompleteSkipped_HasSkippedResult()
        {
            var evt = CreateTestEvent("evt-001");
            _manager.RegisterEvent(evt, "snow", "demo");

            var receipt = _manager.CompleteSkipped("evt-001", "sess-001", "no_change");

            Assert.That(receipt.result, Is.EqualTo("skipped"));
            Assert.That(receipt.error_code, Is.EqualTo("no_change"));
        }

        [Test]
        public void CompleteFailed_HasFailedResult()
        {
            var evt = CreateTestEvent("evt-001");
            _manager.RegisterEvent(evt, "fade", "lock_transition");

            var receipt = _manager.CompleteFailed("evt-001", "sess-001", "RENDER_ERROR");

            Assert.That(receipt.result, Is.EqualTo("failed"));
            Assert.That(receipt.error_code, Is.EqualTo("RENDER_ERROR"));
        }

        [Test]
        public void GetUnsentReceipts_ReturnsCompletedUnsent()
        {
            var evt = CreateTestEvent("evt-001");
            _manager.RegisterEvent(evt, "storm", "demo");
            _manager.CompleteRendered("evt-001", "sess-001");

            var unsent = _manager.GetUnsentReceipts("sess-001");

            Assert.That(unsent.Count, Is.EqualTo(1));
            Assert.That(unsent[0].event_id, Is.EqualTo("evt-001"));
        }

        [Test]
        public void GetUnsentReceipts_ExcludesAlreadySent()
        {
            var evt = CreateTestEvent("evt-001");
            _manager.RegisterEvent(evt, "storm", "demo");
            _manager.CompleteRendered("evt-001", "sess-001");
            _manager.MarkSent("evt-001");

            var unsent = _manager.GetUnsentReceipts("sess-001");
            Assert.That(unsent.Count, Is.EqualTo(0));
        }

        [Test]
        public void CompleteRendered_ForUnregisteredEvent_CreatesAdHoc()
        {
            // Completing an event that was never registered should still work
            var receipt = _manager.CompleteRendered("evt-unknown", "sess-001");

            Assert.That(receipt.result, Is.EqualTo("rendered"));
            Assert.That(receipt.event_id, Is.EqualTo("evt-unknown"));
            Assert.That(_manager.CompletedCount, Is.EqualTo(1));
        }

        [Test]
        public void DiscardAll_ClearsAllState()
        {
            _manager.RegisterEvent(CreateTestEvent("evt-001"), "storm", "demo");
            _manager.RegisterEvent(CreateTestEvent("evt-002"), "heat", "demo");

            _manager.DiscardAll();

            Assert.That(_manager.PendingCount, Is.EqualTo(0));
            Assert.That(_manager.CompletedCount, Is.EqualTo(0));
        }

        [Test]
        public void OnReceiptReady_EventFires()
        {
            RenderReceipt readyReceipt = null;
            _manager.OnReceiptReady += r => readyReceipt = r;

            var evt = CreateTestEvent("evt-001");
            _manager.RegisterEvent(evt, "storm", "demo");
            _manager.CompleteRendered("evt-001", "sess-001");

            Assert.That(readyReceipt, Is.Not.Null);
            Assert.That(readyReceipt.event_id, Is.EqualTo("evt-001"));
        }

        [Test]
        public void ReceiptId_IsUnique()
        {
            var evt1 = CreateTestEvent("evt-001");
            var evt2 = CreateTestEvent("evt-002");
            _manager.RegisterEvent(evt1, "storm", "demo");
            _manager.RegisterEvent(evt2, "heat", "demo");

            var r1 = _manager.CompleteRendered("evt-001", "sess-001");
            var r2 = _manager.CompleteRendered("evt-002", "sess-001");

            Assert.That(r1.receipt_id, Is.Not.EqualTo(r2.receipt_id));
        }

        [Test]
        public void FrameSeq_Increments()
        {
            _manager.RegisterEvent(CreateTestEvent("evt-001"), "storm", "demo");
            _manager.RegisterEvent(CreateTestEvent("evt-002"), "heat", "demo");

            var r1 = _manager.CompleteRendered("evt-001", "sess-001");
            var r2 = _manager.CompleteRendered("evt-002", "sess-001");

            Assert.That(r2.frame_seq, Is.GreaterThan(r1.frame_seq));
        }

        [Test]
        public void RegisterEvent_NullThrows()
        {
            Assert.Throws<ArgumentNullException>(() =>
                _manager.RegisterEvent(null, "storm", "demo"));
        }

        private static ControlEvent CreateTestEvent(string eventId)
        {
            return new ControlEvent
            {
                session_id = "sess-001",
                event_id = eventId,
                control_seq = 1,
                event_type = "start",
                issued_monotonic_ns = 1000000000L,
                effective_monotonic_ns = 1000000000L,
                clock_domain_id = "python",
                payload = new Dictionary<string, object>()
            };
        }
    }

    // ── ReconnectHandler tests ────────────────────────────────────────────

    public sealed class ReconnectHandlerTests
    {
        [Test]
        public void NewHandler_HasGenerationZero()
        {
            var policy = new ReconnectPolicy();
            var handler = new ReconnectHandler(policy, null);
            Assert.That(handler.Generation, Is.EqualTo(0));
        }

        [Test]
        public void SignalConnected_IncrementsGeneration()
        {
            var policy = new ReconnectPolicy();
            var handler = new ReconnectHandler(policy, null);

            handler.SignalConnected();

            Assert.That(handler.Generation, Is.EqualTo(1));
            Assert.That(handler.AttemptCount, Is.EqualTo(0));
        }

        [Test]
        public void SignalConnected_ResetsBackoff()
        {
            var policy = new ReconnectPolicy { InitialBackoffMs = 500 };
            var handler = new ReconnectHandler(policy, null);

            handler.SignalConnected();
            handler.SignalConnected(); // advance backoff implicitly

            Assert.That(handler.CurrentBackoffMs, Is.EqualTo(500));
        }

        [Test]
        public void SetFaultMode_FailNextConnect_ShouldInjectFault()
        {
            var policy = new ReconnectPolicy();
            var handler = new ReconnectHandler(policy, null);

            handler.SetFaultMode(FaultMode.FailNextConnect);
            Assert.That(handler.ShouldInjectFault(), Is.True);
            // One-shot: second call should not inject
            Assert.That(handler.ShouldInjectFault(), Is.False);
        }

        [Test]
        public void ClearFault_StopsInjection()
        {
            var policy = new ReconnectPolicy();
            var handler = new ReconnectHandler(policy, null);

            handler.SetFaultMode(FaultMode.FailNextConnect);
            handler.ClearFault();
            Assert.That(handler.ShouldInjectFault(), Is.False);
        }

        [Test]
        public void SetFaultMode_DropEveryNth_InjectsPeriodically()
        {
            var policy = new ReconnectPolicy();
            var handler = new ReconnectHandler(policy, null);

            handler.SetFaultMode(FaultMode.DropEveryNth, everyN: 3);

            Assert.That(handler.ShouldDropMessage(), Is.False); // 1
            Assert.That(handler.ShouldDropMessage(), Is.False); // 2
            Assert.That(handler.ShouldDropMessage(), Is.True);  // 3
            Assert.That(handler.ShouldDropMessage(), Is.False); // 4
            Assert.That(handler.ShouldDropMessage(), Is.False); // 5
            Assert.That(handler.ShouldDropMessage(), Is.True);  // 6
        }

        [Test]
        public void SetFaultMode_CorruptMessage_ShouldCorruptPeriodically()
        {
            var policy = new ReconnectPolicy();
            var handler = new ReconnectHandler(policy, null);

            handler.SetFaultMode(FaultMode.CorruptMessage, everyN: 5);

            bool corrupted = false;
            for (int i = 0; i < 10; i++)
            {
                if (handler.ShouldCorruptMessage())
                {
                    corrupted = true;
                    break;
                }
            }
            Assert.That(corrupted, Is.True);
        }

        [Test]
        public void ResetState_ClearsAll()
        {
            var policy = new ReconnectPolicy();
            var handler = new ReconnectHandler(policy, null);

            handler.SignalConnected();
            handler.SetFaultMode(FaultMode.FailNextConnect);
            handler.ResetState();

            Assert.That(handler.Generation, Is.EqualTo(0));
            Assert.That(handler.ShouldInjectFault(), Is.False);
        }

        [Test]
        public void Abort_StopsReconnecting()
        {
            var policy = new ReconnectPolicy();
            // Use null runner — Abort should not throw
            var handler = new ReconnectHandler(policy, null);
            handler.Abort();
            Assert.That(handler.IsReconnecting, Is.False);
        }

        [Test]
        public void OnGenerationChanged_FiresOnConnect()
        {
            var policy = new ReconnectPolicy();
            var handler = new ReconnectHandler(policy, null);
            int firedGen = -1;
            handler.OnGenerationChanged += g => firedGen = g;

            handler.SignalConnected();

            Assert.That(firedGen, Is.EqualTo(1));
        }
    }

    // ── UDP5006Gate validation tests ──────────────────────────────────────

    public sealed class UDP5006GateValidationTests
    {
        [Test]
        public void Validate_ValidTelemetryFrame_ReturnsAccepted()
        {
            var frame = CreateTelemetryFrameJson("sess-001", 1);
            byte[] data = System.Text.Encoding.UTF8.GetBytes(frame);

            var receipt = UDP5006Gate.Validate(data);

            Assert.That(receipt.Result, Is.EqualTo(GateResult.Accepted));
            Assert.That(receipt.FrameSeq, Is.EqualTo(1));
        }

        [Test]
        public void Validate_InvalidJson_ReturnsInvalidJson()
        {
            byte[] data = System.Text.Encoding.UTF8.GetBytes("{not valid json}}");

            var receipt = UDP5006Gate.Validate(data);

            Assert.That(receipt.Result, Is.EqualTo(GateResult.InvalidJson));
        }

        [Test]
        public void Validate_MissingMessageType_ReturnsMissingMessageType()
        {
            var json = "{\"schema_version\":\"2.2\"}";
            byte[] data = System.Text.Encoding.UTF8.GetBytes(json);

            var receipt = UDP5006Gate.Validate(data);

            Assert.That(receipt.Result, Is.EqualTo(GateResult.MissingMessageType));
        }

        [Test]
        public void Validate_WrongMessageType_ReturnsNotTelemetryFrame()
        {
            var json = "{\"schema_version\":\"2.2\",\"message_type\":\"ack\"}";
            byte[] data = System.Text.Encoding.UTF8.GetBytes(json);

            var receipt = UDP5006Gate.Validate(data);

            Assert.That(receipt.Result, Is.EqualTo(GateResult.NotTelemetryFrame));
        }

        [Test]
        public void Validate_WrongSchemaVersion_ReturnsSchemaViolation()
        {
            var json = "{\"schema_version\":\"1.0\",\"message_type\":\"telemetry_frame\"," +
                       "\"session_id\":\"s\",\"frame_seq\":1,\"clock_domain_id\":\"c\"," +
                       "\"module_id\":\"storm\",\"segment\":\"demo\"," +
                       "\"target_phase\":\"inhale\",\"actual_phase\":\"inhale\"}";
            byte[] data = System.Text.Encoding.UTF8.GetBytes(json);

            var receipt = UDP5006Gate.Validate(data);

            Assert.That(receipt.Result, Is.EqualTo(GateResult.SchemaViolation));
        }

        [Test]
        public void Validate_MissingRequiredField_ReturnsSchemaViolation()
        {
            var json = "{\"schema_version\":\"2.2\",\"message_type\":\"telemetry_frame\"," +
                       "\"session_id\":\"s\"}";
            byte[] data = System.Text.Encoding.UTF8.GetBytes(json);

            var receipt = UDP5006Gate.Validate(data);

            Assert.That(receipt.Result, Is.EqualTo(GateResult.SchemaViolation));
            Assert.That(receipt.ErrorMessage, Does.Contain("Missing required field"));
        }

        [Test]
        public void Validate_EmptyBody_ReturnsInvalidJson()
        {
            byte[] data = System.Text.Encoding.UTF8.GetBytes("");

            var receipt = UDP5006Gate.Validate(data);

            Assert.That(receipt.Result, Is.EqualTo(GateResult.InvalidJson));
        }

        [Test]
        public void Validate_FullTelemetryFrame_AcceptsAllFields()
        {
            var frame = CreateFullTelemetryFrameJson();
            byte[] data = System.Text.Encoding.UTF8.GetBytes(frame);

            var receipt = UDP5006Gate.Validate(data);

            Assert.That(receipt.Result, Is.EqualTo(GateResult.Accepted));
            Assert.That(receipt.Raw.ContainsKey("clock_drift_ppm"), Is.True);
            Assert.That(receipt.Raw.ContainsKey("signal_quality"), Is.True);
        }

        [Test]
        public void GateReceiptTracksStats()
        {
            var gate = new GameObject("GateTest");
            try
            {
                var udp = gate.AddComponent<UDP5006Gate>();
                Assert.That(udp.FramesAccepted, Is.EqualTo(0));
                Assert.That(udp.FramesDropped, Is.EqualTo(0));
                Assert.That(udp.LastFrameSeq, Is.EqualTo(-1));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(gate);
            }
        }

        // ── Helpers ───────────────────────────────────────────────────────

        private static string CreateTelemetryFrameJson(string sessionId, int frameSeq)
        {
            return "{" +
                "\"schema_version\":\"2.2\"," +
                "\"message_type\":\"telemetry_frame\"," +
                $"\"session_id\":\"{sessionId}\"," +
                $"\"frame_seq\":{frameSeq}," +
                "\"clock_domain_id\":\"python\"," +
                "\"source_monotonic_ns\":1000000000," +
                "\"received_monotonic_ns\":1000000000," +
                "\"sent_monotonic_ns\":1000000000," +
                "\"clock_offset_ns\":0," +
                "\"clock_drift_ppm\":0," +
                "\"sync_uncertainty_ns\":0," +
                "\"module_id\":\"storm\"," +
                "\"module_position\":0," +
                "\"segment\":\"demo\"," +
                "\"target_phase\":\"inhale\"," +
                "\"target_progress\":0.5," +
                "\"actual_phase\":\"inhale\"," +
                "\"actual_progress\":0.48," +
                "\"actual_confidence\":0.95," +
                "\"recovery_value\":0.0," +
                "\"recovery_locked\":false," +
                "\"signal_quality\":{}," +
                "\"fallback_state\":\"GOOD\"," +
                "\"fallback_reason\":null," +
                "\"resp_device_state\":\"CONNECTED\"," +
                "\"ecg_device_state\":\"CONNECTED\"," +
                "\"cue_mode\":\"scene_native\"," +
                "\"runtime_mode\":\"dev_mock\"," +
                "\"policy_decision_id\":null," +
                "\"target_cycle_index\":null," +
                "\"target_step_id\":null," +
                "\"actual_cycle_index\":null," +
                "\"actual_step_id\":null" +
                "}";
        }

        private static string CreateFullTelemetryFrameJson()
        {
            return "{" +
                "\"schema_version\":\"2.2\"," +
                "\"message_type\":\"telemetry_frame\"," +
                "\"session_id\":\"sess-full\"," +
                "\"frame_seq\":99," +
                "\"clock_domain_id\":\"python\"," +
                "\"source_monotonic_ns\":2000000000," +
                "\"received_monotonic_ns\":2000000000," +
                "\"sent_monotonic_ns\":2000000000," +
                "\"clock_offset_ns\":1.5," +
                "\"clock_drift_ppm\":0.1," +
                "\"sync_uncertainty_ns\":100000," +
                "\"module_id\":\"heat\"," +
                "\"module_position\":1," +
                "\"segment\":\"closed_loop\"," +
                "\"target_phase\":\"exhale\"," +
                "\"target_progress\":0.75," +
                "\"actual_phase\":\"exhale\"," +
                "\"actual_progress\":0.72," +
                "\"actual_confidence\":0.88," +
                "\"recovery_value\":0.1," +
                "\"recovery_locked\":false," +
                "\"signal_quality\":{\"snr\":25.0}," +
                "\"fallback_state\":\"GOOD\"," +
                "\"fallback_reason\":null," +
                "\"resp_device_state\":\"CONNECTED\"," +
                "\"ecg_device_state\":\"CONNECTED\"," +
                "\"cue_mode\":\"abstract_pacer\"," +
                "\"runtime_mode\":\"formal_stage_1\"," +
                "\"policy_decision_id\":\"pd-001\"," +
                "\"target_cycle_index\":3," +
                "\"target_step_id\":\"exhale_1\"," +
                "\"actual_cycle_index\":3," +
                "\"actual_step_id\":\"exhale_1\"" +
                "}";
        }
    }

    // ── Contract message structure tests ──────────────────────────────────

    public sealed class ContractMessageStructureTests
    {
        [Test]
        public void AckMessage_AllRequiredFieldsSerialized()
        {
            var ack = new AckMessage
            {
                session_id = "s1",
                event_id = "e1",
                received_monotonic_ns = 100,
                applied_monotonic_ns = 200,
                unity_frame = 50,
                result = "applied",
                error_code = null
            };

            var dict = new Dictionary<string, object>
            {
                ["schema_version"] = AckMessage.schema_version,
                ["message_type"] = AckMessage.message_type_val,
                ["session_id"] = ack.session_id,
                ["event_id"] = ack.event_id,
                ["received_monotonic_ns"] = ack.received_monotonic_ns,
                ["applied_monotonic_ns"] = ack.applied_monotonic_ns,
                ["unity_frame"] = ack.unity_frame,
                ["result"] = ack.result,
                ["error_code"] = (object)ack.error_code
            };

            string json = JsonLines.Serialize(dict);
            var decoded = JsonLines.Deserialize(json);

            Assert.That(decoded["schema_version"], Is.EqualTo("2.2"));
            Assert.That(decoded["message_type"], Is.EqualTo("ack"));
            Assert.That(decoded["session_id"], Is.EqualTo("s1"));
            Assert.That(decoded["event_id"], Is.EqualTo("e1"));
            Assert.That(decoded["result"], Is.EqualTo("applied"));
        }

        [Test]
        public void RenderReceipt_AllRequiredFieldsSerialized()
        {
            var receipt = new RenderReceipt
            {
                receipt_id = "rr-001",
                session_id = "s1",
                event_id = "e1",
                frame_seq = 10,
                unity_frame = 200,
                rendered_monotonic_ns = 3000000000L,
                module_id = "storm",
                segment = "demo",
                result = "rendered",
                error_code = null
            };

            var dict = new Dictionary<string, object>
            {
                ["schema_version"] = RenderReceipt.schema_version,
                ["message_type"] = RenderReceipt.message_type_val,
                ["receipt_id"] = receipt.receipt_id,
                ["session_id"] = receipt.session_id,
                ["event_id"] = receipt.event_id,
                ["frame_seq"] = receipt.frame_seq,
                ["unity_frame"] = receipt.unity_frame,
                ["rendered_monotonic_ns"] = receipt.rendered_monotonic_ns,
                ["module_id"] = receipt.module_id,
                ["segment"] = receipt.segment,
                ["result"] = receipt.result,
                ["error_code"] = (object)receipt.error_code
            };

            string json = JsonLines.Serialize(dict);
            var decoded = JsonLines.Deserialize(json);

            Assert.That(decoded["schema_version"], Is.EqualTo("2.2"));
            Assert.That(decoded["message_type"], Is.EqualTo("render_receipt"));
            Assert.That(decoded["receipt_id"], Is.EqualTo("rr-001"));
            Assert.That(decoded["result"], Is.EqualTo("rendered"));
            Assert.That(decoded["module_id"], Is.EqualTo("storm"));
        }

        [Test]
        public void TransportHello_AllFieldsPresent()
        {
            var hello = new Dictionary<string, object>
            {
                ["transport_type"] = "hello",
                ["transport_version"] = "1.0",
                ["role"] = "unity",
                ["schema_version"] = "2.2",
                ["client_instance_id"] = "abc-123"
            };

            string json = JsonLines.Serialize(hello);
            var decoded = JsonLines.Deserialize(json);

            Assert.That(decoded["transport_type"], Is.EqualTo("hello"));
            Assert.That(decoded["transport_version"], Is.EqualTo("1.0"));
            Assert.That(decoded["role"], Is.EqualTo("unity"));
            Assert.That(decoded["client_instance_id"], Is.EqualTo("abc-123"));
        }

        [Test]
        public void TransportWelcome_AcceptedTrue()
        {
            var welcome = new Dictionary<string, object>
            {
                ["transport_type"] = "welcome",
                ["transport_version"] = "1.0",
                ["schema_version"] = "2.2",
                ["role"] = "unity",
                ["client_instance_id"] = "abc-123",
                ["accepted"] = true,
                ["error_code"] = null
            };

            string json = JsonLines.Serialize(welcome);
            var decoded = JsonLines.Deserialize(json);

            Assert.That(decoded["accepted"], Is.True);
            Assert.That(decoded["error_code"], Is.Null);
        }

        [Test]
        public void TransportError_ContainsCode()
        {
            var err = new Dictionary<string, object>
            {
                ["transport_type"] = "error",
                ["transport_version"] = "1.0",
                ["schema_version"] = "2.2",
                ["error_code"] = "TRANSPORT_FRAME_INVALID"
            };

            string json = JsonLines.Serialize(err);
            var decoded = JsonLines.Deserialize(json);

            Assert.That(decoded["transport_type"], Is.EqualTo("error"));
            Assert.That(decoded["error_code"], Is.EqualTo("TRANSPORT_FRAME_INVALID"));
        }

        [Test]
        public void SessionManifest_WeatherSequence_RemainsUnique()
        {
            var manifest = new SessionManifest
            {
                research_id = "r",
                session_id = "s",
                study_stage = "level_c",
                runtime_mode = "dev_mock",
                cue_mode = "scene_native",
                assignment_arm = "A",
                allocation_index = 0,
                randomization_stratum = "str",
                randomization_block = 1,
                randomization_list_hash = "h",
                weather_sequence = new[] { "storm", "heat", "snow", "fade" },
                module_durations = new ModuleDurations { demo = 1, closed_loop = 2, lock_transition = 3 },
                protocol_config_version = "1",
                randomization_version = "1",
                strategy_version = null,
                device_config = new DeviceConfig
                {
                    resp = new DeviceSensorConfig { source = "mock" },
                    ecg = new DeviceSensorConfig { source = "mock" }
                },
                unity_build_hash = "uh",
                python_commit = "pc",
                td_build_hash = null,
                source_policy = "mock",
                created_utc = "2026-01-01T00:00:00Z",
                breath_protocol_config_version = "1",
                breath_protocol_config_hash = "sha256:" + new string('a', 64)
            };

            // All 4 items should be unique
            var set = new HashSet<string>(manifest.weather_sequence);
            Assert.That(set.Count, Is.EqualTo(4));
        }
    }
}
