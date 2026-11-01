"""Bounded PANAS Monte Carlo precision scenarios, never a formal N freeze."""
import math

import numpy as np
import pandas as pd

from .demo import bounded_scores, candidate_spec
from .io import save_frame, write_json
from .statistics import NotEstimable, analyze_primary


def run_power_grid(*, seed=20261019, replications=10, n_grid=(30, 40, 48, 60),
                   effect_grid=(-3., 0., 3.), missing_rates=(0., .15), floor=False):
    if replications < 2:
        raise ValueError('MONTE_CARLO_REQUIRES_AT_LEAST_TWO_REPLICATIONS')
    if any(not np.isfinite(v) for v in effect_grid) or any(not 0 <= v < 1 for v in missing_rates):
        raise ValueError('INVALID_EFFECT_OR_MISSINGNESS_GRID')
    spec = candidate_spec()
    # MNAR is reported in the analysis demo; precision uses the identical PMM/HC3 primary only.
    spec['delta_pairs'] = []
    rows = []
    for n in n_grid:
        if n < 12 or n % 2:
            raise ValueError('TOTAL_N_REQUIRES_EVEN_INTEGER_AT_LEAST_12')
        for effect in effect_grid:
            for missing_rate in missing_rates:
                results = []
                failures = 0
                for replicate in range(replications):
                    rng = np.random.default_rng(np.random.SeedSequence([seed, n, int((effect + 50) * 100),
                                                                         int(missing_rate * 10000), replicate]))
                    pre, post = bounded_scores(rng, n, effect, floor)
                    frame = pd.DataFrame(dict(B=np.arange(n) % 2, order_id=1 + (np.arange(n) // 2) % 4,
                                              NA_pre=pre, NA_post=post))
                    frame.loc[rng.random(n) < missing_rate, 'NA_post'] = np.nan
                    try:
                        result, _ = analyze_primary(frame, spec)
                        results.append(result)
                    except NotEstimable:
                        failures += 1
                rejected = sum(r['p_value'] < .05 for r in results)
                probability = rejected / replications
                rows.append(dict(n_total=n, effect_raw_points=effect, missing_post_rate=missing_rate,
                                 floor_scenario=floor, replications=replications,
                                 valid_replications=len(results), failed_replications=failures,
                                 rejection_probability=probability,
                                 mc_se=math.sqrt(probability * (1 - probability) / replications),
                                 mean_ci_halfwidth=float(np.mean([(r['ci_upper'] - r['ci_lower']) / 2 for r in results])) if results else None,
                                 mean_beta=float(np.mean([r['beta'] for r in results])) if results else None))
                print(f'POWER N={n} shift={effect:g} missing={missing_rate:g}: {len(results)}/{replications} estimable', flush=True)
    return dict(evidence_class='SYNTHETIC', formal_n_frozen=False,
                model='NA_post ~ B + centered_NA_pre + order_2 + order_3 + order_4',
                pmm_k=5, imputations=50, iterations=20, seed=seed,
                generator='BOUNDED_INTEGER_PANAS_SUM_10_TO_50',
                note='Nominal latent raw-point shifts are attenuated by bounds. Null rejection is type-I error, not power. Low-budget demo has wide Monte Carlo uncertainty. Not real calibration or final N.',
                cells=rows)


def write_power(out, *, replications=10, floor=False):
    result = run_power_grid(replications=replications, floor=floor)
    write_json(out / 'power_grid.json', result)
    save_frame(out / 'power_grid.csv', pd.DataFrame(result['cells']))
    from .report import plt
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.5))
    table = pd.DataFrame(result['cells'])
    for (effect, missing), group in table.groupby(['effect_raw_points', 'missing_post_rate']):
        label = f'delta={effect:g}, missing={missing:g}'
        axes[0].plot(group.n_total, group.rejection_probability, marker='o', label=label)
        axes[1].plot(group.n_total, group.mean_ci_halfwidth, marker='o', label=label)
    axes[0].set(xlabel='Total independent participants', ylabel='Rejection probability (null = type-I error)', ylim=(0, 1))
    axes[1].set(xlabel='Total independent participants', ylabel='Mean 95% CI half-width (NA points)')
    axes[0].legend(fontsize=6)
    fig.suptitle(f'SYNTHETIC | precision scenarios; {replications} replicates/cell, not final N')
    fig.tight_layout()
    fig.savefig(out / 'power_precision.png', dpi=160)
    fig.savefig(out / 'power_precision.pdf', metadata={'CreationDate': None, 'ModDate': None})
    plt.close(fig)
    return result
