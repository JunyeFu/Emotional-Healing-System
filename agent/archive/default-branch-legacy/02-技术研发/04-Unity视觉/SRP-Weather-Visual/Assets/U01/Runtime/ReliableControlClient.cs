using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Diagnostics;

namespace SRP.U01
{
    public sealed class ReliableControlClient : IDisposable
    {
        private const int MaxFrameBytes = 1024 * 1024;
        private const int SendTimeoutMs = 500;
        private readonly string schemaVersion;
        private readonly string clientInstanceId;
        private readonly int port;
        private readonly ConcurrentQueue<string> incoming = new();
        private readonly object writerLock = new();
        private readonly object sendLock = new();
        private volatile bool running;
        private ConnectionState connectionState = new(0, null);
        private int connectionGeneration;
        private Thread worker;
        private TcpClient client;
        private StreamWriter writer;

        public ReliableControlClient(string schemaVersion, string clientInstanceId, int port = 5010)
        {
            this.schemaVersion = schemaVersion;
            this.clientInstanceId = clientInstanceId;
            this.port = port;
        }

        public bool Connected => Volatile.Read(ref connectionState).Generation != 0;
        public string LastError => Volatile.Read(ref connectionState).Error;
        public int ConnectionGeneration => Volatile.Read(ref connectionGeneration);

        public void Start()
        {
            if (running) return;
            running = true;
            worker = new Thread(Run) { IsBackground = true, Name = "SRP-U01-Control" };
            worker.Start();
        }

        public bool TryDequeue(out string json) => incoming.TryDequeue(out json);

        public bool Send(string json)
        {
            var timer = Stopwatch.StartNew();
            var startingGeneration = Volatile.Read(ref connectionState).Generation;
            if (json == null || json.Length >= MaxFrameBytes)
            {
                PublishGenerationError(startingGeneration, "CONTROL_FRAME_TOO_LARGE");
                return false;
            }
            var payload = Encoding.UTF8.GetBytes((json ?? string.Empty) + "\n");
            if (payload.Length > MaxFrameBytes)
            {
                PublishGenerationError(startingGeneration, "CONTROL_FRAME_TOO_LARGE");
                return false;
            }
            if (!Monitor.TryEnter(sendLock, Remaining(timer))) return MarkSendTimeout(startingGeneration);
            try
            {
                if (Volatile.Read(ref connectionState).Generation != startingGeneration) return false;
                TcpClient currentClient;
                long currentGeneration;
                if (!Monitor.TryEnter(writerLock, Remaining(timer))) return MarkSendTimeout(startingGeneration);
                try
                {
                    if (!Connected || writer == null || client == null) return false;
                    currentClient = client;
                    currentGeneration = Volatile.Read(ref connectionState).Generation;
                    if (currentGeneration != startingGeneration) return false;
                }
                finally { Monitor.Exit(writerLock); }

                var offset = 0;
                while (offset < payload.Length)
                {
                    if (Volatile.Read(ref connectionState).Generation != currentGeneration) return false;
                    var remaining = Remaining(timer);
                    if (remaining <= 0)
                    {
                        FailConnection(currentClient, currentGeneration, "CONTROL_SEND_TIMEOUT");
                        return false;
                    }
                    try
                    {
                        currentClient.SendTimeout = remaining;
                        var sent = currentClient.Client.Send(
                            payload, offset, payload.Length - offset, SocketFlags.None);
                        if (sent <= 0) throw new IOException();
                        offset += sent;
                    }
                    catch (SocketException)
                    {
                        FailConnection(currentClient, currentGeneration,
                            Remaining(timer) <= 0 ? "CONTROL_SEND_TIMEOUT" : "CONTROL_SEND_FAILED");
                        return false;
                    }
                    catch (ObjectDisposedException)
                    {
                        FailConnection(currentClient, currentGeneration, "CONTROL_SEND_FAILED");
                        return false;
                    }
                    catch (IOException)
                    {
                        FailConnection(currentClient, currentGeneration, "CONTROL_SEND_FAILED");
                        return false;
                    }
                }
                if (Remaining(timer) <= 0) return MarkSendTimeout(currentGeneration);
                return true;
            }
            finally { Monitor.Exit(sendLock); }
        }

        private void FailConnection(TcpClient expectedClient, long expectedGeneration, string error)
        {
            try { expectedClient?.Dispose(); } catch (SocketException) { }
            UpdateState(expectedGeneration, 0, error);
        }

        private bool MarkSendTimeout(long expectedGeneration)
        {
            UpdateState(expectedGeneration, expectedGeneration, "CONTROL_SEND_TIMEOUT");
            return false;
        }

        private void PublishGenerationError(long expectedGeneration, string error)
        {
            UpdateState(expectedGeneration, expectedGeneration, error);
        }

        private bool UpdateState(long expectedGeneration, long newGeneration, string error)
        {
            var current = Volatile.Read(ref connectionState);
            if (current.Generation != expectedGeneration) return false;
            var updated = new ConnectionState(newGeneration, error);
            return ReferenceEquals(Interlocked.CompareExchange(ref connectionState, updated, current), current);
        }

        private void PublishWorkerError(string error)
        {
            Volatile.Write(ref connectionState, new ConnectionState(0, error));
        }

        private static int Remaining(Stopwatch timer) =>
            Math.Max(0, SendTimeoutMs - (int)timer.ElapsedMilliseconds);

        public void Dispose()
        {
            running = false;
            Disconnect();
            worker?.Join(1000);
        }

        private void Run()
        {
            while (running)
            {
                try
                {
                    var attempt = new TcpClient(AddressFamily.InterNetwork);
                    attempt.SendTimeout = SendTimeoutMs;
                    attempt.ReceiveTimeout = SendTimeoutMs;
                    lock (writerLock)
                    {
                        if (!running) { attempt.Dispose(); return; }
                        client = attempt;
                    }
                    attempt.Connect(IPAddress.Loopback, port);
                    var stream = attempt.GetStream();
                    using var attemptWriter = new StreamWriter(stream, new UTF8Encoding(false), 4096, true) { NewLine = "\n" };
                    attemptWriter.WriteLine(ProtocolCodec.CreateHello(schemaVersion, clientInstanceId));
                    attemptWriter.Flush();
                    var welcome = ReadBoundedLine(stream, attempt, SendTimeoutMs);
                    if (!ProtocolCodec.ValidateWelcome(welcome, schemaVersion, clientInstanceId, out var error))
                    {
                        PublishWorkerError(error);
                        Disconnect();
                        Thread.Sleep(250);
                        continue;
                    }
                    attempt.ReceiveTimeout = 0;
                    using var reader = new StreamReader(stream, new UTF8Encoding(false, true), false, 4096, true);

                    lock (writerLock)
                    {
                        if (!running || client != attempt) throw new ObjectDisposedException(nameof(ReliableControlClient));
                        writer = attemptWriter;
                        var generation = Interlocked.Increment(ref connectionGeneration);
                        Volatile.Write(ref connectionState, new ConnectionState(generation, null));
                    }
                    while (running && Connected)
                    {
                        var line = ReadBoundedLine(reader);
                        if (line == null) break;
                        incoming.Enqueue(line);
                    }
                }
                catch (SocketException) { PublishWorkerError("CONTROL_CONNECT_FAILED"); }
                catch (InvalidDataException) { PublishWorkerError("CONTROL_FRAME_TOO_LARGE"); }
                catch (DecoderFallbackException) { PublishWorkerError("CONTROL_ENCODING_INVALID"); }
                catch (IOException) { PublishWorkerError("CONTROL_CONNECTION_LOST"); }
                catch (ObjectDisposedException) { PublishWorkerError(running ? "CONTROL_CONNECTION_LOST" : null); }
                finally { Disconnect(); }
                if (running) Thread.Sleep(250);
            }
        }

        private void Disconnect()
        {
            TcpClient currentClient;
            lock (writerLock)
            {
                writer = null;
                currentClient = client;
                client = null;
                var state = Volatile.Read(ref connectionState);
                Volatile.Write(ref connectionState, new ConnectionState(0, state.Error));
            }
            try { currentClient?.Dispose(); } catch (SocketException) { }
        }

        private static string ReadBoundedLine(NetworkStream stream, TcpClient timedClient, int timeoutMs)
        {
            var bytes = new byte[MaxFrameBytes + 1];
            var count = 0;
            var timer = Stopwatch.StartNew();
            while (true)
            {
                var remaining = Math.Max(0, timeoutMs - (int)timer.ElapsedMilliseconds);
                if (remaining <= 0) throw new IOException();
                timedClient.ReceiveTimeout = remaining;
                var read = stream.Read(bytes, count, 1);
                if (timer.ElapsedMilliseconds >= timeoutMs) throw new IOException();
                if (read == 0) return count == 0 ? null : Decode(bytes, count);
                if (bytes[count] == (byte)'\n')
                {
                    if (count + 1 > MaxFrameBytes) throw new InvalidDataException();
                    if (count > 0 && bytes[count - 1] == (byte)'\r') count--;
                    return Decode(bytes, count);
                }
                count++;
                if (count > MaxFrameBytes) throw new InvalidDataException();
            }
        }

        private static string Decode(byte[] bytes, int count)
        {
            try { return new UTF8Encoding(false, true).GetString(bytes, 0, count); }
            catch (DecoderFallbackException) { throw new InvalidDataException(); }
        }

        private static string ReadBoundedLine(StreamReader reader)
        {
            var line = new StringBuilder();
            var byteCount = 0;
            var previousHighSurrogate = false;
            while (true)
            {
                var next = reader.Read();
                if (next < 0) return line.Length == 0 ? null : line.ToString();
                var current = (char)next;
                if (current == '\n')
                {
                    if (byteCount + 1 > MaxFrameBytes) throw new InvalidDataException();
                    if (line.Length > 0 && line[line.Length - 1] == '\r') line.Length--;
                    return line.ToString();
                }
                line.Append(current);
                if (current <= 0x7f) byteCount += 1;
                else if (current <= 0x7ff) byteCount += 2;
                else if (char.IsHighSurrogate(current)) byteCount += 4;
                else if (!char.IsLowSurrogate(current) || !previousHighSurrogate) byteCount += 3;
                previousHighSurrogate = char.IsHighSurrogate(current);
                if (byteCount > MaxFrameBytes) throw new InvalidDataException();
            }
        }

        private sealed class ConnectionState
        {
            public ConnectionState(long generation, string error)
            {
                Generation = generation;
                Error = error;
            }

            public long Generation { get; }
            public string Error { get; }
        }
    }
}
