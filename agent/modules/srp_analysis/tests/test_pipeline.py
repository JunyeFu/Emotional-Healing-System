"""End-to-end synthetic data contracts and real observed failure regressions."""
import json
from pathlib import Path
import socket
import sys

import numpy as np
import pandas as pd
import pytest
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from srp_analysis.analyze import analyze
from srp_analysis.demo import make_demo, candidate_spec
from srp_analysis.io import digest, write_json
from srp_analysis.prepare import prepare, reconstruct
from srp_analysis.statistics import analyze_primary, fit_primary, NotEstimable
from srp_analysis.power import run_power_grid


@pytest.fixture(scope='module')
def sample(tmp_path_factory):
    root = tmp_path_factory.mktemp('closure')
    bundle = make_demo(root / 'originals', n=24, scenario='missing')
    before = {p.relative_to(bundle.parent).as_posix(): digest(p) for p in bundle.parent.rglob('*') if p.is_file()}
    prepared = prepare(bundle, root / 'prepared')
    return root, bundle, prepared, before


def test_prepare_all_six_families_and_fixed_participant_unit(sample):
    _, _, prepared, _ = sample
    assert json.loads((prepared / 'input_validation.json').read_text())['ok']
    people = pd.read_csv(prepared / 'participants.csv')
    assert len(people.loc[people.cohort.eq('formal') & people.randomized]) == 24
    assert len(people) == 31
    formal = people.loc[people.cohort.eq('formal')]
    assert formal.NA_post.isna().sum() == 2
    assert formal.NA_pre.isna().sum() == 1
    modules = pd.read_csv(prepared / 'participant_modules.csv')
    for prefix in ('I', 'G'):
        known = modules.dropna(subset=[prefix + '_C_s'])
        np.testing.assert_allclose(known[prefix + '_C_s'] + known[prefix + '_K_s'] + known[prefix + '_U_s'], known.budget_s)
        assert known[prefix + '_lower'].between(0, 1).all()
        assert known[prefix + '_upper'].ge(known[prefix + '_lower']).all()


def test_p02_gap_not_stitched_and_raw_values_preserved(sample):
    _, _, prepared, _ = sample
    signals = pd.read_csv(prepared / 'signals.csv')
    assert len(signals.loc[signals.kind.eq('acc') & signals.research_id.eq('SYN-000')]) == 2
    hrv = pd.read_csv(prepared / 'hrv_windows.csv')
    assert 'SYN-000' not in set(hrv.research_id)
    assert 'SYN-001' in set(hrv.research_id)
    assert signals.loc[signals.kind.eq('rr')].time_basis.eq('PACKET_RECEIVED').all()


def test_full_mi_reproducible_readonly_no_network_and_pdf(sample, monkeypatch):
    root, bundle, prepared, before = sample
    def no_socket(*a, **k):
        raise AssertionError('Analysis must not open a network socket')
    monkeypatch.setattr(socket, 'socket', no_socket)
    first, second = analyze(prepared, root / 'results-1'), analyze(prepared, root / 'results-2')
    a = json.loads((first / 'analysis.json').read_text(encoding='utf-8'))
    b = json.loads((second / 'analysis.json').read_text(encoding='utf-8'))
    assert a == b
    assert a['primary']['n'] == 24 and a['primary']['imputations'] == 50
    assert a['primary']['beta'] < 0
    assert a['evidence_class'] == 'SYNTHETIC' and not a['formal_analysis_authorized']
    assert len(list((first / 'imputations').glob('*.csv'))) == 50
    people = pd.read_csv(prepared / 'participants.csv').query("cohort == 'formal'").reset_index(drop=True)
    for path in (first / 'imputations').glob('*.csv'):
        completed = pd.read_csv(path)
        for col in ('NA_pre', 'NA_post'):
            assert completed[col].between(10, 50).all()
            assert set(completed.loc[people[col].isna(), col]).issubset(set(people[col].dropna()))
            np.testing.assert_allclose(completed.loc[people[col].notna(), col], people.loc[people[col].notna(), col])
    assert len(list((first / 'figures').glob('*.png'))) == 6
    assert len(PdfReader(first / 'report.pdf').pages) >= 4
    after = {p.relative_to(bundle.parent).as_posix(): digest(p) for p in bundle.parent.rglob('*') if p.is_file()}
    assert before == after
    assert digest(first / 'report.pdf') == digest(second / 'report.pdf')


def test_missing_signals_keep_valid_panas(sample):
    root, bundle, _, _ = sample
    value = json.loads(bundle.read_text())
    value['artifacts'] = [a for a in value['artifacts'] if a['family'] != 'device_streams']
    partial = bundle.parent / 'partial.json'
    write_json(partial, value)
    prepared = prepare(partial, root / 'without-signals')
    people = pd.read_csv(prepared / 'participants.csv')
    assert people.query("cohort == 'formal'").NA_post.notna().sum() == 22
    assert not json.loads((prepared / 'input_validation.json').read_text())['ok']


def test_corrupt_input_rejected_and_output_never_overwrites(tmp_path):
    bundle = make_demo(tmp_path / 'originals', n=16, scenario='benefit')
    with pytest.raises(ValueError, match='OVERLAP'):
        prepare(bundle, bundle.parent / 'derived')
    q = bundle.parent / 'questionnaires.csv'
    q.write_bytes(q.read_bytes() + b'\n')
    with pytest.raises(ValueError, match='HASH_MISMATCH'):
        prepare(bundle, tmp_path / 'corrupt')


def test_changed_prepared_tables_are_not_silently_consumed(sample):
    root, _, prepared, _ = sample
    import shutil
    changed = root / 'changed-prepared'
    shutil.copytree(prepared, changed)
    with (changed / 'participants.csv').open('ab') as stream:
        stream.write(b'\n')
    with pytest.raises(ValueError, match='PREPARED_INPUT_CHANGED'):
        analyze(changed, root / 'changed-output')


def test_selected_form_with_contact_column_is_rejected(tmp_path):
    from srp_governance.errors import GovernanceError
    bundle = make_demo(tmp_path / 'originals', n=16, scenario='benefit')
    value = json.loads(bundle.read_text())
    path = bundle.parent / 'questionnaires.csv'
    questions = pd.read_csv(path)
    questions['phone'] = '13800000000'
    questions.to_csv(path, index=False)
    for item in value['artifacts']:
        if item['artifact_id'] == 'questionnaires':
            item['content_sha256'] = digest(path)
    write_json(bundle, value)
    with pytest.raises(GovernanceError):
        prepare(bundle, tmp_path / 'private-output')


@pytest.mark.parametrize('effect, expected', [(-8, 'B_LOWER'), (8, 'A_LOWER'), (0, 'DIRECTION_UNCERTAIN')])
def test_known_direction_and_null(effect, expected):
    rng = np.random.default_rng(99)
    n = 48
    frame = pd.DataFrame({'B': np.arange(n) % 2, 'order_id': 1 + (np.arange(n) // 2) % 4,
                          'NA_pre': rng.integers(18, 34, n)})
    frame['NA_post'] = 12 + .4 * frame.NA_pre + effect * frame.B + rng.normal(0, .8, n)
    assert fit_primary(frame)['interpretation'].startswith(expected)


def test_rank_deficiency_no_silent_covariate_removal():
    frame = pd.DataFrame({'B': [0, 1] * 15, 'order_id': [1] * 30, 'NA_pre': [20] * 30, 'NA_post': [22] * 30})
    with pytest.raises(NotEstimable, match='IDENTIFIABLE'):
        fit_primary(frame)


def test_unvalidated_or_flat_proxy_does_not_supply_actual_x(sample):
    _, _, prepared, _ = sample
    runtime = pd.read_csv(prepared / 'runtime_facts.csv')
    people = pd.read_csv(prepared / 'participants.csv')
    original = pd.read_csv(prepared / 'events.csv')
    annotations = original.rename(columns={'observed': 'was_observed'})
    annotations['status'] = 'OBSERVED'
    annotations['source'] = 'unvalidated_acc_proxy'
    _, modules = reconstruct(runtime, annotations, people, candidate_spec())
    known = modules.dropna(subset=['budget_s'])
    assert known.observed_s.eq(0).all() and known.unknown_s.eq(known.budget_s).all()


def test_changing_guide_cannot_change_common_I_attainment(sample):
    _, _, prepared, _ = sample
    people = pd.read_csv(prepared / 'participants.csv')
    runtime = pd.read_csv(prepared / 'runtime_facts.csv')
    original = pd.read_csv(prepared / 'events.csv')
    annotations = original.copy()
    annotations['status'] = np.where(annotations.observed, 'OBSERVED', 'UNKNOWN')
    _, before = reconstruct(runtime, annotations, people, candidate_spec())
    runtime.loc[runtime.kind.eq('G'), ['start_s', 'end_s']] += .3
    _, after = reconstruct(runtime, annotations, people, candidate_spec())
    pd.testing.assert_series_equal(before.I_lower, after.I_lower)


def test_missing_module_cannot_reweight_remaining_three(sample):
    _, _, prepared, _ = sample
    people = pd.read_csv(prepared / 'participants.csv')
    runtime = pd.read_csv(prepared / 'runtime_facts.csv')
    events = pd.read_csv(prepared / 'events.csv')
    events['status'] = np.where(events.observed, 'OBSERVED', 'UNKNOWN')
    runtime = runtime.loc[~(runtime.research_id.eq('SYN-001') & runtime.module_id.eq('snow'))]
    _, modules = reconstruct(runtime, events, people, candidate_spec())
    assert modules.loc[modules.research_id.eq('SYN-001') & modules.module_id.eq('snow'), 'status'].iloc[0] == 'MODULE_NOT_OBSERVED'
    assert modules.loc[modules.research_id.eq('SYN-001'), 'I_lower'].isna().any()


def test_small_power_grid_runs_actual_missingness_model():
    first = run_power_grid(replications=2, n_grid=(30,), effect_grid=(0,), missing_rates=(.15,))
    assert first == run_power_grid(replications=2, n_grid=(30,), effect_grid=(0,), missing_rates=(.15,))
    assert first['imputations'] == 50 and first['iterations'] == 20
    assert first['cells'][0]['valid_replications'] == 2
    assert not first['formal_n_frozen']


def test_missing_runtime_and_annotations_block_only_dependent_metrics(sample):
    root, bundle, _, _ = sample
    value = json.loads(bundle.read_text())
    value['artifacts'] = [a for a in value['artifacts']
                          if a['artifact_id'] not in ('runtime', 'annotations')]
    partial = bundle.parent / 'without-runtime.json'
    write_json(partial, value)
    prepared = prepare(partial, root / 'without-runtime')
    output = analyze(prepared, root / 'without-runtime-results')
    result = json.loads((output / 'analysis.json').read_text(encoding='utf-8'))
    assert result['primary']['status'] == 'ESTIMATED'
    assert result['primary']['n'] == 24
    costs = pd.read_csv(output / 'participant_costs.csv')
    assert costs.adaptation_count.isna().all()


def test_missing_guide_is_unknown_not_execution_failure(sample):
    _, _, prepared, _ = sample
    people = pd.read_csv(prepared / 'participants.csv')
    runtime = pd.read_csv(prepared / 'runtime_facts.csv')
    events = pd.read_csv(prepared / 'events.csv')
    events['status'] = np.where(events.observed, 'OBSERVED', 'UNKNOWN')
    _, before = reconstruct(runtime, events, people, candidate_spec())
    _, after = reconstruct(runtime.loc[~runtime.kind.eq('G')], events, people, candidate_spec())
    pd.testing.assert_series_equal(before.I_lower, after.I_lower)
    available = after.dropna(subset=['budget_s'])
    assert available.G_K_s.eq(0).all()
    assert available.G_U_s.eq(available.budget_s).all()
    assert available.G_observable.isna().all()


def test_survey_only_batch_reports_no_formal_model_without_mixing_cohorts(tmp_path):
    bundle = make_demo(tmp_path / 'originals', n=16, scenario='benefit')
    value = json.loads(bundle.read_text())
    path = bundle.parent / 'allocations.csv'
    allocations = pd.read_csv(path)
    allocations.loc[allocations.cohort.eq('formal'), 'cohort'] = 'survey'
    allocations['randomized'] = False
    allocations.to_csv(path, index=False)
    for item in value['artifacts']:
        if item['artifact_id'] == 'allocations':
            item['content_sha256'] = digest(path)
    write_json(bundle, value)
    output = analyze(prepare(bundle, tmp_path / 'prepared'), tmp_path / 'results')
    primary = json.loads((output / 'analysis.json').read_text(encoding='utf-8'))['primary']
    assert primary['status'] == 'NOT_ESTIMABLE' and primary['n'] == 0
    assert pd.read_csv(output / 'secondary_results.csv').empty
