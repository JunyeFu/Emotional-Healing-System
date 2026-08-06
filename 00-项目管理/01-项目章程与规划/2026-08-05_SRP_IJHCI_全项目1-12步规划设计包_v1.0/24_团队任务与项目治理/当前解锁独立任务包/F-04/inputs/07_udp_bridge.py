"""UDP->TD Bridge v1.1: receives UDP JSON on port 5005, forwards to TD via HTTP API.

4-dimension scoring model. See scoring_model.py and UDP字段冻结_v1.2.md.
"""

import socket
import json
import urllib.request
import time
import sys
import argparse


def call_td(code, td_url="http://127.0.0.1:9980/api", timeout=5):
    """Execute Python code in TD and return result."""
    payload = {
        "action": "execute",
        "params": {"code": code}
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(td_url, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except urllib.request.HTTPError as e:
        body = e.read().decode()
        return {"error": f"HTTP {e.code}", "body": body[:400]}
    except Exception as e:
        return {"error": str(e)}


# TD script template: __DATA_JSON__ will be replaced with actual JSON string
TD_SCRIPT_TEMPLATE = r'''
data = __DATA_JSON__
dc = op('/project1/SRP_BreathGuide/Data_CHOPs')
mon = op('/project1/SRP_BreathGuide/Monitor_Panel')
bg = op('/project1/SRP_BreathGuide/Breath_Guide')

scores = data.get('scores', {})

# 4-dimension CHOP mapping
ch_map = {
    'breath_sync': 'ch_breath_sync',
    'breath_depth': 'ch_breath_depth',
    'hrv_coherence': 'ch_hrv_coherence',
    'eda_calm': 'ch_eda_calm',
}

for key, ch_name in ch_map.items():
    ch = dc.op(ch_name)
    if ch:
        val = scores.get(key, 0.0)
        if isinstance(val, (int, float)):
            ch.par.value0 = val

weather = data.get('weather', {})
wi = dc.op('ch_weather_intensity')
if wi: wi.par.value0 = float(weather.get('intensity', 0.0))

breath = data.get('breath', {})

# Calculate circle_radius from breath.amplitude or depth, [0,1] → [0.2, 0.9]
raw_amp = float(breath.get('amplitude', 0.5))
circle_radius = 0.2 + raw_amp * 0.7
circle_radius = max(0.15, min(1.0, circle_radius))

cr = dc.op('ch_circle_radius')
if cr: cr.par.value0 = circle_radius
pn = dc.op('ch_phase_num')
if pn:
    phase_map = {'inhale': 0, 'hold': 1, 'exhale': 2}
    pn.par.value0 = phase_map.get(str(breath.get('phase', 'inhale')), 0)

cardiac = data.get('cardiac', {})
hr_ch = dc.op('ch_hr')
if hr_ch: hr_ch.par.value0 = float(cardiac.get('hr', 0))
rr_ch = dc.op('ch_rr')
if rr_ch: rr_ch.par.value0 = float(breath.get('rate', 0))

# Circle animation
radius = circle_radius
xform_node = bg.op('circle_xform')
if xform_node:
    xform_node.par.sx = radius
    xform_node.par.sy = radius

phase = str(breath.get('phase', 'inhale'))
circle_node = bg.op('guide_circle')
if circle_node:
    if phase == 'inhale':
        circle_node.par.fillcolorr = 0.2
        circle_node.par.fillcolorg = 0.75
        circle_node.par.fillcolorb = 0.4
    elif phase == 'hold':
        circle_node.par.fillcolorr = 0.85
        circle_node.par.fillcolorg = 0.75
        circle_node.par.fillcolorb = 0.15
    else:
        circle_node.par.fillcolorr = 0.15
        circle_node.par.fillcolorg = 0.35
        circle_node.par.fillcolorb = 0.8

# Monitor panel — guidance prompt
guidance = data.get('guidance', {})
tp = mon.op('txt_prompt')
if tp: tp.par.text = str(guidance.get('prompt', ''))

# Monitor panel — 4 score texts
for key in ch_map:
    txt = mon.op('txt_' + key)
    if txt:
        label = key.replace('_', ' ').title()
        txt.par.text = label + ': ' + str(round(scores.get(key, 0), 1))

tw = mon.op('txt_weather')
if tw: tw.par.text = 'Weather: ' + str(weather.get('type', '--')) + ' (' + str(round(weather.get('intensity', 0), 1)) + ')'

th = mon.op('txt_hr')
if th: th.par.text = 'HR: ' + str(int(cardiac.get('hr', 0))) + ' BPM  RR: ' + str(int(breath.get('rate', 0))) + ' bpm'
'''


def sanitize(obj):
    """Recursively replace NaN/Infinity with 0.0 so JSON->Python literal works."""
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    if isinstance(obj, float):
        import math
        if math.isnan(obj) or math.isinf(obj):
            return 0.0
    return obj


def build_update_script(data):
    """Build a TD Python script that updates all parameters from UDP data."""
    clean = sanitize(data)
    data_json = json.dumps(clean)
    return TD_SCRIPT_TEMPLATE.replace('__DATA_JSON__', data_json)


def main():
    parser = argparse.ArgumentParser(description="UDP->TD Bridge v1.1 (4-dim)")
    parser.add_argument("--port", type=int, default=5005, help="UDP listen port")
    parser.add_argument("--td-url", default="http://127.0.0.1:9980/api", help="TD HTTP API URL")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-packet logging")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        sock.bind(("127.0.0.1", args.port))
    except OSError as e:
        print(f"FATAL: Cannot bind to 127.0.0.1:{args.port}: {e}")
        print("Make sure TD's udpinDAT is deactivated or TD is not using this port.")
        sys.exit(1)

    sock.settimeout(0.1)
    print(f"UDP->TD Bridge v1.1 listening on 127.0.0.1:{args.port}", flush=True)
    print(f"TD API: {args.td_url}", flush=True)
    print("Waiting for data...", flush=True)
    print()

    frame = 0
    errors = 0
    last_status = time.time()

    while True:
        try:
            data_bytes, addr = sock.recvfrom(65536)
            frame += 1

            try:
                data = json.loads(data_bytes.decode("utf-8"))
            except json.JSONDecodeError:
                if not args.quiet:
                    print(f"[{frame}] Invalid JSON from {addr}")
                continue

            # Build and execute TD update script
            script = build_update_script(data)
            result = call_td(script, td_url=args.td_url)

            if result.get("ok") is not True:
                errors += 1
                err_info = result.get("error", str(result))
                err_body = result.get("body", "")
                if not args.quiet or errors <= 3:
                    print(f"[{frame}] TD error: {err_info[:120]}")
                    if err_body:
                        print(f"       body: {err_body[:300]}")
            elif not args.quiet:
                phase = data.get("breath", {}).get("phase", "?")
                amp = float(data.get("breath", {}).get("amplitude", 0.5))
                cr = 0.2 + amp * 0.7
                print(f"[{frame}] phase={phase} radius={cr:.2f}")

            # Status report every 5 seconds
            if time.time() - last_status >= 5:
                print(f"  ... {frame} frames, {errors} errors ...")
                last_status = time.time()

        except socket.timeout:
            continue
        except KeyboardInterrupt:
            print(f"\nStopped. {frame} frames processed, {errors} errors.")
            break
        except Exception as e:
            errors += 1
            print(f"[{frame}] Unexpected error: {e}")
            time.sleep(0.1)

    sock.close()


if __name__ == "__main__":
    main()
