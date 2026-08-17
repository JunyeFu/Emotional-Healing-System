using UnityEngine;
using System;
using System.Collections.Concurrent;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;

public class UDPReceiver : MonoBehaviour
{
    [SerializeField] private int port = 5006;

    private UdpClient _udpClient;
    private Thread _receiveThread;
    private readonly ConcurrentQueue<string> _messageQueue = new();
    private volatile bool _isRunning;

    public event Action<string> OnMessageReceived;

    void Start()
    {
        _isRunning = true;
        try
        {
            _udpClient = new UdpClient(port);
            _receiveThread = new Thread(ReceiveLoop)
            {
                IsBackground = true,
                Name = "UDP-Receive"
            };
            _receiveThread.Start();
            Debug.Log($"[UDPReceiver] Listening on port {port}");
        }
        catch (Exception e)
        {
            Debug.LogError($"[UDPReceiver] Failed to start: {e.Message}");
        }
    }

    void ReceiveLoop()
    {
        var remoteEndPoint = new IPEndPoint(IPAddress.Any, port);
        while (_isRunning)
        {
            try
            {
                if (_udpClient == null || _udpClient.Client == null) break;
                byte[] data = _udpClient.Receive(ref remoteEndPoint);
                string json = Encoding.UTF8.GetString(data);
                _messageQueue.Enqueue(json);
            }
            catch (SocketException) { /* timeout or close */ }
            catch (ObjectDisposedException) { break; }
            catch (Exception e)
            {
                Debug.LogWarning($"[UDPReceiver] Receive error: {e.Message}");
            }
        }
    }

    void Update()
    {
        while (_messageQueue.TryDequeue(out string json))
        {
            OnMessageReceived?.Invoke(json);
        }
    }

    void OnDestroy()
    {
        _isRunning = false;
        try { _udpClient?.Close(); } catch { }
        _receiveThread?.Join(500);
    }
}
