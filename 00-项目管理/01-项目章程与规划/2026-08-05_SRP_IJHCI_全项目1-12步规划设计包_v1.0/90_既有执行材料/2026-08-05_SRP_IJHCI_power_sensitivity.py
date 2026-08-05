#!/usr/bin/env python3
"""
SRP × IJHCI power sensitivity analysis
Document: SRP-IJHCI-PWR-003
Date: 2026-08-05

Purpose
-------
1. Approximate Gate 1 power for participant-level paired non-inferiority
   of protocol_fidelity.
2. Calculate Gate 2 power for a paired superiority test on SCCI.
3. Apply 15% unusable-session reserve and round recruitment to an
   8-person multiple for AB/BA × four Williams sequence cells.

This script is a planning aid. The final preregistered analysis remains a
cycle-level mixed model. After the Level C pilot, update only nuisance
parameters (baseline fidelity, participant heterogeneity, cycle count,
    within-participant correlation / variability), not the observed study
effect, unless the study is explicitly redesigned and re-registered.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def round_up_multiple(value: float, multiple: int = 8) -> int:
    return int(math.ceil(value / multiple) * multiple)


def paired_superiority_power(n: int, dz: float, alpha: float = 0.05) -> float:
    """Two-sided paired t-test power using a noncentral t distribution."""
    df = n - 1
    critical = stats.t.ppf(1 - alpha / 2, df)
    ncp = dz * math.sqrt(n)
    return float(
        stats.nct.sf(critical, df, ncp)
        + stats.nct.cdf(-critical, df, ncp)
    )


def min_n_paired_superiority(
    dz: float,
    target_power: float = 0.90,
    alpha: float = 0.05,
    n_min: int = 16,
    n_max: int = 400,
) -> int:
    for n in range(n_min, n_max + 1):
        if paired_superiority_power(n, dz, alpha) >= target_power:
            return n
    raise RuntimeError("Required N exceeds search range.")


def logit(p: np.ndarray | float) -> np.ndarray | float:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def inv_logit(x: np.ndarray | float) -> np.ndarray | float:
    return 1 / (1 + np.exp(-x))


def simulate_gate1_power(
    n: int,
    p_abstract: float,
    true_difference: float,
    cycles_per_condition: int = 32,
    margin: float = 0.10,
    participant_sd: float = 0.90,
    condition_noise_sd: float = 0.25,
    alpha_one_sided: float = 0.025,
    repetitions: int = 5000,
    seed: int = 20260805,
) -> float:
    """
    Approximate paired non-inferiority power.

    Data-generating model:
    - Shared participant random effect creates within-person correlation.
    - Condition-specific noise allows day-to-day variation.
    - Each condition has a binomial number of valid cycles.
    - Non-inferiority succeeds when the one-sided (1-alpha) lower
      confidence bound for mean(native - abstract) is above -margin.
    """
    rng = np.random.default_rng(seed)
    base_logit = float(logit(p_abstract))
    native_target = np.clip(p_abstract + true_difference, 0.01, 0.99)
    condition_shift = float(logit(native_target) - logit(p_abstract))
    critical = stats.t.ppf(1 - alpha_one_sided, n - 1)

    successes = 0
    for _ in range(repetitions):
        shared = rng.normal(0, participant_sd, n)
        eps_a = rng.normal(0, condition_noise_sd, n)
        eps_n = rng.normal(0, condition_noise_sd, n)

        p_a = inv_logit(base_logit + shared + eps_a)
        p_n = inv_logit(base_logit + condition_shift + shared + eps_n)

        pf_a = rng.binomial(cycles_per_condition, p_a) / cycles_per_condition
        pf_n = rng.binomial(cycles_per_condition, p_n) / cycles_per_condition
        difference = pf_n - pf_a

        standard_error = difference.std(ddof=1) / math.sqrt(n)
        if standard_error == 0:
            lower = difference.mean()
        else:
            lower = difference.mean() - critical * standard_error

        if lower > -margin:
            successes += 1

    return successes / repetitions


def gate1_sensitivity_table(
    target_power: float = 0.90,
    repetitions: int = 3000,
) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    n_grid = list(range(24, 161, 8))

    for p_abstract in (0.75, 0.82, 0.90):
        for true_difference in (0.00, -0.03, -0.05):
            required = None
            achieved = None
            for n in n_grid:
                power = simulate_gate1_power(
                    n=n,
                    p_abstract=p_abstract,
                    true_difference=true_difference,
                    repetitions=repetitions,
                    seed=20260805
                    + n
                    + int(p_abstract * 100)
                    + int((true_difference + 0.10) * 100),
                )
                if required is None and power >= target_power:
                    required = n
                    achieved = power
                    break

            rows.append(
                {
                    "abstract_fidelity": p_abstract,
                    "true_native_minus_abstract": true_difference,
                    "effective_n_for_90pct_power": required or ">160",
                    "power_at_selected_n": achieved if achieved is not None else np.nan,
                }
            )

    return pd.DataFrame(rows)


def gate2_sensitivity_table(
    target_power: float = 0.90,
    alpha: float = 0.05,
    unusable_reserve: float = 0.15,
) -> pd.DataFrame:
    rows: list[dict[str, float | int]] = []
    for dz in (0.30, 0.35, 0.40, 0.45, 0.50):
        effective_n = min_n_paired_superiority(
            dz=dz,
            target_power=target_power,
            alpha=alpha,
        )
        recruited_n = round_up_multiple(
            effective_n / (1 - unusable_reserve),
            multiple=8,
        )
        rows.append(
            {
                "paired_standardized_effect_dz": dz,
                "effective_n_for_90pct_power": effective_n,
                "recruit_n_with_15pct_reserve_rounded_to_8": recruited_n,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory for CSV outputs.",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=3000,
        help="Monte Carlo repetitions per Gate 1 scenario.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    gate1 = gate1_sensitivity_table(repetitions=args.repetitions)
    gate2 = gate2_sensitivity_table()

    gate1_path = output_dir / "SRP_IJHCI_Gate1_noninferiority_sensitivity.csv"
    gate2_path = output_dir / "SRP_IJHCI_Gate2_SCCI_power_sensitivity.csv"
    gate1.to_csv(gate1_path, index=False, encoding="utf-8-sig")
    gate2.to_csv(gate2_path, index=False, encoding="utf-8-sig")

    print("\nGate 1: protocol_fidelity non-inferiority sensitivity")
    print(gate1.to_string(index=False))
    print("\nGate 2: SCCI paired superiority sensitivity")
    print(gate2.to_string(index=False))
    print("\nPlanning decision:")
    print(
        "- Smallest effect of interest for Gate 2: dz = 0.35\n"
        "- Effective paired participants: 88\n"
        "- With 15% unusable reserve and 8-cell balance: recruit 104\n"
        "- Final nuisance parameters must be updated after Level C pilot."
    )
    print(f"\nSaved:\n- {gate1_path}\n- {gate2_path}")


if __name__ == "__main__":
    main()
