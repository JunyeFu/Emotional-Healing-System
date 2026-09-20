"""Deterministic bounded Monte Carlo power grid for U12-04 PANAS primary result.

Primary model (protocol_authority_v1.2.json):
    NA_post ~ cue_mode + centered_NA_pre + randomization_strata
    contrast = native_minus_abstract, lower_is_better = true
    variance = HC3, test = two_sided, alpha = 0.05

This script computes a power grid over total N x Cohen's d (native vs abstract)
for two analysis sets:
  - PRIMARY_CONSERVATIVE : all randomized; missing NA_post carried forward
    to pre (no change) -> conservative under lower_is_better.
  - OBSERVED_CASE        : participants with observed NA_post only.

N and effect size are NOT frozen; the grid is a reference input for the
future formal sample-size freeze.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

ANALYSIS_SETS = ("PRIMARY_CONSERVATIVE", "OBSERVED_CASE")
DEFAULT_N_GRID = (48, 96, 144, 192, 240)
DEFAULT_EFFECT_GRID = (0.2, 0.3, 0.4, 0.5)
DEFAULT_SEED = 20260906
DEFAULT_REPLICATIONS = 1000

try:  # scipy improves the t-test critical values; fallback to normal approx.
    from scipy import stats as _stats  # type: ignore

    def _two_sided_p(t_value: float, df: float) -> float:
        return float(2.0 * (1.0 - _stats.t.cdf(abs(t_value), df=df)))

    T_DISTRIBUTION = True
except Exception:  # pragma: no cover - fallback path
    def _two_sided_p(t_value: float, df: float) -> float:  # noqa: ARG001
        return float(2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(t_value) / math.sqrt(2.0)))))

    T_DISTRIBUTION = False


def _ols_hc3(X: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """OLS coefficients with HC3 robust standard errors."""
    n, p = X.shape
    xtx_inv = np.linalg.inv(X.T @ X)
    beta = xtx_inv @ (X.T @ y)
    resid = y - X @ beta
    hat = np.einsum("ij,jk,ik->i", X, xtx_inv, X)
    denom = np.maximum(1.0 - hat, 1e-12)
    meat = resid * resid / (denom * denom)
    cov = xtx_inv @ (X.T * meat) @ X @ xtx_inv
    se = np.sqrt(np.diag(cov))
    return {"beta": float(beta[1]), "se": float(se[1])}


def _generate_participants(
    rng: np.random.Generator, n_total: int, effect_d: float, rho: float = 0.5
) -> dict[str, np.ndarray]:
    per_condition = n_total // 2
    n = per_condition * 2
    cue = np.concatenate([np.zeros(per_condition), np.ones(per_condition)])
    rng.shuffle(cue)
    strata = rng.integers(0, 2, size=n).astype(float)
    pre = rng.normal(0.0, 1.0, size=n)
    noise = rng.normal(0.0, 1.0, size=n)
    effect = -effect_d * cue  # native lower on NA (lower_is_better)
    post = 3.0 + effect + rho * pre + 0.1 * strata + noise
    native = cue.astype(bool)
    observed = rng.random(size=n) < np.where(native, 0.98, 0.99)
    return {
        "cue": cue,
        "strata": strata,
        "pre": pre,
        "post": post,
        "observed": observed,
    }


def _replicate(
    rng: np.random.Generator, n_total: int, effect_d: float
) -> dict[str, dict[str, float]]:
    data = _generate_participants(rng, n_total, effect_d)
    n = data["cue"].shape[0]

    # OBSERVED_CASE: keep participants with observed NA_post
    keep_o = data["observed"]
    X_o = np.column_stack(
        [np.ones(int(keep_o.sum())), data["cue"][keep_o],
         data["pre"][keep_o], data["strata"][keep_o]]
    )
    y_o = data["post"][keep_o]

    # PRIMARY_CONSERVATIVE: all randomized; missing post carried forward to pre
    post_c = np.where(data["observed"], data["post"], data["pre"])
    X_c = np.column_stack([np.ones(n), data["cue"], data["pre"], data["strata"]])
    y_c = post_c

    out: dict[str, dict[str, float]] = {}
    if int(keep_o.sum()) >= 4:
        out["OBSERVED_CASE"] = _ols_hc3(X_o, y_o)
    else:
        out["OBSERVED_CASE"] = {"beta": math.nan, "se": math.nan}
    out["PRIMARY_CONSERVATIVE"] = _ols_hc3(X_c, y_c)
    return out


def _cell_power(
    seed: int, replications: int, n_total: int, effect_d: float
) -> dict[str, object]:
    rng = np.random.default_rng(seed)
    per_set: dict[str, list[float]] = {s: [] for s in ANALYSIS_SETS}
    estimates: dict[str, list[float]] = {s: [] for s in ANALYSIS_SETS}
    ses: dict[str, list[float]] = {s: [] for s in ANALYSIS_SETS}

    for _ in range(replications):
        results = _replicate(rng, n_total, effect_d)
        for analysis_set in ANALYSIS_SETS:
            beta = results[analysis_set]["beta"]
            se = results[analysis_set]["se"]
            if math.isnan(beta) or math.isnan(se) or se <= 0.0:
                continue
            t_value = beta / se
            p_value = _two_sided_p(t_value, df=max(n_total - 4, 1))
            per_set[analysis_set].append(1.0 if p_value < 0.05 else 0.0)
            estimates[analysis_set].append(beta)
            ses[analysis_set].append(se)

    cell: dict[str, object] = {"n_total": n_total, "effect_d": effect_d}
    for analysis_set in ANALYSIS_SETS:
        k = len(per_set[analysis_set])
        power = sum(per_set[analysis_set]) / replications if k else math.nan
        mc_se = math.sqrt(power * (1.0 - power) / replications) if k else math.nan
        cell[analysis_set] = {
            "power": power,
            "mc_standard_error": mc_se,
            "mean_beta_estimate": float(np.mean(estimates[analysis_set])) if k else math.nan,
            "mean_hc3_se": float(np.mean(ses[analysis_set])) if k else math.nan,
            "valid_replications": k,
        }
    return cell


def run_power_grid(
    *,
    seed: int = DEFAULT_SEED,
    replications: int = DEFAULT_REPLICATIONS,
    n_grid: tuple[int, ...] = DEFAULT_N_GRID,
    effect_grid: tuple[float, ...] = DEFAULT_EFFECT_GRID,
) -> dict[str, object]:
    if replications < 100:
        raise ValueError("REPLICATIONS_TOO_SMALL")
    cells = [
        _cell_power(seed + 1000 * ni + ei, replications, n_total, effect_d)
        for ni, n_total in enumerate(n_grid)
        for ei, effect_d in enumerate(effect_grid)
    ]
    return {
        "schema_version": "1.0",
        "evidence_class": "DESIGN_AND_SYNTHETIC_ONLY",
        "model": "NA_post ~ cue_mode + centered_NA_pre + randomization_strata",
        "contrast": "native_minus_abstract",
        "lower_is_better": True,
        "variance": "HC3",
        "test": "two_sided",
        "alpha": 0.05,
        "seed": seed,
        "replications": replications,
        "analysis_sets": list(ANALYSIS_SETS),
        "target_power": 0.9,
        "n_grid": list(n_grid),
        "effect_grid": list(effect_grid),
        "t_distribution_used": T_DISTRIBUTION,
        "cells": cells,
        "frozen": {"n_frozen": False, "effect_frozen": False},
        "limitations": [
            "SYNTHETIC_PARAMETERS_ARE_NOT_REAL_CALIBRATION",
            "FORMAL_N_AND_MARGIN_NOT_FROZEN",
            "OLD_ANCHORS_ARE_NOT_FINAL_POWER",
            "EQUIVALENCE_POWER_NOT_CLAIMED",
            "MISSINGNESS_POLICY_PRE_FREEZE",
        ],
    }


def _fmt_power(value: float) -> str:
    return "    --" if math.isnan(value) else f"{value:6.3f}"


def render_power_report(report: dict[str, object]) -> str:
    lines: list[str] = []
    lines.append("# U12-04 主结果功效网格（合成参考，非冻结）")
    lines.append("")
    lines.append("> evidence_class: DESIGN_AND_SYNTHETIC_ONLY — 参数为合成参考，不构成正式样本量声明。")
    lines.append("")
    lines.append("## 主模型")
    lines.append("")
    lines.append("`NA_post ~ cue_mode + centered_NA_pre + randomization_strata`")
    lines.append("")
    lines.append("- 对比：native_minus_abstract（lower_is_better）")
    lines.append("- 方差：HC3 稳健；检验：双侧；α = 0.05")
    lines.append("- 分析集：PRIMARY_CONSERVATIVE（all_randomized + 缺失 carry-forward）/ OBSERVED_CASE（仅观测到 NA_post）")
    lines.append(f"- seed = {report['seed']}；replications = {report['replications']}；t 分布临界值 = {report['t_distribution_used']}")
    lines.append("")
    lines.append("## 功效矩阵（拒绝率）")
    lines.append("")
    lines.append("| N | d | PRIMARY_CONSERVATIVE | OBSERVED_CASE |")
    lines.append("|---|---|---|---|")
    for cell in report["cells"]:  # type: ignore[union-attr]
        lines.append(
            f"| {cell['n_total']} | {cell['effect_d']:g} | "
            f"{_fmt_power(cell['PRIMARY_CONSERVATIVE']['power'])} | "
            f"{_fmt_power(cell['OBSERVED_CASE']['power'])} |"
        )
    lines.append("")
    lines.append("## 解读边界")
    lines.append("")
    for limitation in report["limitations"]:  # type: ignore[union-attr]
        lines.append(f"- {limitation}")
    lines.append("")
    lines.append("本网格仅作为正式样本量冻结的参考；formal N 与最小重要差值须在真实冻结时确定。")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="U12-04 PANAS power grid (synthetic)")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--replications", type=int, default=DEFAULT_REPLICATIONS)
    parser.add_argument("--n-total", type=int, default=0, help="single point N override")
    parser.add_argument("--effect-d", type=float, default=0.0, help="single point d override")
    args = parser.parse_args()

    n_grid = (args.n_total,) if args.n_total else DEFAULT_N_GRID
    effect_grid = (args.effect_d,) if args.effect_d else DEFAULT_EFFECT_GRID
    report = run_power_grid(
        seed=args.seed,
        replications=args.replications,
        n_grid=n_grid,  # type: ignore[arg-type]
        effect_grid=effect_grid,  # type: ignore[arg-type]
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    grid_path = args.output_dir / "power_grid.json"
    report_path = args.output_dir / "power_report.md"
    grid_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(render_power_report(report), encoding="utf-8")
    print(f"POWER_GRID_OK: {grid_path.name}, cells={len(report['cells'])}, replications={args.replications}")


if __name__ == "__main__":
    main()
