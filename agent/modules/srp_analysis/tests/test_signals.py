"""Equal-duration HRV windows stay on the declared RR sequence grid."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from srp_analysis import io
from srp_analysis.signals import fixed_rr_windows


def test_fixed_windows_do_not_drift_by_one_rr_at_every_boundary():
    windows = list(fixed_rr_windows([900.] * 200, 60, (400, 1600)))
    assert len(windows) == 3
    assert [w['window_start_s'] for w in windows] == [0, 60, 120]
    assert [w['window_end_s'] for w in windows] == [60, 120, 180]
    assert all(w['actual_window_s'] == 60 for w in windows)
    assert sum(w['beat_count'] for w in windows) == 200
    assert all(w['RMSSD_ms'] == w['SDNN_ms'] == 0 for w in windows)


def test_invalid_rr_does_not_join_two_short_quality_runs():
    assert not list(fixed_rr_windows([900.] * 64 + [99999.] + [900.] * 64, 60, (400, 1600)))
