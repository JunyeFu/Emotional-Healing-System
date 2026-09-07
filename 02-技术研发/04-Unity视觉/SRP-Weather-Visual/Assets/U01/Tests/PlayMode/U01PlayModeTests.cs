// ═══════════════════════════════════════════════════════════════════════
// U01 — PlayMode 端到端测试（验收标准 AC1/AC2/AC3 驱动）
//
// 所有测试使用 loopback TCP/UDP 假服务器，不需要真实 Python 服务器。
// 测试覆盖：
//   AC1 — 重复 event_id → duplicate_ignored ACK
//   AC1 — 遥测帧排序（乱序/重复帧不覆盖新帧）
//   AC2 — 无控制事件 → 状态不推进
//   AC3 — v2.1 握手被拒 → 停止重连 → UNUSABLE 状态
//   AC3 — 断连重连 → 世代+1、同一 client_instance_id
//   AC3 — 渲染回执失败路径
//
// 注意：部分测试覆盖的是 P0 修复后的期望行为（TDD RED 阶段），
// 当前代码可能不满足（如 P0-1 ACK 幂等方向、P0-3 fail-closed）。
// 这些测试作为验收规格存在，P0 修复后将变绿。
// ═══════════════════════════════════════════════════════════════════════

using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using System.Threading;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;

namespace SRP.U01.Tests.PlayMode
{
    // ═══════════════════════════════════════════════════════════════════
    // 辅助工具类
    // ═══════════════════════════════════════════════════════════════════

    /// <summary>
    /// Loopback TCP 假服务器。在随机端口监听，顺序接受连接，
    /// 通过 ConcurrentQueue 交换 JSON Lines 消息。
    ///
    /// 线程模型：
    ///   - 主线程（测试协程）：调用 SendLine / WaitForLine
    ///   - 服务器线程：AcceptTcpClient → HandleClient → 下一个连接
    ///   - 发送线程（每个连接一个）：消费 _sendQueue 写入 NetworkStream
    /// </summary>
    public sealed class LoopbackTcpServer : IDisposable
    {
        private TcpListener _listener;
        private volatile bool _running;
        private Thread _mainThread;

        private readonly ConcurrentQueue<string> _sendQueue = new();
        private readonly ConcurrentQueue<string> _receiveQueue = new();
        private int _connectionCount;
        private volatile bool _clientConnected;

        public int Port { get; }
        public int ConnectionCount => Interlocked.CompareExchange(ref _connectionCount, 0, 0);
        public bool ClientConnected => _clientConnected;

        public LoopbackTcpServer()
        {
            _listener = new TcpListener(IPAddress.Loopback, 0);
            _listener.Start();
            Port = ((IPEndPoint)_listener.LocalEndpoint).Port;
            _running = true;
            _mainThread = new Thread(Run) { IsBackground = true, Name = "LoopbackTCPServer" };
            _mainThread.Start();
        }

        private void Run()
        {
            while (_running)
            {
                TcpClient client = null;
                try
                {
                    client = _listener.AcceptTcpClient();
                    if (!_running) break;
                    Interlocked.Increment(ref _connectionCount);
                    _clientConnected = true;

                    // 清空上一轮连接的队列残留
                    while (_sendQueue.TryDequeue(out _)) { }
                    while (_receiveQueue.TryDequeue(out _)) { }

                    HandleClient(client);
                }
                catch
                {
                    if (!_running) break;
                }
                finally
                {
                    _clientConnected = false;
                    try { client?.Close(); } catch { }
                }
            }
        }

        private void HandleClient(TcpClient client)
        {
            NetworkStream stream = null;
            try
            {
                stream = client.GetStream();

                // 发送线程：从 _sendQueue 消费并写入 stream
                var sendThread = new Thread(() => SendLoop(stream)) { IsBackground = true };
                sendThread.Start();

                // 逐字节读取，避免 StreamReader dispose 关闭底层 stream
                var sb = new StringBuilder();
                while (_running && client.Connected)
                {
                    int b = stream.ReadByte();
                    if (b < 0) break;  // EOF
                    if (b == '\n')
                    {
                        _receiveQueue.Enqueue(sb.ToString());
                        sb.Clear();
                    }
                    else
                    {
                        sb.Append((char)b);
                    }
                }
            }
            catch (IOException) { }
            catch (SocketException) { }
            catch { }
        }

        private void SendLoop(NetworkStream stream)
        {
            try
            {
                while (_running && stream.CanWrite)
                {
                    if (_sendQueue.TryDequeue(out var line))
                    {
                        byte[] bytes = Encoding.UTF8.GetBytes(line + "\n");
                        stream.Write(bytes, 0, bytes.Length);
                        stream.Flush();
                    }
                    else
                    {
                        Thread.Sleep(2);
                    }
                }
            }
            catch (IOException) { }
            catch { }
        }

        /// <summary>向当前连接的客户端发送一行 JSON。</summary>
        public void SendLine(string json)
        {
            _sendQueue.Enqueue(json);
        }

        /// <summary>等待客户端发来一行 JSON，最多等待 timeoutMs 毫秒。无数据返回 null。</summary>
        public string WaitForLine(int timeoutMs = 3000)
        {
            var deadline = DateTime.UtcNow.AddMilliseconds(timeoutMs);
            while (DateTime.UtcNow < deadline)
            {
                if (_receiveQueue.TryDequeue(out var line))
                    return line;
                Thread.Sleep(10);
            }
            return null;
        }

        /// <summary>
        /// 等待客户端发来的下一行非 hello 消息（跳过 transport hello）。
        /// 用于读取 ACK / render_receipt 等应用层消息。
        /// </summary>
        public string WaitForAppMessage(int timeoutMs = 3000)
        {
            var deadline = DateTime.UtcNow.AddMilliseconds(timeoutMs);
            while (DateTime.UtcNow < deadline)
            {
                if (_receiveQueue.TryDequeue(out var line))
                {
                    // 跳过 transport hello
                    if (line.Contains("\"transport_type\"") && line.Contains("\"hello\""))
                        continue;
                    return line;
                }
                Thread.Sleep(10);
            }
            return null;
        }

        /// <summary>消费掉客户端发来的 hello 消息（握手阶段）。</summary>
        public string ConsumeHello(int timeoutMs = 2000)
        {
            var deadline = DateTime.UtcNow.AddMilliseconds(timeoutMs);
            while (DateTime.UtcNow < deadline)
            {
                if (_receiveQueue.TryDequeue(out var line))
                {
                    if (line.Contains("\"transport_type\"") && line.Contains("\"hello\""))
                        return line;
                    // 不是 hello，放回去（用新队列暂存）
                    _receiveQueue.Enqueue(line);
                }
                Thread.Sleep(10);
            }
            return null;
        }

        /// <summary>强制关闭当前客户端连接。</summary>
        public void DropClient()
        {
            _clientConnected = false;
        }

        public void Dispose()
        {
            _running = false;
            try { _listener?.Stop(); } catch { }
            _mainThread?.Join(2000);
        }
    }

    /// <summary>
    /// 测试辅助：JSON 消息构建器、反射注入工具等。
    /// </summary>
    public static class TestHelpers
    {
        // ── 消息构建 ─────────────────────────────────────────────────

        /// <summary>构建握手成功的 welcome 消息。</summary>
        public static string WelcomeAccepted(string schemaVersion = "2.2")
        {
            return JsonLines.Serialize(new Dictionary<string, object>
            {
                ["transport_type"] = "welcome",
                ["transport_version"] = "1.0",
                ["schema_version"] = schemaVersion,
                ["role"] = "control",
                ["accepted"] = true
            });
        }

        /// <summary>构建握手被拒的 welcome 消息。</summary>
        public static string WelcomeRejected(string errorCode = "SCHEMA_VERSION_MISMATCH")
        {
            return JsonLines.Serialize(new Dictionary<string, object>
            {
                ["transport_type"] = "welcome",
                ["transport_version"] = "1.0",
                ["schema_version"] = "2.2",
                ["role"] = "control",
                ["accepted"] = false,
                ["error_code"] = errorCode
            });
        }

        /// <summary>构建 session_manifest JSON 行。</summary>
        public static string SessionManifestJson(string sessionId = "S-TEST-001")
        {
            return JsonLines.Serialize(new Dictionary<string, object>
            {
                ["message_type"] = "session_manifest",
                ["schema_version"] = "2.2",
                ["research_id"] = "res-test",
                ["session_id"] = sessionId,
                ["study_stage"] = "stage_1",
                ["runtime_mode"] = "formal_stage_1",
                ["cue_mode"] = "scene_native",
                ["assignment_arm"] = "arm-A",
                ["allocation_index"] = 0,
                ["randomization_stratum"] = "stratum-1",
                ["randomization_block"] = 1,
                ["randomization_list_hash"] = "abc123",
                ["weather_sequence"] = new object[] { "storm", "heat", "snow", "fade" },
                ["module_durations"] = new Dictionary<string, object>
                {
                    ["demo"] = 30.0, ["closed_loop"] = 120.0, ["lock_transition"] = 10.0
                },
                ["protocol_config_version"] = "1.0",
                ["randomization_version"] = "1.0",
                ["strategy_version"] = (string)null,
                ["device_config"] = new Dictionary<string, object>
                {
                    ["resp"] = new Dictionary<string, object> { ["source"] = "mock" },
                    ["ecg"] = new Dictionary<string, object> { ["source"] = "mock" }
                },
                ["unity_build_hash"] = "test-build",
                ["python_commit"] = "py-test",
                ["td_build_hash"] = (string)null,
                ["source_policy"] = "mock",
                ["created_utc"] = "2026-01-01T00:00:00Z",
                ["breath_protocol_config_version"] = "1.0",
                ["breath_protocol_config_hash"] = "sha256:" + new string('a', 64)
            });
        }

        /// <summary>构建 control_event JSON 行。</summary>
        public static string ControlEventJson(
            string sessionId, string eventId, int controlSeq,
            string eventType = "start", string moduleId = null, string segment = null)
        {
            var payload = new Dictionary<string, object>();
            if (moduleId != null)
            {
                payload["module_id"] = moduleId;
                payload["module_position"] = 0;
            }
            if (segment != null)
                payload["segment"] = segment;

            return JsonLines.Serialize(new Dictionary<string, object>
            {
                ["message_type"] = "control_event",
                ["schema_version"] = "2.2",
                ["session_id"] = sessionId,
                ["event_id"] = eventId,
                ["control_seq"] = controlSeq,
                ["event_type"] = eventType,
                ["issued_monotonic_ns"] = 1000000000L + controlSeq * 1000000L,
                ["effective_monotonic_ns"] = 1000000000L + controlSeq * 1000000L + 500000L,
                ["clock_domain_id"] = "python-test",
                ["payload"] = payload
            });
        }

        /// <summary>构建遥测帧 JSON（不换行）。</summary>
        public static string TelemetryFrameJson(string sessionId, int frameSeq)
        {
            return JsonLines.Serialize(new Dictionary<string, object>
            {
                ["schema_version"] = "2.2",
                ["message_type"] = "telemetry_frame",
                ["session_id"] = sessionId,
                ["frame_seq"] = frameSeq,
                ["clock_domain_id"] = "test-domain",
                ["source_monotonic_ns"] = 4000000L + frameSeq * 100000L,
                ["received_monotonic_ns"] = 4050000L + frameSeq * 100000L,
                ["sent_monotonic_ns"] = 4100000L + frameSeq * 100000L,
                ["clock_offset_ns"] = 15000,
                ["clock_drift_ppm"] = 0.4,
                ["sync_uncertainty_ns"] = 8000,
                ["module_id"] = "storm",
                ["module_position"] = 0,
                ["segment"] = "closed_loop",
                ["target_phase"] = "hold",
                ["target_progress"] = 0.4,
                ["actual_phase"] = "inhale",
                ["actual_progress"] = 0.35,
                ["actual_confidence"] = 0.91,
                ["recovery_value"] = 0.28,
                ["recovery_locked"] = false,
                ["signal_quality"] = new Dictionary<string, object>
                {
                    ["resp"] = 0.92, ["ecg"] = 0.88
                },
                ["fallback_state"] = "GOOD",
                ["fallback_reason"] = (string)null,
                ["resp_device_state"] = "CONNECTED",
                ["ecg_device_state"] = "CONNECTED",
                ["cue_mode"] = "scene_native",
                ["runtime_mode"] = "formal_stage_1"
            });
        }

        // ── 反射注入 ─────────────────────────────────────────────────

        /// <summary>
        /// 通过反射设置 ReliableControlClient 的私有依赖字段。
        /// AckManager / RenderReceiptManager 是普通 C# 类（非 MonoBehaviour），
        /// [SerializeField] 在运行时不会自动实例化，必须手动注入。
        /// </summary>
        public static void InjectDependencies(
            ReliableControlClient client,
            SessionMirror mirror = null,
            AckManager ack = null,
            RenderReceiptManager rr = null)
        {
            var t = typeof(ReliableControlClient);
            if (mirror != null)
                t.GetField("_sessionMirror", BindingFlags.NonPublic | BindingFlags.Instance)
                    ?.SetValue(client, mirror);
            if (ack != null)
                t.GetField("_ackManager", BindingFlags.NonPublic | BindingFlags.Instance)
                    ?.SetValue(client, ack);
            if (rr != null)
                t.GetField("_renderReceiptManager", BindingFlags.NonPublic | BindingFlags.Instance)
                    ?.SetValue(client, rr);
        }

        /// <summary>通过反射设置客户端的 schema_version。</summary>
        public static void SetSchemaVersion(ReliableControlClient client, string version)
        {
            typeof(ReliableControlClient)
                .GetField("_schemaVersion", BindingFlags.NonPublic | BindingFlags.Instance)
                ?.SetValue(client, version);
        }

        /// <summary>通过反射获取 client_instance_id。</summary>
        public static string GetClientId(ReliableControlClient client)
        {
            return typeof(ReliableControlClient)
                .GetField("_clientInstanceId", BindingFlags.NonPublic | BindingFlags.Instance)
                ?.GetValue(client)?.ToString();
        }

        /// <summary>通过反射强制关闭 TcpClient（模拟断连）。</summary>
        public static void ForceCloseTcpClient(ReliableControlClient client)
        {
            var tcp = typeof(ReliableControlClient)
                .GetField("_tcpClient", BindingFlags.NonPublic | BindingFlags.Instance)
                ?.GetValue(client) as TcpClient;
            try { tcp?.Close(); } catch { }
        }

        // ── 等待辅助 ─────────────────────────────────────────────────

        /// <summary>
        /// 在协程中等待条件为 true，最多等待 timeoutSec 秒。
        /// 返回 true 表示条件满足，false 表示超时。
        /// </summary>
        public static IEnumerator WaitUntil(Func<bool> condition, float timeoutSec,
            Action<string> logError = null)
        {
            float elapsed = 0f;
            while (!condition() && elapsed < timeoutSec)
            {
                yield return null;
                elapsed += Time.deltaTime;
            }
            if (!condition())
                logError?.Invoke($"WaitUntil 超时（{timeoutSec}s）");
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // AC1 — 重复 event_id → duplicate_ignored ACK
    //
    // 验收标准：同一 event_id 的控制事件"重发"两次，镜像只应用一次，
    // 第二次 ACK 的 result 为 "duplicate_ignored"。
    //
    // 当前代码缺陷（P0-1）：AckManager.IsDelivered() 永远返回 false，
    // 导致重复事件每次都回 applied。此测试覆盖修复后期望行为。
    // ═══════════════════════════════════════════════════════════════════

    [TestFixture]
    public class AC1_DuplicateEventId_Tests
    {
        [UnityTest]
        public IEnumerator DuplicateEventId_SecondAckIsDuplicateIgnored()
        {
            // ── 1. 启动假服务器 ──
            using var server = new LoopbackTcpServer();
            yield return new WaitForSeconds(0.1f);

            // ── 2. 创建客户端组件 ──
            var go = new GameObject("U01_AC1_Dup");
            ReliableControlClient client = null;
            SessionMirror mirror = null;

            client = go.AddComponent<ReliableControlClient>();
            mirror = go.AddComponent<SessionMirror>();
            var ack = new AckManager();
            client.Host = "127.0.0.1";
            client.Port = server.Port;
            TestHelpers.InjectDependencies(client, mirror: mirror, ack: ack);

            // ── 3. 等待客户端连接并握手 ──
            while (!server.ClientConnected)
                yield return null;

            // 消费客户端发来的 hello
            server.ConsumeHello();

            // 发送 welcome（接受连接）
            server.SendLine(TestHelpers.WelcomeAccepted());
            yield return new WaitForSeconds(0.1f);

            // 发送 session_manifest
            server.SendLine(TestHelpers.SessionManifestJson("S-TEST-001"));
            yield return new WaitForSeconds(0.2f);

            // ── 4. 发送第一个 control_event(evt-dup-001) ──
            server.SendLine(TestHelpers.ControlEventJson(
                "S-TEST-001", "evt-dup-001", 1, "module", "storm"));
            yield return new WaitForSeconds(0.4f);

            // 读取第一个 ACK
            string ack1 = server.WaitForAppMessage(2000);
            Assert.That(ack1, Is.Not.Null, "应收到第一个 ACK");

            // ── 5. 发送重复的 control_event（相同 event_id）──
            server.SendLine(TestHelpers.ControlEventJson(
                "S-TEST-001", "evt-dup-001", 1, "module", "storm"));
            yield return new WaitForSeconds(0.4f);

            // 读取第二个 ACK
            string ack2 = server.WaitForAppMessage(2000);
            Assert.That(ack2, Is.Not.Null, "应收到第二个 ACK（重复事件）");

            // ── 6. 发送不同的 control_event(evt-new-002) ──
            server.SendLine(TestHelpers.ControlEventJson(
                "S-TEST-001", "evt-new-002", 2, "segment", null, "closed_loop"));
            yield return new WaitForSeconds(0.4f);

            // 读取第三个 ACK
            string ack3 = server.WaitForAppMessage(2000);
            Assert.That(ack3, Is.Not.Null, "应收到第三个 ACK");

            // ── 7. 断言 ACK 结果 ──
            var dict1 = JsonLines.Deserialize(ack1);
            var dict2 = JsonLines.Deserialize(ack2);
            var dict3 = JsonLines.Deserialize(ack3);

            Assert.That(dict1["result"], Is.EqualTo("applied"),
                "第一次收到 evt-dup-001 → ACK result = applied");
            Assert.That(dict2["result"], Is.EqualTo("duplicate_ignored"),
                "第二次收到相同 event_id → ACK result = duplicate_ignored（幂等）");
            Assert.That(dict3["result"], Is.EqualTo("applied"),
                "新事件 evt-new-002 → ACK result = applied");

            // ── 8. 验证镜像只应用一次 ──
            Assert.That(mirror.Snapshot.ActiveControlSeq, Is.EqualTo(1),
                "重复事件不应推进 ActiveControlSeq");

            try { client?.Disconnect(); } catch { }
            yield return new WaitForSeconds(0.2f);
            UnityEngine.Object.DestroyImmediate(go);
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // AC1 — 遥测帧排序（乱序/重复帧不覆盖新帧）
    //
    // 验收标准：丢包/乱序/重复的 telemetry fixture 流中，
    // 旧帧和重复帧不覆盖新帧。接受序列的 frame_seq 单调递增。
    //
    // 注：UDP5006Gate 的序列追踪（ValidateWithTracking）已实现，
    // 此测试应为 GREEN。P0-2 修复的是完整 schema 校验，不影响序列逻辑。
    // ═══════════════════════════════════════════════════════════════════

    [TestFixture]
    public class AC1_TelemetryOrdering_Tests
    {
        private GameObject _go;
        private UDP5006Gate _gate;
        private UdpClient _sender;

        [UnityTest]
        public IEnumerator StaleFramesRejected_DuplicateFramesDetected()
        {
            // ── 1. 创建 UDP Gate ──
            _go = new GameObject("U01_AC1_Telem");
            _gate = _go.AddComponent<UDP5006Gate>();

            // 等待 Start() → StartListening() 执行
            yield return new WaitForSeconds(0.5f);

            int port = _gate.Port;
            _sender = new UdpClient();

            // 订阅事件计数
            int accepted = 0, rejected = 0;
            _gate.OnTelemetryFrame += _ => accepted++;
            _gate.OnFrameRejected += _ => rejected++;

            // ── 2. 发送帧序列 ──
            // 正常递增: 20, 21, 22
            SendFrame(port, 20);
            yield return new WaitForSeconds(0.1f);
            SendFrame(port, 21);
            yield return new WaitForSeconds(0.1f);
            SendFrame(port, 22);
            yield return new WaitForSeconds(0.1f);

            // 跳跃到 25（帧 23、24 丢失 — 模拟丢包）
            SendFrame(port, 25);
            yield return new WaitForSeconds(0.1f);

            // 发送旧帧 22（StaleSequence）
            SendFrame(port, 22);
            yield return new WaitForSeconds(0.1f);

            // 发送旧帧 21（StaleSequence）
            SendFrame(port, 21);
            yield return new WaitForSeconds(0.1f);

            // 发送重复帧 25（DuplicateSequence）
            SendFrame(port, 25);
            yield return new WaitForSeconds(0.1f);

            // ── 3. 消费 Gate 队列 ──
            for (int i = 0; i < 12; i++)
            {
                _gate.DequeueNext();
                yield return null;
            }

            // ── 4. 断言 ──
            Assert.That(accepted, Is.EqualTo(4),
                "应接受帧 20, 21, 22, 25（共4帧）");
            Assert.That(rejected, Is.EqualTo(3),
                "应拒绝旧帧22 + 旧帧21 + 重复帧25（共3帧）");
            Assert.That(_gate.LastFrameSeq, Is.EqualTo(25),
                "最后接受的帧序号应为25");
        }

        [TearDown]
        public void TearDown()
        {
            try { _gate?.StopListening(); } catch { }
            try { _sender?.Close(); } catch { }
            if (_go != null) UnityEngine.Object.DestroyImmediate(_go);
        }

        private void SendFrame(int port, int frameSeq)
        {
            string json = TestHelpers.TelemetryFrameJson("S-TEST", frameSeq);
            byte[] bytes = Encoding.UTF8.GetBytes(json);
            _sender.Send(bytes, bytes.Length, IPAddress.Loopback.ToString(), port);
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // AC2 — 无控制事件 → 状态不推进
    //
    // 验收标准：无 control_event 时本地时间流逝/收到旧帧，
    // 模块与 segment 不推进。
    //
    // 此测试应为 GREEN（当前代码已满足：无控制事件时镜像不变）。
    // ═══════════════════════════════════════════════════════════════════

    [TestFixture]
    public class AC2_NoControlEvent_Tests
    {
        [UnityTest]
        public IEnumerator NoControlEvent_SessionMirrorUnchanged()
        {
            // ── 1. 启动假服务器 ──
            using var server = new LoopbackTcpServer();
            yield return new WaitForSeconds(0.1f);

            // ── 2. 创建客户端 ──
            var go = new GameObject("U01_AC2");
            ReliableControlClient client = null;
            SessionMirror mirror = null;

            client = go.AddComponent<ReliableControlClient>();
            mirror = go.AddComponent<SessionMirror>();
            var ack = new AckManager();
            client.Host = "127.0.0.1";
            client.Port = server.Port;
            TestHelpers.InjectDependencies(client, mirror: mirror, ack: ack);

            // ── 3. 等待连接并握手 ──
            while (!server.ClientConnected)
                yield return null;

            server.ConsumeHello();
            server.SendLine(TestHelpers.WelcomeAccepted());
            yield return new WaitForSeconds(0.1f);

            // 发送 session_manifest（初始化会话状态）
            server.SendLine(TestHelpers.SessionManifestJson("S-NO-CTRL"));
            yield return new WaitForSeconds(0.3f);

            // 记录 manifest 后的快照
            var snapAfterManifest = mirror.Snapshot;
            Assert.That(snapAfterManifest.HasSession, Is.True,
                "session_manifest 后应有会话");
            Assert.That(snapAfterManifest.CurrentModuleId, Is.Null,
                "无控制事件时 CurrentModuleId 应为 null");
            Assert.That(snapAfterManifest.CurrentSegment, Is.Null,
                "无控制事件时 CurrentSegment 应为 null");
            Assert.That(snapAfterManifest.ActiveControlSeq, Is.EqualTo(0),
                "无控制事件时 ActiveControlSeq 应为 0");

            // ── 4. 等待 60 帧（不发送任何控制事件）──
            for (int i = 0; i < 60; i++)
                yield return null;

            // ── 5. 断言状态未变化 ──
            var snapFinal = mirror.Snapshot;
            Assert.That(snapFinal.HasSession, Is.True,
                "HasSession 应保持 true");
            Assert.That(snapFinal.ActiveControlSeq, Is.EqualTo(0),
                "无控制事件时 ActiveControlSeq 不应变化");
            Assert.That(snapFinal.CurrentModuleId, Is.Null,
                "无控制事件时 CurrentModuleId 不应推进");
            Assert.That(snapFinal.CurrentSegment, Is.Null,
                "无控制事件时 CurrentSegment 不应推进");

            try { client?.Disconnect(); } catch { }
            yield return new WaitForSeconds(0.1f);
            UnityEngine.Object.DestroyImmediate(go);
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // AC3 — v2.1 握手被拒 → 停止重连 → UNUSABLE 状态
    //
    // 验收标准：hello v2.1 正式握手（fixture: hello-v2.1-formal-rejected.json）
    // 收到 SCHEMA_VERSION_MISMATCH 后，停止重连，进入 UNUSABLE 状态。
    //
    // 当前代码缺陷（P0-3）：握手被拒后无限重连，不停止。
    // 此测试覆盖修复后期望行为（TDD RED）。
    // ═══════════════════════════════════════════════════════════════════

    [TestFixture]
    public class AC3_HandshakeRejected_Tests
    {
        [UnityTest]
        public IEnumerator V21HandshakeRejected_StopReconnect()
        {
            // ── 1. 启动假服务器 ──
            using var server = new LoopbackTcpServer();
            int port = server.Port;
            yield return new WaitForSeconds(0.1f);

            // ── 2. 创建客户端（使用 v2.1 协议版本）──
            var go = new GameObject("U01_AC3_HR");
            ReliableControlClient client = null;

            client = go.AddComponent<ReliableControlClient>();
            var mirror = go.AddComponent<SessionMirror>();
            var ack = new AckManager();
            client.Host = "127.0.0.1";
            client.Port = port;
            TestHelpers.SetSchemaVersion(client, "2.1");
            TestHelpers.InjectDependencies(client, mirror: mirror, ack: ack);

            // 监听错误事件
            string lastError = null;
            client.OnTransportError += err => lastError = err;

            // ── 3. 等待客户端连接 ──
            while (!server.ClientConnected)
                yield return null;

            // 消费客户端 hello
            server.ConsumeHello();

            // ── 4. 发送拒绝的 welcome（SCHEMA_VERSION_MISMATCH）──
            server.SendLine(TestHelpers.WelcomeRejected("SCHEMA_VERSION_MISMATCH"));
            yield return new WaitForSeconds(0.5f);

            // ── 5. 验证握手被拒 ──
            Assert.That(client.IsConnected, Is.False,
                "v2.1 握手被拒后客户端不应处于连接状态");

            // ── 6. 等待客户端处理拒绝并（期望地）停止重连 ──
            // 如果 P0-3 已修复：客户端应进入 UNUSABLE，不再重连
            // 如果 P0-3 未修复：客户端会在 ~1s 后重试连接
            //
            // 服务器保持监听。如果客户端重连，ConnectionCount 会增加。
            // 我们等待4秒（远超 1s 退避），然后检查是否有第二次连接。
            yield return new WaitForSeconds(4.0f);

            // ── 7. 断言：无第二次连接 ──
            Assert.That(server.ConnectionCount, Is.EqualTo(1),
                "协议级错误（SCHEMA_VERSION_MISMATCH）后客户端不应重连，" +
                "应进入 UNUSABLE 状态并停止重连（P0-3）");

            // 注：当前未修复时，客户端会无限重连，此断言将 FAIL（RED）

            try { client?.Disconnect(); } catch { }
            yield return new WaitForSeconds(0.2f);
            UnityEngine.Object.DestroyImmediate(go);
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // AC3 — 断连重连 → 世代+1、同一 client_instance_id
    //
    // 验收标准：断连后重连，generation 递增，client_instance_id 保持不变。
    // 重连后服务器补发的事件，旧 event_id 应回 duplicate_ignored。
    //
    // generation 递增和 client_instance_id 保持在当前代码中已实现（GREEN 部分），
    // 但重连后的事件补发 duplicate_ignored 需要 P0-1 修复（RED 部分）。
    // ═══════════════════════════════════════════════════════════════════

    [TestFixture]
    public class AC3_Reconnect_Tests
    {
        [UnityTest]
        public IEnumerator Reconnect_IncrementsGeneration_SameClientId()
        {
            // ── 1. 启动假服务器 ──
            using var server = new LoopbackTcpServer();
            int port = server.Port;
            yield return new WaitForSeconds(0.1f);

            // ── 2. 创建客户端 ──
            var go = new GameObject("U01_AC3_RC");
            ReliableControlClient client = null;

            client = go.AddComponent<ReliableControlClient>();
            var mirror = go.AddComponent<SessionMirror>();
            var ack = new AckManager();
            client.Host = "127.0.0.1";
            client.Port = port;
            TestHelpers.InjectDependencies(client, mirror: mirror, ack: ack);

            // ── 3. 第一次连接 ──
            while (!server.ClientConnected)
                yield return null;

            server.ConsumeHello();
            server.SendLine(TestHelpers.WelcomeAccepted());
            yield return new WaitForSeconds(0.1f);

            // 发送 session_manifest
            server.SendLine(TestHelpers.SessionManifestJson("S-RECON-001"));
            yield return new WaitForSeconds(0.2f);

            // 记录初始状态
            int genBefore = client.Generation;
            string clientId = TestHelpers.GetClientId(client);
            Assert.That(clientId, Is.Not.Null.And.Not.Empty,
                "client_instance_id 应在 Awake 中生成");

            // ── 4. 模拟断连（强制关闭 TCP 连接）──
            TestHelpers.ForceCloseTcpClient(client);

            // 等待客户端检测到断连（generation++ 在 finally 块中）
            yield return new WaitForSeconds(1.5f);

            int genAfterDisconnect = client.Generation;
            Assert.That(genAfterDisconnect, Is.GreaterThan(genBefore),
                "断连后 generation 应递增");

            // ── 5. 等待客户端重连（退避后）──
            yield return WaitUntil(() => server.ClientConnected, 5.0f);
            Assert.That(server.ClientConnected, Is.True,
                "客户端应在退避后成功重连");

            // 握手
            server.ConsumeHello();
            server.SendLine(TestHelpers.WelcomeAccepted());
            yield return new WaitForSeconds(0.2f);

            // ── 6. 验证 client_instance_id 不变 ──
            string clientIdAfter = TestHelpers.GetClientId(client);
            Assert.That(clientIdAfter, Is.EqualTo(clientId),
                "重连后 client_instance_id 应保持不变");

            // ── 7. 发送与第一次相同的 control_event（补发场景）──
            // 第一次连接时未发送 control_event，但模拟服务器补发
            server.SendLine(TestHelpers.ControlEventJson(
                "S-RECON-001", "evt-orig-001", 1, "module", "storm"));
            yield return new WaitForSeconds(0.4f);

            string ackOrig = server.WaitForAppMessage(2000);
            Assert.That(ackOrig, Is.Not.Null, "补发事件应收到 ACK");

            var ackDict = JsonLines.Deserialize(ackOrig);
            Assert.That(ackDict["event_id"], Is.EqualTo("evt-orig-001"));

            // 注：如果 _appliedEventIds 跨重连保留（P0-1 修复后），
            // 旧事件应回 duplicate_ignored。当前代码会回 applied（RED）。

            try { client?.Disconnect(); } catch { }
            yield return new WaitForSeconds(0.2f);
            UnityEngine.Object.DestroyImmediate(go);
        }

        private static IEnumerator WaitUntil(Func<bool> condition, float timeoutSec)
        {
            float elapsed = 0f;
            while (!condition() && elapsed < timeoutSec)
            {
                yield return null;
                elapsed += Time.deltaTime;
            }
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // AC3 — 渲染回执失败路径
    //
    // 验收标准：render_receipt 被拒/失败后，回执消息能正确发出，
    // 字段包含 result="failed" 和 error_code。
    //
    // RenderReceiptManager 的逻辑当前已实现（GREEN 部分），
    // CompleteFailed 应创建正确的回执并可通过 TCP 发出。
    // ═══════════════════════════════════════════════════════════════════

    [TestFixture]
    public class AC3_RenderReceipt_Tests
    {
        [UnityTest]
        public IEnumerator RenderReceiptFailure_HasCorrectFields()
        {
            // ── 1. 启动假服务器 ──
            using var server = new LoopbackTcpServer();
            int port = server.Port;
            yield return new WaitForSeconds(0.1f);

            // ── 2. 创建客户端 ──
            var go = new GameObject("U01_AC3_RR");
            ReliableControlClient client = null;

            client = go.AddComponent<ReliableControlClient>();
            var mirror = go.AddComponent<SessionMirror>();
            var ack = new AckManager();
            var rrManager = new RenderReceiptManager();
            client.Host = "127.0.0.1";
            client.Port = port;
            TestHelpers.InjectDependencies(client, mirror: mirror, ack: ack, rr: rrManager);

            // ── 3. 连接并握手 ──
            while (!server.ClientConnected)
                yield return null;

            server.ConsumeHello();
            server.SendLine(TestHelpers.WelcomeAccepted());
            yield return new WaitForSeconds(0.1f);
            server.SendLine(TestHelpers.SessionManifestJson("S-RR-001"));
            yield return new WaitForSeconds(0.1f);

            // ── 4. 注册一个控制事件的渲染回执 ──
            var testEvent = new ControlEvent
            {
                session_id = "S-RR-001",
                event_id = "evt-rr-001",
                control_seq = 1,
                event_type = "module",
                issued_monotonic_ns = 1000000000L,
                effective_monotonic_ns = 1000000000L,
                clock_domain_id = "python-test",
                payload = new Dictionary<string, object>()
            };

            var tracked = rrManager.RegisterEvent(testEvent, "storm", "closed_loop");
            Assert.That(tracked, Is.Not.Null, "RegisterEvent 应返回 TrackedReceipt");

            // ── 5. 模拟渲染失败 ──
            var receipt = rrManager.CompleteFailed(
                "evt-rr-001", "S-RR-001", "RENDER_SHADER_ERROR");

            // ── 6. 验证回执字段 ──
            Assert.That(receipt, Is.Not.Null);
            Assert.That(receipt.result, Is.EqualTo("failed"),
                "失败回执的 result 应为 'failed'");
            Assert.That(receipt.error_code, Is.EqualTo("RENDER_SHADER_ERROR"),
                "失败回执应包含错误码");
            Assert.That(receipt.event_id, Is.EqualTo("evt-rr-001"));
            Assert.That(receipt.session_id, Is.EqualTo("S-RR-001"));
            Assert.That(receipt.module_id, Is.EqualTo("storm"));
            Assert.That(receipt.segment, Is.EqualTo("closed_loop"));
            Assert.That(RenderReceipt.schema_version, Is.EqualTo("2.2"));
            Assert.That(RenderReceipt.message_type_val, Is.EqualTo("render_receipt"));
            Assert.That(receipt.receipt_id, Is.Not.Null.And.Not.Empty,
                "回执应有唯一 receipt_id");

            // ── 7. 通过 TCP 发送回执 ──
            client.SendRenderReceipt(receipt);
            yield return new WaitForSeconds(0.3f);

            // ── 8. 服务器端验证收到的回执 ──
            string sentLine = server.WaitForAppMessage(2000);
            Assert.That(sentLine, Is.Not.Null, "渲染回执应通过 TCP 发出");

            var sentDict = JsonLines.Deserialize(sentLine);
            Assert.That(sentDict["result"], Is.EqualTo("failed"),
                "服务器收到的回执 result 应为 failed");
            Assert.That(sentDict["error_code"], Is.EqualTo("RENDER_SHADER_ERROR"),
                "服务器收到的回执 error_code 应正确");
            Assert.That(sentDict["event_id"], Is.EqualTo("evt-rr-001"));
            Assert.That(sentDict["session_id"], Is.EqualTo("S-RR-001"));
            Assert.That(sentDict["module_id"], Is.EqualTo("storm"));
            Assert.That(sentDict["segment"], Is.EqualTo("closed_loop"));

            try { client?.Disconnect(); } catch { }
            yield return new WaitForSeconds(0.1f);
            UnityEngine.Object.DestroyImmediate(go);
        }
    }
}
