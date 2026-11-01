"""Prespecified participant ANCOVA, PMM and finite-sample Rubin inference."""
import math

import numpy as np
import pandas as pd
from scipy.stats import t
import statsmodels.api as sm
from statsmodels.imputation.mice import MICEData

MODEL = 'NA_post ~ B + centered_NA_pre + order_2 + order_3 + order_4'


class NotEstimable(ValueError):
    pass


def interpretation(lower, upper):
    if upper < 0:
        return 'B_LOWER_NA_WHOLE_PACKAGE_ONLY'
    if lower > 0:
        return 'A_LOWER_NA_WHOLE_PACKAGE_ONLY'
    return 'DIRECTION_UNCERTAIN_NOT_EQUIVALENCE'


def fit_primary(data):
    if data[['B', 'NA_pre', 'NA_post', 'order_id']].isna().any().any():
        raise NotEstimable('MODEL_INPUT_MISSING')
    X = np.column_stack([np.ones(len(data)), data.B, data.NA_pre - data.NA_pre.mean(),
                         *(data.order_id.eq(i).astype(float) for i in (2, 3, 4))])
    if len(data) <= X.shape[1] or np.linalg.matrix_rank(X) != X.shape[1]:
        raise NotEstimable('MODEL_NOT_IDENTIFIABLE_NO_COVARIATE_DROPPING')
    if data.NA_post.nunique() < 2:
        raise NotEstimable('OUTCOME_NO_VARIATION_DESCRIBE_FLOOR_OR_CEILING')
    fit = sm.OLS(data.NA_post.to_numpy(float), X).fit(cov_type='HC3', use_t=True)
    beta, se, df = float(fit.params[1]), float(fit.bse[1]), float(fit.df_resid)
    if not math.isfinite(se) or se <= 0:
        raise NotEstimable('HC3_VARIANCE_NOT_ESTIMABLE')
    lo, hi = fit.conf_int(alpha=.05)[1]
    return dict(status='ESTIMATED', method='ANCOVA_HC3', contrast='B_minus_A',
                beta=beta, se=se, df=df, ci_lower=float(lo), ci_upper=float(hi),
                p_value=float(fit.pvalues[1]), n=len(data), imputations=0,
                interpretation=interpretation(lo, hi))


def pool_rubin(fits):
    m = len(fits)
    if m < 2:
        raise NotEstimable('RUBIN_REQUIRES_MULTIPLE_IMPUTATIONS')
    q = float(np.mean([f['beta'] for f in fits]))
    u = float(np.mean([f['se'] ** 2 for f in fits]))
    b = float(np.var([f['beta'] for f in fits], ddof=1))
    total = u + (1 + 1 / m) * b
    if total <= 0 or not np.isfinite(total):
        raise NotEstimable('POOLED_VARIANCE_NOT_ESTIMABLE')
    fraction = (1 + 1 / m) * b / total
    complete_df = min(f['df'] for f in fits)
    old_df = (m - 1) / fraction ** 2 if fraction > 0 else math.inf
    observed_df = (complete_df + 1) / (complete_df + 3) * complete_df * (1 - fraction)
    df = 1 / (1 / old_df + 1 / observed_df)
    se = math.sqrt(total)
    lo, hi = q - t.ppf(.975, df) * se, q + t.ppf(.975, df) * se
    return dict(status='ESTIMATED', method='PMM_RUBIN_HC3_BARNARD_RUBIN_DF',
                contrast='B_minus_A', beta=q, se=se, df=df,
                ci_lower=float(lo), ci_upper=float(hi), p_value=float(2 * t.sf(abs(q / se), df)),
                within_variance=u, between_variance=b, total_variance=total,
                imputations=m, interpretation=interpretation(lo, hi))


def imputed_datasets(data, spec):
    for name in ('NA_pre', 'NA_post'):
        if data.groupby('B')[name].count().eq(0).any():
            raise NotEstimable('ENTIRE_ARM_WITHOUT_OBSERVED_' + name.upper())
    values = data[['NA_pre', 'NA_post', 'B']].astype(float).copy()
    for i in (2, 3, 4):
        values[f'order_{i}'] = data.order_id.eq(i).astype(float)
    for name in spec.get('imputation_predictors', []):
        values[name] = pd.to_numeric(data[name], errors='raise')
    missing = values.isna().any()
    if any(values[col].notna().sum() < spec['pmm_k'] for col in values.columns[missing]):
        raise NotEstimable('INSUFFICIENT_PMM_DONORS')
    for chain in range(spec['imputations']):
        imp = MICEData(values, k_pmm=spec['pmm_k'], rng=spec['seed'] + chain)
        for col in values.columns[missing]:
            imp.set_imputer(col, formula=' + '.join(c for c in values if c != col),
                            k_pmm=spec['pmm_k'])
        imp.update_all(spec['iterations'])
        completed = data.copy()
        for col in values.columns:
            if col in completed:
                completed[col] = imp.data[col].to_numpy()
        yield completed


def analyze_primary(data, spec, completion_sink=None):
    missing = data[['NA_pre', 'NA_post']].isna()
    sensitivity = []
    cc = data.loc[~missing.any(axis=1)]
    try:
        complete_case = fit_primary(cc)
    except NotEstimable as error:
        complete_case = {'status': 'NOT_ESTIMABLE', 'reason': str(error), 'n': len(cc)}
    complete_case['analysis_set'] = 'complete_case_sensitivity'
    sensitivity.append(complete_case)
    if not missing.any().any():
        primary = fit_primary(data)
        primary['analysis_set'] = 'all_randomized_no_missing'
        return primary, sensitivity
    fits = []
    delta_fits = {(a, b): [] for a, b in spec['delta_pairs']}
    post_missing = missing.NA_post
    for chain, completed in enumerate(imputed_datasets(data, spec)):
        fits.append(fit_primary(completed))
        if completion_sink is not None:
            completion_sink(chain, completed)
        for (a, b), results in delta_fits.items():
            shifted = completed.copy()
            mask_a = post_missing & shifted.B.eq(0)
            mask_b = post_missing & shifted.B.eq(1)
            shifted.loc[mask_a, 'NA_post'] = (shifted.loc[mask_a, 'NA_post'] + a).clip(10, 50)
            shifted.loc[mask_b, 'NA_post'] = (shifted.loc[mask_b, 'NA_post'] + b).clip(10, 50)
            results.append(fit_primary(shifted))
    primary = pool_rubin(fits)
    primary.update(n=len(data), analysis_set='all_randomized_PMM',
                   missing_pre=int(missing.NA_pre.sum()), missing_post=int(missing.NA_post.sum()))
    for (a, b), fits in delta_fits.items():
        row = pool_rubin(fits)
        row.update(analysis_set='MNAR_delta_sensitivity', delta_A=a, delta_B=b, n=len(data))
        sensitivity.append(row)
    return primary, sensitivity
