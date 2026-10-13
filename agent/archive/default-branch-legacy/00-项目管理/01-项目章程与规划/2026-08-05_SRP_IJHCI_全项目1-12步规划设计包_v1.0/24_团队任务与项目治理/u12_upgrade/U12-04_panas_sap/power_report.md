# U12-04 主结果功效网格（合成参考，非冻结）

> evidence_class: DESIGN_AND_SYNTHETIC_ONLY — 参数为合成参考，不构成正式样本量声明。

## 主模型

`NA_post ~ cue_mode + centered_NA_pre + randomization_strata`

- 对比：native_minus_abstract（lower_is_better）
- 方差：HC3 稳健；检验：双侧；α = 0.05
- 分析集：PRIMARY_CONSERVATIVE（all_randomized + 缺失 carry-forward）/ OBSERVED_CASE（仅观测到 NA_post）
- seed = 20260906；replications = 1000；t 分布临界值 = True

## 功效矩阵（拒绝率）

| N | d | PRIMARY_CONSERVATIVE | OBSERVED_CASE |
|---|---|---|---|
| 48 | 0.2 |  0.079 |  0.072 |
| 48 | 0.3 |  0.161 |  0.146 |
| 48 | 0.4 |  0.242 |  0.239 |
| 48 | 0.5 |  0.330 |  0.325 |
| 96 | 0.2 |  0.177 |  0.159 |
| 96 | 0.3 |  0.293 |  0.289 |
| 96 | 0.4 |  0.478 |  0.479 |
| 96 | 0.5 |  0.652 |  0.650 |
| 144 | 0.2 |  0.228 |  0.206 |
| 144 | 0.3 |  0.438 |  0.401 |
| 144 | 0.4 |  0.664 |  0.651 |
| 144 | 0.5 |  0.843 |  0.840 |
| 192 | 0.2 |  0.294 |  0.253 |
| 192 | 0.3 |  0.586 |  0.550 |
| 192 | 0.4 |  0.785 |  0.769 |
| 192 | 0.5 |  0.899 |  0.910 |
| 240 | 0.2 |  0.365 |  0.311 |
| 240 | 0.3 |  0.651 |  0.611 |
| 240 | 0.4 |  0.868 |  0.851 |
| 240 | 0.5 |  0.961 |  0.964 |

## 解读边界

- SYNTHETIC_PARAMETERS_ARE_NOT_REAL_CALIBRATION
- FORMAL_N_AND_MARGIN_NOT_FROZEN
- OLD_ANCHORS_ARE_NOT_FINAL_POWER
- EQUIVALENCE_POWER_NOT_CLAIMED
- MISSINGNESS_POLICY_PRE_FREEZE

本网格仅作为正式样本量冻结的参考；formal N 与最小重要差值须在真实冻结时确定。
