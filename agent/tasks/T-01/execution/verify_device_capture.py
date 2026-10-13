"""Check actual native capture receipts, not AI preview artwork."""
import json
from pathlib import Path
import sys


def verify(directory):
    report = json.loads((directory / 'capture-report.json').read_text(encoding='utf-8'))
    receipts = {row['screenshot']: row for row in report['captures']}
    assert len(receipts) == 14
    assert report['source_preserved']
    assert all(not row['errors'] and row['native_mouse_click'] for row in receipts.values())
    live = receipts['02-devices-live.png']['device_preview']
    assert live['rejected'] == 0, live
    assert live['streams']['resp']['buffered_samples'] >= 11000
    assert live['streams']['ecg']['buffered_samples'] >= 650
    assert all(plot['trace_pixels'] > 600 for plot in live['plots'].values())
    fault = receipts['07-invalid-duplicate.png']['device_preview']
    assert fault['error_counts'] == {'PREVIEW_STALE_SEQUENCE': 2, 'PREVIEW_SAMPLE': 2}, fault
    for name in ('09-preview-stale.png', '10-device-disconnected.png', '11-telemetry-stale.png'):
        assert all(s['state'] == 'STALE' for s in receipts[name]['device_preview']['streams'].values())
    stale = receipts['09-preview-stale.png']['fields']
    assert stale['resp_wave_state']['text'] == '末帧历史波形'
    assert stale['resp_age']['text'].startswith('历史 ')
    assert receipts['10-device-disconnected.png']['fields']['resp_sqi']['text'] == '不可用'
    history = receipts['11-telemetry-stale.png']['fields']
    assert history['resp_state']['text'].startswith('末帧：')
    assert history['resp_sqi']['text'].startswith('历史 ')
    assert receipts['12-degraded.png']['fields']['fallback_state']['text'] == '降级'
    scroll = receipts['06-details-scrolled.png']
    assert scroll['scroll_before'] != scroll['scroll_after']
    final = receipts['14-final.png']
    assert all(s['state'] == 'LIVE' for s in final['device_preview']['streams'].values())
    assert final['fields']['recording_state']['text'] == '未接入'
    result = dict(result='PASS', native_cases=14, source_preserved=True,
        steady_state_rejected=live['rejected'], injected_preview_rejections=fault['rejected'],
        sample_counts=live['streams'], plots=live['plots'],
        scope='Synthetic socket stream and native TD rendering; no physical device evidence')
    (directory / 'interface-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    verify(Path(sys.argv[1]))
