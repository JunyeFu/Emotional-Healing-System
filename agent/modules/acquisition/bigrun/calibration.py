"""Reference-based candidate calibration. No guide curve, no formal PASS label."""
import csv
from pathlib import Path

import numpy as np
from scipy.signal import butter, find_peaks, sosfilt

from .recording import SCOPE


def read_csv(path, columns):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not set(columns).issubset(reader.fieldnames or []):
            raise ValueError(f"CSV_COLUMNS_REQUIRED: {columns}")
        rows = [[float(row[key]) for key in columns] for row in reader]
    data = np.asarray(rows, dtype=float)
    if data.ndim != 2 or len(data) < 3 or not np.isfinite(data).all():
        raise ValueError("CSV_REQUIRES_FINITE_SAMPLES")
    if np.any(np.diff(data[:, 0]) <= 0):
        raise ValueError("CSV_TIME_MUST_INCREASE")
    return data


def sample_rate(t):
    dt = np.diff(np.asarray(t))
    if len(dt) == 0 or not np.isfinite(dt).all() or np.any(dt <= 0):
        raise ValueError("INVALID_SAMPLE_TIME")
    median = float(np.median(dt))
    if np.max(np.abs(dt - median)) > median * .05:
        raise ValueError("NONUNIFORM_OR_GAPPED_TIME_NO_SILENT_INTERPOLATION")
    return 1 / median


def _resp_inputs(t, xyz, ref_t, ref, fs, band, delay):
    t, xyz, ref_t, ref = (np.asarray(v, dtype=float) for v in (t, xyz, ref_t, ref))
    if xyz.shape != (len(t), 3) or ref.shape != ref_t.shape:
        raise ValueError("RESP_SHAPE_MISMATCH")
    if not all(np.isfinite(v).all() for v in (t, xyz, ref_t, ref)) or not np.isfinite(delay):
        raise ValueError("NONFINITE_CALIBRATION_INPUT")
    if abs(sample_rate(t) - fs) > fs * .01:
        raise ValueError("CALIBRATION_TIME_RATE_MISMATCH")
    sample_rate(ref_t)
    if len(band) != 2 or not 0 < band[0] < band[1] < fs / 2:
        raise ValueError("INVALID_RESP_BAND")
    # Exclude filter startup and never extrapolate the reference signal.
    warmup = 2 / band[0]
    target_t = t - delay
    mask = (t >= t[0] + warmup) & (target_t >= ref_t[0]) & (target_t <= ref_t[-1])
    if mask.sum() < fs * 2 / band[0]:
        raise ValueError("CALIBRATION_TOO_SHORT_FOR_BAND")
    target = np.interp(target_t[mask], ref_t, ref)
    if np.std(target) < 1e-10:
        raise ValueError("NO_REFERENCE_RESP_VARIATION")
    return t, xyz, mask, target


class RespirationProxy:
    """Causal, stateful projection; outputs relative units, not breath events."""
    def __init__(self, profile):
        if profile["kind"] != "bigrun_respiration_projection_v1":
            raise ValueError("WRONG_RESP_PROFILE")
        self.center = np.asarray(profile["acc_center"], dtype=float)
        self.weights = np.asarray(profile["weights"], dtype=float)
        self.intercept = float(profile["intercept"])
        self.sos = butter(2, profile["band_hz"], btype="bandpass",
                          fs=profile["acc_hz"], output="sos")
        self.state = np.zeros((len(self.sos), 2, 3))
        self.sample_count = 0
        self.warmup_samples = int(np.ceil(profile["warmup_s"] * profile["acc_hz"]))

    @property
    def warmed_up(self):
        return self.sample_count >= self.warmup_samples

    def feed(self, xyz):
        xyz = np.asarray(xyz, dtype=float)
        if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
            raise ValueError("INVALID_ACC_BATCH")
        filtered, self.state = sosfilt(self.sos, xyz - self.center, axis=0, zi=self.state)
        self.sample_count += len(xyz)
        return filtered @ self.weights + self.intercept


def fit_respiration(t, xyz, ref_t, ref, fs, band, reference_delay_s):
    t, xyz, mask, target = _resp_inputs(t, xyz, ref_t, ref, fs, band, reference_delay_s)
    if np.max(np.std(xyz, axis=0)) < 1e-10:
        raise ValueError("NO_ACC_VARIATION")
    center = np.median(xyz, axis=0)
    filtered = sosfilt(butter(2, band, btype="bandpass", fs=fs, output="sos"),
                       xyz - center, axis=0)
    mean, scale = float(np.mean(target)), float(np.std(target))
    design = np.column_stack([filtered[mask], np.ones(mask.sum())])
    coefficients = np.linalg.lstsq(design, (target - mean) / scale, rcond=None)[0]
    profile = {
        "kind": "bigrun_respiration_projection_v1", "evidence_scope": SCOPE,
        "acc_hz": fs, "band_hz": list(band), "warmup_s": 2 / band[0],
        "acc_center": center.tolist(), "weights": coefficients[:3].tolist(),
        "intercept": float(coefficients[3]), "reference_mean": mean,
        "reference_scale": scale, "reference_delay_s": reference_delay_s,
        "delay_definition": "proxy(t) compared with reference(t - delay); no live time shift",
        "delay_source": "operator_supplied_not_automatically_calibrated",
        "units": "relative_reference_standard_deviations_not_volume",
        "event_recognition": "NOT_IMPLEMENTED", "device_timing": "UNVERIFIED",
        "real_device_acceptance": "NOT_RUN",
    }
    profile["fit_metrics"] = validate_respiration(profile, t, xyz, ref_t, ref)
    return profile


def _breathing_rate(values, fs, band):
    peaks, _ = find_peaks(values, distance=fs / band[1], prominence=np.std(values) * .2)
    if len(peaks) < 3:
        return None
    return float(60 * fs / np.median(np.diff(peaks)))


def validate_respiration(profile, t, xyz, ref_t, ref):
    fs, band = profile["acc_hz"], profile["band_hz"]
    t, xyz, mask, target = _resp_inputs(t, xyz, ref_t, ref, fs, band,
                                       profile["reference_delay_s"])
    estimated = RespirationProxy(profile).feed(xyz)[mask]
    expected = (target - profile["reference_mean"]) / profile["reference_scale"]
    correlation = (float(np.corrcoef(estimated, expected)[0, 1])
                   if np.std(estimated) > 1e-10 else None)
    estimated_rate = _breathing_rate(estimated, fs, band)
    reference_rate = _breathing_rate(expected, fs, band)
    return {
        "evidence_scope": SCOPE, "automatic_acceptance": False,
        "waveform_correlation": correlation,
        "normalized_rmse": float(np.sqrt(np.mean((estimated - expected) ** 2))),
        "estimated_rate_bpm": estimated_rate, "reference_rate_bpm": reference_rate,
        "rate_absolute_error_bpm": (abs(estimated_rate - reference_rate)
                                     if estimated_rate is not None and reference_rate is not None else None),
        "samples_compared": int(mask.sum()),
        "phase_hold_topup_accuracy": "NOT_EVALUATED",
    }


def heart_metrics(detected, reference, tolerance_s):
    detected, reference = np.asarray(detected), np.asarray(reference)
    if (not np.isfinite(tolerance_s) or tolerance_s <= 0 or
            not np.isfinite(detected).all() or not np.isfinite(reference).all() or
            np.any(np.diff(detected) <= 0) or np.any(np.diff(reference) <= 0)):
        raise ValueError("INVALID_HEART_REFERENCE_OR_TOLERANCE")
    if len(detected) < 3 or len(reference) < 3:
        raise ValueError("TOO_FEW_HEART_BEATS")
    pairs, last = [], -1
    for i, beat in enumerate(detected):
        j = int(np.searchsorted(reference, beat))
        candidates = [k for k in (j - 1, j) if last < k < len(reference)]
        if candidates:
            best = min(candidates, key=lambda k: abs(reference[k] - beat))
            if abs(reference[best] - beat) <= tolerance_s:
                pairs.append((i, best))
                last = best
    rr_errors = [abs((detected[i] - detected[pi]) - (reference[j] - reference[pj])) * 1000
                 for (pi, pj), (i, j) in zip(pairs, pairs[1:]) if i == pi + 1 and j == pj + 1]
    return {
        "matched_beats": len(pairs), "missed_reference_beats": len(reference) - len(pairs),
        "unmatched_detected_beats": len(detected) - len(pairs),
        "r_peak_timing_mae_ms": (float(np.mean([abs(detected[i] - reference[j]) * 1000
                                               for i, j in pairs])) if pairs else None),
        "rr_mae_ms_on_consecutive_matches": float(np.mean(rr_errors)) if rr_errors else None,
        "detected_hr_mean_bpm": float(60 / np.mean(np.diff(detected))),
        "reference_hr_mean_bpm": float(60 / np.mean(np.diff(reference))),
        "detected_rmssd_ms": float(np.sqrt(np.mean(np.diff(np.diff(detected) * 1000) ** 2))),
        "automatic_acceptance": False, "evidence_scope": SCOPE,
    }


def calibrate_heart(t, ecg, reference_beats, polarity, reference_delay_s, tolerance_s):
    import neurokit2 as nk
    fs = sample_rate(t)
    if not np.isfinite(reference_delay_s):
        raise ValueError("INVALID_REFERENCE_DELAY")
    cleaned = nk.ecg_clean(np.asarray(ecg) * polarity, sampling_rate=int(round(fs)))
    _, info = nk.ecg_peaks(cleaned, sampling_rate=int(round(fs)), correct_artifacts=False)
    peaks = np.asarray(t)[info["ECG_R_Peaks"]] - reference_delay_s
    return {
        "kind": "bigrun_heart_check_v1", "ecg_hz": fs, "polarity": polarity,
        "reference_delay_s": reference_delay_s, "tolerance_s": tolerance_s,
        "evidence_scope": SCOPE, "ecg_voltage_units": "UNVERIFIED_ADC_COUNTS",
        "device_rr_units": "UNVERIFIED_UNLESS_EXPLICITLY_CONFIGURED",
        "metrics": heart_metrics(peaks, reference_beats, tolerance_s),
        "real_device_acceptance": "NOT_RUN",
    }
