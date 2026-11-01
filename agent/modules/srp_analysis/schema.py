"""Machine-readable dictionary for the actual produced tables."""
import pandas as pd

from .io import write_json

DESCRIPTIONS = {
    'research_id': 'Opaque research identifier; no identity mapping included.',
    'cohort': 'survey / pilot / formal; only randomized formal enters primary analysis.',
    'B': '0=fixed open-loop A; 1=native constrained-adaptive B.',
    'order_id': 'Prespecified Williams weather order, 1..4; not observed completion order.',
    'NA_pre': 'NA ten-item sum before allocation reveal; 10..50, incomplete subscale=null.',
    'NA_post': 'NA ten-item sum at primary post time; 10..50, incomplete subscale=null.',
    'PA_pre': 'PA ten-item pre sum, 10..50; secondary.',
    'PA_post': 'PA ten-item post sum, 10..50; secondary.',
    'effort': 'Custom 0..10 item, higher=more effort; not a validated composite.',
    'comfort': 'Custom 0..10 item, higher=more comfortable; not a validated composite.',
    'time_s': 'See time_basis; nominal or packet time is not validated device time.',
    'device_time_ns': 'Original device timestamp if supplied; never inferred.',
    'budget_s': 'Fixed module exposure budget T, not the sum of detected cycles.',
    'observed_s': 'Validated complete-cycle actual X exposure within fixed module budget.',
    'unknown_s': 'T minus observable actual X; not a success or failure label.',
    'I_lower': 'I-compliant actual duration / fixed T; participant mean requires all four modules.',
    'I_upper': '(I-compliant actual duration + unknown duration) / fixed T.',
    'G_lower': 'G-boundary/phase-compliant actual duration / fixed T.',
    'G_upper': '(G-compliant actual duration + unknown duration) / fixed T.',
    'I_observable': 'I-compliant / observable exposure; undefined when observable exposure=0.',
    'G_observable': 'G-compliant / X exposure with comparable presented G; undefined when none.',
    'G_U_s': 'Fixed T minus X exposure with comparable presented G; missing G is unknown, not failure.',
    'observed_modules': 'Modules with runtime budget facts; 0..4; cost totals require all four.',
    'RMSSD_ms': 'Exploratory RMSSD in a contiguous accepted fixed-duration RR window.',
    'SDNN_ms': 'Exploratory sample SD of RR in the same window.',
    'window_start_s': 'Fixed HRV window start relative to this contiguous RR quality run, not a device/experiment clock.',
    'window_end_s': 'Fixed HRV window end; the same target duration for all compared windows.',
    'actual_window_s': 'Observable continuous RR sequence time covering the complete fixed window.',
    'rr_span_s': 'Sum of RR values assigned by their ending beat; may differ from fixed window duration at boundaries.',
    'measured_at': 'Original questionnaire timestamp; no contact fields permitted.',
    'measurement_delay_s': 'Observed delay from prespecified measurement time, seconds.',
}


def write_dictionary(folder):
    tables = {}
    for path in sorted(folder.glob('*.csv')):
        data = pd.read_csv(path)
        tables[path.name] = {col: {'dtype': str(data[col].dtype), 'missing': 'empty CSV cell / JSON null',
                                  'description': DESCRIPTIONS.get(col, col.replace('_', ' ')),
                                  'unit': 'seconds' if col.endswith('_s') else 'milliseconds' if col.endswith('_ms') else None}
                             for col in data}
    write_json(folder / 'data_dictionary.json', {'schema_version': '1.0', 'tables': tables})
