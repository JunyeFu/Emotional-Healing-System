"""Six-family inputs -> scored participants, independent events and quality tables."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import BASELINE
from .io import load_bundle, new_output, save_frame, write_json
from .signals import decode_recordings

WEATHERS = ('storm', 'heat', 'fade', 'snow')
STEPS = {'storm': ('inhale_1', 'hold_1', 'exhale_1', 'hold_2'),
         'heat': ('inhale_1', 'exhale_1'), 'snow': ('inhale_1', 'exhale_1'),
         'fade': ('inhale_1', 'inhale_2', 'exhale_1')}
RUNTIME_COLUMNS = ['research_id', 'module_id', 'kind', 'start_s', 'end_s', 'cycle_id',
                   'step_id', 'phase', 'I_duration_s', 'presented']
ANNOTATION_COLUMNS = ['research_id', 'module_id', 'cycle_id', 'step_id', 'phase',
                      'start_s', 'end_s', 'status', 'source', 'validation_ref']
QUESTION_COLUMNS = ['research_id', 'instrument', 'form_id', 'timepoint', 'item_id', 'value',
                    'response_status', 'measured_at', 'measurement_delay_s']
EVENT_COLUMNS = ['research_id', 'module_id', 'cycle_id', 'step_id', 'phase', 'start_s', 'end_s',
                 'observed', 'source', 'validation_ref', 'exposure_s', 'I_duration_error_s',
                 'G_duration_error_s', 'I_compliant', 'G_compliant', 'reason']
MODULE_COLUMNS = ['research_id', 'module_id', 'status', 'budget_s', 'observed_s', 'unknown_s',
                  'observed_coverage', 'I_absolute_error_s', 'G_absolute_error_s',
                  'adaptation_count', 'help_count', 'pause_s', 'exit_count'] + [
                      f'{p}_{s}' for p in ('I', 'G') for s in
                      ('C_s', 'K_s', 'U_s', 'lower', 'upper', 'observable')]


def score_scale(rows, key):
    values = rows.loc[rows.item_id.isin(key)]
    if values.item_id.duplicated().any():
        raise ValueError('DUPLICATE_QUESTIONNAIRE_ITEM')
    if set(values.item_id) != set(key) or values.value.isna().any():
        return None
    numbers = pd.to_numeric(values.value, errors='raise')
    if not numbers.between(1, 5).all() or not numbers.eq(numbers.round()).all():
        raise ValueError('PANAS_ITEM_REQUIRES_INTEGER_1_TO_5')
    return int(numbers.sum())


def _empty(columns):
    return pd.DataFrame(columns=columns)


def _check_intervals(rows, group_columns):
    if rows.empty:
        return
    numbers = rows[['start_s', 'end_s']].to_numpy(float)
    if not np.isfinite(numbers).all() or (numbers[:, 1] <= numbers[:, 0]).any():
        raise ValueError('INVALID_OR_NONFINITE_EVENT_INTERVAL')
    for _, group in rows.groupby(group_columns):
        ordered = group.sort_values('start_s')
        if (ordered.start_s.to_numpy()[1:] < ordered.end_s.to_numpy()[:-1] - 1e-9).any():
            raise ValueError('OVERLAPPING_EVENT_INTERVALS')


def build_participants(allocations, questions, spec):
    required = {'research_id', 'cohort', 'condition', 'order_id', 'randomized', 'completed', 'withdrawn'}
    if not required.issubset(allocations):
        raise ValueError('ALLOCATION_COLUMNS_MISSING')
    if allocations.research_id.duplicated().any():
        raise ValueError('DUPLICATE_PARTICIPANT_ALLOCATION')
    if not allocations.cohort.isin(['formal', 'pilot', 'survey']).all():
        raise ValueError('UNKNOWN_COHORT')
    for name in ('randomized', 'completed', 'withdrawn'):
        if not allocations[name].isin([True, False, 0, 1]).all():
            raise ValueError('INVALID_ALLOCATION_BOOLEAN')
    result = allocations.copy()
    selected = result.cohort.eq('formal') & result.randomized.eq(True)
    if not result.loc[selected, 'condition'].isin(['A', 'B']).all():
        raise ValueError('UNKNOWN_CONDITION')
    if not result.loc[selected, 'order_id'].isin([1, 2, 3, 4]).all():
        raise ValueError('UNKNOWN_RANDOMIZATION_ORDER')
    result['B'] = result.condition.map({'A': 0, 'B': 1})
    for col in ('NA_pre', 'NA_post', 'PA_pre', 'PA_post', 'effort', 'comfort'):
        result[col] = np.nan
    if questions.empty:
        return result
    q_required = {'research_id', 'instrument', 'form_id', 'timepoint', 'item_id', 'value',
                  'response_status', 'measured_at', 'measurement_delay_s'}
    if not q_required.issubset(questions):
        raise ValueError('QUESTIONNAIRE_COLUMNS_MISSING')
    if not questions.research_id.isin(result.research_id).all():
        raise ValueError('QUESTIONNAIRE_WITHOUT_ALLOCATION_RECORD')
    if questions.duplicated(['research_id', 'instrument', 'timepoint', 'item_id']).any():
        raise ValueError('DUPLICATE_QUESTIONNAIRE_ITEM')
    for rid, rows in questions.groupby('research_id'):
        index = result.index[result.research_id.eq(rid)][0]
        for when in ('pre', 'post'):
            items = rows.loc[rows.instrument.eq('PANAS') & rows.timepoint.eq(when)].copy()
            if not items.empty:
                if not items.form_id.eq(spec['panas_form']['form_id']).all():
                    raise ValueError('QUESTIONNAIRE_FORM_VERSION_MISMATCH')
                if not items.item_id.isin(spec['panas_form']['NA'] + spec['panas_form']['PA']).all():
                    raise ValueError('QUESTIONNAIRE_ITEM_NOT_IN_SELECTED_KEY')
                if not items.response_status.isin(['RESPONDED', 'SKIPPED', 'TIMEOUT', 'NOT_PRESENTED']).all():
                    raise ValueError('UNKNOWN_QUESTIONNAIRE_RESPONSE_STATUS')
                if items.loc[~items.response_status.eq('RESPONDED'), 'value'].notna().any():
                    raise ValueError('NONRESPONSE_HAS_VALUE')
                items.loc[~items.response_status.eq('RESPONDED'), 'value'] = np.nan
            for scale in ('NA', 'PA'):
                result.loc[index, f'{scale}_{when}'] = score_scale(items, spec['panas_form'][scale])
        for instrument in ('effort', 'comfort'):
            item = rows.loc[rows.instrument.eq(instrument) & rows.response_status.eq('RESPONDED')]
            if len(item) > 1:
                raise ValueError('DUPLICATE_SINGLE_ITEM_OUTCOME')
            if len(item):
                value = float(item.iloc[0].value)
                if not 0 <= value <= 10:
                    raise ValueError('EFFORT_COMFORT_REQUIRES_0_TO_10')
                result.loc[index, instrument] = value
    return result


def reconstruct(runtime, annotations, participants, spec):
    if runtime.empty:
        runtime = _empty(RUNTIME_COLUMNS)
    if annotations.empty:
        annotations = _empty(ANNOTATION_COLUMNS)
    if not set(RUNTIME_COLUMNS).issubset(runtime) or not set(ANNOTATION_COLUMNS).issubset(annotations):
        raise ValueError('EVENT_COLUMNS_MISSING')
    known_ids = set(participants.research_id)
    if not set(runtime.research_id).issubset(known_ids) or not set(annotations.research_id).issubset(known_ids):
        raise ValueError('EVENT_WITHOUT_ALLOCATION')
    events, modules = [], []
    tolerance = spec.get('scoring_tolerance_s')
    for rid in participants.research_id:
        for weather in WEATHERS:
            facts = runtime.loc[runtime.research_id.eq(rid) & runtime.module_id.eq(weather)]
            bounds = facts.loc[facts.kind.eq('module')]
            if len(bounds) != 1:
                modules.append(dict(research_id=rid, module_id=weather, status='MODULE_NOT_OBSERVED'))
                continue
            start, end = float(bounds.iloc[0].start_s), float(bounds.iloc[0].end_s)
            if not np.isfinite([start, end]).all() or end <= start:
                raise ValueError('INVALID_MODULE_BUDGET')
            budget = end - start
            guide = facts.loc[facts.kind.eq('G') & facts.presented.eq(True)].sort_values('start_s')
            _check_intervals(guide, ['research_id', 'module_id'])
            actual = annotations.loc[annotations.research_id.eq(rid) & annotations.module_id.eq(weather)].sort_values('start_s')
            _check_intervals(actual, ['research_id', 'module_id'])
            observed = compliant_i = compliant_g = 0.
            observable_i = observable_g = 0.
            signed_errors_i, signed_errors_g = [], []
            scored = tolerance is not None
            for _, cycle in actual.groupby('cycle_id', sort=False):
                ordered_steps = tuple(cycle.step_id)
                expected_phases = tuple('hold' if s.startswith('hold') else 'exhale' if s.startswith('exhale') else 'inhale'
                                        for s in STEPS[weather])
                complete = ordered_steps == STEPS[weather] and tuple(cycle.phase) == expected_phases
                for row in cycle.itertuples():
                    duration = row.end_s - row.start_s
                    exposure = max(0., min(end, row.end_s) - max(start, row.start_s))
                    usable = (row.status == 'OBSERVED' and row.source in ('independent_annotation', 'validated_detector')
                              and pd.notna(row.validation_ref) and bool(str(row.validation_ref).strip()) and complete)
                    ideal = spec['ideal_steps'][weather].get(row.step_id)
                    match = guide.loc[guide.step_id.eq(row.step_id)]
                    closest = (match.iloc[(match.start_s - row.start_s).abs().argmin()] if len(match) else None)
                    error_i = duration - ideal if usable and ideal is not None else None
                    error_g = (duration - (closest.end_s - closest.start_s)
                               if usable and closest is not None else None)
                    i_ok = (abs(error_i) <= tolerance if error_i is not None and scored else None)
                    g_ok = (abs(row.start_s - closest.start_s) <= tolerance and
                            abs(row.end_s - closest.end_s) <= tolerance and row.phase == closest.phase
                            if error_g is not None and scored else None)
                    if usable:
                        observed += exposure
                        compliant_i += exposure if i_ok else 0
                        compliant_g += exposure if g_ok else 0
                        if error_i is not None:
                            observable_i += exposure
                            signed_errors_i.append(error_i)
                        if error_g is not None:
                            observable_g += exposure
                            signed_errors_g.append(error_g)
                    events.append(dict(research_id=rid, module_id=weather, cycle_id=row.cycle_id,
                                       step_id=row.step_id, phase=row.phase, start_s=row.start_s, end_s=row.end_s,
                                       observed=usable, source=row.source, validation_ref=row.validation_ref,
                                       exposure_s=exposure, I_duration_error_s=error_i,
                                       G_duration_error_s=error_g, I_compliant=i_ok, G_compliant=g_ok,
                                       reason='OBSERVED' if usable else 'UNKNOWN_OR_INCOMPLETE_CYCLE'))
            if observed > budget + 1e-6:
                raise ValueError('OBSERVED_EXPOSURE_EXCEEDS_BUDGET')
            costs = {kind: facts.loc[facts.kind.eq(kind)] for kind in ('adaptation', 'pause', 'help', 'exit')}
            row = dict(research_id=rid, module_id=weather, status='SCORED' if scored else 'TOLERANCE_UNFROZEN',
                       budget_s=budget, observed_s=observed, unknown_s=budget - observed,
                       observed_coverage=observed / budget,
                       I_absolute_error_s=float(np.mean(np.abs(signed_errors_i))) if signed_errors_i else None,
                       G_absolute_error_s=float(np.mean(np.abs(signed_errors_g))) if signed_errors_g else None,
                       adaptation_count=len(costs['adaptation']), help_count=len(costs['help']),
                       pause_s=float((costs['pause'].end_s - costs['pause'].start_s).sum()),
                       exit_count=len(costs['exit']))
            for prefix, c, known in [('I', compliant_i, observable_i), ('G', compliant_g, observable_g)]:
                row.update({f'{prefix}_C_s': c if scored else None,
                            f'{prefix}_K_s': known - c if scored else None,
                            f'{prefix}_U_s': budget - known,
                            f'{prefix}_lower': c / budget if scored else None,
                            f'{prefix}_upper': (c + budget - known) / budget if scored else None,
                            f'{prefix}_observable': c / known if scored and known else None})
            modules.append(row)
    return pd.DataFrame(events, columns=EVENT_COLUMNS), pd.DataFrame(modules, columns=MODULE_COLUMNS)


def prepare(bundle_path, output):
    base, validation, artifact = load_bundle(bundle_path)
    config_path = artifact('configuration')
    if config_path is None:
        raise ValueError('CONFIGURATION_REQUIRED_FOR_SCORING')
    spec = json.loads(config_path.read_text(encoding='utf-8-sig'))
    from srp_governance.privacy import privacy_lint_manifest
    privacy_lint_manifest(spec)
    if spec['design_baseline_id'] != BASELINE:
        raise ValueError('UNEXPECTED_DESIGN_BASELINE')
    for key, minimum in [('imputations', 2), ('iterations', 1), ('pmm_k', 1)]:
        if type(spec[key]) is not int or spec[key] < minimum:
            raise ValueError('INVALID_IMPUTATION_CONFIGURATION')
    if spec['evidence_class'] not in ('SYNTHETIC', 'DEVELOPMENT_UNVERIFIED', 'REAL_PRELIMINARY'):
        raise ValueError('ANALYSIS_EVIDENCE_CLASS_INVALID')
    repo = Path(__file__).resolve().parents[3]
    if spec['evidence_class'] != 'SYNTHETIC' and base.is_relative_to(repo):
        raise ValueError('REAL_ORIGINALS_MUST_BE_OUTSIDE_REPOSITORY')
    key = spec['panas_form']
    if len(key['NA']) != 10 or len(key['PA']) != 10 or len(set(key['NA'] + key['PA'])) != 20:
        raise ValueError('PANAS_REQUIRES_TWO_DISJOINT_TEN_ITEM_KEYS')
    allocations, questions = artifact('allocations', True), artifact('questionnaires', True)
    if questions.empty:
        questions = _empty(QUESTION_COLUMNS)
    participants = build_participants(allocations, questions, spec)
    runtime, annotations = artifact('runtime', True), artifact('annotations', True)
    if runtime.empty:
        runtime = _empty(RUNTIME_COLUMNS)
    events, modules = reconstruct(runtime, annotations, participants, spec)
    out = new_output(output, base)
    signal_qc, hrv = decode_recordings(artifact('device_index', True), base, out, spec)
    if len(hrv):
        save_frame(out / 'hrv_windows.csv', hrv)
    else:
        save_frame(out / 'hrv_windows.csv', _empty(['research_id', 'segment_id', 'window_s', 'RMSSD_ms', 'SDNN_ms']))
    for prefix in ('I', 'G'):
        for measure in ('lower', 'upper', 'observable'):
            column = f'{prefix}_{measure}'
            participants[column] = np.nan
            if column in modules:
                for rid, values in modules.groupby('research_id'):
                    if len(values) == 4 and values[column].notna().all():
                        participants.loc[participants.research_id.eq(rid), column] = values[column].mean()
    for name, frame in [('participants', participants), ('participant_modules', modules),
                        ('events', events),
                        ('questionnaire_items', questions), ('runtime_facts', runtime)]:
        save_frame(out / f'{name}.csv', frame)
    qc = list(signal_qc)
    qc.append(dict(domain='bundle', status='COMPLETE' if validation['ok'] else 'INCOMPLETE',
                   reason=';'.join(validation['errors']), research_id=''))
    for row in participants.itertuples():
        qc.append(dict(domain='PANAS', status='OBSERVED' if pd.notna(row.NA_post) else 'MISSING_POST',
                       reason='SENSOR_FAILURE_DOES_NOT_DROP_PANAS', research_id=row.research_id))
    save_frame(out / 'qc.csv', pd.DataFrame(qc))
    write_json(out / 'analysis_spec.json', spec)
    write_json(out / 'input_validation.json', validation)
    from .io import digest
    write_json(out / 'prepared.json', dict(schema_version='1.0', evidence_class=spec['evidence_class'],
               design_baseline_id=BASELINE, bundle_input_identity=validation['input_identity'],
               source_bundle=str(Path(bundle_path).resolve()), formal_analysis_authorized=False,
               prepared_hashes={p.name: digest(p) for p in sorted(out.glob('*.csv'))},
               spec_hash=digest(out / 'analysis_spec.json'),
               research_gates=spec.get('research_gates', {})))
    from .schema import write_dictionary
    write_dictionary(out)
    return out
