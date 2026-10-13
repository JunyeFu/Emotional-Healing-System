using System;
using System.Collections.Concurrent;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;

namespace SRP.U01
{
    public sealed class TelemetryReceiver : IDisposable
    {
        private readonly int port;
        private readonly ConcurrentQueue<string> incoming = new();
        private volatile bool running;
        private UdpClient client;
        private Thread worker;

        public TelemetryReceiver(int port = 5006) { this.port = port; }

        public string LastError { get; private set; }

        public void Start()
        {
            if (running) return;
            running = true;
            client = new UdpClient(new IPEndPoint(IPAddress.Loopback, port));
            worker = new Thread(Run) { IsBackground = true, Name = "SRP-U01-Telemetry" };
            worker.Start();
        }

        public bool TryDequeue(out string json) => incoming.TryDequeue(out json);

        public void Dispose()
        {
            running = false;
            client?.Dispose();
            worker?.Join(1000);
        }

        private void Run()
        {
            var sender = new IPEndPoint(IPAddress.Loopback, 0);
            while (running)
            {
                try
                {
                    var data = client.Receive(ref sender);
                    if (!IPAddress.IsLoopback(sender.Address) || data.Length > 1024 * 1024)
                    {
                        LastError = "TELEMETRY_SOURCE_REJECTED";
                        continue;
                    }
                    try { incoming.Enqueue(new UTF8Encoding(false, true).GetString(data)); }
                    catch (DecoderFallbackException) { LastError = "TELEMETRY_ENCODING_INVALID"; }
                }
                catch (ObjectDisposedException) { break; }
                catch (SocketException) { if (running) LastError = "TELEMETRY_RECEIVE_FAILED"; }
            }
        }
    }
}
