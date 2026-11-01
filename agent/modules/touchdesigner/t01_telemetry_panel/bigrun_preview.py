"""BigRun-only display model; no device, experiment or research authorization."""
from collections import deque
import json
import math

VIEWS = {"resp": ("resp", "acceleration"), "ecg": ("ecg", "rr", "hr")}
LABELS = {"resp": "呼吸代理", "acceleration": "三轴 ACC", "ecg": "ECG", "rr": "原生 RR", "hr": "心率"}
UNITS = {"resp": "相对幅度", "acceleration": "原始整数", "ecg": "ADC", "rr": "原始整数", "hr": "bpm"}
COLORS = {"resp": (37/255, 99/255, 166/255), "ecg": (35/255, 122/255, 71/255),
          "hr": (35/255, 122/255, 71/255), "rr": (.47, .31, .63),
          "x": (.71, .23, .23), "y": (.14, .48, .28), "z": (.15, .39, .65)}


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


class BigRunPreview:
    def __init__(self):
        self.stream_id = None
        self.sequence = 0
        self.data = {}
        self.receipts = {}
        self.clocks = {}
        self.status = {}
        self.status_ns = None
        self.accepted = self.rejected = self.lost = 0
        self.last_error = None
        self.raw = {}

    def ingest(self, raw, now_ns):
        try:
            p = json.loads(raw)
            if (p.get("message_type") != "bigrun_preview" or p.get("version") != "1.0"
                    or p.get("source_mode") != "real" or p.get("device") != "BigRun Team"
                    or p.get("evidence_scope") != "DEVELOPMENT_UNVERIFIED"
                    or p.get("formal_capable") is not False):
                raise ValueError("BIGRUN_SOURCE")
            sid, seq, stamp = p["stream_id"], p["packet_seq"], p["received_monotonic_ns"]
            if not isinstance(sid, str) or not sid or type(seq) is not int or seq < 1:
                raise ValueError("BIGRUN_IDENTITY")
            sent = p["sent_monotonic_ns"]
            if type(stamp) is not int or stamp < 0 or type(sent) is not int or sent < stamp:
                raise ValueError("BIGRUN_TIME")
            kind, samples = p["kind"], p["samples"]
            if kind not in ("ecg", "acc", "rr", "hr", "status", "config", "unparsed"):
                raise ValueError("BIGRUN_KIND")
            if not isinstance(samples, list) or len(samples) > 400:
                raise ValueError("BIGRUN_BATCH")
            if kind == "acc":
                if any(not isinstance(v, list) or len(v) != 3 or not all(map(finite, v)) for v in samples):
                    raise ValueError("BIGRUN_XYZ")
            elif not all(map(finite, samples)):
                raise ValueError("BIGRUN_SAMPLES")
            rate = p.get("sample_rate_hz_nominal")
            if rate is not None and (not finite(rate) or not 0 < rate <= 10000):
                raise ValueError("BIGRUN_RATE")
            proxy = p.get("respiration_proxy", [])
            if not isinstance(proxy, list) or (proxy and (kind != "acc" or len(proxy) != len(samples))) or not all(map(finite, proxy)):
                raise ValueError("BIGRUN_PROXY")
            if kind == "status":
                if type(p.get("connected")) is not bool:
                    raise ValueError("BIGRUN_CONNECTION")
                hr = p.get("heart_rate_bpm")
                if hr is not None and (not finite(hr) or hr <= 0):
                    raise ValueError("BIGRUN_HR")
            if sid == self.stream_id and seq <= self.sequence:
                raise ValueError("BIGRUN_STALE_SEQUENCE")
            if sid != self.stream_id:
                self.data.clear()
                self.receipts.clear()
                self.clocks.clear()
                self.status = {}
                self.status_ns = None
                self.sequence = 0
                self.stream_id = sid
            if self.sequence and seq != self.sequence + 1:
                self.lost += seq - self.sequence - 1
                self.clocks.clear()
                for q in self.data.values():
                    q.append((stamp, None))
            self.sequence = seq
            self.raw = p
            lag = sent - stamp
            if kind == "status":
                self.status, self.status_ns = p, now_ns
                if p.get("heart_source") == "ecg_past_window_estimate" and p.get("heart_rate_bpm") is not None:
                    self._append("hr", [(stamp, p["heart_rate_bpm"])], now_ns, lag)
            elif samples and kind in ("ecg", "acc", "rr", "hr"):
                stamps = self._stamps(kind, stamp, len(samples), rate)
                if kind == "acc":
                    for i, axis in enumerate("xyz"):
                        self._append(axis, list(zip(stamps, (s[i] for s in samples))), now_ns, lag)
                    if proxy and p.get("resp_warmed_up") is True:
                        self._append("resp", list(zip(stamps, proxy)), now_ns, lag)
                else:
                    self._append(kind, list(zip(stamps, samples)), now_ns, lag)
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            self.rejected += 1
            self.last_error = str(error)
            return False
        self.accepted += 1
        self.last_error = None
        return True

    def _stamps(self, kind, received, count, rate):
        # ECG/ACC only: nominal indexing, never a verified device sample clock.
        if not rate or kind not in ("ecg", "acc"):
            return [received] * count
        anchor, index, old_rate, last_received = self.clocks.get(kind, (None, 0, rate, received))
        if anchor is None or old_rate != rate or received - last_received > 2_000_000_000:
            anchor, index = received - round((count - 1) * 1e9 / rate), 0
            for key in (("x", "y", "z", "resp") if kind == "acc" else ("ecg",)):
                if key in self.data:
                    self.data[key].append((anchor, None))
        values = [anchor + round((index + i) * 1e9 / rate) for i in range(count)]
        self.clocks[kind] = anchor, index + count, rate, received
        return values

    def _append(self, key, points, now, lag):
        q = self.data.setdefault(key, deque(maxlen=120001))
        q.extend(points)
        self.receipts[key] = now, lag
        cutoff = points[-1][0] - 30_000_000_000
        while q and q[0][0] < cutoff:
            q.popleft()

    def fresh(self, key, now):
        receipt = self.receipts.get(key)
        return bool(receipt and now - receipt[0] + receipt[1] < 2_000_000_000 and self.connected(now))

    def connected(self, now):
        return bool(self.status.get("connected") and self.status_ns is not None and now - self.status_ns < 2_000_000_000)

    def value(self, key, now):
        q = self.data.get(key)
        return q[-1][1] if q and self.fresh(key, now) else None

    def series(self, key, now):
        axes = "xyz" if key == "acceleration" else (key,)
        result = []
        for axis in axes:
            points = tuple(self.data.get(axis, ()))
            window = 6 if key == "ecg" else 30
            values = [v for _, v in points if v is not None]
            if not points or not values:
                continue
            receipt = self.receipts[axis]
            end = points[-1][0] + max(0, now - receipt[0]) if self.fresh(axis, now) else points[-1][0]
            low, high = min(values), max(values)
            margin = .1 * (high - low) if high != low else 1
            result.append(dict(points=points, window=window, end_ns=end, unit=UNITS[key],
                               state="LIVE" if self.fresh(axis, now) else "STALE",
                               color=COLORS[axis], range=(low-margin, high+margin),
                               gap_ns=2_000_000_000, line_width=2, axis=axis))
        return result

    def fields(self, now):
        s = self.status
        conn = self.connected(now)
        resp = ("未标定" if not s.get("resp_profile_loaded") else "预热中" if not s.get("resp_warmed_up")
                else "代理待验" if self.fresh("resp", now) else "代理断流")
        def val(key):
            v = self.value(key, now)
            return "—" if v is None else format(v, ".1f") if key == "hr" else str(v)
        def rate(key):
            r = s.get(key + "_hz_nominal")
            return str(r) + " Hz（名义）" if r else "输出率待核"
        return dict(connection="已连接" if conn else "未连接" if not s else "已断流",
                    resp_state=resp if conn else "未接入" if not s else "已断流",
                    ecg_state="原始数据" if self.fresh("ecg", now) else "未接入" if conn or not s else "已断流",
                    heart_rate=val("hr"), rr_interval=val("rr"), resp_rate=rate("acc"), ecg_rate=rate("ecg"),
                    resp_sqi="未验证", ecg_sqi="未验证", motion_state="XYZ" if self.fresh("x", now) else "未接入",
                    heart_calibration="已加载待验" if s.get("heart_profile_loaded") else "未加载",
                    resp_calibration=resp, archive=s.get("archive", ""),
                    timing="名义采样时轴" if s.get("ecg_hz_nominal") or s.get("acc_hz_nominal") else "主机接收时轴",
                    gate="实验桥未接入", actual_step_id="未识别", actual_confidence="未验证",
                    error=s.get("error") or self.last_error)

    def action_allowed(self, name):
        # No local confirmation can create a real SessionCore/Unity receipt.
        return name in {"new", "cancel", "history", "details", "back", "raw", "copy", "open"}
