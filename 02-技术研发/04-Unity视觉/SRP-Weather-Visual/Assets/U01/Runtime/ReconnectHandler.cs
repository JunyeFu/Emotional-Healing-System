// U01 — ReconnectHandler: manages TCP reconnection with exponential backoff,
// generation tracking for stale-connection detection, and fault injection
// hooks for testing.

using System;
using System.Collections;
using UnityEngine;

namespace SRP.U01
{
    /// <summary>
    /// Reconnect policy and fault-injection interface.
    /// </summary>
    public sealed class ReconnectPolicy
    {
        public int InitialBackoffMs { get; set; } = 500;
        public int MaxBackoffMs { get; set; } = 10000;
        public float BackoffMultiplier { get; set; } = 2.0f;
        public int MaxReconnectAttempts { get; set; } = 20;
        public int JitterMaxMs { get; set; } = 200;
    }

    /// <summary>
    /// Fault injection modes for testing reconnect behavior.
    /// </summary>
    public enum FaultMode
    {
        None,
        /// <summary>Always fail the next connection attempt.</summary>
        FailNextConnect,
        /// <summary>Always fail with a specific delay.</summary>
        FailWithDelay,
        /// <summary>Drop every Nth message.</summary>
        DropEveryNth,
        /// <summary>Inject a malformed message.</summary>
        CorruptMessage
    }

    /// <summary>
    /// Manages reconnection lifecycle with exponential backoff, jitter,
    /// generation tracking, and fault injection support.
    ///
    /// Usage:
    ///   var handler = new ReconnectHandler(policy, coroutineRunner);
    ///   handler.OnReconnectAttempt += (attempt) => ...;
    ///   handler.OnReconnectFailed += () => ...;
    ///   handler.OnReconnected += () => ...;
    ///   handler.RequestReconnect();
    /// </summary>
    public sealed class ReconnectHandler
    {
        // ── Configuration ─────────────────────────────────────────────────
        private readonly ReconnectPolicy _policy;
        private readonly MonoBehaviour _coroutineRunner;

        // ── State ─────────────────────────────────────────────────────────
        private int _generation;
        private int _attemptCount;
        private int _currentBackoffMs;
        private bool _reconnecting;
        private Coroutine _reconnectCoroutine;

        // ── Fault injection ───────────────────────────────────────────────
        private FaultMode _faultMode = FaultMode.None;
        private int _faultCounter;
        private int _faultEveryN;
        private float _faultDelaySeconds;

        // ── Events ────────────────────────────────────────────────────────
        /// <summary>Fired before each reconnect attempt.  Args: attempt number.</summary>
        public event Action<int> OnReconnectAttempt;

        /// <summary>Fired when max attempts exceeded.</summary>
        public event Action OnReconnectFailed;

        /// <summary>Fired on successful reconnection.</summary>
        public event Action OnReconnected;

        /// <summary>Fired when generation changes (connection established).</summary>
        public event Action<int> OnGenerationChanged;

        // ── Properties ────────────────────────────────────────────────────
        public int Generation => _generation;
        public int AttemptCount => _attemptCount;
        public bool IsReconnecting => _reconnecting;
        public int CurrentBackoffMs => _currentBackoffMs;

        public ReconnectHandler(ReconnectPolicy policy, MonoBehaviour coroutineRunner)
        {
            _policy = policy ?? new ReconnectPolicy();
            _coroutineRunner = coroutineRunner;
            _currentBackoffMs = _policy.InitialBackoffMs;
        }

        // ── Public API ────────────────────────────────────────────────────

        /// <summary>
        /// Request a reconnection cycle.  If already reconnecting, this is a no-op.
        /// The caller provides a Func that performs the actual connect; it should
        /// return true on success.
        /// </summary>
        public void RequestReconnect(Func<bool> connectAction)
        {
            if (_reconnecting) return;
            if (_coroutineRunner == null)
            {
                Log("No coroutine runner — cannot reconnect");
                OnReconnectFailed?.Invoke();
                return;
            }
            _reconnectCoroutine = _coroutineRunner.StartCoroutine(
                ReconnectLoop(connectAction));
        }

        /// <summary>
        /// Signal that the connection succeeded.  Resets backoff and increments
        /// generation.
        /// </summary>
        public void SignalConnected()
        {
            int prev = _generation;
            _generation++;
            _attemptCount = 0;
            _currentBackoffMs = _policy.InitialBackoffMs;
            _reconnecting = false;
            if (_generation != prev)
                OnGenerationChanged?.Invoke(_generation);
            Log($"Connected — generation {_generation}");
        }

        /// <summary>
        /// Signal that the connection was lost.  Triggers reconnect if not active.
        /// </summary>
        public void SignalDisconnected(Func<bool> connectAction)
        {
            Log("Disconnected");
            RequestReconnect(connectAction);
        }

        /// <summary>
        /// Abort any in-progress reconnect cycle.
        /// </summary>
        public void Abort()
        {
            _reconnecting = false;
            if (_reconnectCoroutine != null && _coroutineRunner != null)
            {
                _coroutineRunner.StopCoroutine(_reconnectCoroutine);
                _reconnectCoroutine = null;
            }
        }

        /// <summary>
        /// Reset all state (e.g., when shutting down).
        /// </summary>
        public void ResetState()
        {
            Abort();
            _generation = 0;
            _attemptCount = 0;
            _currentBackoffMs = _policy.InitialBackoffMs;
            _faultMode = FaultMode.None;
            _faultCounter = 0;
        }

        // ── Fault injection ───────────────────────────────────────────────

        /// <summary>Set the active fault mode for testing.</summary>
        public void SetFaultMode(FaultMode mode, int everyN = 0, float delaySeconds = 0f)
        {
            _faultMode = mode;
            _faultEveryN = everyN;
            _faultDelaySeconds = delaySeconds;
        }

        /// <summary>Clear fault injection.</summary>
        public void ClearFault()
        {
            _faultMode = FaultMode.None;
            _faultCounter = 0;
        }

        /// <summary>
        /// Check if the current fault mode should block the connection.
        /// Returns true if the connect should be forced to fail.
        /// </summary>
        public bool ShouldInjectFault()
        {
            switch (_faultMode)
            {
                case FaultMode.FailNextConnect:
                    ClearFault(); // one-shot
                    return true;
                case FaultMode.FailWithDelay:
                    ClearFault();
                    return true;
                case FaultMode.DropEveryNth:
                    _faultCounter++;
                    return _faultEveryN > 0 && (_faultCounter % _faultEveryN == 0);
                case FaultMode.CorruptMessage:
                    _faultCounter++;
                    return _faultEveryN > 0 && (_faultCounter % _faultEveryN == 0);
                default:
                    return false;
            }
        }

        /// <summary>
        /// Whether the next receive should be corrupted.
        /// </summary>
        public bool ShouldCorruptMessage()
        {
            return _faultMode == FaultMode.CorruptMessage && ShouldInjectFault();
        }

        /// <summary>
        /// Whether the next receive should be dropped.
        /// </summary>
        public bool ShouldDropMessage()
        {
            return _faultMode == FaultMode.DropEveryNth && ShouldInjectFault();
        }

        // ── Internal ──────────────────────────────────────────────────────

        private IEnumerator ReconnectLoop(Func<bool> connectAction)
        {
            _reconnecting = true;
            _attemptCount = 0;

            while (_reconnecting && _attemptCount < _policy.MaxReconnectAttempts)
            {
                _attemptCount++;
                int attempt = _attemptCount;
                OnReconnectAttempt?.Invoke(attempt);

                Log($"Reconnect attempt {attempt}/{_policy.MaxReconnectAttempts} " +
                    $"(backoff {_currentBackoffMs}ms)");

                // Fault injection: force failure
                if (ShouldInjectFault())
                {
                    Log("Fault injection — connect forced to fail");
                    yield return new WaitForSeconds(_policy.MaxBackoffMs / 1000f);
                    AdvanceBackoff();
                    continue;
                }

                // Attempt connect
                bool success = false;
                try
                {
                    success = connectAction();
                }
                catch (Exception ex)
                {
                    Log($"Connect threw: {ex.Message}");
                }

                if (success)
                {
                    SignalConnected();
                    _reconnectCoroutine = null;
                    OnReconnected?.Invoke();
                    yield break;
                }

                // Wait with jitter
                float jitter = UnityEngine.Random.Range(0, _policy.JitterMaxMs) / 1000f;
                float waitSec = (_currentBackoffMs / 1000f) + jitter;

                if (_faultMode == FaultMode.FailWithDelay)
                    waitSec = _faultDelaySeconds > 0 ? _faultDelaySeconds : waitSec;

                yield return new WaitForSeconds(waitSec);
                AdvanceBackoff();
            }

            // Exhausted
            _reconnecting = false;
            _reconnectCoroutine = null;
            Log($"Reconnect failed after {_attemptCount} attempts");
            OnReconnectFailed?.Invoke();
        }

        private void AdvanceBackoff()
        {
            _currentBackoffMs = Mathf.Min(
                (int)(_currentBackoffMs * _policy.BackoffMultiplier),
                _policy.MaxBackoffMs);
        }

        private static void Log(string msg)
        {
            Debug.Log($"[U01.ReconnectHandler] {msg}");
        }
    }
}
