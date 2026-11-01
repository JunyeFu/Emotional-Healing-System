"""Observable analysis contracts; no hardware or real participant acceptance."""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from srp_analysis.statistics import fit_primary, pool_rubin, analyze_primary, NotEstimable
from srp_analysis.prepare import score_scale


def test_panas_exact_key_and_missingness():
    rows = pd.DataFrame({'item_id': [f'N{i}' for i in range(10)], 'value': [3] * 10})
    assert score_scale(rows, [f'N{i}' for i in range(10)]) == 30
    assert score_scale(rows.iloc[:-1], [f'N{i}' for i in range(10)]) is None


def test_hc3_matches_independent_statsmodels_call():
    rng = np.random.default_rng(14)
    data = pd.DataFrame({'B': np.tile([0, 1], 24), 'NA_pre': rng.integers(12, 36, 48),
                         'order_id': np.tile(np.repeat([1, 2, 3, 4], 2), 6)})
    data['NA_post'] = 8 + .5 * data.NA_pre - 4 * data.B + rng.normal(0, 2, 48)
    result = fit_primary(data)
    X = np.column_stack([np.ones(48), data.B, data.NA_pre - data.NA_pre.mean(),
                         *(data.order_id.eq(i).astype(float) for i in (2, 3, 4))])
    expected = sm.OLS(data.NA_post, X).fit(cov_type='HC3', use_t=True)
    assert result['beta'] == pytest.approx(expected.params.iloc[1])
    assert result['se'] == pytest.approx(expected.bse.iloc[1])
    assert result['beta'] < 0


def test_rubin_known_variance_and_no_fake_equivalence():
    result = pool_rubin([{'beta': 1., 'se': 2., 'df': 24},
                         {'beta': 3., 'se': 2., 'df': 24}])
    assert result['beta'] == 2
    assert result['total_variance'] == pytest.approx(7.)
    assert result['interpretation'] == 'DIRECTION_UNCERTAIN_NOT_EQUIVALENCE'


def test_entire_arm_missing_is_not_identified_by_imputation():
    from srp_analysis.demo import candidate_spec
    data = pd.DataFrame({'B': [0, 1] * 15, 'order_id': 1 + (np.arange(30) // 2) % 4,
                         'NA_pre': np.arange(30) % 12 + 18, 'NA_post': np.arange(30) % 12 + 20.})
    data.loc[data.B.eq(1), 'NA_post'] = np.nan
    with pytest.raises(NotEstimable, match='ENTIRE_ARM'):
        analyze_primary(data, candidate_spec())


def test_all_at_floor_does_not_report_numerical_noise_as_precision():
    data = pd.DataFrame({'B': np.arange(40) % 2, 'order_id': 1 + (np.arange(40) // 2) % 4,
                         'NA_pre': np.arange(40) % 12 + 18, 'NA_post': [10.] * 40})
    with pytest.raises(NotEstimable, match='OUTCOME_NO_VARIATION'):
        fit_primary(data)
