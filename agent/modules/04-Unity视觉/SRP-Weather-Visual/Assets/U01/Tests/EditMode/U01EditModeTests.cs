using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using NUnit.Framework;
using UnityEngine;

namespace SRP.U01.Tests
{
    public sealed class U01EditModeTests
    {
        [Serializable] private sealed class GoldenTrace { public ControlEventDto[] control_events; }

        [Test]
        public void GoldenControlTraceIsMirroredWithoutLocalSequencing()
        {
            var trace = JsonUtility.FromJson<GoldenTrace>(File.ReadAllText(GoldenPath()));
            var mirror = new SessionMirror("2.1");

            foreach (var value in trace.control_events)
            {
                var raw = JsonUtility.ToJson(value);
                Assert.That(ProtocolCodec.TryParseControl(raw, "2.1", out var parsed, out var error), Is.True, error);
                Assert.That(mirror.ApplyControl(parsed, raw).Result, Is.EqualTo("applied"));
            }

            Assert.That(mirror.Status, Is.EqualTo(MirrorStatus.Completed));
            Assert.That(mirror.LastControlSeq, Is.EqualTo(19));
            Assert.That(mirror.ModuleId, Is.EqualTo("fade"));
            Assert.That(mirror.ModulePosition, Is.EqualTo(3));
            Assert.That(mirror.Segment, Is.EqualTo("lock_transition"));
        }

        [Test]
        public void ExactRetryIsIdempotentButAlteredDuplicateAndOldSequenceAreRejected()
        {
            var mirror = PreparedRunningMirror("2.2");
            var module = Control("2.2", 3, "module", "{\"module_id\":\"storm\",\"module_position\":0}");
            Assert.That(ProtocolCodec.TryParseControl(module, "2.2", out var parsed, out _), Is.True);
            Assert.That(mirror.ApplyControl(parsed, module).Result, Is.EqualTo("applied"));
            var duplicate = mirror.ApplyControl(parsed, module);
            Assert.That(duplicate.Result, Is.EqualTo("duplicate_ignored"));
            Assert.That(duplicate.ErrorCode, Is.EqualTo("DUPLICATE_CONTROL"));

            var changed = module.Replace("storm", "heat");
            Assert.That(ProtocolCodec.TryParseControl(changed, "2.2", out var altered, out _), Is.True);
            Assert.That(mirror.ApplyControl(altered, changed).ErrorCode, Is.EqualTo("DUPLICATE_EVENT_MISMATCH"));

            var stale = Control("2.2", 2, "pause", "{}").Replace(":control:000002", ":control:stale");
            Assert.That(ProtocolCodec.TryParseControl(stale, "2.2", out var old, out _), Is.True);
            Assert.That(mirror.ApplyControl(old, stale).ErrorCode, Is.EqualTo("CONTROL_SEQUENCE_STALE"));
            Assert.That(mirror.ModuleId, Is.EqualTo("storm"));
        }

        [Test]
        public void StaleAndMismatchedTelemetryCannotOverwriteLatestMirrorFrame()
        {
            var mirror = PreparedRunningMirror("2.2");
            Apply(mirror, Control("2.2", 3, "module", "{\"module_id\":\"storm\",\"module_position\":0}"));
            Apply(mirror, Control("2.2", 4, "segment", "{\"module_id\":\"storm\",\"module_position\":0,\"segment\":\"closed_loop\"}"));
            var lines = File.ReadAllLines(TelemetryPath());

            Assert.That(ProtocolCodec.TryParseTelemetry(lines[0], "2.2", out var first, out _), Is.True);
            Assert.That(ProtocolCodec.TryParseTelemetry(lines[1], "2.2", out var second, out _), Is.True);
            Assert.That(ProtocolCodec.TryParseTelemetry(lines[2], "2.2", out var otherModule, out _), Is.True);
            Assert.That(mirror.ApplyTelemetry(first).Result, Is.EqualTo("applied"));
            Assert.That(mirror.ApplyTelemetry(second).Result, Is.EqualTo("applied"));
            Assert.That(mirror.ApplyTelemetry(first).ErrorCode, Is.EqualTo("TELEMETRY_SEQUENCE_STALE"));
            Assert.That(mirror.ApplyTelemetry(otherModule).ErrorCode, Is.EqualTo("TELEMETRY_MIRROR_MISMATCH"));
            Assert.That(mirror.LastTelemetrySeq, Is.EqualTo(21));
            Assert.That(mirror.LatestTelemetry.actual_step_id, Is.EqualTo("exhale_1"));

            Apply(mirror, Control("2.2", 5, "end", "{\"reason_code\":\"COMPLETED\"}"));
            var completedJson = lines[1].Replace("\"frame_seq\":21", "\"frame_seq\":22");
            Assert.That(ProtocolCodec.TryParseTelemetry(completedJson, "2.2", out var completed, out _), Is.True);
            Assert.That(mirror.ApplyTelemetry(completed).Result, Is.EqualTo("applied"));

            var aborted = PreparedRunningMirror("2.2");
            Apply(aborted, Control("2.2", 3, "module", "{\"module_id\":\"storm\",\"module_position\":0}"));
            Apply(aborted, Control("2.2", 4, "segment", "{\"module_id\":\"storm\",\"module_position\":0,\"segment\":\"closed_loop\"}"));
            Apply(aborted, Control("2.2", 5, "abort", "{\"reason_code\":\"TEST_ABORT\"}"));
            Assert.That(aborted.ApplyTelemetry(first).ErrorCode, Is.EqualTo("TELEMETRY_SESSION_NOT_ACTIVE"));
        }

        [Test]
        public void FormalV21AndWrongHandshakeFailClosed()
        {
            var formalPrepare = Control("2.1", 1, "prepare", "{\"manifest\":{\"runtime_mode\":\"formal_stage_1\"}}");
            Assert.That(ProtocolCodec.TryParseControl(formalPrepare, "2.1", out _, out var error), Is.False);
            Assert.That(error, Is.EqualTo("FORMAL_V21_FORBIDDEN"));

            var welcome = "{\"transport_type\":\"welcome\",\"transport_version\":\"1.0\",\"schema_version\":\"2.1\",\"role\":\"unity\",\"client_instance_id\":\"U01-TEST\",\"accepted\":true,\"error_code\":null}";
            Assert.That(ProtocolCodec.ValidateWelcome(welcome, "2.2", "U01-TEST", out error), Is.False);
            Assert.That(error, Is.EqualTo("WELCOME_REJECTED"));
        }

        [Test]
        public void ReliableClientReconnectsAndKeepsTheSameIdentity()
        {
            var listener = new TcpListener(IPAddress.Loopback, 0);
            listener.Start();
            var port = ((IPEndPoint)listener.LocalEndpoint).Port;
            using var client = new ReliableControlClient("2.2", "U01-TEST", port);
            client.Start();

            foreach (var partialWelcome in new[] { false, true })
            {
                using var silent = listener.AcceptTcpClient();
                using var silentReader = new StreamReader(silent.GetStream(), Encoding.UTF8, false, 4096, true);
                Assert.That(silentReader.ReadLine(), Does.Contain("\"client_instance_id\":\"U01-TEST\""));
                var welcomeTimer = System.Diagnostics.Stopwatch.StartNew();
                if (partialWelcome)
                {
                    Thread.Sleep(400);
                    var bytes = Encoding.UTF8.GetBytes("{\"transport_type\":\"welcome\"");
                    silent.GetStream().Write(bytes, 0, bytes.Length);
                    silent.GetStream().Flush();
                }
                Assert.That(WaitUntil(() => silent.Client.Poll(0, SelectMode.SelectRead) && silent.Client.Available == 0), Is.True);
                Assert.That(welcomeTimer.ElapsedMilliseconds, Is.LessThan(800));
                Assert.That(WaitUntil(() => client.LastError == "CONTROL_CONNECTION_LOST"), Is.True);
            }

            for (var generation = 1; generation <= 2; generation++)
            {
                using var server = listener.AcceptTcpClient();
                using var reader = new StreamReader(server.GetStream(), Encoding.UTF8, false, 4096, true);
                using var writer = new StreamWriter(server.GetStream(), new UTF8Encoding(false), 4096, true) { NewLine = "\n" };
                Assert.That(reader.ReadLine(), Does.Contain("\"client_instance_id\":\"U01-TEST\""));
                writer.WriteLine("{\"transport_type\":\"welcome\",\"transport_version\":\"1.0\",\"schema_version\":\"2.2\",\"role\":\"unity\",\"client_instance_id\":\"U01-TEST\",\"accepted\":true,\"error_code\":null}");
                writer.Flush();
                Assert.That(WaitUntil(() => client.ConnectionGeneration == generation), Is.True);
                var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic;
                var activeSocket = (TcpClient)typeof(ReliableControlClient).GetField("client", flags)?.GetValue(client);
                Assert.That(activeSocket?.SendTimeout, Is.EqualTo(500));
                Assert.That(activeSocket?.ReceiveTimeout, Is.EqualTo(0));
                const string retriedEvent = "{\"event_id\":\"S-U01-TEST:control:000001\"}";
                Assert.That(client.Send(retriedEvent), Is.True);
                Assert.That(reader.ReadLine(), Is.EqualTo(retriedEvent));
                Assert.That(client.Send(new string('x', 1024 * 1024)), Is.False);
                Assert.That(client.LastError, Is.EqualTo("CONTROL_FRAME_TOO_LARGE"));
                if (generation == 1)
                {
                    server.GetStream().Write(new byte[] { 0xff, (byte)'\n' }, 0, 2);
                    server.GetStream().Flush();
                    Assert.That(WaitUntil(() => client.LastError == "CONTROL_ENCODING_INVALID"), Is.True);
                }
                else
                {
                    writer.Write(new string('x', 1024 * 1024 + 1));
                    writer.Flush();
                    Assert.That(WaitUntil(() => client.LastError == "CONTROL_FRAME_TOO_LARGE"), Is.True);
                }
            }

            listener.Stop();
            Assert.That(client.ConnectionGeneration, Is.EqualTo(2));
        }

        [Test]
        public void DisposeDoesNotWaitForABlockedSendLock()
        {
            var client = new ReliableControlClient("2.2", "U01-TEST");
            var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic;
            var sendLock = typeof(ReliableControlClient).GetField("sendLock", flags)?.GetValue(client);
            var lockEntered = new ManualResetEventSlim(false);
            var lockHolder = Task.Run(() =>
            {
                lock (sendLock)
                {
                    lockEntered.Set();
                    Thread.Sleep(1200);
                }
            });
            Assert.That(lockEntered.Wait(1000), Is.True);
            var timer = System.Diagnostics.Stopwatch.StartNew();
            Assert.That(client.Send("{}"), Is.False);
            Assert.That(timer.ElapsedMilliseconds, Is.LessThan(750));
            Assert.That(client.LastError, Is.EqualTo("CONTROL_SEND_TIMEOUT"));
            var dispose = Task.Run(client.Dispose);
            Assert.That(dispose.Wait(1000), Is.True);
            lockHolder.Wait();

            var writerLock = typeof(ReliableControlClient).GetField("writerLock", flags)?.GetValue(client);
            lockEntered.Reset();
            lockHolder = Task.Run(() =>
            {
                lock (writerLock)
                {
                    lockEntered.Set();
                    Thread.Sleep(1200);
                }
            });
            Assert.That(lockEntered.Wait(1000), Is.True);
            timer.Restart();
            Assert.That(client.Send("{}"), Is.False);
            Assert.That(timer.ElapsedMilliseconds, Is.LessThan(750));
            lockHolder.Wait();
        }

        [Test]
        public void DeliveryFactoryPreservesIdentityAndRejectsInvalidFailureReceipt()
        {
            var mirror = PreparedRunningMirror("2.2");
            var segment = Control("2.2", 3, "module", "{\"module_id\":\"storm\",\"module_position\":0}");
            Apply(mirror, segment);
            segment = Control("2.2", 4, "segment", "{\"module_id\":\"storm\",\"module_position\":0,\"segment\":\"demo\"}");
            Assert.That(ProtocolCodec.TryParseControl(segment, "2.2", out var message, out _), Is.True);
            var result = mirror.ApplyControl(message, segment);
            var ack = DeliveryFactory.CreateAck(message, result, 10, 11, 12);
            var receipt = DeliveryFactory.CreateReceipt(
                message, "unity-a", mirror.ModuleId, mirror.Segment, mirror.LastTelemetrySeq, 12, 13, "rendered");
            var sameInstance = DeliveryFactory.CreateReceipt(
                message, "unity-a", mirror.ModuleId, mirror.Segment, mirror.LastTelemetrySeq, 12, 13, "rendered");
            var otherInstance = DeliveryFactory.CreateReceipt(
                message, "unity-b", mirror.ModuleId, mirror.Segment, mirror.LastTelemetrySeq, 12, 13, "rendered");

            Assert.That(ack.event_id, Is.EqualTo(message.event_id));
            Assert.That(receipt.event_id, Is.EqualTo(message.event_id));
            Assert.That(receipt.session_id, Is.EqualTo(message.session_id));
            Assert.That(receipt.module_id, Is.EqualTo("storm"));
            Assert.That(sameInstance.receipt_id, Is.EqualTo(receipt.receipt_id));
            Assert.That(otherInstance.receipt_id, Is.Not.EqualTo(receipt.receipt_id));
            Assert.Throws<ArgumentException>(() => DeliveryFactory.CreateReceipt(
                message, "unity-a", mirror.ModuleId, mirror.Segment, mirror.LastTelemetrySeq, 12, 13, "failed"));
        }

        [Test]
        public void FailedOldConnectionIsDisposedWithoutTouchingNewGeneration()
        {
            using var client = new ReliableControlClient("2.2", "U01-TEST");
            var listener = new TcpListener(IPAddress.Loopback, 0);
            try
            {
                listener.Start();
                var port = ((IPEndPoint)listener.LocalEndpoint).Port;
                var active = new TcpClient(AddressFamily.InterNetwork);
                var accept = Task.Run(listener.AcceptTcpClient);
                active.Connect(IPAddress.Loopback, port);
                Assert.That(accept.Wait(2_000), Is.True);
                using var peer = accept.Result;
                peer.ReceiveTimeout = 2_000;
                var flags = BindingFlags.Instance | BindingFlags.NonPublic;
                typeof(ReliableControlClient).GetField("client", flags).SetValue(client, active);
                var stateType = typeof(ReliableControlClient).GetNestedType("ConnectionState", BindingFlags.NonPublic);
                var activeState = Activator.CreateInstance(stateType, new object[] { 2L, null });
                typeof(ReliableControlClient).GetField("connectionState", flags).SetValue(client, activeState);
                var captured = new TcpClient(AddressFamily.InterNetwork);
                var method = typeof(ReliableControlClient).GetMethod("FailConnection", flags);

                method.Invoke(client, new object[] { captured, 1L, "CONTROL_SEND_FAILED" });

                Assert.Throws<ObjectDisposedException>(() => captured.Connect(IPAddress.Loopback, 1));
                Assert.That(client.Connected, Is.True);
                Assert.That(typeof(ReliableControlClient).GetField("client", flags).GetValue(client), Is.SameAs(active));
                Assert.That(active.Client.Send(new byte[] { 7 }), Is.EqualTo(1));
                var received = new byte[1];
                Assert.That(peer.Client.Receive(received), Is.EqualTo(1));
                Assert.That(received[0], Is.EqualTo(7));
            }
            finally { listener.Stop(); }
        }

        [Test]
        public void IncomingFrameLimitIncludesLineFeed()
        {
            var readerMethod = typeof(ReliableControlClient).GetMethod(
                "ReadBoundedLine",
                BindingFlags.Static | BindingFlags.NonPublic,
                null,
                new[] { typeof(StreamReader) },
                null);
            string Read(int bodyBytes)
            {
                var bytes = Encoding.UTF8.GetBytes(new string('a', bodyBytes) + "\n");
                using var stream = new MemoryStream(bytes);
                using var reader = new StreamReader(stream, new UTF8Encoding(false, true));
                try { return (string)readerMethod.Invoke(null, new object[] { reader }); }
                catch (TargetInvocationException error) { throw error.InnerException; }
            }
            string ReadRaw(int bodyBytes)
            {
                var listener = new TcpListener(IPAddress.Loopback, 0);
                TcpClient receiver = null;
                Task sender = null;
                try
                {
                    listener.Start();
                    var port = ((IPEndPoint)listener.LocalEndpoint).Port;
                    var payload = Encoding.UTF8.GetBytes(new string('a', bodyBytes) + "\n");
                    var accept = Task.Run(listener.AcceptTcpClient);
                    sender = Task.Run(() =>
                    {
                        using var socket = new TcpClient(AddressFamily.InterNetwork);
                        socket.Connect(IPAddress.Loopback, port);
                        socket.GetStream().Write(payload, 0, payload.Length);
                    });
                    if (!accept.Wait(2_000)) throw new TimeoutException("TCP accept timed out");
                    receiver = accept.Result;
                    var rawMethod = typeof(ReliableControlClient).GetMethod(
                        "ReadBoundedLine",
                        BindingFlags.Static | BindingFlags.NonPublic,
                        null,
                        new[] { typeof(NetworkStream), typeof(TcpClient), typeof(int) },
                        null);
                    try
                    {
                        return (string)rawMethod.Invoke(
                            null, new object[] { receiver.GetStream(), receiver, 30_000 });
                    }
                    catch (TargetInvocationException error) { throw error.InnerException; }
                }
                finally
                {
                    receiver?.Dispose();
                    listener.Stop();
                    if (sender != null && !sender.Wait(2_000))
                        throw new TimeoutException("TCP sender did not stop");
                }
            }

            Assert.That(Read(1024 * 1024 - 1).Length, Is.EqualTo(1024 * 1024 - 1));
            Assert.Throws<InvalidDataException>(() => Read(1024 * 1024));
            Assert.That(ReadRaw(1024 * 1024 - 1).Length, Is.EqualTo(1024 * 1024 - 1));
            Assert.Throws<InvalidDataException>(() => ReadRaw(1024 * 1024));
        }

        [Test]
        public void V22TelemetryFixturesMatchTheAuthoritativeContract()
        {
            var root = ContractFixtureRoot();
            foreach (var path in Directory.GetFiles(Path.Combine(root, "valid"), "telemetry*.json"))
            {
                var json = File.ReadAllText(path);
                Assert.That(ProtocolCodec.TryParseTelemetry(json, "2.2", out _, out var error), Is.True,
                    Path.GetFileName(path) + ":" + error);
            }

            foreach (var path in Directory.GetFiles(Path.Combine(root, "invalid"), "telemetry*.json"))
            {
                var json = File.ReadAllText(path);
                Assert.That(ProtocolCodec.TryParseTelemetry(json, "2.2", out _, out _), Is.False,
                    Path.GetFileName(path));
            }

            using var reservation = new UdpClient(new IPEndPoint(IPAddress.Loopback, 0));
            var udpPort = ((IPEndPoint)reservation.Client.LocalEndPoint).Port;
            reservation.Close();
            using var receiver = new TelemetryReceiver(udpPort);
            receiver.Start();
            using var sender = new UdpClient();
            sender.Send(new byte[] { 0xff }, 1, new IPEndPoint(IPAddress.Loopback, udpPort));
            Assert.That(WaitUntil(() => receiver.LastError == "TELEMETRY_ENCODING_INVALID"), Is.True);
        }

        [Test]
        public void AckSerializationKeepsPythonContractNullSemantics()
        {
            var mirror = PreparedRunningMirror("2.2");
            var json = Control("2.2", 3, "module", "{\"module_id\":\"storm\",\"module_position\":0}");
            Assert.That(ProtocolCodec.TryParseControl(json, "2.2", out var message, out _), Is.True);
            var applied = mirror.ApplyControl(message, json);
            var duplicate = mirror.ApplyControl(message, json);

            Assert.That(ProtocolCodec.ToJson(DeliveryFactory.CreateAck(message, applied, 10, 11, 12)),
                Does.Contain("\"result\":\"applied\",\"error_code\":null"));
            Assert.That(ProtocolCodec.ToJson(DeliveryFactory.CreateAck(message, duplicate, 10, 11, 12)),
                Does.Contain("\"result\":\"duplicate_ignored\",\"error_code\":\"DUPLICATE_CONTROL\""));
            var escapedAck = DeliveryFactory.CreateAck(message, applied, 10, 11, 12);
            escapedAck.session_id = "S\nX\tY";
            var escaped = ProtocolCodec.ToJson(escapedAck);
            Assert.That(escaped, Does.Contain("S\\nX\\tY"));
            Assert.That(escaped, Does.Not.Contain("\n"));
        }

        [Test]
        public void NullableCycleIdentityIsPreservedAndNegativeCycleIsRejected()
        {
            var path = Path.Combine(ContractFixtureRoot(), "valid", "telemetry-actual-unavailable.json");
            var json = File.ReadAllText(path);
            Assert.That(ProtocolCodec.TryParseTelemetry(json, "2.2", out var value, out _), Is.True);
            Assert.That(value.TargetCycleIndex, Is.EqualTo(0));
            Assert.That(value.ActualCycleIndex, Is.Null);

            var negative = json.Replace("\"target_cycle_index\": 0", "\"target_cycle_index\": -1");
            Assert.That(ProtocolCodec.TryParseTelemetry(negative, "2.2", out _, out _), Is.False);
            var fractional = json.Replace("\"target_cycle_index\": 0", "\"target_cycle_index\": 0.5");
            Assert.That(ProtocolCodec.TryParseTelemetry(fractional, "2.2", out _, out _), Is.False);
            var roundedCycle = json.Replace("\"target_cycle_index\": 0", "\"target_cycle_index\": 1.0000000000000001");
            Assert.That(ProtocolCodec.TryParseTelemetry(roundedCycle, "2.2", out var roundedValue, out _), Is.True);
            Assert.That(roundedValue.TargetCycleIndex, Is.EqualTo(1));
            var roundedMaximum = json.Replace("\"target_cycle_index\": 0", "\"target_cycle_index\": 2147483647.0000001");
            Assert.That(ProtocolCodec.TryParseTelemetry(roundedMaximum, "2.2", out var maximumValue, out _), Is.True);
            Assert.That(maximumValue.TargetCycleIndex, Is.EqualTo(int.MaxValue));
            var underflowCycle = json.Replace("\"target_cycle_index\": 0", "\"target_cycle_index\": 1e-400");
            Assert.That(ProtocolCodec.TryParseTelemetry(underflowCycle, "2.2", out var underflowValue, out _), Is.True);
            Assert.That(underflowValue.TargetCycleIndex, Is.EqualTo(0));
            var underflowUnavailableProgress = json.Replace("\"actual_progress\": 0", "\"actual_progress\": 1e-400");
            Assert.That(ProtocolCodec.TryParseTelemetry(underflowUnavailableProgress, "2.2", out var progressValue, out _), Is.True);
            Assert.That(progressValue.actual_progress, Is.EqualTo(0));
        }

        [Test]
        public void V21TelemetryAndSharedStateRulesMatchTheAuthoritativeContract()
        {
            var root = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../05-通信协议/contracts/fixtures"));
            foreach (var path in Directory.GetFiles(Path.Combine(root, "valid"), "telemetry*.json"))
            {
                var json = File.ReadAllText(path);
                Assert.That(ProtocolCodec.TryParseTelemetry(json, "2.1", out _, out _), Is.False,
                    Path.GetFileName(path) + ": formal v2.1 must be rejected");
                var replay = json.Replace("\"runtime_mode\": \"formal_stage_1\"", "\"runtime_mode\": \"dev_replay\"");
                Assert.That(ProtocolCodec.TryParseTelemetry(replay, "2.1", out _, out var error), Is.True,
                    Path.GetFileName(path) + ":" + error);
            }

            foreach (var path in Directory.GetFiles(Path.Combine(root, "invalid"), "telemetry*.json"))
                Assert.That(ProtocolCodec.TryParseTelemetry(File.ReadAllText(path), "2.1", out _, out _), Is.False);

            var valid = File.ReadAllText(Path.Combine(ContractFixtureRoot(), "valid", "telemetry-fade-inhale-1.json"));
            Assert.That(ProtocolCodec.TryParseTelemetry(
                valid.Replace("\"received_monotonic_ns\": 4250000", "\"received_monotonic_ns\": 4150000"),
                "2.2", out _, out _), Is.False);
            Assert.That(ProtocolCodec.TryParseTelemetry(
                valid.Replace("\"fallback_state\": \"GOOD\"", "\"fallback_state\": \"DISCONNECTED\""),
                "2.2", out _, out _), Is.False);
            Assert.That(ProtocolCodec.TryParseTelemetry(valid.Replace("PD-0001", "PD-NaN"),
                "2.2", out _, out var stringError), Is.True, stringError);
            Assert.That(ProtocolCodec.TryParseTelemetry(valid.Replace("\"session_id\"", "\"\\u0073ession_id\""),
                "2.2", out _, out var escapedKeyError), Is.True, escapedKeyError);
            Assert.That(ProtocolCodec.TryParseTelemetry(valid.Replace("\"clock_drift_ppm\": 0.4", "\"clock_drift_ppm\": 1e309"),
                "2.2", out _, out _), Is.False);
            Assert.That(ProtocolCodec.TryParseTelemetry(valid.Replace("\"target_progress\": 0.4", "\"target_progress\": null"),
                "2.2", out _, out _), Is.False);
            Assert.That(ProtocolCodec.TryParseTelemetry(valid.Replace("\"target_progress\": 0.4", "\"target_progress\": 1.00000001"),
                "2.2", out _, out _), Is.False);
            Assert.That(ProtocolCodec.TryParseTelemetry(valid.Replace("\"frame_seq\": 22", "\"frame_seq\": 9223372036854775808"),
                "2.2", out _, out _), Is.False);
            var nestedNull = valid
                .Replace("\"fallback_reason\": null", "\"fallback_reason\": \"unexpected\"")
                .Replace("\"ecg\": 0.88", "\"ecg\": 0.88, \"fallback_reason\": null");
            Assert.That(ProtocolCodec.TryParseTelemetry(nestedNull, "2.2", out _, out _), Is.False);

        }

        [Test]
        public void ConfirmedReceiptSurvivesDuplicateControlWithoutMirrorDrift()
        {
            var mirror = PreparedRunningMirror("2.2");
            Apply(mirror, Control("2.2", 3, "module", "{\"module_id\":\"storm\",\"module_position\":0}"));
            var demoJson = Control("2.2", 4, "segment", "{\"module_id\":\"storm\",\"module_position\":0,\"segment\":\"demo\"}");
            Assert.That(ProtocolCodec.TryParseControl(demoJson, "2.2", out var demo, out _), Is.True);
            var applied = mirror.ApplyControl(demo, demoJson);
            var gate = new RenderReceiptGate("unity-test");
            gate.Register(demo, applied, mirror);
            gate.ObserveTelemetry(Telemetry(demo, 8), new ApplyResult("applied"));
            Assert.That(gate.TryConfirm(demo.event_id, 8, 9, 10, "rendered", null, out var original), Is.True);

            var repeatedJson = Control("2.2", 5, "segment", "{\"module_id\":\"storm\",\"module_position\":0,\"segment\":\"demo\"}");
            Assert.That(ProtocolCodec.TryParseControl(repeatedJson, "2.2", out var repeated, out _), Is.True);
            var repeatedResult = mirror.ApplyControl(repeated, repeatedJson);
            gate.Register(repeated, repeatedResult, mirror);
            Assert.That(gate.TryConfirm(repeated.event_id, 8, 10, 11, "rendered", null, out _), Is.False);
            gate.ObserveTelemetry(Telemetry(repeated, 9), new ApplyResult("applied"));

            var thirdJson = Control("2.2", 6, "segment", "{\"module_id\":\"storm\",\"module_position\":0,\"segment\":\"demo\"}");
            Assert.That(ProtocolCodec.TryParseControl(thirdJson, "2.2", out var third, out _), Is.True);
            var thirdResult = mirror.ApplyControl(third, thirdJson);
            gate.Register(third, thirdResult, mirror);
            gate.ObserveTelemetry(Telemetry(third, 10), new ApplyResult("applied"));
            Assert.That(gate.TryConfirm(repeated.event_id, 10, 10, 11, "rendered", null, out _), Is.False);
            Assert.That(gate.TryConfirm(third.event_id, 10, 10, 11, "rendered", null, out _), Is.True);
            var duplicate = mirror.ApplyControl(demo, demoJson);
            gate.Register(demo, duplicate, mirror);
            Assert.That(gate.TryGetConfirmed(demo.event_id, out var replayed), Is.True);
            Assert.That(replayed.receipt_id, Is.EqualTo(original.receipt_id));
            Assert.That(replayed.segment, Is.EqualTo("demo"));
            Assert.That(replayed.frame_seq, Is.EqualTo(8));
        }

        private static TelemetryFrameDto Telemetry(ControlEventDto message, long frameSeq) => new()
        {
            session_id = message.session_id,
            frame_seq = frameSeq,
            module_id = message.payload.module_id,
            segment = message.payload.segment
        };

        private static SessionMirror PreparedRunningMirror(string schema)
        {
            var mirror = new SessionMirror(schema);
            var runtime = schema == "2.1" ? "dev_replay" : "formal_stage_1";
            Apply(mirror, Control(schema, 1, "prepare", "{\"manifest\":{\"runtime_mode\":\"" + runtime + "\"}}"));
            Apply(mirror, Control(schema, 2, "start", "{\"resumed\":false}"));
            return mirror;
        }

        private static void Apply(SessionMirror mirror, string json)
        {
            Assert.That(ProtocolCodec.TryParseControl(json, mirror.SchemaVersion, out var value, out var error), Is.True, error);
            Assert.That(mirror.ApplyControl(value, json).Result, Is.EqualTo("applied"));
        }

        private static string Control(string schema, long seq, string type, string payload)
        {
            return "{\"schema_version\":\"" + schema + "\",\"message_type\":\"control_event\",\"session_id\":\"S-20260807-0001\",\"event_id\":\"S-20260807-0001:control:" + seq.ToString("000000") + "\",\"control_seq\":" + seq + ",\"event_type\":\"" + type + "\",\"issued_monotonic_ns\":0,\"effective_monotonic_ns\":0,\"clock_domain_id\":\"python:S-20260807-0001\",\"payload\":" + payload + "}";
        }

        private static bool WaitUntil(Func<bool> predicate)
        {
            for (var i = 0; i < 100; i++) { if (predicate()) return true; Thread.Sleep(20); }
            return false;
        }

        private static string GoldenPath() => Path.GetFullPath(Path.Combine(Application.dataPath, "../../../srp_session_core/fixtures/golden/four-module-trace-v1.json"));
        private static string TelemetryPath() => Path.GetFullPath(Path.Combine(Application.dataPath, "../../../05-通信协议/contracts/consumer-fixtures/v2.2/unity/phase-instance-stream.jsonl"));
        private static string ContractFixtureRoot() => Path.GetFullPath(Path.Combine(Application.dataPath, "../../../05-通信协议/contracts/fixtures-v2.2"));
    }
}
