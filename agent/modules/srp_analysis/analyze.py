"""Participant-only analysis and fixed report production."""
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .io import digest, new_output, save_frame, write_json
from .report import figures, write_report
from .statistics import MODEL, NotEstimable, analyze_primary


def analyze(prepared, output):
    prepared = Path(prepared).resolve()
    metadata = json.loads((prepared / 'prepared.json').read_text(encoding='utf-8'))
    for filename, expected in metadata['prepared_hashes'].items():
        if digest(prepared / filename) != expected:
            raise ValueError('PREPARED_INPUT_CHANGED:' + filename)
    if digest(prepared / 'analysis_spec.json') != metadata['spec_hash']:
        raise ValueError('ANALYSIS_SPEC_CHANGED_AFTER_PREPARE')
    spec = json.loads((prepared / 'analysis_spec.json').read_text(encoding='utf-8'))
    people = pd.read_csv(prepared / 'participants.csv')
    data = people.loc[people.cohort.eq('formal') & people.randomized.eq(True)].copy().reset_index(drop=True)
    modules = pd.read_csv(prepared / 'participant_modules.csv')
    events, runtime = pd.read_csv(prepared / 'events.csv'), pd.read_csv(prepared / 'runtime_facts.csv')
    qc = pd.read_csv(prepared / 'qc.csv')
    out = new_output(output, prepared)
    (out / 'imputations').mkdir()
    def save_completion(chain, frame):
        save_frame(out / 'imputations' / f'completion-{chain + 1:03d}.csv',
                   frame[['research_id', 'B', 'order_id', 'NA_pre', 'NA_post']])
    try:
        primary, sensitivity = analyze_primary(data, spec, save_completion)
    except NotEstimable as error:
        primary, sensitivity = dict(status='NOT_ESTIMABLE', reason=str(error), n=len(data)), []
    versions = {p: importlib.metadata.version(p) for p in
                ('numpy', 'scipy', 'pandas', 'statsmodels', 'matplotlib', 'reportlab')}
    result = dict(schema_version='1.0', evidence_class=spec['evidence_class'],
                  status='SOFTWARE_OUTPUT_NOT_RESEARCH_ACCEPTANCE', formal_analysis_authorized=False,
                  input=metadata, model=MODEL, primary=primary, sensitivity=sensitivity,
                  spec=spec, versions=versions,
                  prepared_hashes={p.name: digest(p) for p in sorted(prepared.glob('*.csv'))},
                  code_hashes={p.name: digest(p) for p in sorted(Path(__file__).parent.glob('*.py'))})
    write_json(out / 'analysis.json', result)
    save_frame(out / 'estimates.csv', pd.DataFrame([primary]))
    save_frame(out / 'missingness_sensitivity.csv', pd.DataFrame(sensitivity) if sensitivity else pd.DataFrame(columns=['analysis_set', 'status', 'reason']))
    save_frame(out / 'cohort_counts.csv', people.groupby(['cohort', 'randomized'], dropna=False).size().reset_index(name='n'))
    secondary = []
    for condition, group in data.groupby('condition'):
        for metric in ('PA_pre', 'PA_post', 'effort', 'comfort', 'I_lower', 'I_upper', 'G_lower', 'G_upper'):
            values = group[metric].dropna()
            secondary.append(dict(condition=condition, outcome=metric, n=len(values), missing=len(group) - len(values),
                                  mean=values.mean(), sd=values.std(), median=values.median(),
                                  interpretation='DESCRIPTIVE_SECONDARY_OR_EXPLORATORY_NOT_CONFIRMATORY'))
    save_frame(out / 'secondary_results.csv', pd.DataFrame(secondary, columns=[
        'condition', 'outcome', 'n', 'missing', 'mean', 'sd', 'median', 'interpretation']))
    distributions = []
    for condition, group in data.groupby('condition'):
        for score in ('NA_pre', 'NA_post', 'PA_pre', 'PA_post'):
            observed = group[score].dropna()
            distributions.append(dict(condition=condition, score=score, n_observed=len(observed),
                n_missing=len(group) - len(observed), minimum=observed.min(), maximum=observed.max(),
                floor_count=int(observed.eq(10).sum()), ceiling_count=int(observed.eq(50).sum()),
                floor_fraction=float(observed.eq(10).mean()) if len(observed) else None,
                ceiling_fraction=float(observed.eq(50).mean()) if len(observed) else None))
    save_frame(out / 'score_distribution.csv', pd.DataFrame(distributions, columns=[
        'condition', 'score', 'n_observed', 'n_missing', 'minimum', 'maximum',
        'floor_count', 'ceiling_count', 'floor_fraction', 'ceiling_fraction']))
    cost_fields = ['budget_s', 'adaptation_count', 'help_count', 'pause_s', 'exit_count']
    costs = data[['research_id', 'condition']].copy()
    for field in cost_fields:
        totals = modules.groupby('research_id')[field].sum(min_count=4)
        costs[field] = costs.research_id.map(totals)
    costs['observed_modules'] = costs.research_id.map(
        modules.loc[modules.budget_s.notna()].groupby('research_id').size()).fillna(0).astype(int)
    save_frame(out / 'participant_costs.csv', costs)
    questions = pd.read_csv(prepared / 'questionnaire_items.csv')
    process = (questions.groupby(['instrument', 'timepoint', 'response_status'], dropna=False)
               .size().reset_index(name='responses')) if len(questions) else pd.DataFrame(columns=['instrument', 'timepoint', 'response_status', 'responses'])
    save_frame(out / 'questionnaire_process.csv', process)
    save_frame(out / 'result_sources.csv', pd.DataFrame([
        dict(output='estimates.csv', input_table='participants.csv', fields='B;NA_pre;NA_post;order_id',
             method='ANCOVA_HC3_PMM_RUBIN', interpretation='B_minus_A_whole_package'),
        dict(output='missingness_sensitivity.csv', input_table='participants.csv', fields='B;NA_pre;NA_post;order_id',
             method='complete_case_and_MNAR_delta', interpretation='sensitivity_not_new_primary'),
        dict(output='secondary_results.csv', input_table='participants.csv', fields='PA_pre;PA_post;effort;comfort;I_lower;G_lower',
             method='participant_descriptive', interpretation='secondary_or_exploratory'),
        dict(output='participant_modules.csv', input_table='events.csv;runtime_facts.csv', fields='module_id;start_s;end_s;step_id;phase;validation_ref',
             method='independent_X_vs_I_and_presented_G_fixed_T', interpretation='I_G_cost_coverage_separate'),
        dict(output='participant_costs.csv', input_table='participant_modules.csv', fields='budget_s;adaptation_count;help_count;pause_s;exit_count',
             method='sum_four_observed_modules_no_missing_as_zero', interpretation='participant_cost_distribution'),
        dict(output='hrv_windows.csv', input_table='signals.csv;analysis_spec.json', fields='kind;segment_id;value;rr_units;validation_ref',
             method='fixed_contiguous_qualified_RR_windows', interpretation='exploratory_not_affect_proof')]))
    save_frame(out / 'participant_modules.csv', modules)
    save_frame(out / 'participants.csv', people)
    save_frame(out / 'qc.csv', qc)
    for filename in ('hrv_windows.csv', 'questionnaire_items.csv', 'events.csv', 'runtime_facts.csv', 'signals.csv'):
        (out / filename).write_bytes((prepared / filename).read_bytes())
    figures(data, modules, events, runtime, primary, sensitivity, out / 'figures', spec['evidence_class'], costs)
    write_report(out, data, modules, qc, result, secondary)
    from .schema import write_dictionary
    write_dictionary(out)
    return out
