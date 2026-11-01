"""Six-family synthetic originals, including real-format P-02 raw archives."""
import struct
from pathlib import Path

import numpy as np
import pandas as pd

from acquisition.bigrun.recording import CandidateRecording
from . import BASELINE
from .io import digest, save_frame, write_json
from .prepare import STEPS


def candidate_spec():
    return dict(schema_version='1.0', design_baseline_id=BASELINE, evidence_class='SYNTHETIC',
                measurement_frozen=False, sap_frozen=False, seed=20261019,
                pmm_k=5, imputations=50, iterations=20, imputation_predictors=[],
                delta_pairs=[[0, 0], [0, 2], [0, 4], [-2, 0], [-4, 0]],
                delta_grid_status='SOFTWARE_EXERCISE_NOT_FORMAL_MNAR_FREEZE',
                panas_form={'form_id': 'SYNTHETIC_GENERAL_PANAS20',
                            'NA': [f'N{i}' for i in range(10)], 'PA': [f'P{i}' for i in range(10)]},
                scoring_tolerance_s=.5, scoring_tolerance_status='SYNTHETIC_ONLY',
                ideal_steps={'storm': {'inhale_1': 3, 'hold_1': 3, 'exhale_1': 3, 'hold_2': 3},
                             'heat': {'inhale_1': 4, 'exhale_1': 6},
                             'snow': {'inhale_1': 4, 'exhale_1': 6},
                             'fade': {'inhale_1': 2.5, 'inhale_2': 1.5, 'exhale_1': 6}},
                signals={'ecg_hz': 130, 'acc_hz': 25, 'gap_limit_s': 1.5,
                         'rr_units': 'ms', 'rr_units_validated': True, 'rr_sequence_validated': True,
                         'quality_validated': True, 'validation_ref': 'SYNTHETIC_KNOWN_GENERATOR',
                         'rr_accept_ms': [400, 1600], 'hrv_window_s': 60},
                research_gates={'device_validation': 'NOT_RUN', 'measurement_approval': 'NOT_RUN',
                                'research_lock': 'NOT_RUN', 'unblind_authorization': 'NOT_RUN'})


def bounded_scores(rng, n, effect, floor=False):
    pre = np.clip(np.rint(rng.normal(12 if floor else 26, 2 if floor else 5, n)), 10, 50)
    B = np.arange(n) % 2
    post = np.clip(np.rint(10 + .55 * pre + effect * B + rng.normal(0, 2.2, n)), 10, 50)
    if floor:
        post = np.clip(post - 6, 10, 50)
    return pre, post


def make_demo(root, n=30, scenario='missing', seed=20261019):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(seed)
    spec = candidate_spec()
    spec['seed'] = seed
    effect = {'benefit': -6, 'null': 0, 'harm': 6, 'floor': -6, 'missing': -6}[scenario]
    pre, post = bounded_scores(rng, n, effect, scenario == 'floor')
    allocations, questions, runtime, annotations, device_index = [], [], [], [], []
    for i in range(n):
        rid, condition = f'SYN-{i:03d}', 'B' if i % 2 else 'A'
        allocations.append(dict(research_id=rid, cohort='formal', condition=condition,
                                order_id=1 + (i // 2) % 4, randomized=True,
                                completed=i != 7, withdrawn=i == 7))
        for when, na in [('pre', pre[i]), ('post', post[i])]:
            for scale, total in [('N', na), ('P', int(rng.integers(20, 40)))]:
                total = int(total)
                values = [total // 10 + (j < total % 10) for j in range(10)]
                rng.shuffle(values)
                for j, value in enumerate(values):
                    missing = scenario == 'missing' and ((when == 'post' and i in (2, 7)) or (when == 'pre' and i == 11))
                    questions.append(dict(research_id=rid, instrument='PANAS',
                                          form_id=spec['panas_form']['form_id'], timepoint=when,
                                          item_id=f'{scale}{j}', value=None if missing and j == 0 else value,
                                          response_status='SKIPPED' if missing and j == 0 else 'RESPONDED',
                                          measured_at=f'2026-10-19T10:{0 if when == "pre" else 30:02d}:00+08:00',
                                          measurement_delay_s=0))
        for instrument in ('effort', 'comfort'):
            questions.append(dict(research_id=rid, instrument=instrument, form_id='SYNTHETIC_SINGLE_ITEM',
                                  timepoint='post', item_id=instrument, value=int(rng.integers(2, 9)),
                                  response_status='RESPONDED', measured_at='2026-10-19T10:32:00+08:00',
                                  measurement_delay_s=0))
        for m, weather in enumerate(STEPS):
            offset = m * 100.
            runtime.append(dict(research_id=rid, module_id=weather, kind='module', start_s=offset,
                                end_s=offset + 100, cycle_id='', step_id='', phase='',
                                I_duration_s=None, presented=True))
            g_time, x_time = offset, offset + .15
            for cycle in range(3):
                for step in STEPS[weather]:
                    ideal = spec['ideal_steps'][weather][step]
                    g_duration = ideal * (1.08 if condition == 'B' and cycle == 1 else 1)
                    x_duration = ideal + float(rng.normal(0, .25))
                    phase = 'hold' if step.startswith('hold') else 'exhale' if step.startswith('exhale') else 'inhale'
                    runtime.append(dict(research_id=rid, module_id=weather, kind='G', start_s=g_time,
                                        end_s=g_time + g_duration, cycle_id=f'G{cycle}', step_id=step,
                                        phase=phase, I_duration_s=ideal, presented=True))
                    unknown = i % 9 == 0 and weather == 'fade'
                    annotations.append(dict(research_id=rid, module_id=weather, cycle_id=f'X{cycle}',
                                            step_id=step, phase=phase, start_s=x_time, end_s=x_time + x_duration,
                                            status='UNKNOWN' if unknown else 'OBSERVED',
                                            source='independent_annotation', validation_ref='SYNTHETIC_LABELS'))
                    g_time += g_duration
                    x_time += x_duration
            for kind in (['adaptation'] if condition == 'B' else []) + (['pause', 'help', 'exit'] if i == 7 and m == 3 else []):
                runtime.append(dict(research_id=rid, module_id=weather, kind=kind, start_s=offset + 60,
                                    end_s=offset + (65 if kind == 'pause' else 60.01), cycle_id='',
                                    step_id='', phase='', I_duration_s=None, presented=False))
        origin = 100_000_000_000
        recording = CandidateRecording(root / 'p02', rid, 'replay', {'synthetic': True})
        for packet_index in range(12):
            raw = bytes([0x14, 7, packet_index, 8]) + struct.pack('>8h',
                         *[int(v) for v in rng.integers(780, 900, 8)])
            gap = 5_000_000_000 if i == 0 and packet_index >= 6 else 0
            recording.record(raw, origin + int(packet_index * .5e9) + gap)
        recording.record(bytes([0x41, 0]) + struct.pack('>9h', *range(1000, 1009)), origin + 12_000_000_000)
        recording.record(bytes([0x0F, 0x12, 0, 0]) + struct.pack('>6h', 1, 2, 3, 4, 5, 6) + bytes(4),
                         origin + 12_100_000_000)
        recording.close('SYNTHETIC_COMPLETE')
        device_index.append(dict(research_id=rid, archive_ref=recording.path.relative_to(root).as_posix(),
                                 host_origin_ns=origin))
    for cohort, count in [('survey', 5), ('pilot', 2)]:
        for i in range(count):
            allocations.append(dict(research_id=f'SYN-{cohort}-{i}', cohort=cohort, condition=None,
                                    order_id=None, randomized=False, completed=False, withdrawn=False))
    definitions = [('allocations', 'allocations', allocations), ('questionnaires', 'questionnaires', questions),
                   ('runtime', 'runtime_facts', runtime), ('annotations', 'annotations', annotations),
                   ('device_index', 'device_streams', device_index)]
    artifacts = []
    for identifier, family, rows in definitions:
        path = root / f'{identifier}.csv'
        save_frame(path, pd.DataFrame(rows))
        artifacts.append(_artifact(root, path, identifier, family))
    write_json(root / 'analysis_spec.json', spec)
    artifacts.append(_artifact(root, root / 'analysis_spec.json', 'configuration', 'configuration_build'))
    for i, path in enumerate(sorted((root / 'p02').rglob('*'))):
        if path.is_file():
            artifacts.append(_artifact(root, path, f'raw-{i}', 'device_streams'))
    bundle = dict(schema_version='1.0', bundle_id='SYNTHETIC-COHORT', session_ref='SYNTHETIC-COHORT',
                  families=['device_streams', 'runtime_facts', 'questionnaires', 'allocations',
                            'annotations', 'configuration_build'], artifacts=artifacts)
    write_json(root / 'bundle.json', bundle)
    return root / 'bundle.json'


def _artifact(root, path, identifier, family):
    return dict(family=family, artifact_id=identifier, location_type='local_file',
                location=path.relative_to(root).as_posix(), content_kind='raw_evidence',
                hash_strategy='byte_sha256', content_sha256=digest(path),
                observed_or_derived='observed', reason_code=None)
